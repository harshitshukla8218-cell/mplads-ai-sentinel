export type RiskLevel = 'High' | 'Medium' | 'Low' | string

export type Project = {
  work_id: string
  state?: string | null
  district?: string | null
  constituency?: string | null
  mp_name?: string | null
  sector?: string | null
  work_name?: string | null
  sanction_amount?: number | null
  expenditure?: number | null
  date_of_administrative_approval?: string | null
  expected_completion_date?: string | null
  actual_completion_date?: string | null
  work_status?: string | null
  physical_progress_percent?: number | null
  implementing_agency_name?: string | null
  latitude?: number | null
  longitude?: number | null
  cost_anomaly_score?: number | null
  cost_confidence?: number | null
  cost_ratio_vs_peers?: number | null
  delay_anomaly_score?: number | null
  delay_confidence?: number | null
  days_overdue?: number | null
  progress_mismatch_score?: number | null
  progress_confidence?: number | null
  expenditure_ratio?: number | null
  duplicate_score?: number | null
  duplicate_confidence?: number | null
  most_similar_work_id?: string | null
  overall_confidence?: number | null
  risk_score?: number | null
  risk_level?: RiskLevel | null
  reasons?: string[]
}

export type Stats = {
  total?: number
  high?: number
  medium?: number
  low?: number
  avg_score?: number | null
  total_sanctioned?: number | null
}

export type Filters = { states: string[]; districts: string[]; sectors: string[] }
export type ProjectResponse = { total: number; limit: number; offset: number; projects: Project[] }
export type Entity = { entity_name?: string; total_works?: number; high_risk_works?: number; high_risk_rate?: number; avg_risk_score?: number; total_sanctioned?: number }
export type Weights = { total_feedback?: number; confirmed?: number; false_positive?: number; current_weights?: Record<string, number> }
export type SourceStatus = { source?: string; last_ingestion?: string; source_max_date?: string; records?: number; new_records?: number; changed_fields?: number; missing_fields?: string[]; freshness?: string }
export type Change = { work_id:string; detected_at:string; field_name:string; previous_value:string; current_value:string; source_name:string }
export type Validation = { evaluation_type:string; projects:number; labelled_test_anomalies:number; note:string }
export type Spatial = { available:boolean; projects: Array<Pick<Project,'work_id'|'work_name'|'state'|'constituency'|'latitude'|'longitude'|'risk_score'|'risk_level'>>; note:string }

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers: { Accept: 'application/json', ...(init?.headers || {}) }, cache: 'no-store' })
  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try { const body = await response.json(); detail = body.detail || detail } catch {}
    throw new Error(detail)
  }
  return response.json()
}

export const api = {
  health: () => request<{ status: string; time: string }>('/api/health'),
  stats: () => request<Stats>('/api/stats'),
  filters: () => request<Filters>('/api/filters'),
  projects: (params: Record<string, string | number | undefined> = {}) => {
    const query = new URLSearchParams()
    Object.entries({ limit: 50, ...params }).forEach(([key, value]) => { if (value !== undefined && value !== '') query.set(key, String(value)) })
    return request<ProjectResponse>(`/api/projects?${query.toString()}`)
  },
  project: (workId: string) => request<Project>(`/api/projects/${encodeURIComponent(workId)}`),
  entities: (type: 'mp' | 'agency' = 'mp') => request<Entity[]>(`/api/entities?type=${type}`),
  weights: () => request<Weights>('/api/weights'),
  sourceStatus: () => request<SourceStatus>('/api/source-status'),
  changes: () => request<Change[]>('/api/changes'),
  validation: () => request<Validation>('/api/validation'),
  spatial: () => request<Spatial>('/api/spatial'),
  ingest: async (file: File) => { const form = new FormData(); form.append('file', file); return request<{status:string;source:string;records:number;new_records:number;changed_fields:number;missing_fields:string[]}>('/api/ingest', { method:'POST', body: form }) },
  feedback: (workId: string, verdict: 'confirmed' | 'false_positive') => request<{ updated_project: Project; weights: Record<string, number> }>('/api/feedback', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ work_id: workId, verdict }) }),
}

export function formatAmount(value?: number | null) {
  if (value == null || Number.isNaN(value)) return 'Not available'
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value)
}

export function formatDate(value?: string | null) {
  if (!value) return 'Not available'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function displayValue(value?: string | number | null) { return value === null || value === undefined || value === '' ? 'Not available' : String(value) }


