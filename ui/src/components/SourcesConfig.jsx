import { useState } from 'react'
import { Rss, Search, Power } from 'lucide-react'
import { toggleSource } from '../api.js'

const SourceRow = ({ source, onToggled }) => {
  const [busy, setBusy] = useState(false)

  const handle = async () => {
    setBusy(true)
    await toggleSource(source.id)
    onToggled()
    setBusy(false)
  }

  return (
    <div className={`flex items-center justify-between gap-3 border border-jr-border rounded-lg px-3 py-2.5 bg-jr-bg transition-opacity ${!source.enabled ? 'opacity-50' : ''}`}>
      <div className="flex items-center gap-3 min-w-0">
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
          source.type === 'search' ? 'bg-jr-purple-light text-jr-purple' : 'bg-jr-accent-light text-jr-accent'
        }`}>
          {source.type === 'search' ? <Search size={13} /> : <Rss size={13} />}
        </div>
        <div className="min-w-0">
          <div className="text-sm font-medium text-jr-text truncate">{source.name}</div>
          <div className="text-xs text-jr-muted font-mono">
            {source.last_count ?? 0} jobs · {source.last_fetched
              ? new Date(source.last_fetched + 'Z').toLocaleString('es-AR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
              : 'never fetched'}
          </div>
        </div>
      </div>
      <button
        onClick={handle}
        disabled={busy}
        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-all cursor-pointer ${busy ? 'opacity-50' : ''} ${
          source.enabled
            ? 'bg-jr-green-light border-green-200 text-jr-green hover:bg-jr-red-light hover:border-red-200 hover:text-jr-red'
            : 'bg-jr-bg border-jr-border text-jr-muted hover:bg-jr-accent-light hover:border-indigo-200 hover:text-jr-accent'
        }`}
      >
        <Power size={11} />
        {source.enabled ? 'Enabled' : 'Disabled'}
      </button>
    </div>
  )
}

export default function SourcesConfig({ sources, onUpdate }) {
  const rss = sources.filter(s => s.type !== 'search')
  const ai = sources.filter(s => s.type === 'search')

  return (
    <div className="card p-5 space-y-5">
      <div>
        <h2 className="text-sm font-semibold text-jr-text">Job Sources</h2>
        <p className="text-xs text-jr-sub mt-0.5">Disable a source to skip it on the next scan cycle</p>
      </div>

      {sources.length === 0 ? (
        <div className="text-center py-10 text-xs text-jr-muted">No sources registered yet — run a scan first</div>
      ) : (
        <>
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-medium text-jr-sub uppercase tracking-wide">
              <Rss size={11} />RSS / API Feeds ({rss.length})
            </div>
            {rss.map(s => <SourceRow key={s.id} source={s} onToggled={onUpdate} />)}
          </div>
          {ai.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-medium text-jr-sub uppercase tracking-wide">
                <Search size={11} />AI Search Sources ({ai.length})
              </div>
              {ai.map(s => <SourceRow key={s.id} source={s} onToggled={onUpdate} />)}
            </div>
          )}
        </>
      )}
    </div>
  )
}
