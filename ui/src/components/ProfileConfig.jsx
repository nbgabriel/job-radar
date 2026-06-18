import { useState } from 'react'
import { Plus, Trash2, Edit2, Check, X, Tag } from 'lucide-react'
import { createProfile, updateProfile, deleteProfile } from '../api.js'

const ProfileRow = ({ profile, onUpdate, onDelete }) => {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(profile.name)
  const [kw, setKw] = useState(profile.keywords.join(', '))

  const save = async () => {
    const keywords = kw.split(',').map(k => k.trim()).filter(Boolean)
    await updateProfile(profile.id, { name, keywords, enabled: profile.enabled })
    onUpdate(); setEditing(false)
  }

  return (
    <div className="border border-jr-border rounded-lg p-3 bg-jr-bg">
      {editing ? (
        <div className="space-y-2">
          <input value={name} onChange={e => setName(e.target.value)}
            className="w-full text-sm border border-jr-border rounded-lg px-3 py-1.5 bg-jr-surface text-jr-text focus:outline-none focus:border-jr-accent"
            placeholder="Profile name" />
          <textarea value={kw} onChange={e => setKw(e.target.value)} rows={2}
            className="w-full text-sm border border-jr-border rounded-lg px-3 py-1.5 bg-jr-surface text-jr-text resize-none focus:outline-none focus:border-jr-accent font-mono"
            placeholder="keyword1, keyword2" />
          <div className="flex gap-2">
            <button onClick={save} className="btn-primary text-xs"><Check size={11} />Save</button>
            <button onClick={() => setEditing(false)} className="btn-ghost text-xs"><X size={11} />Cancel</button>
          </div>
        </div>
      ) : (
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-sm font-medium text-jr-text">{profile.name}</span>
              <div className={`w-1.5 h-1.5 rounded-full ${profile.enabled ? 'bg-jr-green' : 'bg-jr-muted'}`} />
            </div>
            <div className="flex flex-wrap gap-1">
              {profile.keywords.map(k => (
                <span key={k} className="flex items-center gap-1 tag"><Tag size={9} />{k}</span>
              ))}
            </div>
          </div>
          <div className="flex gap-1">
            <button onClick={() => setEditing(true)} className="w-7 h-7 flex items-center justify-center rounded-lg text-jr-muted hover:bg-jr-accent-light hover:text-jr-accent transition-colors">
              <Edit2 size={13} />
            </button>
            <button onClick={() => onDelete(profile.id)} className="w-7 h-7 flex items-center justify-center rounded-lg text-jr-muted hover:bg-jr-red-light hover:text-jr-red transition-colors">
              <Trash2 size={13} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function ProfileConfig({ profiles, onUpdate }) {
  const [adding, setAdding] = useState(false)
  const [name, setName] = useState('')
  const [kw, setKw] = useState('')

  const handleAdd = async () => {
    const keywords = kw.split(',').map(k => k.trim()).filter(Boolean)
    if (!name || !keywords.length) return
    await createProfile({ name, keywords, enabled: true })
    setName(''); setKw(''); setAdding(false); onUpdate()
  }

  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-jr-text">Search Profiles</h2>
          <p className="text-xs text-jr-sub mt-0.5">Keywords used to filter listings across all sources</p>
        </div>
        <button onClick={() => setAdding(!adding)} className="btn-primary text-xs">
          <Plus size={13} />Add Profile
        </button>
      </div>

      {adding && (
        <div className="border border-jr-accent/30 bg-jr-accent-light/30 rounded-lg p-3 space-y-2 animate-slide-in">
          <input value={name} onChange={e => setName(e.target.value)} autoFocus
            placeholder="Profile name (e.g. Cloud Engineer)"
            className="w-full text-sm border border-jr-border rounded-lg px-3 py-1.5 bg-jr-surface text-jr-text focus:outline-none focus:border-jr-accent" />
          <textarea value={kw} onChange={e => setKw(e.target.value)} rows={2}
            placeholder="cloud engineer, aws engineer, gcp, platform"
            className="w-full text-sm border border-jr-border rounded-lg px-3 py-1.5 bg-jr-surface text-jr-text resize-none focus:outline-none focus:border-jr-accent font-mono" />
          <div className="flex gap-2">
            <button onClick={handleAdd} className="btn-primary text-xs"><Check size={11} />Create</button>
            <button onClick={() => setAdding(false)} className="btn-ghost text-xs"><X size={11} />Cancel</button>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {profiles.map(p => (
          <ProfileRow key={p.id} profile={p} onUpdate={onUpdate}
            onDelete={async id => { if (confirm('Delete profile?')) { await deleteProfile(id); onUpdate() } }} />
        ))}
      </div>
    </div>
  )
}
