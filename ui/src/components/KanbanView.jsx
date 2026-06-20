import { useState } from 'react'
import { ExternalLink, Building2 } from 'lucide-react'
import { updateJobStatus } from '../api.js'

const COLS = [
  { id: 'new',       label: 'New',       accent: 'border-t-jr-accent',  count: 'bg-jr-accent-light text-jr-accent' },
  { id: 'seen',      label: 'Reviewing', accent: 'border-t-jr-amber',   count: 'bg-jr-amber-light text-jr-amber' },
  { id: 'applied',   label: 'Applied',   accent: 'border-t-jr-purple',  count: 'bg-jr-purple-light text-jr-purple' },
  { id: 'discarded', label: 'Discarded', accent: 'border-t-jr-red',     count: 'bg-jr-red-light text-jr-red' },
]

const MiniCard = ({ job, onDragStart, onDragEnd, isDragging }) => {
  const tags = (() => { try { return JSON.parse(job.tags || '[]') } catch { return [] } })()
  return (
    <div
      draggable
      onDragStart={e => onDragStart(e, job)}
      onDragEnd={onDragEnd}
      className={`bg-jr-surface border border-jr-border rounded-lg p-3 hover:border-jr-border-strong transition-colors group cursor-grab active:cursor-grabbing ${
        isDragging ? 'opacity-40' : ''
      }`}
    >
      <a href={job.url} target="_blank" rel="noopener noreferrer"
        className="text-sm font-medium text-jr-text hover:text-jr-accent transition-colors flex items-start gap-1.5">
        <span className="flex-1 leading-snug">{job.title}</span>
        <ExternalLink size={11} className="shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity" />
      </a>
      {job.company && (
        <div className="flex items-center gap-1 mt-1">
          <Building2 size={10} className="text-jr-muted" />
          <span className="text-xs text-jr-sub truncate">{job.company}</span>
        </div>
      )}
      <div className="flex flex-wrap gap-1 mt-2">
        {tags.slice(0, 3).map(t => <span key={t} className="tag">{t}</span>)}
      </div>
      <div className="flex items-center justify-between mt-2">
        <span className="text-xs text-jr-muted">{job.source}</span>
        {job.work_mode && job.work_mode !== 'unknown' && (
          <span className={`badge text-xs ${
            job.work_mode === 'remote' ? 'bg-jr-green-light text-jr-green' :
            job.work_mode === 'hybrid' ? 'bg-jr-amber-light text-jr-amber' : 'bg-jr-bg text-jr-muted'
          }`}>{job.work_mode}</span>
        )}
      </div>
    </div>
  )
}

export default function KanbanView({ jobs, onStatusChange }) {
  const [draggedJob, setDraggedJob] = useState(null)
  const [dragOverCol, setDragOverCol] = useState(null)

  const handleDragStart = (e, job) => {
    setDraggedJob(job)
    // Required for Firefox to allow the drag to start
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', job.id)
  }

  const handleDragEnd = () => {
    setDraggedJob(null)
    setDragOverCol(null)
  }

  const handleDragOver = (e, colId) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    if (dragOverCol !== colId) setDragOverCol(colId)
  }

  const handleDragLeave = (e, colId) => {
    // Only clear if we're actually leaving the column (not entering a child)
    if (e.currentTarget.contains(e.relatedTarget)) return
    if (dragOverCol === colId) setDragOverCol(null)
  }

  const handleDrop = async (e, colId) => {
    e.preventDefault()
    setDragOverCol(null)
    if (!draggedJob || draggedJob.status === colId) {
      setDraggedJob(null)
      return
    }
    // Optimistic update — UI reflects the move immediately
    onStatusChange(draggedJob.id, colId)
    setDraggedJob(null)
    try {
      await updateJobStatus(draggedJob.id, colId)
    } catch (err) {
      // Roll back on failure
      onStatusChange(draggedJob.id, draggedJob.status)
    }
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
      {COLS.map(col => {
        const items = jobs.filter(j => j.status === col.id)
        const isOver = dragOverCol === col.id
        return (
          <div
            key={col.id}
            onDragOver={e => handleDragOver(e, col.id)}
            onDragLeave={e => handleDragLeave(e, col.id)}
            onDrop={e => handleDrop(e, col.id)}
            className={`card border-t-2 ${col.accent} p-4 transition-colors ${
              isOver ? 'bg-jr-accent-light/30 ring-2 ring-jr-accent/30' : ''
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-jr-text">{col.label}</span>
              <span className={`text-xs font-mono px-2 py-0.5 rounded-full ${col.count}`}>{items.length}</span>
            </div>
            <div className="space-y-2 max-h-[65vh] overflow-y-auto pr-0.5 min-h-[80px]">
              {items.length === 0
                ? (
                  <div className={`text-xs text-center py-8 rounded-lg border-2 border-dashed transition-colors ${
                      isOver ? 'border-jr-accent text-jr-accent' : 'border-transparent text-jr-muted'
                    }`}>
                    {isOver ? 'Drop here' : '— empty —'}
                  </div>
                )
                : items.map(j => (
                  <MiniCard
                    key={j.id}
                    job={j}
                    onDragStart={handleDragStart}
                    onDragEnd={handleDragEnd}
                    isDragging={draggedJob?.id === j.id}
                  />
                ))
              }
            </div>
          </div>
        )
      })}
    </div>
  )
}
