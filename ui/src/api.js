const BASE = '/api'

export async function fetchJobs(filters = {}) {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.source) params.set('source', filters.source)
  if (filters.work_mode) params.set('work_mode', filters.work_mode)
  if (filters.search) params.set('search', filters.search)
  params.set('limit', filters.limit || 300)

  const res = await fetch(`${BASE}/jobs?${params}`)
  return res.json()
}

export async function updateJobStatus(id, status) {
  await fetch(`${BASE}/jobs/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
}

export async function updateJobNotes(id, notes) {
  await fetch(`${BASE}/jobs/${id}/notes`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ notes }),
  })
}

export async function fetchStats() {
  const res = await fetch(`${BASE}/stats`)
  return res.json()
}

export async function fetchProfiles() {
  const res = await fetch(`${BASE}/profiles`)
  return res.json()
}

export async function createProfile(data) {
  const res = await fetch(`${BASE}/profiles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function updateProfile(id, data) {
  await fetch(`${BASE}/profiles/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function deleteProfile(id) {
  await fetch(`${BASE}/profiles/${id}`, { method: 'DELETE' })
}

export async function triggerFetch() {
  await fetch(`${BASE}/fetch/trigger`, { method: 'POST' })
}

export async function fetchSources() {
  const res = await fetch(`${BASE}/sources`)
  return res.json()
}

export async function toggleSource(id) {
  const res = await fetch(`${BASE}/sources/${id}/toggle`, { method: 'PATCH' })
  return res.json()
}

export async function fetchLog() {
  const res = await fetch(`${BASE}/fetch/log`)
  return res.json()
}
