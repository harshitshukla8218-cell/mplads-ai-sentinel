import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function Entities() {
  const [type, setType] = useState('mp')
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.entities(type).then(setRows).finally(() => setLoading(false))
  }, [type])

  return (
    <div className="p-8">
      <header className="mb-6">
        <h1 className="font-display text-3xl text-ink-900">Repeat Patterns</h1>
        <p className="text-ink-500 text-sm mt-1 max-w-2xl">
          Aggregated across all works tied to the same MP or implementing agency —
          a single flagged project can be noise, but a pattern across many works
          from the same source is a systemic signal worth a closer look.
        </p>
      </header>

      <div className="flex gap-2 mb-5">
        <TabButton active={type === 'mp'} onClick={() => setType('mp')}>By MP</TabButton>
        <TabButton active={type === 'agency'} onClick={() => setType('agency')}>By Implementing Agency</TabButton>
      </div>

      <div className="bg-white border border-line rounded-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-ink-500 text-xs uppercase tracking-wide border-b border-line">
              <th className="py-3 px-4 font-medium">{type === 'mp' ? 'Member of Parliament' : 'Implementing Agency'}</th>
              <th className="py-3 px-4 font-medium text-right">Total works</th>
              <th className="py-3 px-4 font-medium text-right">High-risk works</th>
              <th className="py-3 px-4 font-medium text-right">High-risk rate</th>
              <th className="py-3 px-4 font-medium text-right">Avg. risk score</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.entity_name} className="ledger-row">
                <td className="py-3 px-4 font-medium text-ink-900">{r.entity_name}</td>
                <td className="py-3 px-4 text-right font-mono">{r.total_works}</td>
                <td className="py-3 px-4 text-right font-mono text-signal-red">{r.high_risk_works}</td>
                <td className="py-3 px-4 text-right font-mono">{r.high_risk_rate}%</td>
                <td className="py-3 px-4 text-right font-mono">{r.avg_risk_score}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && rows.length === 0 && (
          <div className="p-10 text-center text-ink-500 text-sm">
            Not enough works per entity yet to surface a pattern.
          </div>
        )}
      </div>
    </div>
  )
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm rounded-sm border ${
        active ? 'bg-ink-900 text-white border-ink-900' : 'bg-white text-ink-700 border-line'
      }`}
    >
      {children}
    </button>
  )
}
