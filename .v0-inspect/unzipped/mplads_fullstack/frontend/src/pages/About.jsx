import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function About() {
  const [weights, setWeights] = useState(null)

  useEffect(() => { api.weights().then(setWeights).catch(() => {}) }, [])

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="font-display text-3xl text-ink-900 mb-2">How Scoring Works</h1>
      <p className="text-ink-500 text-sm mb-6">
        Four independent signals are combined into one risk score per work.
        None of them alone proves wrongdoing — together, they tell an
        investigator where to look first.
      </p>

      <div className="space-y-4 mb-8">
        <Signal name="Cost anomaly" desc="How far a work's sanctioned amount sits from the median of similar works in the same sector and district." />
        <Signal name="Delay anomaly" desc="How many days overdue a work is against its expected completion date." />
        <Signal name="Duplicate similarity" desc="How closely a work's description matches another nearby work — a sign of possible overlap or double-counting." />
        <Signal name="Progress mismatch" desc="Cases where a large share of funds is spent but reported physical progress stays low." />
      </div>

      {weights && (
        <div className="bg-white border border-line rounded-sm p-5">
          <h2 className="font-display text-lg text-ink-900 mb-1">Current signal weights</h2>
          <p className="text-xs text-ink-500 mb-4">
            These start equal and shift slightly every time an investigator confirms or
            rejects a flagged case ({weights.total_feedback} verdicts recorded so far).
          </p>
          {Object.entries(weights.current_weights).map(([k, v]) => (
            <div key={k} className="flex justify-between text-sm py-1.5 border-b border-line last:border-0">
              <span className="text-ink-700">{labelFor(k)}</span>
              <span className="font-mono text-ink-900">{(v * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function labelFor(key) {
  return {
    cost_anomaly_score: 'Cost anomaly',
    delay_anomaly_score: 'Delay anomaly',
    duplicate_score: 'Duplicate similarity',
    progress_mismatch_score: 'Progress mismatch',
  }[key] || key
}

function Signal({ name, desc }) {
  return (
    <div className="border-l-2 border-gold-600 pl-4">
      <div className="font-medium text-ink-900 text-sm">{name}</div>
      <div className="text-sm text-ink-500 mt-0.5">{desc}</div>
    </div>
  )
}
