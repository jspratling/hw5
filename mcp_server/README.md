# Campus Customs MCP server

**What it's for:** it is the only way the five agents (Boss, Inventory, Accounting, Facilities, Customer Service) see or change shop data. Every fact comes through these tools, and each tool returns only what's in the database ("not found" instead of a guess).

**Database:** `data/campus_customs_new.db`, the working copy. The original, `data/campus_customs.db`, is never written to; it is only copied over the working copy for a clean run.

**"Today":** every date comparison uses `desk.date_today` (2026-08-31), never the computer clock.

**Files:** `server.py` registers the tools; `shop_db.py` holds the shop logic and rules.

## Tools

### Read-only (look things up)

| Tool | Reads | Returns |
|---|---|---|
| `list_tickets` | tickets, desk | Every ticket and its status, plus today |
| `get_ticket` | tickets, ticket_log, desk | One ticket's fields and the Boss's status log |
| `check_stock` | inventory | Quantity on hand for a SKU and size, aisle, in stock yes/no |
| `quote_order` | pricing | List total, cost, early-payment discount total, margin % |
| `get_vendors` | vendors, invoices, desk | Specialty, lead days, arrival if ordered today, open invoices, will ship now yes/no |
| `get_invoice_status` | invoices, vendors, payments, approvals, desk | Amount, due date, open/paid, overdue, blocks shipping, payments, payment waiting for manager |
| `list_open_invoices` | invoices, vendors, desk | All unpaid vendor invoices and the total |
| `get_rent_status` | leases, payments, desk | Rent, next due, days until due, open/paid, late-fee terms only if stored |
| `get_cash_balance` | cash_accounts, approvals | Checking balance, payments waiting, what's left if approved |
| `list_pending_approvals` | approvals | Every prepared payment and its status |
| `list_drafts` | drafts | Drafted messages and bills and whether the Boss approved them |

### Actions (change the working database, never move cash)

| Tool | Writes | What it does |
|---|---|---|
| `prepare_payment` | approvals | Queues an invoice or rent payment for the manager. Amount comes from the database. Refuses if already paid, already waiting, or if cash would go negative. |
| `verify_payment` | approvals | Boss marks a prepared payment as checked |
| `place_restock_order` | invoices | Refuses if the vendor has an open invoice. Records a new open invoice (qty × unit cost, due on arrival); vendor bills later. |
| `record_shipment` | inventory, shipments | Ships units on hand and lowers stock; refuses more than on hand |
| `save_draft` | drafts | Saves a customer message, customer bill, landlord note or vendor note. Never sent. |
| `approve_draft` | drafts | Boss approves a draft; it stays on the board, not sent |
| `set_ticket_status` | tickets, ticket_log | Boss sets open / waiting_on_approval / held / resolved; can't resolve while a payment waits |

**Not an MCP tool, on purpose:** paying an approved bill (`shop_db.decide_payment`) and resetting the database (`shop_db.reset_database`). Only the store manager, through the backend's approve and reset routes, can do these. Paying checks the balance again, refuses a negative balance, writes `payments` (with the manager's name in `approved_by`), lowers `cash_accounts.balance`, and marks the invoice paid.

The team adds four helper tables to the working copy (`approvals`, `drafts`, `shipments`, `ticket_log`) to keep its work. The nine original tables keep their structure.

## Run it

From the project root:

```bash
pip install -r requirements.txt
python mcp_server/server.py
```
