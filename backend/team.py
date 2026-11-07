"""The Campus Customs agent team: Boss, Inventory, Accounting, Facilities, Customer Service.

How the team works (owner's design):
- Every new ticket goes to the Boss first. The Boss decides who works on it.
- Money (invoices, bills, payments, margins, cash) goes to Accounting; stock, shortfalls,
  vendors and restock orders go to Inventory; leases and rent go to Facilities; customer
  questions and messages go to Customer Service.
- Full connectivity: any agent can hand a task straight to any other agent with the
  `delegate` tool. Every result comes back up to the Boss for final inspection.
- The Boss verifies payments and drafts. Payments then wait for the store manager, who
  approves them on the board (a human-only route). No agent can move cash or send a message.

Every agent uses ONLY gpt-6-luna through Portkey, and every shop fact comes from the MCP
server (mcp_server/server.py) over data/campus_customs_new.db.

Run one ticket from the project root:  python backend/team.py 101
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext, UsageLimitExceeded
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from models import (  # noqa: E402
    AGENT_NAMES, MAX_HANDOFF_DEPTH, MAX_HANDOFFS_PER_TICKET, MAX_OUTPUT_TOKENS_PER_REPLY,
    MAX_REQUESTS_PER_TICKET, MAX_TOKENS_PER_TICKET, MODEL_NAME, PORTKEY_BASE_URL,
    TOOL_RESULT_CHARS_IN_AUDIT, AgentName, AgentReport, BossDecision, TeamDeps, TeamRun,
)

PROMPTS_DIR = BACKEND_DIR / "prompts"
MCP_SERVER = PROJECT_ROOT / "mcp_server" / "server.py"
AUDIT_PATH = PROJECT_ROOT / "output" / "audit_trail.json"

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env")

# Which MCP tools each agent may call. Anything not listed is hidden from that agent.
TOOLS_FOR: dict[str, set[str]] = {
    "boss": {"list_tickets", "get_ticket", "check_stock", "get_invoice_status", "get_rent_status",
             "get_cash_balance", "list_pending_approvals", "list_drafts", "verify_payment",
             "approve_draft", "set_ticket_status"},
    "inventory": {"get_ticket", "check_stock", "get_vendors", "get_invoice_status", "quote_order",
                  "place_restock_order", "record_shipment"},
    "accounting": {"get_ticket", "check_stock", "quote_order", "get_invoice_status", "list_open_invoices",
                   "get_rent_status", "get_cash_balance", "list_pending_approvals", "prepare_payment",
                   "save_draft", "list_drafts"},
    "facilities": {"get_ticket", "get_rent_status", "get_cash_balance", "list_pending_approvals",
                   "save_draft", "list_drafts"},
    "customer_service": {"get_ticket", "check_stock", "get_vendors", "quote_order", "save_draft",
                         "list_drafts"},
}


class AgentNotConfigured(RuntimeError):
    pass


# ------------------------------------------------------------------ audit trail (append-only)

_audit_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def append_audit(entries: list[dict]) -> None:
    """Append entries to output/audit_trail.json. Never wipes earlier runs."""
    if not entries:
        return
    with _audit_lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing: list = []
        if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size:
            try:
                existing = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                # Never lose old records: keep the unreadable file and start a new list.
                AUDIT_PATH.rename(AUDIT_PATH.with_suffix(f".corrupt-{int(time.time())}.json"))
        existing.extend(entries)
        tmp = AUDIT_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(existing, indent=2, default=str), encoding="utf-8")
        tmp.replace(AUDIT_PATH)


def _short(value, limit: int = TOOL_RESULT_CHARS_IN_AUDIT) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= limit else text[:limit] + " ...[truncated]"


def _event(run: TeamRun, agent: str, kind: str, **data) -> dict:
    ev = {"run_id": run.run_id, "ticket_id": run.ticket_id, "time": _now(), "agent": agent,
          "kind": kind, "step": len(run.events) + 1, **data}
    run.events.append(ev)
    return ev


async def audit_mcp_call(ctx: RunContext[TeamDeps], call_tool, name: str, tool_args: dict):
    """Runs around EVERY MCP tool call, so the audit trail logs each step as it happens."""
    deps = ctx.deps
    append_audit([_event(deps.run, deps.agent, "tool_call", tool=name, args=tool_args, depth=deps.depth)])
    try:
        result = await call_tool(name, tool_args)
    except Exception as exc:
        append_audit([_event(deps.run, deps.agent, "tool_error", tool=name,
                             error=f"{type(exc).__name__}: {exc}", depth=deps.depth)])
        raise
    append_audit([_event(deps.run, deps.agent, "tool_result", tool=name, result=_short(result), depth=deps.depth)])
    return result


def record_agent_text(deps: TeamDeps, messages) -> list[dict]:
    """Anything an agent said in plain text during its run (tool steps are logged live)."""
    out = []
    for msg in messages:
        if isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, TextPart) and part.content.strip():
                    ev = _event(deps.run, deps.agent, "said", text=_short(part.content), depth=deps.depth)
                    if getattr(msg, "timestamp", None):  # when the agent actually said it
                        ev["time"] = msg.timestamp.astimezone(timezone.utc).isoformat(timespec="milliseconds")
                    out.append(ev)
    return out


# ------------------------------------------------------------------ model, tools, agents

def build_model() -> OpenAIResponsesModel:
    api_key = os.environ.get("PORTKEY_API_KEY", "").strip()
    if not api_key:
        raise AgentNotConfigured("PORTKEY_API_KEY is missing. Put it in hw5/.env (see .env.example).")
    client = AsyncOpenAI(api_key="portkey", base_url=PORTKEY_BASE_URL,
                         default_headers={"x-portkey-api-key": api_key})
    # Fixed on purpose: every agent uses gpt-6-luna and nothing else.
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


@lru_cache(maxsize=1)
def shop_mcp() -> MCPToolset:
    """One connection to the Campus Customs MCP server, shared by all five agents."""
    transport = PythonStdioTransport(MCP_SERVER, python_cmd=sys.executable, cwd=str(PROJECT_ROOT))
    return MCPToolset(Client(transport), id="campus-customs", process_tool_call=audit_mcp_call)


def _tools_for(agent_name: str):
    allowed = TOOLS_FOR[agent_name]
    return shop_mcp().filtered(lambda ctx, tool_def: tool_def.name in allowed)


async def delegate(ctx: RunContext[TeamDeps], to_agent: AgentName, task: str) -> str:
    """Hand a task to another agent (boss, inventory, accounting, facilities or customer_service).
    Say exactly what you need, with the ticket number and the facts you already have.
    Returns that agent's report. Any agent can hand work to any other agent."""
    deps, run = ctx.deps, ctx.deps.run
    refusal = None
    if to_agent == deps.agent:
        refusal = "You cannot hand a task to yourself."
    elif to_agent not in AGENT_NAMES:
        refusal = f"Unknown agent '{to_agent}'. Use one of: {', '.join(AGENT_NAMES)}."
    elif deps.depth >= MAX_HANDOFF_DEPTH:
        refusal = (f"Handoff refused: the chain {' -> '.join(deps.chain)} is already {MAX_HANDOFF_DEPTH} deep. "
                   "Finish with what you have and report back.")
    elif to_agent in deps.chain:
        refusal = (f"Handoff refused: {to_agent} is already working on this request above you "
                   f"({' -> '.join(deps.chain)}). Report back instead.")
    elif run.handoffs >= MAX_HANDOFFS_PER_TICKET:
        refusal = f"Handoff refused: this ticket already used {MAX_HANDOFFS_PER_TICKET} handoffs. Report back."
    if refusal:
        append_audit([_event(run, deps.agent, "handoff_refused", to=to_agent, reason=refusal, depth=deps.depth)])
        return refusal
    key = (deps.agent, to_agent, " ".join(task.lower().split()))
    if key in run.finished_handoffs:
        append_audit([_event(run, deps.agent, "handoff_repeat_skipped", to=to_agent, depth=deps.depth)])
        if not run.finished_handoffs[key]:
            return f"{to_agent} is already working on this exact task. Wait for that report; do not send it twice."
        return ("You already handed this exact task to " + to_agent + " and it reported back. "
                "Here is that report again; do not hand it off again:\n" + run.finished_handoffs[key])
    run.finished_handoffs[key] = ""  # in progress
    run.handoffs += 1
    append_audit([_event(run, deps.agent, "handoff", to=to_agent, task=_short(task, 600), depth=deps.depth)])
    child = TeamDeps(run=run, agent=to_agent, depth=deps.depth + 1, chain=deps.chain + (to_agent,))
    result = await team()[to_agent].run(task, deps=child, usage=ctx.usage, usage_limits=_limits())
    append_audit(record_agent_text(child, result.new_messages()))
    report = result.output
    append_audit([_event(run, to_agent, "report", to=deps.agent,
                         report=report.model_dump() if hasattr(report, "model_dump") else str(report),
                         depth=child.depth)])
    text = report.model_dump_json() if hasattr(report, "model_dump_json") else str(report)
    run.finished_handoffs[key] = text
    return text


