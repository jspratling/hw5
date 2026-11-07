"""Data types for the Campus Customs agent team."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

# The ONLY model any agent may use (shop rule). Called through Portkey.
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
AGENT_NAMES: tuple[str, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")
SPECIALISTS: tuple[str, ...] = ("inventory", "accounting", "facilities", "customer_service")

TicketStatus = Literal["open", "waiting_on_approval", "held", "resolved"]

# ---- token and loop limits (safety section of harness.md) ----
MAX_REQUESTS_PER_TICKET = 40        # model calls shared by every agent on one ticket
MAX_TOKENS_PER_TICKET = 200_000     # total tokens shared by every agent on one ticket
MAX_HANDOFFS_PER_TICKET = 10        # agent-to-agent handoffs on one ticket
MAX_HANDOFF_DEPTH = 3               # Boss -> A -> B -> C at most
MAX_OUTPUT_TOKENS_PER_REPLY = 1_500
TOOL_RESULT_CHARS_IN_AUDIT = 1_500


class AgentReport(BaseModel):
    """What a specialist hands back after working on a task."""

    agent: AgentName
    summary: str = Field(description="Two or three sentences: what you found and did, with the real numbers.")
    actions_taken: list[str] = Field(default_factory=list,
                                     description="Each change you made (order placed, shipment, draft saved, payment prepared).")
    facts_used: list[str] = Field(default_factory=list,
                                  description="Key facts from the tools, e.g. 'tee size S qty 0', 'invoice 501 $840 open'.")
    waiting_on: list[str] = Field(default_factory=list,
                                  description="Anything still waiting, e.g. 'manager approval for approval 2 ($840)'.")
    suggested_next: list[str] = Field(default_factory=list,
                                      description="Who should do what next, if anything.")


class Contribution(BaseModel):
    agent: AgentName
    what_they_did: str


class BossDecision(BaseModel):
    """The Boss's final inspection of a ticket."""

    ticket_id: int
    status: TicketStatus
    outcome: str = Field(description="Short outcome a manager can read in one glance.")
    agent_contributions: list[Contribution] = Field(default_factory=list)
    approvals_for_manager: list[str] = Field(default_factory=list,
                                             description="Payments verified and waiting for the manager (id, payee, amount).")
    drafts_approved: list[int] = Field(default_factory=list)
    open_items: list[str] = Field(default_factory=list)


@dataclass
class TeamRun:
    """Shared state for one ticket run (all agents on the ticket see the same object)."""

    run_id: str
    ticket_id: int
    handoffs: int = 0
    events: list[dict] = field(default_factory=list)
    # (from_agent, to_agent, task) -> report, so a repeated handoff doesn't redo the work
    finished_handoffs: dict[tuple[str, str, str], str] = field(default_factory=dict)


@dataclass
class TeamDeps:
    run: TeamRun
    agent: str
    depth: int = 0
    chain: tuple[str, ...] = ()
