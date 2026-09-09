import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'

const LEVEL_COLOR = {
  High: 'text-signal-red',
  Medium: 'text-gold-600',
  Low: 'text-signal-green',
}

function money(n) {
  if (n == null) return '—'
  if (n >= 10000000) return `Rs.${(n / 10000000).toFixed(2)}Cr`
  if (n >= 100000) return `Rs.${(n / 100000).toFixed(1)}L`
  return `Rs.${Math.round(n).toLocaleString('en-IN')}`
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [filterOptions, setFilterOptions] = useState({ states: [], districts: [], sectors: [] })
  const [filters, setFilters] = useState({ state: '', district: '', sector: '', min_score: 0, search: '' })
  const [projects, setProjects] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.stats().then(setStats).catch(() => {})
    api.filters().then(setFilterOptions).catch(() => {})
  }, [])

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    api.projects({ ...filters, limit: 100 })
      .then((data) => {
        setProjects(data.projects)
        setTotal(data.total)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [filters])

  useEffect(() => { load() }, [load])

  return (
    <div className="p-8">
      <header className="mb-6">
        <h1 className="font-display text-3xl text-ink-900">Case Register</h1>
        <p className="text-ink-500 text-sm mt-1">
          MPLADS development works, screened and ranked by anomaly risk.
        </p>
      </header>

      {error && (
        <div className="mb-4 px-4 py-3 bg-signal-redlight text-signal-red text-sm rounded-sm">
          Could not reach the API ({error}). Is the backend running on port 8000?
        </div>
      )}

      {stats && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <StatCard label="Total works" value={stats.total} />
          <StatCard label="High risk" value={stats.high} accent="text-signal-red" />
          <StatCard label="Medium risk" value={stats.medium} accent="text-gold-600" />
          <StatCard label="Total sanctioned" value={money(stats.total_sanctioned)} />
        </div>
      )}

      <div className="bg-white border border-line rounded-sm p-4 mb-5 flex flex-wrap gap-3 items-end">
        <Field label="Search">
          <input
            className="input"
            placeholder="Work ID or description…"
            value={filters.search}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
          />
        </Field>
        <Field label="State">
          <select className="input" value={filters.state}
            onChange={(e) => setFilters((f) => ({ ...f, state: e.target.value }))}>
            <option value="">All states</option>
            {filterOptions.states.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field label="Sector">
          <select className="input" value={filters.sector}
            onChange={(e) => setFilters((f) => ({ ...f, sector: e.target.value }))}>
            <option value="">All sectors</option>
            {filterOptions.sectors.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field label={`Min. risk score: ${filters.min_score}`}>
          <input
            type="range" min="0" max="100" step="5" className="w-40"
            value={filters.min_score}
            onChange={(e) => setFilters((f) => ({ ...f, min_score: Number(e.target.value) }))}
          />
        </Field>
      </div>

      <div className="bg-white border border-line rounded-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-ink-500 text-xs uppercase tracking-wide border-b border-line">
              <th className="py-3 px-4 font-medium">Work ID</th>
              <th className="py-3 px-4 font-medium">Description</th>
              <th className="py-3 px-4 font-medium">District</th>
              <th className="py-3 px-4 font-medium">Sanctioned</th>
              <th className="py-3 px-4 font-medium text-right">Risk</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((p) => (
              <tr key={p.work_id} className="ledger-row cursor-pointer"
                  onClick={() => navigate(`/project/${encodeURIComponent(p.work_id)}`)}>
                <td className="py-3 px-4 font-mono text-xs text-ink-700">{p.work_id}</td>
                <td className="py-3 px-4 max-w-xs truncate">{p.work_name}</td>
                <td className="py-3 px-4 text-ink-500">{p.district}</td>
                <td className="py-3 px-4 font-mono text-xs">{money(p.sanction_amount)}</td>
                <td className={`py-3 px-4 text-right font-mono font-semibold ${LEVEL_COLOR[p.risk_level]}`}>
                  {Math.round(p.risk_score)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && projects.length === 0 && (
          <div className="p-10 text-center text-ink-500 text-sm">
            No works match these filters.
          </div>
        )}
      </div>
      <div className="text-xs text-ink-500 mt-3">
        Showing {projects.length} of {total} works
      </div>

      <style>{`.input { border: 1px solid #DDD6C6; background: white; padding: 6px 10px; font-size: 13px; border-radius: 2px; min-width: 160px; }
      .input:focus { outline: 2px solid #B8862E; outline-offset: 1px; }`}</style>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-ink-500 mb-1">{label}</div>
      {children}
    </div>
  )
}

function StatCard({ label, value, accent = 'text-ink-900' }) {
  return (
    <div className="bg-white border border-line rounded-sm p-4">
      <div className="text-[11px] uppercase tracking-wide text-ink-500">{label}</div>
      <div className={`font-display text-2xl mt-1 ${accent}`}>{value}</div>
    </div>
  )
}
