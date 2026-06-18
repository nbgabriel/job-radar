import { RefreshCw } from 'lucide-react'

const Stat = ({ label, value, sub, color }) => (
  <div className="card p-4">
    <div className={`text-2xl font-semibold tracking-tight ${color}`}>{value ?? '—'}</div>
    <div className="text-xs text-jr-sub mt-0.5">{label}</div>
    {sub && <div className="text-xs text-jr-muted mt-0.5 font-mono">{sub}</div>}
  </div>
)

export default function StatsPanel({ stats, onScan, scanning }) {
  if (!stats) return null

  const lastFetch = stats.last_fetch?.finished_at
    ? new Date(stats.last_fetch.finished_at).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
    : null

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-jr-green animate-pulse" />
          <span className="text-xs text-jr-sub font-medium">System active</span>
          {lastFetch && <span className="text-xs text-jr-muted">· Last scan {lastFetch}</span>}
        </div>
        <button
          onClick={onScan}
          disabled={scanning}
          className="btn-ghost text-xs"
        >
          <RefreshCw size={12} className={scanning ? 'animate-spin' : ''} />
          {scanning ? 'Scanning…' : 'Scan now'}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Total listings" value={stats.total} sub={`+${stats.today ?? 0} today`} color="text-jr-text" />
        <Stat label="New / Unread" value={stats.new} color="text-jr-accent" />
        <Stat label="Seen" value={stats.seen} color="text-jr-amber" />
        <Stat label="Applied" value={stats.applied} sub={stats.last_fetch?.new_jobs ? `${stats.last_fetch.new_jobs} new last scan` : null} color="text-jr-purple" />
      </div>
    </div>
  )
}
