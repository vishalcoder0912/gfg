import type {
  DatasetProfile,
  DatasetsListResponse,
  FollowUpResponse,
  GenerateDashboardResponse,
} from './types'

function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL
  const url = (raw && raw.trim()) || '/api'
  return url.endsWith('/') ? url.slice(0, -1) : url
}

function getUploadBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL
  // If we are using the internal proxy '/api', we must bypass for FormData
  // because Next.js rewrites consume the body stream causing FastAPI 400 Bad Request.
  if (!raw || raw.trim() === '/api') {
    return 'http://localhost:8000'
  }
  const url = raw.trim()
  return url.endsWith('/') ? url.slice(0, -1) : url
}

async function parseJsonOrThrow(res: Response) {
  const text = await res.text()
  const data = text ? JSON.parse(text) : null
  if (!res.ok) {
    // FastAPI typically returns { detail: ... }
    const detail = data?.detail ? String(data.detail) : `${res.status} ${res.statusText}`
    throw new Error(detail)
  }
  return data
}

export async function listDatasets(): Promise<DatasetsListResponse> {
  const res = await fetch(`${getApiBaseUrl()}/datasets`, { cache: 'no-store' })
  return parseJsonOrThrow(res)
}

export async function uploadCsv(file: File): Promise<DatasetProfile> {
  const form = new FormData()
  form.append('file', file)

  const res = await fetch(`${getUploadBaseUrl()}/upload-csv`, {
    method: 'POST',
    body: form,
  })
  return parseJsonOrThrow(res)
}

export async function generateDashboard(datasetId: string, prompt: string): Promise<GenerateDashboardResponse> {
  const res = await fetch(`${getApiBaseUrl()}/generate-dashboard`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dataset_id: datasetId, prompt }),
  })
  return parseJsonOrThrow(res)
}

export async function followUp(sessionId: string, prompt: string): Promise<FollowUpResponse> {
  const res = await fetch(`${getApiBaseUrl()}/follow-up`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, prompt }),
  })
  return parseJsonOrThrow(res)
}
