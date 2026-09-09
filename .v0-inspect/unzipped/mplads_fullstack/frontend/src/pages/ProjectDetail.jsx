import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api.js'
import StampBadge from '../components/StampBadge.jsx'

function money(n) {
  if (n == null) return '—'
  return `Rs.${Math.round(n).toLocaleString('en-IN')}`
}

export default function ProjectDetail() {
  const { workId } = useParams()
  const [project, setProject] = useState(null)
  const [error, setError] = useState(null)
  const [feedbackSent, setFeedbackSent] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const load = () => {
    api.project(workId).then(setProject).catch((e) => setError(e.message))
  }

  useEffect(() => { load() }, [workId])

  const sendFeedback = async (verdict) => {
    setSubmitting(true)
    try {
      const res = await api.submitFeedback(workId, verdict)
      setProject(res.updated_project)
      setFeedbackSent(verdict)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (error) return <div className="p-8 text-signal-red text-sm">{error}</div>
  if (!project) return <div className="p-8 text-ink-500 text-sm">Loading case file…</div>

  return (
    <div className="p-8 max-w-4xl">
      <Link to="/" className="text-xs text-ink-500 hover:text-ink-900 font-mono">&larr; BACK TO CASE REGISTER</Link>

      <div className="flex items-start justify-between mt-4 mb-6">
        <div>
          <div className="text-xs font-mono text-ink-500 mb-1">{project.work_id}</div>
          <h1 className="font-display text-2xl text-ink-900 leading-snug max-w-xl">{project.work_name}</h1>
          <div className="text-sm text-ink-500 mt-2">
            {project.district}, {project.state} &middot; {project.sector}
          </div>
        </div>
        <StampBadge level={project.risk_level} score={project.risk_score} size="lg" />
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <InfoBox label="Sanctioned amount" value={money(project.sanction_amount)} />
        <InfoBox label="Expenditure" value={money(project.expenditure)} />
        <InfoBox label="Status" value={`${project.work_status} (${Math.round(project.physical_progress_percent || 0)}% progress)`} />
      </div>

      <div className="bg-white border border-line rounded-sm p-5 mb-6">
        <h2 className="font-display text-lg text-ink-900 mb-3">Evidence on file</h2>
        {project.overall_confidence < 0.6 && (
          <div className="text-xs bg-gold-100 text-gold-600 px-3 py-2 rounded-sm mb-3">
            Confidence: {Math.round(project.overall_confidence * 100)}% — some signals rely on
            incomplete data for this record. Treat this score as indicative, not final.
          </div>
        )}
        <ul className="space-y-2">
          {project.reasons.map((r, i) => (
            <li key={i} className="text-sm text-ink-700 flex gap-2">
              <span className="text-gold-600 mt-0.5">&bull;</span>
              <span>{r}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="bg-white border border-line rounded-sm p-5 mb-6">
        <h2 className="font-display text-lg text-ink-900 mb-1">Signal breakdown</h2>
        <SignalBar label="Cost anomaly" value={project.cost_anomaly_score} />
        <SignalBar label="Delay anomaly" value={project.delay_anomaly_score} />
        <SignalBar label="Duplicate similarity" value={project.duplicate_score} />
        <SignalBar label="Progress mismatch" value={project.progress_mismatch_score} />
      </div>

      <div className="bg-white border border-line rounded-sm p-5">
        <h2 className="font-display text-lg text-ink-900 mb-1">Investigator verdict</h2>
        <p className="text-xs text-ink-500 mb-3">
          Your verdict adjusts how much weight each signal carries across the whole system.
        </p>
        {feedbackSent ? (
          <div className="text-sm text-signal-green">
            Recorded as {feedbackSent === 'confirmed' ? 'Confirmed' : 'False Positive'}. Weights updated.
          </div>
        ) : (
          <div className="flex gap-3">
            <button
              disabled={submitting}
              onClick={() => sendFeedback('confirmed')}
              className="px-4 py-2 text-sm bg-signal-red text-white rounded-sm hover:opacity-90 disabled:opacity-50"
            >
              Confirm — real issue
            </button>
            <button
              disabled={submitting}
              onClick={() => sendFeedback('false_positive')}
              className="px-4 py-2 text-sm border border-line text-ink-700 rounded-sm hover:bg-paper-50 disabled:opacity-50"
            >
              Mark false positive
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function InfoBox({ label, value }) {
  return (
    <div className="bg-white border border-line rounded-sm p-4">
      <div className="text-[11px] uppercase tracking-wide text-ink-500">{label}</div>
      <div className="text-sm font-medium text-ink-900 mt-1">{value}</div>
    </div>
  )
}

function SignalBar({ label, value = 0 }) {
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs text-ink-500 mb-1">
        <span>{label}</span>
        <span className="font-mono">{Math.round(value)}</span>
      </div>
      <div className="h-1.5 bg-paper-50 rounded-full overflow-hidden">
        <div className="h-full bg-gold-600" style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
    </div>
  )
}
