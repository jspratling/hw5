# AI Prompts Log — Homework 5: Campus Customs Multi-Agent Operations

This file records what I typed to my vibe coder for each problem, in my own words.

---

## Problem 1: Vibe coder prompts

**Prompt(s) I typed:**

> find homework assignment assignment 5 from the github page

> lets start the homework assignment. download the necessary data. Also, get the last page which is the instructions page and begin with that

> Do all of this and proceed

> I need to read the instructions also

> Make sure you read and adhere to the scenario and rules of the shop. this must be done for the assignment and i want you to keep me on track to make sure nothing is missed. lets begin

> We have to have enough funds to fulfil the next order. do not pay the rent until i authorize it. order the hoodies to restock. the order for the Yale AI club needs to be COD. what other items am i missing that I need to address

> 2. I will accept terms of 2% net 10. 3. the vendor sends an invoice later. 4. pay the invoice. 5. pay for the order. 6. send 8 hoodies now and bill for the 20 and send the 12 when they are sent. 7. hold the rent until we get these order in and paid for. note that we will pay a late fee per the lease. 8. order an additional 5 hoodies for inventory

> 1. pay the bill 2. 2% net 10 on the entire order. 3. i will pay the regular lease terms.

**Follow-up (if needed) and what was missing after the first prompt:**

None needed.

---

## Problem 2: Study the Campus Customs database

**Prompt(s) I typed:**

> go through every table and its field, show tickets 101-103 connect to the other tables, and start output\harness.md with each tables fields. i do not understand the rest of the request. "why what matters to the agents"? that is to vague and broad to answer

**Follow-up (if needed) and what was missing after the first prompt:**

> Ok. walk me through each table line by line and will answer it

What was missing after the first prompt: The first answer was completed by AI so i went through each table line by line and gave my own set of instructions for the agent to follow.

---

## Problem 3: Build the MCP server

**Prompt(s) I typed:**

> check the stock for product size tickets 101 and 103. look up invoices and see if they have been paid. ticket 101. look up the rent invoice to see if it is paid or open. ticket 102

**Follow-up (if needed) and what was missing after the first prompt:**

None needed.

---

## Problem 4: Add the MCP server to the vibe coder and test each tool

**Prompt(s) I typed:**

> I am ok with using cursor or whatever i used in my previous homework assignments to complete this function. I want you to connect to cursor or one or the tool i used in previous homework assignments to test each of the three tools.

Test prompts I typed in Cursor:

> How many Classic Bulldog Tees in size S do we have?
> Has invoice 501 been paid, and is it overdue?
> Is the rent on lease 1 paid or still open?

> Add .mcp.json

**Follow-up (if needed) and what was missing after the first prompt:**

None needed.

---

## Problem 5: Build the agent team and grow the MCP tools

**Prompt(s) I typed:**

> This is how the team should work together: all new tasks come in to the boss. the boss decides who the task goes to. Any task that deals with orders, billing, inventory, sales, returns, invoices, leases go to accounting. Once every task is completed, it goes back to the boss agent for a final inspection and check to make sure the task in completed. Once the task is completed, the boss agent will determine if that task needs to be sent to another agent that has a different role but equally as important. the boss agent will send any facility and lease and rent related items to facilities. once completed, the task will be sent back to the boss agent for final inspection and completion. the boss will send the completed task to another agent if deemed necessary. the boss will send any items to customer service for questions that need to be answered. the draft will be completed and sent to the boss agent whom will inspect the response and send the drafted message. the boss will send any bills that need to be paid to the manager once verified by the boss agent and the manager will pay the invoices.

**Follow-up (if needed) and what was missing after the first prompt:**

> i ran the last test prompt in cursor

What was missing after the first prompt: the live test on ticket 102 worked (Facilities first, rent held, no payment), but the Boss handed the same task to Facilities twice and got two landlord notes, so duplicate handoffs now return the first report instead.

---

## Problem 6: Plan the three tickets

**Prompt(s) I typed:**

> proceed

(The Expected plans follow the team design I gave in Problem 5: everything goes to the Boss; orders, billing, sales and invoices go to Accounting; leases and rent go to Facilities; customer questions go to Customer Service; every result comes back to the Boss for final inspection; agents can hand work directly to each other.)

**Follow-up (if needed) and what was missing after the first prompt:**

None needed.

---

## Problem 7: Backend routes

**Prompt(s) I typed:**

> what type of items go in the backend? Answer that for me and i will give the prompts

> The backend should reset the database, check the balance, approve payments, run a ticket, list the tickets, give permission for the dashboard to call the backend, list payments for the manager to approve, show the drafts to read the messages to tauhid, a final check after an approval. 1. David. 2. The manager and reject or approve payments. 3. after an approval, the boss's final check should run automatically

**Follow-up (if needed) and what was missing after the first prompt:**

None needed.

---

## Problem 8: Agent dashboard

**Prompt(s) I typed:**

> I want it to feel like a real shop front desk that is inviting and easy to use. each agent should have its own color and an unique icon geared around apparel. the agents talking should stand out more. i love yale blue, white or cream.

**Follow-up (if needed) and what was missing after the first prompt:**

None needed.

---

## Problem 9: Resolve the tickets

**Prompt(s) I typed:**

> fix any issues to meet the requirements of the homework assignment. also proceed

> my cursor is open. proceed and take the next steps

> I give you permission to start this

(During the run I approved both payments as the store manager, David: "approved", then "1" to have Claude click Approve for me on the board.)

**Follow-up (if needed) and what was missing after the first prompt:**

> proceed

What was missing after the first prompt: after David approved the $840, the Boss's final check left ticket 101 open "pending tee arrival," so the Boss's prompt was changed so a future delivery date doesn't keep a ticket open, and a final-check button was added to the board.

---

## Problem 10: Reflection

**Prompt(s) I typed:**

> i would grade the agents 1-5 based on accuracy, returns, customer complaints, and sales that reach 61% margin. any area is a 1 point deduction. 2. each ticket was accurate with what was planned. 3. one agent is simplier because it can simplify the routing of the work and pinpoint any flaws in the system quicker. 4. 1. the work goes through on agent. 2. it simplifies the workflow process. 3. it puts more checks and balances in place. 4. it streamlines the process to make the order process quicker. the agents handle administrative and operations functionsl

**Follow-up (if needed) and what was missing after the first prompt:**

None needed.

---

## Problem 11: Submit to GitHub

**Prompt(s) I typed:**

> fix all this shit. you are stretching this assignment our entirely too long. get the to crux and finalize this assignment accurately

**Follow-up (if needed) and what was missing after the first prompt:**

None needed.
