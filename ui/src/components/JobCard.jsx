import { useState } from 'react'
import { ExternalLink, CheckCircle, Eye, X, Building2, MapPin, ChevronDown, ChevronUp } from 'lucide-react'
import { updateJobStatus, updateJobNotes } from '../api.js'

const STATUS = {
  new:       { badge: 'bg-jr-accent-light text-jr-accent',   border: 'border-l-jr-accent' },
  seen:      { badge: 'bg-jr-amber-light text-jr-amber',     border: 'border-l-jr-amber' },
  applied:   { badge: 'bg-jr-purple-light text-jr-purple',   border: 'border-l-jr-purple' },
  discarded: { badge: 'bg-jr-red-light text-jr-red',         border: 'border-l-jr-red' },
}

const MODE = {
  remote:  'bg-jr-green-light text-jr-green',
  hybrid:  'bg-jr-amber-light text-jr-amber',
  onsite:  'bg-jr-red-light text-jr-red',
  unknown: 'bg-jr-bg text-jr-muted',
}

const IconBtn = ({ onClick, title, icon: Icon, hoverClass }) => (
  <button
    onClick={onClick}
    title={title}
    className={`w-7 h-7 flex items-center justify-center rounded-lg text-jr-muted transition-colors cursor-pointer ${hoverClass}`}
  >
    <Icon size={14} />
  </button>
)

export default function JobCard({ job, onStatusChange }) {
  const [expanded, setExpanded] = useState(false)
  const [notes, setNotes] = useState(job.notes || '')
  const [saving, setSaving] = useState(false)

  const tags = (() => { try { return JSON.parse(job.tags || '[]') } catch { return [] } })()
  const s = STATUS[job.status] || STATUS.new

  const handleStatus = async status => {
    await updateJobStatus(job.id, status)
    onStatusChange(job.id, status)
  }

  const saveNotes = async () => {
    setSaving(true)
    await updateJobNotes(job.id, notes)
    setSaving(false)
  }

  const timeAgo = d => {
    if (!d) return null
    const diff = Math.floor((Date.now() - new Date(d)) / 86400000)
    if (diff === 0) return 'Today'
    if (diff === 1) return 'Yesterday'
    return `${diff}d ago`
  }

  return (
    <div className={`card border-l-2 ${s.border} px-4 py-3 animate-fade-in`}>
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 mb-1">
            <span className={`badge ${s.badge}`}>{job.status}</span>
            {job.work_mode && job.work_mode !== 'unknown' && (
              <span className={`badge ${MODE[job.work_mode] || MODE.unknown}`}>{job.work_mode}</span>
            )}
            <span className="text-xs text-jr-muted">{job.source}</span>
            {timeAgo(job.fetched_at) && (
              <span className="text-xs text-jr-muted">· {timeAgo(job.fetched_at)}</span>
            )}
          </div>

          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => job.status === 'new' && handleStatus('seen')}
            className="group flex items-center gap-1.5 text-jr-text font-medium text-sm hover:text-jr-accent transition-colors"
          >
            <span className="truncate">{job.title}</span>
            <ExternalLink size={11} className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
          </a>

          <div className="flex flex-wrap items-center gap-3 mt-0.5">
            {job.company && (
              <span className="flex items-center gap-1 text-xs text-jr-sub">
                <Building2 size={11} />{job.company}
              </span>
            )}
            {job.location && (
              <span className="flex items-center gap-1 text-xs text-jr-sub">
                <MapPin size={11} />{job.location}
              </span>
            )}
            {job.salary && (
              <span className="text-xs text-jr-green font-mono font-medium">{job.salary}</span>
            )}
          </div>

          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {tags.slice(0, 8).map(t => <span key={t} className="tag">{t}</span>)}
              {tags.length > 8 && <span className="tag">+{tags.length - 8}</span>}
            </div>
          )}
        </div>

        <div className="flex items-center gap-0.5 shrink-0">
          {job.status !== 'applied' && (
            <IconBtn onClick={() => handleStatus('applied')} title="Mark applied" icon={CheckCircle} hoverClass="hover:bg-jr-purple-light hover:text-jr-purple" />
          )}
          {job.status === 'new' && (
            <IconBtn onClick={() => handleStatus('seen')} title="Mark seen" icon={Eye} hoverClass="hover:bg-jr-amber-light hover:text-jr-amber" />
          )}
          {job.status !== 'discarded' && (
            <IconBtn onClick={() => handleStatus('discarded')} title="Discard" icon={X} hoverClass="hover:bg-jr-red-light hover:text-jr-red" />
          )}
          <IconBtn onClick={() => setExpanded(!expanded)} title="Expand" icon={expanded ? ChevronUp : ChevronDown} hoverClass="hover:bg-jr-bg hover:text-jr-text" />
        </div>
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-jr-border space-y-3 animate-slide-in">
          {job.description && (
            <p className="text-sm text-jr-sub leading-relaxed">
              {job.description.slice(0, 500)}{job.description.length > 500 ? '…' : ''}
            </p>
          )}
          <div>
            <label className="text-xs font-medium text-jr-sub uppercase tracking-wide block mb-1.5">Notes</label>
            <div className="flex gap-2">
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                rows={2}
                placeholder="Add notes…"
                className="flex-1 text-sm border border-jr-border rounded-lg px-3 py-2 bg-jr-bg text-jr-text placeholder-jr-muted resize-none focus:outline-none focus:border-jr-accent focus:ring-1 focus:ring-jr-accent/20"
              />
              <button onClick={saveNotes} disabled={saving} className="btn-primary self-end text-xs">
                {saving ? '…' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
