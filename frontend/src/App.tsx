import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, type AgentEvent, type AgentName, type Approval, type Cash, type Draft, type RunInfo, type Ticket } from './api'
import { AGENTS, AGENT_ORDER, AgentIcon, Avatar } from './agents'

const money = (n: number) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
const clock = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', second: '2-digit' })
const longDate = (d: string) =>
  new Date(d + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })

const STATUS_LABEL: Record<string, string> = {
  open: 'Open',
  waiting_on_approval: 'Waiting on David',
  held: 'Held',
  resolved: 'Resolved',
}

const TICKET_KIND: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Bulk price request',
}

// Plain-language names for the MCP tools, as the manager would say them.
const TOOL_LABEL: Record<string, string> = {
  list_tickets: 'looked at the ticket board',
  get_ticket: 'read the ticket',
  check_stock: 'checked stock',
  quote_order: 'priced the order',
  get_vendors: 'checked vendors and lead times',
  get_invoice_status: 'looked up the invoice',
  list_open_invoices: 'listed unpaid invoices',
  get_rent_status: 'looked up the rent',
  get_cash_balance: 'checked the cash',
  list_pending_approvals: 'checked the approval tray',
  list_drafts: 'read the drafts',
  prepare_payment: 'prepared a payment for David',
  verify_payment: 'verified a payment',
  place_restock_order: 'placed a restock order',
  record_shipment: 'shipped stock',
  save_draft: 'saved a draft',
  approve_draft: 'approved a draft',
  set_ticket_status: 'updated the ticket status',
}

function argsLine(args?: Record<string, unknown>): string {
  if (!args) return ''
  const skip = new Set(['prepared_by', 'ordered_by', 'shipped_by', 'author', 'body', 'reason', 'summary', 'boss_note'])
  return Object.entries(args)
    .filter(([k]) => !skip.has(k))
    .map(([k, v]) => `${k.replace(/_/g, ' ')} ${String(v)}`)
    .join(', ')
}

