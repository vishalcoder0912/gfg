/**
 * API client for the Conversational BI Dashboard.
 *
 * FIX 1: parseJsonOrThrow now handles non-JSON responses gracefully.
 *   Previously:  const data = JSON.parse(text)  ← crashes on plain text 500s
 *   Now: try/catch, strips HTML entities from nginx 502 pages, clean error msg.
 *
 * FIX 2: getUploadBaseUrl reads from NEXT_PUBLIC_BACKEND_URL env var.
 *   Previously hardcoded to http://localhost:8000 — broke Docker and production.
 */

import type {
  DatasetProfile,
  DatasetsListResponse,
  FollowUpResponse,
  GenerateDashboardResponse,
} from './types'


function normalizeUrl(url: string): string {
  return url.endsWith('/') ? url.slice(0, -1) : url
}

function ensureApiSuffix(base: string): string {
  const normalized = normalizeUrl(base)
  return normalized.endsWith('/api') ? normalized : `${normalized}/api`
}

function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL?.trim()
  if (raw) return normalizeUrl(raw)

  const backend = process.env.NEXT_PUBLIC_BACKEND_URL?.trim()
  if (backend) return ensureApiSuffix(backend)

  // Local dev default when no Next.js rewrite is available
  return 'http://localhost:8000/api'
}

function getUploadBaseUrl(): string {
  // Explicit override (useful for production/reverse proxy setups)
  const override = process.env.NEXT_PUBLIC_UPLOAD_URL
  if (override?.trim()) return normalizeUrl(override.trim())

  // Direct backend URL (bypasses Next.js proxy which breaks multipart uploads)
  const backend = process.env.NEXT_PUBLIC_BACKEND_URL
  if (backend?.trim()) return ensureApiSuffix(backend.trim())

  // If API URL is an absolute http address, use it directly
  const api = process.env.NEXT_PUBLIC_API_URL
  if (api?.trim().startsWith('http')) return normalizeUrl(api.trim())

  // Local dev default
  return 'http://localhost:8000/api'
}


// Reusable fetch with 1 automatic retry for transient proxy errors (ECONNRESET/502)
async function fetchWithRetry(url: string, options?: RequestInit): Promise<Response> {
  try {
    const res = await fetch(url, options)
    if (res.status === 502 || res.status === 503) throw new Error('Proxy error')
    return res
  } catch (err) {
    // Wait 500ms and retry once if it's a network error (like ECONNRESET) or 502 Bad Gateway
    await new Promise(r => setTimeout(r, 500))
    return fetch(url, options)
  }
}

async function parseJsonOrThrow(res: Response): Promise<any> {
  let text = ''
  try {
    text = await res.text()
  } catch {
    throw new Error(`Server returned ${res.status} ${res.statusText} (unreadable body)`)
  }

  // Try JSON parse first
  let data: any = null
  let parseOk = false
  if (text.trim()) {
    try {
      data = JSON.parse(text)
      parseOk = true
    } catch {
      // plain text or HTML response — handled below
    }
  }

  if (res.ok) return parseOk ? data : { message: text }

  // Build a clean human-readable error message
  let msg: string
  if (parseOk && data !== null) {
    if (typeof data.detail === 'string') {
      msg = data.detail
    } else if (Array.isArray(data.detail)) {
      // FastAPI validation errors: [{loc, msg, type}]
      msg = data.detail.map((e: any) => `${e.loc?.join('.')} — ${e.msg}`).join('; ')
    } else if (typeof data.message === 'string') {
      msg = data.message
    } else {
      msg = JSON.stringify(data)
    }
  } else if (text.trim()) {
    // Strip HTML tags from nginx 502/503 pages
    const cleaned = text.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim()
    msg = cleaned.length > 200 ? cleaned.slice(0, 200) + '…' : cleaned
  } else {
    msg = `${res.status} ${res.statusText}`
  }

  throw new Error(msg)
}


export async function listDatasets(): Promise<DatasetsListResponse> {
  const res = await fetchWithRetry(`${getApiBaseUrl()}/datasets`, { cache: 'no-store' })
  return parseJsonOrThrow(res)
}

export async function uploadCsv(file: File): Promise<DatasetProfile> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${getUploadBaseUrl()}/upload-csv`, { method: 'POST', body: form })
  return parseJsonOrThrow(res)
}

export async function generateDashboard(
  datasetId: string,
  prompt: string,
): Promise<GenerateDashboardResponse> {
  const res = await fetchWithRetry(`${getApiBaseUrl()}/generate-dashboard`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dataset_id: datasetId, prompt }),
  })
  return parseJsonOrThrow(res)
}

export async function followUp(
  sessionId: string,
  prompt: string,
): Promise<FollowUpResponse> {
  const res = await fetchWithRetry(`${getApiBaseUrl()}/follow-up`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, prompt }),
  })
  return parseJsonOrThrow(res)
}