def _limits() -> UsageLimits:
    return UsageLimits(request_limit=MAX_REQUESTS_PER_TICKET, total_tokens_limit=MAX_TOKENS_PER_TICKET)


def _make_agent(name: str, model) -> Agent:
    output_type = BossDecision if name == "boss" else AgentReport
    agent = Agent(
        model,
        name=name,
        deps_type=TeamDeps,
        output_type=output_type,
        instructions=(PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8"),
        toolsets=[_tools_for(name)],
        tools=[delegate],
        retries=2,
        model_settings={"max_tokens": MAX_OUTPUT_TOKENS_PER_REPLY},
    )

    @agent.instructions
    def where_am_i(ctx: RunContext[TeamDeps]) -> str:
        d = ctx.deps
        return (f"## This run\n- You are the **{d.agent}** agent. Ticket: **{d.run.ticket_id}**.\n"
                f"- Handoff chain so far: {' -> '.join(d.chain)} (depth {d.depth} of {MAX_HANDOFF_DEPTH}).\n"
                f"- Handoffs used on this ticket: {d.run.handoffs} of {MAX_HANDOFFS_PER_TICKET}.\n"
                f"- When you call a tool that asks for your name (prepared_by, ordered_by, shipped_by, author), "
                f"use '{d.agent}'.")

    return agent


@lru_cache(maxsize=1)
def team() -> dict[str, Agent]:
    model = build_model()
    return {name: _make_agent(name, model) for name in AGENT_NAMES}


# ------------------------------------------------------------------ running a ticket

def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


async def _run_boss(ticket_id: int, prompt: str, run_id: str | None = None) -> dict:
    run = TeamRun(run_id=run_id or new_run_id(), ticket_id=ticket_id)
    deps = TeamDeps(run=run, agent="boss", depth=0, chain=("boss",))
    append_audit([_event(run, "boss", "ticket_started", prompt=_short(prompt, 600), model=MODEL_NAME)])
    status, decision, error = "finished", None, None
    async with shop_mcp():  # keep one MCP connection open for the whole ticket
        try:
            result = await team()["boss"].run(prompt, deps=deps, usage_limits=_limits())
            append_audit(record_agent_text(deps, result.new_messages()))
            decision = result.output.model_dump()
            usage = result.usage
        except UsageLimitExceeded as exc:
            status, error, usage = "stopped_at_limit", str(exc), None
        except Exception as exc:  # recorded, then re-raised for the caller
            append_audit([_event(run, "boss", "error", error=f"{type(exc).__name__}: {exc}")])
            raise
    append_audit([_event(run, "boss", "ticket_finished", status=status, decision=decision, error=error,
                         requests=getattr(usage, "requests", None),
                         total_tokens=getattr(usage, "total_tokens", None), handoffs=run.handoffs)])
    return {"run_id": run.run_id, "ticket_id": ticket_id, "status": status, "decision": decision,
            "error": error, "handoffs": run.handoffs, "events": run.events}


async def run_ticket(ticket_id: int, run_id: str | None = None) -> dict:
    """Run the whole team on one ticket, starting with the Boss."""
    prompt = (f"New ticket {ticket_id} just arrived at the desk. Read it with get_ticket, decide who should "
              "work on it, hand off the work, inspect every result that comes back, and give your final decision.")
    return await _run_boss(ticket_id, prompt, run_id)


async def final_check(ticket_id: int, run_id: str | None = None, note: str = "") -> dict:
    """After the store manager decides a payment on the board, the Boss re-inspects the ticket."""
    prompt = (f"The store manager has just decided a payment for ticket {ticket_id}. {note} Do your final "
              "inspection: check list_pending_approvals, the invoice or rent status and the cash balance, confirm "
              "every piece of the ticket is done, and set the ticket status. Hand off only if something is missing.")
    return await _run_boss(ticket_id, prompt, run_id)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python backend/team.py <ticket_id>")
    out = asyncio.run(run_ticket(int(sys.argv[1])))
    print(json.dumps({k: v for k, v in out.items() if k != "events"}, indent=2, default=str))
