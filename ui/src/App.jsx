import { useState, useEffect, useCallback } from 'react'
import { Briefcase, LayoutGrid, List, Settings, Rss } from 'lucide-react'
import StatsPanel from './components/StatsPanel.jsx'
import FilterBar from './components/FilterBar.jsx'
import JobCard from './components/JobCard.jsx'
import KanbanView from './components/KanbanView.jsx'
import ProfileConfig from './components/ProfileConfig.jsx'
import SourcesConfig from './components/SourcesConfig.jsx'
import { fetchJobs, fetchStats, fetchProfiles, fetchSources, triggerFetch } from './api.js'

const TABS = [
  { id: 'list',     icon: List,        label: 'Listings' },
  { id: 'kanban',   icon: LayoutGrid,  label: 'Kanban' },
  { id: 'profiles', icon: Settings,    label: 'Profiles' },
  { id: 'sources',  icon: Rss,         label: 'Sources' },
]

export default function App() {
  const [jobs, setJobs] = useState([])
  const [stats, setStats] = useState(null)
  const [profiles, setProfiles] = useState([])
  const [sources, setSources] = useState([])
  const [filters, setFilters] = useState({ status: 'new', search: '', source: '', work_mode: '' })
  const [tab, setTab] = useState('list')
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)

  const loadAll = useCallback(async () => {
    const [j, s, p, src] = await Promise.all([
      fetchJobs({ limit: 500 }),
      fetchStats(),
      fetchProfiles(),
      fetchSources(),
    ])
    setJobs(j); setStats(s); setProfiles(p); setSources(src)
    setLoading(false)
  }, [])

  useEffect(() => { loadAll() }, [loadAll])
  useEffect(() => {
    const t = setInterval(() => fetchStats().then(setStats), 30000)
    return () => clearInterval(t)
  }, [])

  const handleScan = async () => {
    setScanning(true)
    await triggerFetch()
    setTimeout(async () => {
      const [j, s] = await Promise.all([fetchJobs({ limit: 500 }), fetchStats()])
      setJobs(j); setStats(s); setScanning(false)
    }, 5000)
  }

  const handleStatusChange = (id, status) => {
    setJobs(prev => prev.map(j => j.id === id ? { ...j, status } : j))
  }

  const filteredJobs = jobs.filter(j => {
    if (filters.status && j.status !== filters.status) return false
    if (filters.source && j.source !== filters.source) return false
    if (filters.work_mode && j.work_mode !== filters.work_mode) return false
    if (filters.search) {
      const q = filters.search.toLowerCase()
      if (!j.title?.toLowerCase().includes(q) && !j.company?.toLowerCase().includes(q) && !j.description?.toLowerCase().includes(q)) return false
    }
    return true
  })

  return (
    <div className="min-h-screen bg-jr-bg">
      {/* Titlebar */}
      <div className="bg-jr-surface border-b border-jr-border">
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex items-center h-12 gap-4">
            {/* Traffic lights */}
            <div className="flex items-center gap-1.5 shrink-0">
              <div className="w-3 h-3 rounded-full bg-[#FF5F57]" />
              <div className="w-3 h-3 rounded-full bg-[#FEBC2E]" />
              <div className="w-3 h-3 rounded-full bg-[#28C840]" />
            </div>

            {/* Logo */}
            <div className="flex items-center gap-2 shrink-0">
              <div className="w-6 h-6 rounded-md bg-jr-accent flex items-center justify-center">
                <Briefcase size={13} className="text-white" />
              </div>
              <span className="text-sm font-semibold text-jr-text tracking-tight">JobRadar</span>
            </div>

            {/* Tabs */}
            <nav className="flex items-end h-full gap-0 ml-2">
              {TABS.map(t => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`flex items-center gap-1.5 px-3 h-full text-sm font-medium border-b-2 transition-colors cursor-pointer ${
                    tab === t.id
                      ? 'text-jr-accent border-jr-accent'
                      : 'text-jr-sub border-transparent hover:text-jr-text'
                  }`}
                >
                  <t.icon size={13} />
                  {t.label}
                </button>
              ))}
            </nav>

            <div className="ml-auto flex items-center gap-2">
              <span className="text-xs text-jr-muted font-mono">{stats?.total ?? 0} tracked</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main */}
      <main className="max-w-6xl mx-auto px-4 py-5 space-y-4">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center space-y-3">
              <div className="w-8 h-8 border-2 border-jr-border border-t-jr-accent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-jr-muted">Loading…</p>
            </div>
          </div>
        ) : (
          <>
            <StatsPanel stats={stats} onScan={handleScan} scanning={scanning} />

            {tab === 'list' && (
              <>
                <FilterBar
                  filters={filters}
                  onChange={setFilters}
                  sources={sources}
                  total={filteredJobs.length}
                />
                <div className="space-y-2">
                  {filteredJobs.length === 0 ? (
                    <div className="card p-12 text-center">
                      <Briefcase size={28} className="text-jr-muted mx-auto mb-3 opacity-40" />
                      <p className="text-sm text-jr-sub">No listings match your filters</p>
                      <p className="text-xs text-jr-muted mt-1">Try adjusting filters or trigger a new scan</p>
                    </div>
                  ) : filteredJobs.map(job => (
                    <JobCard key={job.id} job={job} onStatusChange={handleStatusChange} />
                  ))}
                </div>
              </>
            )}

            {tab === 'kanban' && <KanbanView jobs={jobs} />}
            {tab === 'profiles' && <ProfileConfig profiles={profiles} onUpdate={() => fetchProfiles().then(setProfiles)} />}
            {tab === 'sources' && <SourcesConfig sources={sources} onUpdate={() => fetchSources().then(setSources)} />}
          </>
        )}
      </main>
    </div>
  )
}
