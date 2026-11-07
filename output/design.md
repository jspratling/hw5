# Dashboard design: the Campus Customs front desk

## What I asked for

A board that feels like a real shop front desk, inviting and easy to use. Each agent has its own color and its own icon from the world of apparel. The agents talking should stand out more than anything else. Colors: Yale blue, white and cream.

## Layout: a counter you stand behind

The page is laid out like a shop counter, left to right in the order the work happens:

```
┌───────────────── Yale blue awning (scalloped edge) ─────────────────┐
│ hanger  Campus Customs, Front desk, Monday, August 31, 2026  [Reset] │
└──────────────────────────────────────────────────────────────────────┘
┌ Tickets ───┐ ┌ The conversation (biggest) ───────┐ ┌ Manager ────────┐
│ #101 stub  │ │ Ticket 101, Bulldog tee   [5 icons]│ │ Checking $3,400 │
│ #102 stub  │ │ Boss: "Accounting goes first."     │ │ Waiting for     │
│ #103 stub  │ │   Accounting checked the cash …    │ │ David: $840     │
│            │ │ Accounting → Inventory: "…"        │ │ [Approve][Reject]│
│ [Send to   │ │ Boss's decision: Waiting on David  │ │ Drafts (never   │
│  the team] │ │ What each agent did (5 agents)     │ │ sent)           │
└────────────┘ └────────────────────────────────────┘ └─────────────────┘
```

- **Left: tickets on the desk.** Each ticket is a paper order stub with a big number, who it's from, a perforated tear line and a rubber-stamp status (Open, Waiting on David, Held, Resolved). The **Send to the team** button sits on the stub, so starting a ticket happens where the ticket is.
- **Center: the conversation.** The widest, whitest panel, because the agents talking is the point. It reads like a chat between coworkers at the desk.
- **Right: the manager's side.** The cash register, the tray of payments waiting for David, and the drafts.

## How the agents read differently

| Agent | Color | Icon | Why that icon |
|---|---|---|---|
| Boss | Yale blue | Necktie | The one in charge dresses the part |
| Inventory | Forest green | Hoodie | The stock on the shelves (the hoodies on ticket 103) |
| Accounting | Brass | Price tag | Prices, margins and bills |
| Facilities | Teal | Clothing rack | The shop floor and fixtures, the physical space |
| Customer Service | Raspberry | T-shirt | What the customer actually wears (Tauhid's tee) |

The icons are drawn by hand as simple line art, so they stay sharp at any size. Each agent's color shows up everywhere it appears: its round avatar, the stripe down the left of its speech bubble, its name, and the small icon on each tool it used. You can follow one agent through a long conversation by color alone, and the names are always written too, so color is never the only clue.

## How the conversation stands out

- **Speech bubbles are the biggest text on the page** (17px, larger than anything else except the register). Each one has the agent's avatar, name and the time.
- **Handoffs read like asking a coworker:** "Accounting, to Inventory: confirm stock for size S…", with the receiving agent's icon.
- **Tool use is quieter:** one small line in the agent's color in plain words ("Accounting prepared a payment for David"), with "What the tool returned" folded underneath for anyone who wants the raw facts.
- **The Boss's decision is a highlighted card** with a status stamp, blue while waiting, green when resolved, teal when held, so the result of each run is easy to find.
- **While the team works**, the active agent's avatar pulses in the strip at the top and a "the team is working" line shows at the bottom. New messages scroll into view inside the conversation box.
- **The final check after an approval** gets its own divider ("Final check after approval"), so the first look and the Boss's re-inspection are clearly separate.
- **"What each agent did"** sits under the conversation, one line per agent. Agents not needed on that ticket are faded and say so. That makes it visible that the Boss didn't send everyone.

## How cash and resolved tickets show up

- **The register** is a Yale blue block at the top right with the checking balance in large numbers. When a payment is approved it shows what the balance was and the change (for example "was $3,400.00, -$840.00") in gold, so the drop is impossible to miss. Payments still waiting are shown with what checking would be if David approves them.
- **Approvals:** each payment waiting for David is a small bill showing the payee, the amount in large type, why it's needed, which ticket and invoice it's for, who prepared it, and whether the Boss checked it. The approve button names the amount ("Approve $840.00"), and both buttons stay disabled until a name is typed. Only David is accepted by the backend. Paid bills move to a short list stamped "Paid by David."
- **Resolved tickets** get a green "Resolved" stamp on their stub and a green decision card in the conversation. Held tickets get a teal "Held" stamp.

## Creative choices that make it feel like a real shop

- **A striped Yale blue awning with a scalloped edge** across the top, like the awning over a storefront on Chapel Street, with a coat-hanger logo.
- **Cream counter, white paper:** the page background is a warm cream counter top, and everything you read (tickets, the conversation, bills) sits on white paper.
- **Paper ticket stubs** with a dashed tear line, punched notches and a slightly tilted rubber-stamp status.
- **A collegiate slab typeface (Bitter)** for headings and numbers, like a varsity sweater or a printed price card, paired with **Atkinson Hyperlegible** for everything you read, a typeface designed for clear reading.
- **Plain-language labels** everywhere ("Send to the team", "Waiting for David", "Drafts for this ticket… Nothing is ever sent") instead of technical tool names.

## Easy to use

- Works on a laptop, a narrow window and a phone (the columns stack).
- Keyboard focus is clearly outlined; motion is turned off for people who set "reduce motion".
- Reset needs a second click to confirm, so it can't happen by accident, and it's off while the team is working.
- If the backend isn't running, a banner says exactly which command starts it.
