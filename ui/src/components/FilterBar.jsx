import { Search, X } from 'lucide-react'

const STATUSES = ['all', 'new', 'seen', 'applied', 'discarded']
const MODES = ['all', 'remote', 'hybrid', 'onsite']

const FilterBtn = ({ active, onClick, children, activeClass }) => (
  <button
    onClick={onClick}
    className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors border cursor-pointer ${
      active ? activeClass : 'bg-transparent border-transparent text-jr-sub hover:text-jr-text hover:bg-jr-bg'
    }`}
  >
    {children}
  </button>
)

export default function FilterBar({ filters, onChange, sources, total }) {
  const set = (k, v) => onChange({ ...filters, [k]: v === 'all' ? '' : v })

  const STATUS_ACTIVE = {
    new: 'bg-jr-accent-light border-indigo-200 text-jr-accent',
    seen: 'bg-jr-amber-light border-amber-200 text-jr-amber',
    applied: 'bg-jr-purple-light border-purple-200 text-jr-purple',
    discarded: 'bg-jr-red-light border-red-200 text-jr-red',
    all: 'bg-jr-bg border-jr-border text-jr-text',
  }

  const active = filters.status || 'all'

  return (
    <div className="card px-4 py-3 flex flex-wrap items-center gap-3">
      <div className="relative flex-1 min-w-[180px]">
        <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-jr-muted" />
        <input
          type="text"
          value={filters.search || ''}
          onChange={e => onChange({ ...filters, search: e.target.value })}
          placeholder="Search title, company…"
          className="w-full pl-8 pr-7 py-1.5 text-sm border border-jr-border rounded-lg bg-jr-bg text-jr-text placeholder-jr-muted focus:outline-none focus:border-jr-accent focus:ring-1 focus:ring-jr-accent/20"
        />
        {filters.search && (
          <button onClick={() => onChange({ ...filters, search: '' })} className="absolute right-2 top-1/2 -translate-y-1/2 text-jr-muted hover:text-jr-text">
            <X size={12} />
          </button>
        )}
      </div>

      <div className="flex items-center gap-0.5 bg-jr-bg border border-jr-border rounded-lg p-0.5">
        {STATUSES.map(s => (
          <FilterBtn key={s} active={active === s} onClick={() => set('status', s)} activeClass={STATUS_ACTIVE[s] || STATUS_ACTIVE.all}>
            {s}
          </FilterBtn>
        ))}
      </div>

      <div className="flex items-center gap-0.5 bg-jr-bg border border-jr-border rounded-lg p-0.5">
        {MODES.map(m => (
          <FilterBtn key={m} active={(filters.work_mode || 'all') === m} onClick={() => set('work_mode', m)} activeClass="bg-jr-green-light border-green-200 text-jr-green">
            {m}
          </FilterBtn>
        ))}
      </div>

      {sources?.length > 0 && (
        <select
          value={filters.source || ''}
          onChange={e => onChange({ ...filters, source: e.target.value })}
          className="text-xs border border-jr-border rounded-lg px-2.5 py-1.5 bg-jr-bg text-jr-sub focus:outline-none focus:border-jr-accent"
        >
          <option value="">All sources</option>
          {sources.map(s => (
            <option key={s.name} value={s.name}>{s.name} ({s.last_count ?? 0})</option>
          ))}
        </select>
      )}

      <span className="text-xs text-jr-muted ml-auto font-mono">{total} results</span>
    </div>
  )
}
