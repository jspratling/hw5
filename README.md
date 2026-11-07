# Homework 5 — Campus Customs Multi-Agent Operations

An MCP server, a FastAPI backend with a five-agent team (Boss, Inventory, Accounting, Facilities, Customer Service), and a React dashboard where a human watches the agents work tickets and approves payments.

> This README is a starting outline. The run steps get filled in as each piece is built.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then put your PORTKEY_API_KEY in .env
```

## Reset the database (clean run)

`data/campus_customs.db` is the original and is never changed. Everything runs against the working copy `data/campus_customs_new.db`. To start clean, copy the original over the working copy:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

Windows PowerShell:

```powershell
Copy-Item data\campus_customs.db data\campus_customs_new.db -Force
```

Always reset before a full three-ticket run.

## Quick start on Windows

Double-click `start-backend.bat`, then `start-frontend.bat` (leave both windows open), and open http://localhost:5173.

## The MCP server

The agents start it on their own (`mcp_server/server.py`), so you don't need to run it for the board. To use it from Cursor or Claude Code, the project's `.cursor/mcp.json` and `.mcp.json` already point at it. To start it by hand:

```bash
python mcp_server/server.py
```

## Start the FastAPI backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The backend runs at http://localhost:8000 (route list at http://localhost:8000/docs). It needs `PORTKEY_API_KEY` in `.env`; only the store manager in `STORE_MANAGER` (David) can approve or reject payments. You can also reset from the board, or with `POST /api/reset`.

## Start the React board

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Pick a ticket and press **Send to the team** to watch the agents work. When a payment waits for approval, type the store manager's name (David) and press **Approve** or **Reject**; after an approval the Boss's final check runs by itself. **Reset the shop** (top right) copies the original database over the working copy.
