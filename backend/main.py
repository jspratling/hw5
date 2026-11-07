"""Campus Customs backend (FastAPI): the routes the React board calls.

Start it from the backend/ folder:
    uvicorn main:app --reload --port 8000

Routes (all under /api):
  GET  /api/tickets                     the three tickets and their status
  POST /api/tickets/{id}/run            run the agent team on a ticket (Boss first)
  GET  /api/runs/{run_id}               a run's status and the Boss's decision
  GET  /api/events                      recent agent events: who said what, which tools they used
  GET  /api/approvals                   payments waiting for the store manager (and decided ones)
  POST /api/approvals/{id}/decide       the store manager (David) approves or rejects a payment
  GET  /api/cash                        checking balance from cash_accounts
  GET  /api/drafts                      drafted messages and bills (never sent)
  POST /api/reset                       copy the original database over the working copy

Only the approve route moves money, and only for the store manager. Agents can only
prepare payments. After an approval, the Boss's final check runs automatically.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(PROJECT_ROOT / "mcp_server"))

import shop_db  # noqa: E402  (human-only actions: decide_payment, reset_database)
import team  # noqa: E402
from models import MODEL_NAME  # noqa: E402

# The store manager allowed to approve or reject payments (owner's choice: David).
STORE_MANAGER = os.environ.get("STORE_MANAGER", "David").strip()

app = FastAPI(title="Campus Customs Desk", version="1.0")

# Let the React board (Vite, port 5173) call this backend from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# One team run at a time, so two runs never change the shop at once.
_run_lock = asyncio.Lock()
RUNS: dict[str, dict] = {}
_tasks: set[asyncio.Task] = set()


def _start(coro_factory, ticket_id: int, kind: str) -> dict:
    run_id = team.new_run_id()
    RUNS[run_id] = {"run_id": run_id, "ticket_id": ticket_id, "kind": kind, "status": "running",
                    "decision": None, "error": None}

    async def worker():
        async with _run_lock:
            try:
                out = await coro_factory(run_id)
                RUNS[run_id].update(status=out["status"], decision=out["decision"], error=out["error"],
                                    handoffs=out["handoffs"])
            except Exception as exc:  # shown on the board; details are in the audit trail
                RUNS[run_id].update(status="error", error=f"{type(exc).__name__}: {exc}")

    task = asyncio.create_task(worker())
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return RUNS[run_id]


def _busy() -> bool:
    return _run_lock.locked() or any(r["status"] == "running" for r in RUNS.values())


# ------------------------------------------------------------------ tickets and runs

@app.get("/api/tickets")
def list_tickets():
    """The three tickets and whether each is open, waiting_on_approval, held or resolved."""
    data = shop_db.list_tickets()
    for t in data["tickets"]:
        t["resolved"] = t["status"] == "resolved"
    data["running"] = [r for r in RUNS.values() if r["status"] == "running"]
    return data


@app.post("/api/tickets/{ticket_id}/run")
async def run_ticket(ticket_id: int):
    """Run the agent team on one ticket. Returns at once with a run id; watch /api/events."""
    if not shop_db.get_ticket(ticket_id)["found"]:
        raise HTTPException(404, f"No ticket {ticket_id}.")
    if _busy():
        raise HTTPException(409, "The team is already working on a ticket. Wait for it to finish.")
    try:
        team.build_model()  # fail fast if PORTKEY_API_KEY is missing
    except team.AgentNotConfigured as exc:
        raise HTTPException(500, str(exc))
    return _start(lambda rid: team.run_ticket(ticket_id, rid), ticket_id, "run_ticket")


@app.post("/api/tickets/{ticket_id}/final-check")
async def final_check(ticket_id: int):
    """Ask the Boss to re-inspect a ticket and set its status (without re-running the whole team)."""
    if not shop_db.get_ticket(ticket_id)["found"]:
        raise HTTPException(404, f"No ticket {ticket_id}.")
    if _busy():
        raise HTTPException(409, "The team is already working on a ticket. Wait for it to finish.")
    note = "The manager asked for a final check from the board."
    return _start(lambda rid: team.final_check(ticket_id, rid, note), ticket_id, "final_check")


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    if run_id not in RUNS:
        raise HTTPException(404, f"No run {run_id} since the backend started.")
    return RUNS[run_id]


@app.get("/api/events")
def recent_events(ticket_id: int | None = None, run_id: str | None = None,
                  after: int = Query(0, ge=0, description="Return events after this index (for polling)"),
                  limit: int = Query(200, ge=1, le=1000)):
    """Recent agent events from output/audit_trail.json: what each agent said and which tools it used.
    Poll with ?after=<next> to get only new events."""
    path = team.AUDIT_PATH
    events = json.loads(path.read_text(encoding="utf-8")) if path.exists() and path.stat().st_size else []
    indexed = [dict(e, index=i) for i, e in enumerate(events) if isinstance(e, dict)]
    picked = [e for e in indexed if e["index"] >= after
              and (ticket_id is None or e.get("ticket_id") == ticket_id)
              and (run_id is None or e.get("run_id") == run_id)]
    return {"events": picked[-limit:], "next": len(events), "total": len(events)}


# ------------------------------------------------------------------ money

@app.get("/api/cash")
def cash_balance():
    """Current checking balance from cash_accounts (plus payments waiting for the manager)."""
    return shop_db.get_cash_balance()


@app.get("/api/approvals")
def approvals():
    """Payments the agents prepared for the store manager, newest status included."""
    data = shop_db.list_pending_approvals()
    data["store_manager"] = STORE_MANAGER
    data["waiting"] = [a for a in data["approvals"] if a["status"] == "pending"]
    return data


class Decision(BaseModel):
    manager_name: str = Field(description="Must be the store manager's name.")
    approve: bool = Field(description="true = approve and pay, false = reject")


@app.post("/api/approvals/{approval_id}/decide")
async def decide(approval_id: int, body: Decision):
    """The ONLY route that moves cash. The store manager approves (pays) or rejects a prepared payment.
    After an approval, the Boss's final check on that ticket starts automatically."""
    if body.manager_name.strip().lower() != STORE_MANAGER.lower():
        raise HTTPException(403, f"Only the store manager ({STORE_MANAGER}) can approve or reject payments.")
    if _busy():
        raise HTTPException(409, "The team is still working. Approve when the run finishes.")
    result = shop_db.decide_payment(approval_id, STORE_MANAGER, body.approve)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Could not decide this payment."))
    ticket_id = next((a["ticket_id"] for a in shop_db.list_pending_approvals()["approvals"]
                      if a["id"] == approval_id), None)
    result["final_check"] = None
    if body.approve and ticket_id is not None:
        note = (f"{STORE_MANAGER} approved approval {approval_id} "
                f"({result['payee']}, ${result['amount']:,.2f}); checking is now ${result['checking_after']:,.2f}.")
        result["final_check"] = _start(lambda rid: team.final_check(ticket_id, rid, note), ticket_id, "final_check")
    return result


# ------------------------------------------------------------------ drafts and reset

@app.get("/api/drafts")
def drafts(ticket_id: int | None = None):
    """Drafted messages and bills (to Tauhid, the Yale AI Club, the landlord). Nothing is ever sent."""
    return shop_db.list_drafts(ticket_id)


@app.post("/api/reset")
def reset():
    """Copy data/campus_customs.db over data/campus_customs_new.db for a fresh run."""
    if _busy():
        raise HTTPException(409, "The team is still working. Reset when the run finishes.")
    RUNS.clear()
    return shop_db.reset_database()


@app.get("/api/health")
def health():
    return {"ok": True, "model": MODEL_NAME, "store_manager": STORE_MANAGER,
            "portkey_key_set": bool(os.environ.get("PORTKEY_API_KEY", "").strip())}
