"""Campus Customs MCP server.

The only way the agents see or change shop data. It works on the WORKING database,
data/campus_customs_new.db (the original data/campus_customs.db is never written to).
The shop logic lives in shop_db.py.

Read-only tools look things up. "Action" tools change the working database but can never
move cash: payments are only PREPARED here and wait for the store manager, whose approval
happens in the backend (a human-only route), not through any MCP tool.

Run (from the project root):  python mcp_server/server.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastmcp import FastMCP

import shop_db

mcp = FastMCP("campus-customs")

READ = {"readOnlyHint": True, "destructiveHint": False}
WRITE = {"readOnlyHint": False, "destructiveHint": False}


# ------------------------------------------------------------ read-only tools

def list_tickets() -> dict:
    """List every ticket on the desk with its type, requester, subject and status (open,
    waiting_on_approval, held, resolved), plus the shop's 'today' (desk.date_today).
    Reads the tickets and desk tables."""
    return shop_db.list_tickets()


def get_ticket(ticket_id: int) -> dict:
    """Get one ticket with all its fields (type, requester, sku, size, qty, lease_id,
    invoice_id, status, notes) and the Boss's status log. Start every ticket here.
    Reads the tickets, ticket_log and desk tables."""
    return shop_db.get_ticket(ticket_id)


def check_stock(sku: str, size: str) -> dict:
    """Check how many units of a product (SKU) in one size are on hand.

    Use for ticket 101 (Classic Bulldog Tee CC-TEE-WHITE, size S) and
    ticket 103 (Basic Hoodie CC-HOOD-NAVY, size M).
    Returns the product name, size, quantity on hand and aisle location,
    plus whether it is in stock. Reads the inventory table.
    """
    return shop_db.check_stock(sku, size)


def quote_order(sku: str, qty: int, early_pay_discount_pct: float = 0.0) -> dict:
    """Price an order of a SKU from the pricing table: list total, the shop's cost, the total
    with an early-payment discount (for example 2 for '2% net 10'), and the margin percent.
    Use it to check the shop still makes enough money on a discount. Reads the pricing table."""
    return shop_db.quote_order(sku, qty, early_pay_discount_pct)


def get_vendors() -> dict:
    """List every vendor with its specialty, lead days, the arrival date if ordered today
    (desk.date_today + lead_days), its open invoices, and whether it will ship now (a vendor
    will not ship while it has an open unpaid invoice). Reads the vendors, invoices and desk tables."""
    return shop_db.get_vendors()


def get_invoice_status(invoice_id: int) -> dict:
    """Look up a vendor invoice and whether it has been paid.

    Use for ticket 101, which links to invoice 501 (Bulldog Print Co).
    Returns the vendor, amount, due date, status (open/paid), whether it is overdue compared
    with desk.date_today, payments recorded, and any payment waiting for the manager.
    An open invoice means that vendor will not ship new product until it is paid.
    Reads the invoices, vendors, payments, approvals and desk tables.
    """
    return shop_db.get_invoice_status(invoice_id)


def list_open_invoices() -> dict:
    """List every unpaid (open) vendor invoice with days past due and the total owed.
    Reads the invoices, vendors and desk tables."""
    return shop_db.list_open_invoices()


def get_rent_status(lease_id: int) -> dict:
    """Look up the rent on a lease and whether it has been paid or is still open.

    Use for ticket 102, which links to lease 1 (Chapel Street shop, Elm City Properties).
    Rent has no invoice row; the amount and due date live on the lease, and a rent payment
    is recorded in the payments table (kind 'rent', ref_id = lease id). Returns the rent,
    next due date, days until due (from desk.date_today), paid/open status, and late-fee
    terms only if the lease notes hold them. Reads the leases, payments and desk tables.
    """
    return shop_db.get_rent_status(lease_id)


def get_cash_balance() -> dict:
    """Get the checking balance, the total of payments waiting for the manager, and what would
    be left if they were all approved. Reads the cash_accounts and approvals tables."""
    return shop_db.get_cash_balance()


def list_pending_approvals() -> dict:
    """List every payment that has been prepared for the store manager and its status
    (pending, paid, rejected, refused). Reads the approvals table."""
    return shop_db.list_pending_approvals()


def list_drafts(ticket_id: int | None = None) -> dict:
    """List drafted messages and bills (optionally for one ticket) and whether the Boss has
    approved them. Drafts are never sent. Reads the drafts table."""
    return shop_db.list_drafts(ticket_id)


# ------------------------------------------------------------ action tools (never move cash)

def prepare_payment(kind: str, ref_id: int, ticket_id: int, prepared_by: str, reason: str) -> dict:
    """PREPARE a payment for the store manager to approve. kind is 'invoice' (ref_id = invoice id)
    or 'rent' (ref_id = lease id). The amount is read from the database. Refuses if it is already
    paid, already waiting, or if checking would go negative counting payments already waiting.
    Does NOT move cash. Writes the approvals table."""
    return shop_db.prepare_payment(kind, ref_id, ticket_id, prepared_by, reason)


def verify_payment(approval_id: int, boss_note: str) -> dict:
    """Boss only: mark a prepared payment as checked by the Boss before the manager sees it.
    Does NOT move cash. Writes the approvals table."""
    return shop_db.verify_payment(approval_id, boss_note)


def place_restock_order(vendor_id: int, sku: str, size: str, qty: int, ticket_id: int, ordered_by: str) -> dict:
    """Order stock from a vendor. Refuses if the vendor has any open unpaid invoice. The vendor
    bills later: this records a new OPEN invoice for qty x unit_cost (due on the arrival date) and
    moves no cash. Stock is not added until the goods arrive. Writes the invoices table."""
    return shop_db.place_restock_order(vendor_id, sku, size, qty, ticket_id, ordered_by)


def record_shipment(ticket_id: int, sku: str, size: str, qty: int, ship_to: str, shipped_by: str) -> dict:
    """Ship units that are on hand to a customer and lower inventory.qty. Refuses to ship more
    than is on hand. Writes the inventory and shipments tables."""
    return shop_db.record_shipment(ticket_id, sku, size, qty, ship_to, shipped_by)


def save_draft(ticket_id: int, kind: str, author: str, recipient: str, subject: str, body: str) -> dict:
    """Save a message or bill as a DRAFT on the board. kind is customer_message, customer_bill,
    landlord_note or vendor_note. Nothing is emailed or sent. Writes the drafts table."""
    return shop_db.save_draft(ticket_id, kind, author, recipient, subject, body)


def approve_draft(draft_id: int) -> dict:
    """Boss only: approve a draft after checking it. It stays on the board and is NOT sent.
    Writes the drafts table."""
    return shop_db.approve_draft(draft_id)


def set_ticket_status(ticket_id: int, status: str, summary: str) -> dict:
    """Boss only: set a ticket's status (open, waiting_on_approval, held, resolved) with a short
    summary. A ticket cannot be resolved while one of its payments still waits for the manager.
    Writes the tickets and ticket_log tables."""
    return shop_db.set_ticket_status(ticket_id, status, summary)


READ_TOOLS = (list_tickets, get_ticket, check_stock, quote_order, get_vendors, get_invoice_status,
              list_open_invoices, get_rent_status, get_cash_balance, list_pending_approvals, list_drafts)
ACTION_TOOLS = (prepare_payment, verify_payment, place_restock_order, record_shipment, save_draft,
                approve_draft, set_ticket_status)

for _fn in READ_TOOLS:
    mcp.tool(_fn, annotations=READ)
for _fn in ACTION_TOOLS:
    mcp.tool(_fn, annotations=WRITE)


if __name__ == "__main__":
    mcp.run(show_banner=False)