function prettyJson(text?: string): string {
  if (!text) return ''
  try { return JSON.stringify(JSON.parse(text), null, 2) } catch { return text }
}

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [today, setToday] = useState('')
  const [running, setRunning] = useState<RunInfo[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [cash, setCash] = useState<Cash | null>(null)
  const [prevBalance, setPrevBalance] = useState<number | null>(null)
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [manager, setManager] = useState('David')
  const [managerInput, setManagerInput] = useState('')
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [notice, setNotice] = useState<{ tone: 'good' | 'bad'; text: string } | null>(null)
  const [offline, setOffline] = useState(false)
  const [confirmReset, setConfirmReset] = useState(false)
  const feedRef = useRef<HTMLDivElement>(null)
  const lastCount = useRef(0)

  const refresh = useCallback(async () => {
    try {
      const [t, c, a, d] = await Promise.all([api.tickets(), api.cash(), api.approvals(), api.drafts()])
      setTickets(t.tickets)
      setToday(t.today)
      setRunning(t.running)
      setCash(prev => {
        if (prev && prev.balance !== c.balance) setPrevBalance(prev.balance)
        return c
      })
      setApprovals(a.approvals)
      setManager(a.store_manager)
      setDrafts(d.drafts)
      setSelected(s => s ?? t.tickets[0]?.id ?? null)
      setOffline(false)
    } catch {
      setOffline(true)
    }
  }, [])

  const refreshEvents = useCallback(async (ticketId: number) => {
    try {
      const e = await api.events(ticketId)
      setEvents(e.events)
    } catch { /* shown by the offline banner */ }
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 2500)
    return () => clearInterval(id)
  }, [refresh])

  useEffect(() => {
    if (selected == null) return
    refreshEvents(selected)
    const id = setInterval(() => refreshEvents(selected), 2000)
    return () => clearInterval(id)
  }, [selected, refreshEvents])

  useEffect(() => {
    const feed = feedRef.current
    // Follow new messages inside the conversation box only (never jump the whole page).
    if (feed && events.length > lastCount.current && feed.scrollHeight > feed.clientHeight + 4) {
      feed.scrollTo({ top: feed.scrollHeight, behavior: 'smooth' })
    }
    lastCount.current = events.length
  }, [events.length])

  const busy = running.length > 0
  const ticket = tickets.find(t => t.id === selected) || null
  const waiting = approvals.filter(a => a.status === 'pending')
  const decided = approvals.filter(a => a.status !== 'pending')
  const ticketDrafts = drafts.filter(d => d.ticket_id === selected)

  // Group the feed into runs (first look, then the Boss's final check after David approves).
  const runs = useMemo(() => {
    const byRun = new Map<string, AgentEvent[]>()
    for (const e of events) {
      if (!byRun.has(e.run_id)) byRun.set(e.run_id, [])
      byRun.get(e.run_id)!.push(e)
    }
    // Order by when it happened (an agent's remarks are saved after its turn ends).
    const when = (e: AgentEvent) => Date.parse(e.time) || 0
    return [...byRun.entries()].map(([id, evs]) => ({
      id, events: [...evs].sort((a, b) => when(a) - when(b) || a.index - b.index),
    }))
  }, [events])

  // What each agent did on this ticket: Boss's final contributions, else each agent's last report.
  const summary = useMemo(() => {
    const out = new Map<AgentName, string>()
    const finished = [...events].reverse().find(e => e.kind === 'ticket_finished' && e.decision)
    finished?.decision?.agent_contributions.forEach(c => out.set(c.agent, c.what_they_did))
    for (const e of events) if (e.kind === 'report' && e.report && !out.has(e.agent)) out.set(e.agent, e.report.summary)
    if (finished?.decision && !out.has('boss')) out.set('boss', finished.decision.outcome)
    return out
  }, [events])

  async function runTicket(id: number) {
    setNotice(null)
    setSelected(id)
    try {
      await api.run(id)
      setNotice({ tone: 'good', text: `Ticket ${id} is with the team. The Boss is reading it now.` })
      refresh()
    } catch (e) {
      setNotice({ tone: 'bad', text: (e as Error).message })
    }
  }

  async function finalCheck(id: number) {
    setNotice(null)
    try {
      await api.finalCheck(id)
      setNotice({ tone: 'good', text: `The Boss is doing a final check on ticket ${id}.` })
      refresh()
    } catch (e) {
      setNotice({ tone: 'bad', text: (e as Error).message })
    }
  }

  async function decide(a: Approval, approve: boolean) {
    setNotice(null)
    try {
      const r = await api.decide(a.id, managerInput, approve)
      setNotice({
        tone: 'good',
        text: approve
          ? `Paid ${money(a.amount)} to ${a.payee}. Checking is now ${money(r.checking_after ?? 0)}. The Boss is doing the final check.`
          : `Rejected the ${money(a.amount)} payment to ${a.payee}.`,
      })
      if (a.ticket_id) setSelected(a.ticket_id)
      refresh()
    } catch (e) {
      setNotice({ tone: 'bad', text: (e as Error).message })
    }
  }

  async function reset() {
    if (!confirmReset) { setConfirmReset(true); return }
    setConfirmReset(false)
    try {
      const r = await api.reset()
      setPrevBalance(null)
      setNotice({ tone: 'good', text: `Shop reset to the original data. Checking is back to ${money(r.checking)}.` })
      refresh()
    } catch (e) {
      setNotice({ tone: 'bad', text: (e as Error).message })
    }
  }

  return (
    <div className="shop">
      <header className="awning">
        <div className="brand">
          <svg className="hanger" viewBox="0 0 48 32" aria-hidden="true">
            <path d="M24 9.5c0-3.2 4.4-3.2 4.4-6.2 0-1.8-1.6-3-3.4-3S22 1.4 22 3.1" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
            <path d="M24 9.5 3 24.5h42z" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinejoin="round" />
          </svg>
          <div>
            <h1>Campus Customs</h1>
            <p>Front desk{today ? ` · ${longDate(today)}` : ''}</p>
          </div>
        </div>
        <div className="awning-actions">
          <button className={`btn ghost ${confirmReset ? 'warn' : ''}`} onClick={reset} disabled={busy}
                  onBlur={() => setConfirmReset(false)}>
            {confirmReset ? 'Click again to reset the shop' : 'Reset the shop'}
          </button>
        </div>
      </header>
      <div className="scallop" aria-hidden="true" />

      {offline && (
        <div className="banner bad">The desk can't reach the backend. Start it in <code>backend/</code> with <code>uvicorn main:app --reload --port 8000</code>.</div>
      )}
      {notice && <div className={`banner ${notice.tone}`} role="status">{notice.text}</div>}

      <main className="counter">
        {/* ------------------------------------------------ ticket rail */}
        <aside className="rail" aria-label="Tickets">
          <h2>Tickets on the desk</h2>
          <ul>
            {tickets.map(t => {
              const isRunning = running.some(r => r.ticket_id === t.id)
              return (
                <li key={t.id}>
                  <div className={`stub ${selected === t.id ? 'on' : ''} s-${t.status}`}>
                    <button className="stub-body" onClick={() => setSelected(t.id)} aria-pressed={selected === t.id}>
                      <span className="stub-no">#{t.id}</span>
                      <span className="stub-kind">{TICKET_KIND[t.type] || t.type}</span>
                      <span className="stub-subject">{t.subject}</span>
                      <span className="stub-from">from {t.requester}</span>
                    </button>
                    <div className="stub-foot">
                      <span className={`stamp s-${t.status}`}>{isRunning ? 'Working…' : STATUS_LABEL[t.status] || t.status}</span>
                      {t.status === 'open' && (
                        <button className="btn small" disabled={busy} onClick={() => runTicket(t.id)}>
                          Send to the team
                        </button>
                      )}
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        </aside>

        {/* ------------------------------------------------ the conversation */}
        <section className="talk" aria-label="Agent conversation">
          <div className="talk-head">
            <div>
              <h2>{ticket ? `Ticket ${ticket.id} · ${ticket.subject}` : 'The team'}</h2>
              <p>{ticket ? `${TICKET_KIND[ticket.type] || ticket.type} from ${ticket.requester}` : ''}</p>
            </div>
            {ticket && runs.length > 0 && ticket.status !== 'resolved' && (
              <button className="btn small check" disabled={busy} onClick={() => finalCheck(ticket.id)}>
                Ask the Boss for a final check
              </button>
            )}
            <div className="team-strip" aria-label="Agents">
              {AGENT_ORDER.map(a => {
                const active = busy && runs.at(-1)?.events.at(-1)?.agent === a
                return <span key={a} className={active ? 'live' : ''}><Avatar agent={a} size={34} /></span>
              })}
            </div>
          </div>

          <div className="feed" aria-live="polite" ref={feedRef}>
            {runs.length === 0 && (
              <div className="empty">
                <p>No one has worked this ticket yet.</p>
                {ticket?.status === 'open' && <p>Press <b>Send to the team</b> and the Boss will pick it up.</p>}
              </div>
            )}
            {runs.map(run => (
              <div key={run.id} className="run">
                {run.events.map(e => <Line key={e.index} e={e} />)}
              </div>
            ))}
            {busy && running.some(r => r.ticket_id === selected) && (
              <div className="typing"><span /><span /><span /> the team is working</div>
            )}
          </div>

          <div className="did">
            <h3>What each agent did</h3>
            <ul>
              {AGENT_ORDER.map(a => (
                <li key={a} className={summary.has(a) ? '' : 'idle'}>
                  <Avatar agent={a} size={28} />
                  <div>
                    <b className={`n-${a}`}>{AGENTS[a].label}</b>
                    <span>{summary.get(a) || 'Not needed on this ticket'}</span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* ------------------------------------------------ manager's side */}
        <aside className="tray" aria-label="Manager">
          <div className="register">
            <h2>Checking</h2>
            <div className="till">{cash ? money(cash.balance) : '—'}</div>
            {prevBalance != null && cash && prevBalance !== cash.balance && (
              <div className="change">was {money(prevBalance)} · {money(cash.balance - prevBalance)}</div>
            )}
            {cash && cash.pending_approvals_total > 0 && (
              <div className="pending">{money(cash.pending_approvals_total)} waiting for approval · {money(cash.available_after_pending)} if approved</div>
            )}
          </div>

          <div className="approvals">
            <h2>Waiting for {manager}</h2>
            {waiting.length === 0 && <p className="quiet">No payments are waiting. Agents prepare payments here; only {manager} can pay them.</p>}
            {waiting.length > 0 && (
              <label className="who">
                Your name
                <input value={managerInput} onChange={e => setManagerInput(e.target.value)} placeholder={`${manager}, the store manager`} autoComplete="name" />
              </label>
            )}
            {waiting.map(a => (
              <div key={a.id} className="bill">
                <div className="bill-top">
                  <b>{a.payee}</b>
                  <span className="amt">{money(a.amount)}</span>
                </div>
                <p>{a.reason}</p>
                <p className="meta">
                  Ticket {a.ticket_id}, {a.kind === 'invoice' ? `invoice ${a.ref_id}` : `lease ${a.ref_id}`}. Prepared by {AGENTS[a.prepared_by]?.label}
                  {a.verified_by_boss ? ', checked by the Boss.' : '.'}
                </p>
                <div className="bill-actions">
                  <button className="btn pay" disabled={busy || !managerInput.trim()} onClick={() => decide(a, true)}>Approve {money(a.amount)}</button>
                  <button className="btn ghost dark" disabled={busy || !managerInput.trim()} onClick={() => decide(a, false)}>Reject</button>
                </div>
              </div>
            ))}
            {decided.length > 0 && (
              <ul className="paid">
                {decided.map(a => (
                  <li key={a.id}><span>{a.payee} {money(a.amount)}</span><span className={`stamp s-${a.status}`}>{a.status === 'paid' ? `Paid by ${a.decided_by}` : a.status}</span></li>
                ))}
              </ul>
            )}
          </div>

          <div className="drafts">
            <h2>Drafts for this ticket</h2>
            {ticketDrafts.length === 0 && <p className="quiet">Messages and bills the agents write show up here. Nothing is ever sent.</p>}
            {ticketDrafts.map(d => (
              <details key={d.id} className="note">
                <summary>
                  <Avatar agent={d.author} size={24} />
                  <span><b>To {d.recipient}</b><small>{d.subject}</small></span>
                  <em className={d.status === 'approved_by_boss' ? 'ok' : ''}>{d.status === 'approved_by_boss' ? 'Approved by the Boss' : 'Draft'}</em>
                </summary>
                <pre>{d.body}</pre>
              </details>
            ))}
          </div>
        </aside>
      </main>

      <footer className="foot">
        Every agent runs on gpt-6-luna. Drafts stay on this board, and only {manager} can move money.
      </footer>
    </div>
  )
}

function Line({ e }: { e: AgentEvent }) {
  const name = AGENTS[e.agent]?.label || e.agent
  switch (e.kind) {
    case 'ticket_started':
      return <div className="divider"><span>{e.prompt?.includes('final inspection') ? 'Final check after approval' : 'Ticket sent to the team'} · {clock(e.time)}</span></div>
    case 'handoff':
      return (
        <Bubble agent={e.agent} name={name} time={e.time}>
          <div className="handoff">
            <span className="to">to <Avatar agent={e.to!} size={20} /> <b className={`n-${e.to}`}>{AGENTS[e.to!]?.label}</b></span>
            <p>{e.task}</p>
          </div>
        </Bubble>
      )
    case 'report':
      return (
        <Bubble agent={e.agent} name={name} time={e.time} tone="report">
          <p>{e.report?.summary}</p>
          {!!e.report?.actions_taken?.length && <ul className="acts">{e.report.actions_taken.map((a, i) => <li key={i}>{a}</li>)}</ul>}
          {!!e.report?.waiting_on?.length && <p className="wait">Waiting on: {e.report.waiting_on.join('; ')}</p>}
        </Bubble>
      )
    case 'said':
      return <Bubble agent={e.agent} name={name} time={e.time}><p>{e.text}</p></Bubble>
    case 'tool_call':
      return (
        <div className={`tool t-${e.agent}`}>
          <AgentIcon agent={e.agent} size={14} />
          <span><b>{name}</b> {TOOL_LABEL[e.tool || ''] || e.tool}{argsLine(e.args) ? ` (${argsLine(e.args)})` : ''}</span>
        </div>
      )
    case 'tool_result':
      return (
        <details className={`result t-${e.agent}`}>
          <summary>What the {e.tool?.replace(/_/g, ' ')} tool returned</summary>
          <pre>{prettyJson(e.result)}</pre>
        </details>
      )
    case 'handoff_refused':
    case 'handoff_repeat_skipped':
      return <div className="tool muted"><span>{name} tried to hand off again; the desk stopped the repeat.</span></div>
    case 'ticket_finished': {
      const d = e.decision
      return (
        <div className={`verdict s-${d?.status || e.status}`}>
          <Avatar agent="boss" size={36} />
          <div>
            <div className="verdict-top"><b>Boss's decision</b><span className={`stamp s-${d?.status}`}>{STATUS_LABEL[d?.status || ''] || e.status}</span></div>
            <p>{d?.outcome || e.error || 'The run stopped before the Boss decided.'}</p>
            {!!d?.approvals_for_manager?.length && <p className="wait">For David: {d.approvals_for_manager.join('; ')}</p>}
            {!!d?.open_items?.length && <p className="wait">Still open: {d.open_items.join('; ')}</p>}
          </div>
        </div>
      )
    }
    case 'error':
      return <div className="banner bad inline">Something broke: {e.error}</div>
    default:
      return null
  }
}

function Bubble({ agent, name, time, tone, children }: {
  agent: AgentName; name: string; time: string; tone?: 'report'; children: React.ReactNode
}) {
  return (
    <div className={`bubble b-${agent} ${tone || ''}`}>
      <Avatar agent={agent} size={40} />
      <div className="said">
        <div className="who-line"><b className={`n-${agent}`}>{name}</b><time>{clock(time)}</time></div>
        {children}
      </div>
    </div>
  )
}
