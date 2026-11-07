"""Campus Customs shop logic over the WORKING database (data/campus_customs_new.db).

Everything the agents can see or do goes through the MCP server (server.py), which calls
these functions. A few functions here are HUMAN-ONLY (paying an approved bill, resetting the
database). They are used by the backend's approve/reset routes and are never exposed as MCP
tools, so no agent can move money.

Shop rules enforced here:
- "Today" is desk.date_today, never the computer clock.
- Facts come only from the database; anything missing is reported as not found.
- A vendor will not ship (no restock order) while it has an open unpaid invoice.
- Agents can only PREPARE a payment. Cash changes only when a human approves it.
- A payment is refused if checking would go negative. Cash only goes out.
- Messages to customers, vendors or the landlord are saved as drafts. Nothing is sent.
- The original data/campus_customs.db is never written to.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ORIGINAL_DB = PROJECT_ROOT / "data" / "campus_customs.db"
DB_PATH = PROJECT_ROOT / "data" / "campus_customs_new.db"

AGENTS = ("boss", "inventory", "accounting", "facilities", "customer_service")
TICKET_STATUSES = ("open", "waiting_on_approval", "held", "resolved")
DRAFT_KINDS = ("customer_message", "customer_bill", "landlord_note", "vendor_note")

# Tables the team adds to the working copy to keep its own work. The shop's nine
# original tables are unchanged in structure.
SUPPORT_TABLES = """
CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    kind TEXT NOT NULL,              -- 'invoice' or 'rent' (same values as payments.kind)
    ref_id INTEGER NOT NULL,         -- invoice id or lease id
    payee TEXT NOT NULL,
    amount REAL NOT NULL,
    reason TEXT NOT NULL,
    prepared_by TEXT NOT NULL,       -- agent that prepared it
    verified_by_boss INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',   -- pending / paid / rejected / refused
    decided_by TEXT,
    decided_at TEXT,
    note TEXT,
    created_on TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    kind TEXT NOT NULL,
    author TEXT NOT NULL,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',      -- draft / approved_by_boss (never sent)
    reviewed_by TEXT,
    created_on TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS shipments (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    sku TEXT NOT NULL,
    size TEXT NOT NULL,
    qty INTEGER NOT NULL,
    ship_to TEXT NOT NULL,
    shipped_by TEXT NOT NULL,
    shipped_on TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ticket_log (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    agent TEXT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT NOT NULL,
    logged_on TEXT NOT NULL
);
"""


# ---------------------------------------------------------------- helpers

def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Working database not found at {DB_PATH}. "
            "Copy data/campus_customs.db to data/campus_customs_new.db first."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SUPPORT_TABLES)
    return conn


def today(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    if row is None:
        raise ValueError("desk table has no date_today row.")
    return row["date_today"]


def _days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days


def _plus_days(day: str, n: int) -> str:
    return (date.fromisoformat(day[:10]) + timedelta(days=n)).isoformat()


def _money(x: float) -> float:
    return round(float(x) + 1e-9, 2)


def _checking(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute("SELECT name, balance, date FROM cash_accounts WHERE name = 'checking'").fetchone()
    if row is None:
        raise ValueError("No checking account in cash_accounts.")
    return row


def _pending_total(conn: sqlite3.Connection) -> float:
    return _money(conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM approvals WHERE status = 'pending'").fetchone()[0])


def _check_agent(name: str) -> str | None:
    return None if name in AGENTS else f"Unknown agent '{name}'. Use one of: {', '.join(AGENTS)}."


# ---------------------------------------------------------------- read: tickets

def list_tickets() -> dict:
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT id, type, requester, subject, status, created_at FROM tickets ORDER BY id")]
        return {"today": today(conn), "tickets": rows}


def get_ticket(ticket_id: int) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return {"found": False, "ticket_id": ticket_id, "message": "No ticket with this id."}
        log = [dict(r) for r in conn.execute(
            "SELECT agent, status, summary, logged_on FROM ticket_log WHERE ticket_id = ? ORDER BY id",
            (ticket_id,))]
        return {"found": True, "today": today(conn), "ticket": dict(row), "log": log}


# ---------------------------------------------------------------- read: stock, price, vendors

def check_stock(sku: str, size: str) -> dict:
    with connect() as conn:
        row = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (sku.strip(), size.strip()),
        ).fetchone()
        if row is None:
            sizes = [r["size"] for r in conn.execute("SELECT size FROM inventory WHERE sku = ?", (sku.strip(),))]
            return {"found": False, "sku": sku, "size": size,
                    "message": "No inventory row for this SKU and size.", "sizes_on_file_for_sku": sizes}
        return {"found": True, "sku": row["sku"], "name": row["name"], "size": row["size"],
                "qty_on_hand": row["qty"], "location": row["location"], "in_stock": row["qty"] > 0}


def quote_order(sku: str, qty: int, early_pay_discount_pct: float = 0.0) -> dict:
    """Price an order from the pricing table and show the shop's margin."""
    with connect() as conn:
        p = conn.execute("SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku.strip(),)).fetchone()
        if p is None:
            return {"found": False, "sku": sku, "message": "No pricing row for this SKU."}
        if qty <= 0:
            return {"found": True, "error": "Quantity must be at least 1."}
        if not 0 <= early_pay_discount_pct < 100:
            return {"found": True, "error": "Discount percent must be between 0 and 100."}
        list_total = _money(p["list_price"] * qty)
        cost_total = _money(p["unit_cost"] * qty)
        disc_unit = _money(p["list_price"] * (1 - early_pay_discount_pct / 100))
        disc_total = _money(list_total * (1 - early_pay_discount_pct / 100))
        return {
            "found": True, "sku": p["sku"], "qty": qty,
            "unit_cost": p["unit_cost"], "list_price": p["list_price"],
            "list_total": list_total, "cost_total": cost_total,
            "early_pay_discount_pct": early_pay_discount_pct,
            "unit_price_if_paid_early": disc_unit, "total_if_paid_early": disc_total,
            "margin_pct_at_list": round((p["list_price"] - p["unit_cost"]) / p["list_price"] * 100, 1),
            "margin_pct_if_paid_early": round((disc_unit - p["unit_cost"]) / disc_unit * 100, 1),
            "note": "Customer money is not modeled: a customer bill is a draft only and never adds cash.",
        }


def get_vendors() -> dict:
    """Every vendor with lead time, expected arrival if ordered today, and open invoices."""
    with connect() as conn:
        t = today(conn)
        out = []
        for v in conn.execute("SELECT id, name, specialty, lead_days FROM vendors ORDER BY id"):
            open_inv = [dict(r) for r in conn.execute(
                "SELECT id, amount, due_date, description FROM invoices WHERE vendor_id = ? AND status = 'open'",
                (v["id"],))]
            out.append({**dict(v), "arrival_if_ordered_today": _plus_days(t, v["lead_days"]),
                        "open_invoices": open_inv, "will_ship_now": not open_inv})
        return {"today": t, "vendors": out,
                "note": "No table links a SKU to a vendor; match by specialty (apparel = 'apparel reprint')."}


# ---------------------------------------------------------------- read: money

def get_invoice_status(invoice_id: int) -> dict:
    with connect() as conn:
        t = today(conn)
        row = conn.execute(
            "SELECT i.id, i.vendor_id, v.name AS vendor_name, v.lead_days, i.amount, i.due_date, "
            "i.status, i.description FROM invoices i LEFT JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
            (invoice_id,),
        ).fetchone()
        if row is None:
            return {"found": False, "invoice_id": invoice_id, "message": "No invoice with this id."}
        payments = [dict(p) for p in conn.execute(
            "SELECT id, amount, account, paid_at, approved_by FROM payments "
            "WHERE kind = 'invoice' AND ref_id = ? ORDER BY id", (invoice_id,))]
        pending = [dict(a) for a in conn.execute(
            "SELECT id, amount, prepared_by, status FROM approvals WHERE kind = 'invoice' AND ref_id = ? "
            "AND status = 'pending'", (invoice_id,))]
        is_open = row["status"] == "open"
        days_past_due = _days_between(row["due_date"], t)
        return {
            "found": True, "invoice_id": row["id"], "vendor_id": row["vendor_id"],
            "vendor_name": row["vendor_name"], "vendor_lead_days": row["lead_days"],
            "amount": row["amount"], "due_date": row["due_date"], "status": row["status"],
            "description": row["description"], "today": t, "is_paid": not is_open,
            "is_overdue": is_open and days_past_due > 0,
            "days_past_due": max(days_past_due, 0) if is_open else 0,
            "blocks_vendor_shipping": is_open, "payments_recorded": payments,
            "payment_waiting_for_manager": pending,
        }


def list_open_invoices() -> dict:
    with connect() as conn:
        t = today(conn)
        rows = []
        for r in conn.execute(
                "SELECT i.id, i.vendor_id, v.name AS vendor_name, i.amount, i.due_date, i.description "
                "FROM invoices i LEFT JOIN vendors v ON v.id = i.vendor_id WHERE i.status = 'open' ORDER BY i.due_date"):
            d = dict(r)
            d["days_past_due"] = max(_days_between(r["due_date"], t), 0)
            rows.append(d)
        return {"today": t, "open_invoices": rows, "total_open": _money(sum(r["amount"] for r in rows))}


def get_rent_status(lease_id: int) -> dict:
    with connect() as conn:
        t = today(conn)
        row = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
            (lease_id,)).fetchone()
        if row is None:
            return {"found": False, "lease_id": lease_id, "message": "No lease with this id."}
        payments = [dict(p) for p in conn.execute(
            "SELECT id, amount, account, paid_at, approved_by FROM payments "
            "WHERE kind = 'rent' AND ref_id = ? ORDER BY id", (lease_id,))]
        paid = any(p["amount"] >= row["monthly_rent"] for p in payments)
        days_until_due = _days_between(t, row["next_due"])
        return {
            "found": True, "lease_id": row["id"], "space_name": row["space_name"],
            "landlord": row["landlord"], "monthly_rent": row["monthly_rent"], "next_due": row["next_due"],
            "today": t, "days_until_due": days_until_due,
            "is_overdue": (not paid) and days_until_due < 0,
            "status": "paid" if paid else "open",
            "late_fee_terms": row["notes"] if row["notes"] else "Not stored in the database",
            "payments_recorded": payments,
        }


def get_cash_balance() -> dict:
    with connect() as conn:
        acct = _checking(conn)
        pending = _pending_total(conn)
        return {
            "account": acct["name"], "balance": acct["balance"], "balance_date": acct["date"],
            "today": today(conn), "pending_approvals_total": pending,
            "available_after_pending": _money(acct["balance"] - pending),
            "note": "Cash only goes out. Only a human approval changes the balance.",
        }


def list_pending_approvals() -> dict:
    with connect() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM approvals ORDER BY id")]
        return {"approvals": rows, "pending_total": _pending_total(conn)}


def list_drafts(ticket_id: int | None = None) -> dict:
    with connect() as conn:
        if ticket_id is None:
            rows = conn.execute("SELECT * FROM drafts ORDER BY id")
        else:
            rows = conn.execute("SELECT * FROM drafts WHERE ticket_id = ? ORDER BY id", (ticket_id,))
        return {"drafts": [dict(r) for r in rows], "note": "Drafts are never sent."}


# ---------------------------------------------------------------- agent writes (no cash moves)

def prepare_payment(kind: str, ref_id: int, ticket_id: int, prepared_by: str, reason: str) -> dict:
    """Queue a payment for the store manager. The amount always comes from the database."""
    if (err := _check_agent(prepared_by)):
        return {"prepared": False, "error": err}
    if kind not in ("invoice", "rent"):
        return {"prepared": False, "error": "kind must be 'invoice' or 'rent'."}
    with connect() as conn:
        t = today(conn)
        if kind == "invoice":
            inv = conn.execute(
                "SELECT i.amount, i.status, v.name FROM invoices i LEFT JOIN vendors v ON v.id = i.vendor_id "
                "WHERE i.id = ?", (ref_id,)).fetchone()
            if inv is None:
                return {"prepared": False, "error": f"No invoice {ref_id}."}
            if inv["status"] != "open":
                return {"prepared": False, "error": f"Invoice {ref_id} is already {inv['status']}."}
            amount, payee = inv["amount"], inv["name"]
        else:
            lease = conn.execute("SELECT monthly_rent, landlord FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if lease is None:
                return {"prepared": False, "error": f"No lease {ref_id}."}
            amount, payee = lease["monthly_rent"], lease["landlord"]
        dup = conn.execute("SELECT id FROM approvals WHERE kind = ? AND ref_id = ? AND status = 'pending'",
                           (kind, ref_id)).fetchone()
        if dup:
            return {"prepared": False, "error": f"Already waiting for the manager as approval {dup['id']}."}
        balance = _checking(conn)["balance"]
        pending = _pending_total(conn)
        if balance - pending - amount < 0:
            return {"prepared": False, "refused": True,
                    "error": (f"Not enough cash: checking ${balance:,.2f}, already waiting ${pending:,.2f}, "
                              f"this payment ${amount:,.2f}. It would go negative."),
                    "shortfall": _money(amount - (balance - pending))}
        cur = conn.execute(
            "INSERT INTO approvals (ticket_id, kind, ref_id, payee, amount, reason, prepared_by, created_on) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (ticket_id, kind, ref_id, payee, amount, reason, prepared_by, t))
        return {"prepared": True, "approval_id": cur.lastrowid, "kind": kind, "ref_id": ref_id,
                "payee": payee, "amount": amount, "status": "pending",
                "checking_now": balance, "checking_if_approved": _money(balance - pending - amount),
                "next_step": "The Boss verifies it; then the store manager approves or rejects it on the board."}


def verify_payment(approval_id: int, boss_note: str) -> dict:
    """Boss's check before a payment goes to the manager."""
    with connect() as conn:
        a = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if a is None:
            return {"verified": False, "error": f"No approval {approval_id}."}
        if a["status"] != "pending":
            return {"verified": False, "error": f"Approval {approval_id} is {a['status']}."}
        conn.execute("UPDATE approvals SET verified_by_boss = 1, note = ? WHERE id = ?", (boss_note, approval_id))
        return {"verified": True, "approval_id": approval_id, "amount": a["amount"], "payee": a["payee"],
                "next_step": "Waiting for the store manager to approve on the board."}


def place_restock_order(vendor_id: int, sku: str, size: str, qty: int, ticket_id: int, ordered_by: str) -> dict:
    """Order stock. The vendor bills later, so this records a new OPEN invoice and moves no cash."""
    if (err := _check_agent(ordered_by)):
        return {"ordered": False, "error": err}
    if qty <= 0:
        return {"ordered": False, "error": "Quantity must be at least 1."}
    with connect() as conn:
        t = today(conn)
        v = conn.execute("SELECT id, name, lead_days FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if v is None:
            return {"ordered": False, "error": f"No vendor {vendor_id}."}
        if conn.execute("SELECT 1 FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone() is None:
            return {"ordered": False, "error": f"No inventory row for {sku} size {size}."}
        open_inv = [r["id"] for r in conn.execute(
            "SELECT id FROM invoices WHERE vendor_id = ? AND status = 'open'", (vendor_id,))]
        if open_inv:
            return {"ordered": False, "refused": True,
                    "error": (f"{v['name']} will not ship while invoice(s) {open_inv} are unpaid. "
                              "Pay them first (manager approval).")}
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if price is None:
            return {"ordered": False, "error": f"No unit cost for {sku}."}
        amount = _money(price["unit_cost"] * qty)
        arrival = _plus_days(t, v["lead_days"])
        desc = f"Restock order: {qty} x {sku} size {size} (ticket {ticket_id}, ordered by {ordered_by})"
        cur = conn.execute(
            "INSERT INTO invoices (vendor_id, amount, due_date, status, description) VALUES (?, ?, ?, 'open', ?)",
            (vendor_id, amount, arrival, desc))
        return {"ordered": True, "invoice_id": cur.lastrowid, "vendor": v["name"], "sku": sku, "size": size,
                "qty": qty, "amount": amount, "unit_cost": price["unit_cost"], "expected_arrival": arrival,
                "invoice_status": "open",
                "note": ("No cash moved. The vendor's bill is now an open invoice; Accounting prepares it "
                         "for the manager. Stock is added when the goods arrive.")}


def record_shipment(ticket_id: int, sku: str, size: str, qty: int, ship_to: str, shipped_by: str) -> dict:
    if (err := _check_agent(shipped_by)):
        return {"shipped": False, "error": err}
    if qty <= 0:
        return {"shipped": False, "error": "Quantity must be at least 1."}
    with connect() as conn:
        row = conn.execute("SELECT qty FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone()
        if row is None:
            return {"shipped": False, "error": f"No inventory row for {sku} size {size}."}
        if qty > row["qty"]:
            return {"shipped": False, "error": f"Only {row['qty']} on hand; cannot ship {qty}."}
        t = today(conn)
        conn.execute("UPDATE inventory SET qty = qty - ? WHERE sku = ? AND size = ?", (qty, sku, size))
        conn.execute("INSERT INTO shipments (ticket_id, sku, size, qty, ship_to, shipped_by, shipped_on) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?)", (ticket_id, sku, size, qty, ship_to, shipped_by, t))
        return {"shipped": True, "sku": sku, "size": size, "qty": qty, "ship_to": ship_to,
                "qty_left": row["qty"] - qty, "shipped_on": t}


def save_draft(ticket_id: int, kind: str, author: str, recipient: str, subject: str, body: str) -> dict:
    if (err := _check_agent(author)):
        return {"saved": False, "error": err}
    if kind not in DRAFT_KINDS:
        return {"saved": False, "error": f"kind must be one of: {', '.join(DRAFT_KINDS)}."}
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO drafts (ticket_id, kind, author, recipient, subject, body, created_on) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)", (ticket_id, kind, author, recipient, subject, body, today(conn)))
        return {"saved": True, "draft_id": cur.lastrowid, "status": "draft",
                "note": "Saved on the board only. Nothing is emailed or sent."}


def approve_draft(draft_id: int) -> dict:
    with connect() as conn:
        d = conn.execute("SELECT id, status FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        if d is None:
            return {"approved": False, "error": f"No draft {draft_id}."}
        conn.execute("UPDATE drafts SET status = 'approved_by_boss', reviewed_by = 'boss' WHERE id = ?", (draft_id,))
        return {"approved": True, "draft_id": draft_id, "status": "approved_by_boss",
                "note": "Approved and kept on the board. It is not sent."}


def set_ticket_status(ticket_id: int, status: str, summary: str) -> dict:
    if status not in TICKET_STATUSES:
        return {"updated": False, "error": f"status must be one of: {', '.join(TICKET_STATUSES)}."}
    with connect() as conn:
        if conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
            return {"updated": False, "error": f"No ticket {ticket_id}."}
        if status == "resolved":
            pending = conn.execute(
                "SELECT COUNT(*) FROM approvals WHERE ticket_id = ? AND status = 'pending'", (ticket_id,)
            ).fetchone()[0]
            if pending:
                return {"updated": False,
                        "error": (f"{pending} payment(s) for this ticket still wait for the manager. "
                                  "Use 'waiting_on_approval' until they are decided.")}
        conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        conn.execute("INSERT INTO ticket_log (ticket_id, agent, status, summary, logged_on) VALUES (?, 'boss', ?, ?, ?)",
                     (ticket_id, status, summary, today(conn)))
        return {"updated": True, "ticket_id": ticket_id, "status": status}


# ---------------------------------------------------------------- HUMAN ONLY (not MCP tools)

def decide_payment(approval_id: int, manager_name: str, approve: bool) -> dict:
    """The store manager approves or rejects a prepared payment. Only this moves cash."""
    manager_name = (manager_name or "").strip()
    if not manager_name:
        return {"ok": False, "error": "The manager's name is required (it goes in payments.approved_by)."}
    with connect() as conn:
        t = today(conn)
        a = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if a is None:
            return {"ok": False, "error": f"No approval {approval_id}."}
        if a["status"] != "pending":
            return {"ok": False, "error": f"Approval {approval_id} is already {a['status']}."}
        if not approve:
            conn.execute("UPDATE approvals SET status = 'rejected', decided_by = ?, decided_at = ? WHERE id = ?",
                         (manager_name, t, approval_id))
            return {"ok": True, "approval_id": approval_id, "status": "rejected"}
        acct = _checking(conn)
        if acct["balance"] - a["amount"] < 0:
            conn.execute("UPDATE approvals SET status = 'refused', decided_by = ?, decided_at = ?, note = ? "
                         "WHERE id = ?", (manager_name, t, "Not enough cash", approval_id))
            return {"ok": False, "refused": True, "error": (
                f"Not enough cash: checking ${acct['balance']:,.2f}, payment ${a['amount']:,.2f}.")}
        if a["kind"] == "invoice":
            inv = conn.execute("SELECT status FROM invoices WHERE id = ?", (a["ref_id"],)).fetchone()
            if inv is None or inv["status"] != "open":
                return {"ok": False, "error": f"Invoice {a['ref_id']} is not open."}
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (a["ref_id"],))
        new_balance = _money(acct["balance"] - a["amount"])
        conn.execute("UPDATE cash_accounts SET balance = ?, date = ? WHERE name = 'checking'", (new_balance, t))
        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, 'checking', ?, ?)",
            (a["kind"], a["ref_id"], a["amount"], t, manager_name))
        conn.execute("UPDATE approvals SET status = 'paid', decided_by = ?, decided_at = ? WHERE id = ?",
                     (manager_name, t, approval_id))
        return {"ok": True, "approval_id": approval_id, "status": "paid", "payment_id": cur.lastrowid,
                "amount": a["amount"], "payee": a["payee"], "checking_before": acct["balance"],
                "checking_after": new_balance}


def reset_database() -> dict:
    """Copy the original database over the working copy (clean run)."""
    shutil.copyfile(ORIGINAL_DB, DB_PATH)
    with connect() as conn:
        return {"reset": True, "checking": _checking(conn)["balance"], "today": today(conn)}
