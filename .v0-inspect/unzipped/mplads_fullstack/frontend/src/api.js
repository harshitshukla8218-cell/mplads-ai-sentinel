const BASE = '/api'

async function handle(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

export const api = {
  stats: () => fetch(`${BASE}/stats`).then(handle),

  filters: () => fetch(`${BASE}/filters`).then(handle),

  projects: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
    ).toString()
    return fetch(`${BASE}/projects?${qs}`).then(handle)
  },

  project: (workId) => fetch(`${BASE}/projects/${encodeURIComponent(workId)}`).then(handle),

  entities: (type = 'mp', minWorks = 2) =>
    fetch(`${BASE}/entities?type=${type}&min_works=${minWorks}`).then(handle),

  weights: () => fetch(`${BASE}/weights`).then(handle),

  submitFeedback: (workId, verdict) =>
    fetch(`${BASE}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ work_id: workId, verdict }),
    }).then(handle),
}
