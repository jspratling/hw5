// Talks to the FastAPI backend (Problem 7).
export const API_BASE = 'http://localhost:8000'

export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  status: 'open' | 'waiting_on_approval' | 'held' | 'resolved'
  created_at: string
  resolved: boolean
}

export interface RunInfo {
  run_id: string
  ticket_id: number
  kind: 'run_ticket' | 'final_check'
  status: string
  decision: BossDecision | null
  error: string | null
}

export interface BossDecision {
  ticket_id: number
  status: string
  outcome: string
  agent_contributions: { agent: AgentName; what_they_did: string }[]
  approvals_for_manager: string[]
  drafts_approved: number[]
  open_items: string[]
}

export interface AgentEvent {
  index: number
  run_id: string
  ticket_id: number
  time: string
  agent: AgentName
  kind: string
  step: number
  depth?: number
  tool?: string
  args?: Record<string, unknown>
  result?: string
  to?: AgentName
  task?: string
  reason?: string
  text?: string
  report?: { agent: AgentName; summary: string; actions_taken?: string[]; waiting_on?: string[] }
  decision?: BossDecision | null
  status?: string
  error?: string | null
  prompt?: string
}

export interface Approval {
  id: number
  ticket_id: number | null
  kind: string
  ref_id: number
  payee: string
  amount: number
  reason: string
  prepared_by: AgentName
  verified_by_boss: number
  status: 'pending' | 'paid' | 'rejected' | 'refused'
  decided_by: string | null
}

export interface Draft {
  id: number
  ticket_id: number | null
  kind: string
  author: AgentName
  recipient: string
  subject: string
  body: string
  status: 'draft' | 'approved_by_boss'
}

export interface Cash {
  balance: number
  balance_date: string
  today: string
  pending_approvals_total: number
  available_after_pending: number
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API_BASE + path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${res.status})`)
  return body as T
}

export const api = {
  tickets: () => call<{ today: string; tickets: Ticket[]; running: RunInfo[] }>('/api/tickets'),
  run: (id: number) => call<RunInfo>(`/api/tickets/${id}/run`, { method: 'POST' }),
  finalCheck: (id: number) => call<RunInfo>(`/api/tickets/${id}/final-check`, { method: 'POST' }),
  events: (ticketId: number) => call<{ events: AgentEvent[]; next: number }>(`/api/events?ticket_id=${ticketId}&limit=400`),
  cash: () => call<Cash>('/api/cash'),
  approvals: () => call<{ approvals: Approval[]; waiting: Approval[]; store_manager: string }>('/api/approvals'),
  decide: (id: number, manager_name: string, approve: boolean) =>
    call<{ status: string; checking_after?: number; final_check?: RunInfo | null }>(
      `/api/approvals/${id}/decide`, { method: 'POST', body: JSON.stringify({ manager_name, approve }) }),
  drafts: () => call<{ drafts: Draft[] }>('/api/drafts'),
  reset: () => call<{ reset: boolean; checking: number }>('/api/reset', { method: 'POST' }),
}
