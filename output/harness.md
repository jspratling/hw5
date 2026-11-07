# Harness — Campus Customs Multi-Agent Operations

This file maps the shop's data, tools, agents, routes and safety rules. It grows with each problem.

## 1. Database tables (Problem 2)

Database: `data/campus_customs.db` is the original and is never changed. The agents work on the copy, `data/campus_customs_new.db`. Reset by copying the original over the copy.

Nine tables. Field lists come from the database schema, and row counts are from the original file.

### desk (1 row)

| Field | Type | Meaning |
|---|---|---|
| date_today | TEXT, required | The shop's "today": **2026-08-31** |
| notes | TEXT | Desk notes (empty) |

**Why it matters:** the Boss needs this date first so he can route each ticket to the right agent. Accounting needs it to track and pay bills on time (invoice 501 was due 08-28, so it's overdue on ticket 101). Facilities needs it because it's in charge of the lease (rent is due 09-02, two days away, on ticket 102). Inventory uses today's date to work out delivery times from the vendor's lead days (Bulldog Print Co takes 5 days, so the tee and hoodies arrive around 09-05). Customer Service puts that date in the messages to Tauhid (ticket 101) and the Yale AI Club (ticket 103).

### tickets (3 rows)

| Field | Type | Meaning |
|---|---|---|
| id | INTEGER, key | Ticket number (101, 102, 103) |
| type | TEXT, required | customer_order, rent_notice or price_override |
| requester | TEXT, required | Who asked |
| subject | TEXT, required | Short title |
| sku | TEXT | Product, if the ticket is about one → `inventory.sku`, `pricing.sku` |
| size | TEXT | Product size → `inventory.size` |
| qty | INTEGER | Quantity requested |
| lease_id | INTEGER | Linked lease → `leases.id` |
| invoice_id | INTEGER | Linked vendor invoice → `invoices.id` |
| status | TEXT, required | open or resolved |
| notes | TEXT | Request details |
| created_at | TEXT, required | When the ticket arrived |

**Why it matters:** the Boss reads this table first. He uses each ticket's type to send it to the right agent or agents, and makes sure each assigned agent follows the right link (the product and size on 101 and 103, invoice 501 on 101, lease 1 on 102) and keeps the correct status. The Boss marks a ticket resolved once the other agents finish and any payment has been approved by a human. The board shows `status` as open or resolved.

### inventory (10 rows)

| Field | Type | Meaning |
|---|---|---|
| sku | TEXT, key (with size) | Product code |
| name | TEXT, required | Product name |
| size | TEXT, key (with sku) | S, M, L, XL or OS (one size) |
| qty | INTEGER, required | Units on hand |
| location | TEXT, required | Aisle |

**Why it matters:** four agents use this table. The Boss tells the other agents when an item is out of stock, so they don't sell what isn't there and more gets ordered (ticket 101: tee size S has **0**; ticket 103: hoodie size M has **8** against 20 requested, **12 short**). Inventory uses it to refill stock and updates `qty` when hoodies ship to the club and when the restock arrives. Accounting needs it because refilling stock costs money, and to make sure stock that was sold has been billed. Customer Service needs it to draft a message for a customer looking for an item that's out of stock.

### pricing (4 rows)

| Field | Type | Meaning |
|---|---|---|
| sku | TEXT, key | Product code → `inventory.sku` |
| unit_cost | REAL, required | What the shop pays per unit |
| list_price | REAL, required | Normal selling price |

**Why it matters:** the Boss uses it to keep track of what stock costs and what gets billed, so he can make the final call on the Yale AI Club's discount (ticket 103). Inventory uses `unit_cost` to price what it orders to restock (17 hoodies × $22 = **$374**). Accounting uses it to track billing against the cash on hand the shop needs to operate, and to check the shop makes enough money on each item sold: hoodies cost **$22** and list at **$58**, so the club's bill is $1,160, or $1,136.80 with 2% net 10, which still leaves about a **61% margin**. Customer Service uses `list_price` to tell customers what an item costs and to put the right amounts in the club's bill.

### vendors (3 rows)

| Field | Type | Meaning |
|---|---|---|
| id | INTEGER, key | Vendor number → `invoices.vendor_id` |
| name | TEXT, required | Vendor name |
| specialty | TEXT, required | What they supply |
| lead_days | INTEGER, required | Days from order to delivery |

**Why it matters:** the Boss, Inventory, Accounting and Customer Service use this table. **Bulldog Print Co** (id 1, apparel reprint, **5 days**) supplies the tee (ticket 101) and the hoodies (ticket 103), and it has to be paid (invoice 501) before it ships, so the customer orders can be filled and received on time. The Boss uses that to put paying Bulldog Print Co first. Inventory uses it to restock the size S tee and size M hoodies and to work out the arrival date (5 days from 08-31 = about 09-05). Accounting pays Bulldog Print Co. Customer Service uses the lead time for the delivery date in the messages to Tauhid and the club. Elm City Gifts (mugs and small goods, 3 days) and QuickShip CT (local courier, 1 day) aren't needed for these tickets.

### leases (1 row)

| Field | Type | Meaning |
|---|---|---|
| id | INTEGER, key | Lease number → `tickets.lease_id` |
| space_name | TEXT, required | Chapel Street shop |
| landlord | TEXT, required | Elm City Properties |
| monthly_rent | REAL, required | **$2,400** |
| next_due | TEXT, required | **2026-09-02** |
| notes | TEXT | Empty: no late-fee terms are stored |

**Why it matters:** the Boss uses this table to send ticket 102 to Accounting and Facilities. Accounting is in charge of paying the rent ($2,400, due 09-02), and holds it until the owner approves (rent is held until the hoodie orders are in and paid for). Facilities tracks the lease payments because it manages the leases, and drafts the note to Elm City Properties (the landlord) saying the rent is held and the late fee will be paid per the lease terms (a draft only, never sent). Because `notes` is empty, no agent may state a late-fee dollar amount; the late fee is paid per the regular lease terms.

### cash_accounts (1 row)

| Field | Type | Meaning |
|---|---|---|
| name | TEXT, key | Account name (checking) |
| balance | REAL, required | **$3,400.00** at the start |
| date | TEXT, required | Balance date (2026-08-31) |

**Why it matters:** the Boss uses this table to route money questions to Accounting. Accounting tracks the cash account and payables (vendor invoices and rent), checks the balance before preparing any payment, and bills the customer (the Yale AI Club's bill is a draft on the board; there is no receivables table and no money comes in). Accounting prepares payments, but the balance only changes when a human approves a payment; the pay step then lowers `balance` and must refuse if the balance would go negative. Under the owner's plan: $3,400 → $2,560 after invoice 501 → $2,186 after the hoodie invoice. The dashboard shows this balance, and the Problem 9 Cash tab's ending balance must match it.

### payments (0 rows)

| Field | Type | Meaning |
|---|---|---|
| id | INTEGER, key | Payment number |
| kind | TEXT, required | What was paid (for example, invoice or rent) |
| ref_id | INTEGER | The invoice or lease paid |
| amount | REAL, required | Dollar amount |
| account | TEXT, required | Account the money came from → `cash_accounts.name` |
| paid_at | TEXT, required | When it was paid |
| approved_by | TEXT, required | The human who approved it |

**Why it matters:** this is the record of every payment a human approved. `approved_by` can't be blank because no agent may pay on its own: the store manager approves each payment manually, signed in with a secure login name and password, and their name goes in `approved_by`. A row is added only when the manager approves invoice 501 ($840, ticket 101) or the hoodie invoice ($374, ticket 103); rent (ticket 102) is held, so it gets no row. Accounting reads this table to confirm what has been paid, Facilities checks it for lease payments, and the Boss checks it before marking a ticket resolved.

### invoices (1 row)

| Field | Type | Meaning |
|---|---|---|
| id | INTEGER, key | Invoice number → `tickets.invoice_id` |
| vendor_id | INTEGER, required | Vendor billing the shop → `vendors.id` |
| amount | REAL, required | Amount owed |
| due_date | TEXT, required | Due date |
| status | TEXT, required | open (unpaid) or paid |
| description | TEXT | What it's for |

**Why it matters:** the Boss uses this table to send invoice work to Accounting, which tracks what has been paid, the new invoice to be paid, and reconciles the accounts. **Invoice 501** (Bulldog Print Co, **$840**, due 08-28, **open**, "Rush reprint CC-TEE-WHITE S") is overdue, and an open invoice stops the vendor from shipping, so it blocks both the tee (ticket 101) and the hoodie restock (ticket 103) until the manager approves paying it. The hoodie order then adds a new Bulldog Print Co invoice for **$374** (ticket 103), which Accounting also prepares for approval. The Boss also sends it to Inventory to track new stock coming in from what was purchased and what is going out in orders. Customer Service is updated so it can tell customers the current stock levels and when items arrive. This table holds vendor bills only (`vendor_id` is required), so the Yale AI Club's bill can't be stored here.

## 2. How the three open tickets connect to the other tables

```
desk.date_today = 2026-08-31  (used by every ticket for "overdue" / "due soon")

Ticket 101  customer_order   Tauhid Zaman: 1 Classic Bulldog Tee, size S
  ├─ sku CC-TEE-WHITE + size S ─→ inventory: qty 0 (out of stock)
  │                              └→ pricing: cost $8, list $28
  └─ invoice_id 501 ──────────→ invoices: $840, due 08-28, open (overdue)
                                 └─ vendor_id 1 → vendors: Bulldog Print Co, 5-day lead
     Payment, if approved ──→ payments (new row) + cash_accounts (balance down)

Ticket 102  rent_notice      Elm City Properties: rent due
  └─ lease_id 1 ──────────────→ leases: Chapel Street shop, $2,400, due 09-02
     Payment, if approved ──→ payments (new row) + cash_accounts (balance down)

Ticket 103  price_override   Yale AI Club: 20 hoodies, size M, bulk discount
  ├─ sku CC-HOOD-NAVY + size M ─→ inventory: qty 8 (12 short)
  │                              └→ pricing: cost $22, list $58 (margin check)
  └─ restock (no direct link) ──→ vendors: Bulldog Print Co by specialty
                                  "apparel reprint", 5-day lead; blocked while
                                  invoice 501 is open
```

**Gaps the agents must handle without inventing data:**
- No table links a SKU to its vendor. The apparel vendor is matched only by `vendors.specialty` ("apparel reprint").
- Ticket 103 has no `invoice_id` or `lease_id`. Its links go only through `sku` and `size`.
- `leases.notes` is empty, so there are no late-fee terms.
- There is no table for customer bills or incoming cash. That matches the rule that cash only goes out.

## 3. MCP tools (Problem 3)

Server: `mcp_server/server.py` (FastMCP, server name `campus-customs`). It reads only `data/campus_customs_new.db`, uses `desk.date_today` as "today," and returns only what's in the database ("not found" instead of a guess).

| Tool | Table(s) it reads | Ticket it unlocks | Why it's the right tool for that ticket |
|---|---|---|---|
| `check_stock(sku, size)` | inventory | **101** and **103** | Ticket 101 asks for a Classic Bulldog Tee in **size S** and ticket 103 asks for 20 hoodies in **size M**. Stock is stored per SKU *and* size, so this tool returns exactly that row: **0** tees in size S (out of stock, so the reprint is needed) and **8** hoodies in size M (so 12 must be restocked). |
| `get_invoice_status(invoice_id)` | invoices, vendors, payments, desk | **101** (and it decides 103) | Ticket 101 links to **invoice 501**. The tool shows Bulldog Print Co's **$840** bill, due 08-28, is **open and 3 days overdue** as of 08-31, and that an open invoice **blocks the vendor from shipping**. That tells Accounting it must be paid (with the manager's approval) before the tee can arrive, and the same block applies to the hoodie restock on ticket 103. |
| `get_rent_status(lease_id)` | leases, payments, desk | **102** | Ticket 102 links to **lease 1**. Rent has no invoice row; it lives on the lease, and a rent payment would be a row in payments. The tool shows **$2,400** to Elm City Properties, due 09-02 (**2 days away**), status **open** (no rent payment recorded), and that **no late-fee terms are stored**. Facilities and Accounting use this to hold the rent and draft the landlord note without inventing a fee. |

How "paid" is found: `get_invoice_status` reads the invoice's own `status` (open or paid) and lists matching payments (`kind = 'invoice'`). `get_rent_status` counts the rent as paid only if payments has a `kind = 'rent'` row for that lease covering the full rent. The payment tools added later must record payments with these same `kind` values.

## 4. The agent team (Problem 5)

Code: `backend/team.py` (PydanticAI), data types in `backend/models.py`, one prompt per agent in `backend/prompts/`. Every agent uses **only `gpt-6-luna` through Portkey** (`PORTKEY_API_KEY`); the model name is fixed in `models.py` and cannot be changed by a setting. Every shop fact comes from the MCP server; the agents never open the database themselves.

**How the team works together (owner's design):** all new tickets come in to the Boss, who decides who works on each one. Money (orders, billing, sales, returns, invoices, cash) goes to Accounting; stock, shortfalls, vendors and restock orders go to Inventory; facilities, leases and rent go to Facilities; customer questions go to Customer Service. Every finished task comes back to the Boss for a final inspection, and the Boss decides whether it now needs another agent. **Full connectivity:** any agent can also hand a task straight to any other agent with the `delegate` tool (for example Accounting asking Inventory to confirm stock), and the result flows back up to the Boss. Bills the Boss has verified go to the store manager, who approves and pays them. Drafted messages are inspected by the Boss and stay on the board; nothing is sent.

| Agent | Prompt | Job | MCP tools it can use (others are hidden) |
|---|---|---|---|
| **Boss** | `boss.md` | Routes every ticket, inspects every result, verifies payments and drafts, sets ticket status, final call | list_tickets, get_ticket, check_stock, get_invoice_status, get_rent_status, get_cash_balance, list_pending_approvals, list_drafts, **verify_payment, approve_draft, set_ticket_status** |
| **Inventory** | `inventory.md` | Stock by SKU and size, shortfalls, vendor and arrival date, restock orders, shipping what's on hand | get_ticket, check_stock, get_vendors, get_invoice_status, quote_order, **place_restock_order, record_shipment** |
| **Accounting** | `accounting.md` | Invoices, cash, margins, prepares payments for the manager, bills customers, reconciles | get_ticket, check_stock, quote_order, get_invoice_status, list_open_invoices, get_rent_status, get_cash_balance, list_pending_approvals, list_drafts, **prepare_payment, save_draft** |
| **Facilities** | `facilities.md` | Leases and rent, tracks lease payments, drafts landlord notes | get_ticket, get_rent_status, get_cash_balance, list_pending_approvals, list_drafts, **save_draft** |
| **Customer Service** | `customer_service.md` | Answers customers with stock levels and delivery dates; drafts messages | get_ticket, check_stock, get_vendors, quote_order, list_drafts, **save_draft** |

Every agent also has `delegate(to_agent, task)`. **Bold** tools change the working database; none of them moves cash.

### MCP tools and the table each uses

| Tool | Table(s) | Kind |
|---|---|---|
| list_tickets | tickets, desk | read |
| get_ticket | tickets, ticket_log, desk | read |
| check_stock | inventory | read |
| quote_order | pricing | read |
| get_vendors | vendors, invoices, desk | read |
| get_invoice_status | invoices, vendors, payments, approvals, desk | read |
| list_open_invoices | invoices, vendors, desk | read |
| get_rent_status | leases, payments, desk | read |
| get_cash_balance | cash_accounts, approvals | read |
| list_pending_approvals | approvals | read |
| list_drafts | drafts | read |
| prepare_payment | approvals (reads invoices, leases, cash_accounts) | action, no cash |
| verify_payment | approvals | action, no cash |
| place_restock_order | invoices (reads vendors, pricing, inventory) | action, no cash |
| record_shipment | inventory, shipments | action, no cash |
| save_draft | drafts | action, nothing sent |
| approve_draft | drafts | action, nothing sent |
| set_ticket_status | tickets, ticket_log | action |
| *(human only, not MCP)* decide_payment | approvals, payments, cash_accounts, invoices | **moves cash, manager only** |
| *(human only, not MCP)* reset_database | copies `campus_customs.db` over `campus_customs_new.db` | manager only |

`approvals`, `drafts`, `shipments` and `ticket_log` are helper tables the team adds to the working copy.

### Audit trail

Every agent-loop step is appended to `output/audit_trail.json` as it happens (the file is appended to, never wiped): ticket started, every MCP tool call with its arguments, every tool result, every handoff (and refused handoff) between agents, each agent's report back, anything an agent said, and the ticket's finish with the Boss's decision, the number of model requests, total tokens and handoffs. Each entry has the run id, ticket id, time, agent, step number and handoff depth.

## 5. Safety and token limits (Problem 5)

### Guardrails for real customers and real money

1. **No agent can move money.** Agents can only *prepare* a payment. The Boss verifies it, and the store manager approves or rejects it on the board. Paying is a human-only function, not an MCP tool, so a model can't call it even by mistake.
2. **The manager signs every payment.** `payments.approved_by` is required and holds the manager's name. In a real shop this would sit behind a secure login (user name and password), so only the store manager can approve.
3. **No negative cash.** A payment is refused when it is prepared (counting payments already waiting) and again when it is approved, if checking would go below $0.
4. **The amount comes from the database, never from the model.** `prepare_payment` reads the invoice or lease amount itself, so an agent can't pay a wrong or made-up number.
5. **The vendor rule is enforced in code.** `place_restock_order` refuses while the vendor has an open unpaid invoice.
6. **Least privilege.** Each agent sees only the tools its job needs: only the Boss can resolve tickets or approve drafts, only Accounting can prepare payments, only Inventory can order or ship.
7. **Nothing leaves the shop.** Messages, bills and landlord notes are drafts on the board; no email or vendor call exists in the code.
8. **No invented facts.** Tools return "not found" instead of guessing; prompts tell agents to use only tool results and never to state a late-fee amount that isn't stored.
9. **A ticket can't be closed early.** It can't be marked resolved while one of its payments still waits for the manager.
10. **The original data is protected.** Agents work on `campus_customs_new.db`; `campus_customs.db` is only read when the manager resets.
11. **Full audit.** Every tool call, result and handoff is logged with time and agent, append-only, so any action can be traced afterward.

### Limits that keep token use in check (`backend/models.py`)

| Limit | Value | Why |
|---|---|---|
| Model calls per ticket (all agents together) | 40 | Stops runaway loops; sub-agents share the Boss's count |
| Total tokens per ticket (all agents together) | 200,000 | Hard cost cap for one ticket |
| Handoffs per ticket | 10 | Stops agents passing work around in circles |
| Handoff depth | 3 (Boss → A → B → C) | Keeps chains short |
| No handoff back up the chain | refused | An agent can't hand work to an agent already above it |
| Output tokens per reply | 1,500 | Keeps answers short |
| Tool result text in the audit | 1,500 characters | Keeps the audit file small |

If a ticket hits a limit, the run stops, the audit records `stopped_at_limit`, and the ticket stays open for a person to look at.

## 6. Backend routes (Problem 7)

`backend/main.py` (FastAPI). Start it from `backend/` with `uvicorn main:app --reload --port 8000`. CORS allows the React board at `http://localhost:5173` (and `127.0.0.1:5173`).

| Route | What it does |
|---|---|
| `GET /api/tickets` | Returns the three tickets and whether each is open, waiting_on_approval, held or resolved |
| `POST /api/tickets/{id}/run` | Runs the agent team on that ticket (Boss first) in the background; returns a run id. Refused while another run is going. |
| `POST /api/tickets/{id}/final-check` | Asks the Boss to re-inspect a ticket and set its status, without re-running the whole team (a button on the board) |
| `GET /api/runs/{run_id}` | Status of a run and the Boss's final decision |
| `GET /api/events?ticket_id=&run_id=&after=` | Recent agent events from the audit trail: what each agent said, which tools it used, handoffs and reports; poll with `after` for new ones |
| `GET /api/approvals` | Payments the agents prepared for the store manager (waiting and decided) |
| `POST /api/approvals/{id}/decide` | **The only route that moves cash.** Only the store manager (David) can approve (pays: checking goes down, payment recorded with his name, invoice marked paid) or reject. Refuses a negative balance. After an approval the Boss's final check on that ticket runs automatically. |
| `GET /api/cash` | Current checking balance from `cash_accounts`, plus payments waiting |
| `GET /api/drafts?ticket_id=` | Drafted messages and bills (to Tauhid, the Yale AI Club, the landlord); never sent |
| `POST /api/reset` | Copies `campus_customs.db` over `campus_customs_new.db` for a fresh run; refused while a run is going |
| `GET /api/health` | Model in use (gpt-6-luna), store manager, whether the Portkey key is set |

The agents still get every shop fact through the MCP server. The backend reads the database directly only to show the board its lists and for the two human-only actions (deciding a payment, resetting).

## 7. Dashboard (Problem 8)

`frontend/` (React + Vite + TypeScript). Start with `npm install` then `npm run dev` in `frontend/`, open http://localhost:5173. It calls the backend at http://localhost:8000 every 2–2.5 seconds: tickets, cash, approvals and drafts from their routes, and the conversation from `/api/events`. The layout is a shop counter: ticket stubs on the left (with **Send to the team**), the agents' conversation in the center (each agent in its own color and apparel icon, plus the Boss's decision card and "What each agent did"), and the manager's side on the right (checking balance, payments waiting for David with Approve/Reject, drafts). Design choices are in `output/design.md`.


## 8. The full run (Problem 9)

Run on 2026-11-06 from the board, after **Reset the shop** (checking started at **$3,400.00**). Order: 101 → David approves $840 → 102 → 103 → David approves $374. After each approval, the Boss's final check ran automatically.

| Ticket | Boss's first call | Agent-to-agent handoff | Final status | Cash change | Model calls / tokens (first run) |
|---|---|---|---|---|---|
| 101 | Inventory | Inventory → Accounting | resolved | −$840.00 (invoice 501) | 21 / 64,518 |
| 102 | Facilities | none (Facilities checked cash itself) | held | $0 | 10 / 26,759 |
| 103 | Inventory | Inventory → Accounting | resolved | −$374.00 (invoice 502) | 20 / 67,484 |

**Ending checking: $2,186.00**, matching `cash_accounts` in `data/campus_customs_new.db` (two `payments` rows, both `approved_by` David). Details: `output/desk_tickets.html` (Actual and Cash tabs), `output/resolved_tickets.json`, `output/resolved_board.html`, and every step in `output/audit_trail.json`.

**Fix during the run:** the first automatic final check on ticket 101 left it `open` "pending tee arrival." The Boss prompt now says a future delivery date is a scheduled follow-up, not a reason to keep a ticket open, and the board got an **Ask the Boss for a final check** button (`POST /api/tickets/{id}/final-check`). The second check resolved 101, and ticket 103 resolved on its first final check.
