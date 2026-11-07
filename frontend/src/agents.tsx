import type { AgentName } from './api'

// Each agent has its own color (see styles.css --boss, --inventory, ...) and an apparel icon.
export const AGENTS: Record<AgentName, { label: string; role: string }> = {
  boss: { label: 'Boss', role: 'Routes every ticket, makes the final call' },
  inventory: { label: 'Inventory', role: 'Stock, restocks, shipping' },
  accounting: { label: 'Accounting', role: 'Invoices, cash, billing, margins' },
  facilities: { label: 'Facilities', role: 'Leases and rent' },
  customer_service: { label: 'Customer Service', role: 'Drafts messages to customers' },
}

export const AGENT_ORDER: AgentName[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

const stroke = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.7, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const }

// Hand-drawn apparel icons: necktie, hoodie, price tag, clothing rack, t-shirt.
export function AgentIcon({ agent, size = 22 }: { agent: AgentName; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      {agent === 'boss' && (
        <g {...stroke}>
          <path d="M9.5 2.8h5l-1.2 3.4h-2.6z" />
          <path d="M10.7 6.2 8.8 16.4l3.2 4.8 3.2-4.8-1.9-10.2" />
          <path d="M10 11.5l4-2" />
        </g>
      )}
      {agent === 'inventory' && (
        <g {...stroke}>
          <path d="M8.5 4.5C9.3 3 10.6 2.4 12 2.4s2.7.6 3.5 2.1l4 2.6-1.6 3.6-1.9-.9v10.8H8V9.8l-1.9.9-1.6-3.6z" />
          <path d="M9.2 4.8c.9 2 4.7 2 5.6 0" />
          <path d="M10 15.5h4v2.6h-4z" />
          <path d="M11 7.2v2.2M13 7.2v2.2" />
        </g>
      )}
      {agent === 'accounting' && (
        <g {...stroke}>
          <path d="M3.2 11.4V4.2a1 1 0 0 1 1-1h7.2l9.4 9.4a1 1 0 0 1 0 1.4l-7.2 7.2a1 1 0 0 1-1.4 0z" />
          <circle cx="7.6" cy="7.6" r="1.5" />
          <path d="M12.4 10.6c-1.2-.8-2.6.2-1.8 1.3.7 1 2.6.6 2.6 1.9 0 1.2-1.6 1.6-2.7.8M11.6 9.6l-.3-.4M12.6 15.2l.3.4" />
        </g>
      )}
      {agent === 'facilities' && (
        <g {...stroke}>
          <path d="M3 4.5h18M5 4.5V21M19 4.5V21M3.5 21h3M17.5 21h3" />
          <path d="M9 4.5v1.3M9 5.8l-2.6 2.6h5.2zM8.2 8.4l-.6 6.4h2.8l-.6-6.4" />
          <path d="M15 4.5v1.3M15 5.8l-2.6 2.6h5.2zM13.4 8.4v5.6h3.2V8.4" />
        </g>
      )}
      {agent === 'customer_service' && (
        <g {...stroke}>
          <path d="M8.6 3.3 3.4 6.1l2 4 2.6-1.1V21h8V9l2.6 1.1 2-4-5.2-2.8c-.5 1.6-1.8 2.4-3.4 2.4s-2.9-.8-3.4-2.4z" />
          <path d="M10 13.4h4M10 16h2.6" />
        </g>
      )}
    </svg>
  )
}

export function Avatar({ agent, size = 40 }: { agent: AgentName; size?: number }) {
  return (
    <span className={`avatar a-${agent}`} style={{ width: size, height: size }} title={AGENTS[agent].label}>
      <AgentIcon agent={agent} size={Math.round(size * 0.58)} />
    </span>
  )
}
