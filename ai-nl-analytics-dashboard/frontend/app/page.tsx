'use client'

import { useEffect, useMemo, useState } from 'react'
import clsx from 'clsx'
import { 
  BarChart3, 
  TrendingUp, 
  Users, 
  DollarSign, 
  ArrowUpRight, 
  ArrowDownRight,
  MessageSquare,
  Sparkles,
  Send,
  AlertTriangle,
  Loader2,
  Database,
  LayoutDashboard
} from 'lucide-react'

import FileUpload from '../components/dashboard/FileUpload'
import { SqlPanel } from '../components/SqlPanel'
import { ChartRenderer } from '../components/ChartRenderer'
import { DataTable } from '../components/DataTable'
import { followUp, generateDashboard, listDatasets } from '../lib/api'
import type { DashboardSpec, DatasetProfile } from '../lib/types'

function Pill({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: 'neutral' | 'warn' }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs border',
        tone === 'warn' ? 'bg-sand-50 border-sand-200 text-sand-800' : 'bg-white/70 border-ink-100 text-ink-700'
      )}
    >
      {children}
    </span>
  )
}

export default function Home() {
  const [datasets, setDatasets] = useState<DatasetProfile[]>([])
  const [datasetId, setDatasetId] = useState<string>('')
  const [datasetProfile, setDatasetProfile] = useState<DatasetProfile | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>('')
  const [dashboard, setDashboard] = useState<DashboardSpec | null>(null)
  const [sessionId, setSessionId] = useState<string>('')
  const [warnings, setWarnings] = useState<string[]>([])
  const [chatHistory, setChatHistory] = useState<any[]>([])
  const [prompt, setPrompt] = useState('Build an executive dashboard for sales performance')
  const [followPrompt, setFollowPrompt] = useState('')
  const [chatMessage, setChatMessage] = useState('')

  const selectedDataset = useMemo(
    () => datasets.find((d) => d.dataset_id === datasetId) ?? datasetProfile,
    [datasets, datasetId, datasetProfile]
  )

  const handleUploadComplete = async (profile: DatasetProfile) => {
    setDatasets((prev) => [profile, ...prev.filter((d) => d.dataset_id !== profile.dataset_id)])
    setDatasetId(profile.dataset_id)
    setDatasetProfile(profile)
    setError('')
    setBusy(true)
    try {
      const res = await generateDashboard(profile.dataset_id, prompt.trim())
      setDashboard(res.dashboard)
      setSessionId(res.session_id)
      setWarnings(res.warnings ?? [])
    } catch (err) {
      console.error('Failed to generate dashboard:', err)
      setError(err instanceof Error ? err.message : 'Failed to generate dashboard')
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const res = await listDatasets()
        if (!alive) return
        setDatasets(res.datasets ?? [])

        const defaultDataset = res.datasets?.[0]
        if (defaultDataset) {
          setDatasetId(defaultDataset.dataset_id)
          setDatasetProfile(defaultDataset)
        }
      } catch (e) {
        if (!alive) return
        setError(e instanceof Error ? e.message : String(e))
      }
    })()
    return () => {
      alive = false
    }
  }, [])

  async function onGenerate() {
    if (!datasetId) return
    setError('')
    setBusy(true)
    try {
      const res = await generateDashboard(datasetId, prompt.trim())
      setDashboard(res.dashboard)
      setSessionId(res.session_id)
      setWarnings(res.warnings ?? [])
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function onFollowUp() {
    if (!sessionId) return
    setError('')
    setBusy(true)
    try {
      const res = await followUp(sessionId, followPrompt.trim())
      setDashboard(res.dashboard)
      setWarnings(res.warnings ?? [])
      setFollowPrompt('')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!chatMessage.trim() || !datasetId || !sessionId) return

    const userMsg = { role: 'user', content: chatMessage }
    setChatHistory((prev) => [...prev, userMsg])
    const currentQuery = chatMessage.trim()
    setChatMessage('')
    setBusy(true)

    try {
      const res = await followUp(sessionId, currentQuery)
      setDashboard(res.dashboard)
      setWarnings(res.warnings ?? [])
      setChatHistory((prev) => [...prev, { role: 'ai', content: 'Updated dashboard.' }])
    } catch (err) {
      console.error('Chat failed:', err)
      setError(err instanceof Error ? err.message : 'Chat failed')
    } finally {
      setBusy(false)
    }
  }

  const stats = [
    { label: 'Total Rows', value: selectedDataset?.row_count?.toLocaleString() || '0', icon: Database, color: 'text-green-600', bg: 'bg-green-50' },
    { label: 'Columns', value: selectedDataset?.column_count?.toString() || '0', icon: LayoutDashboard, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Status', value: busy ? 'Busy' : 'Ready', icon: Sparkles, color: 'text-indigo-600', bg: 'bg-indigo-50' },
  ]

  return (
    <main className="min-h-screen">
      <div className="mx-auto max-w-6xl px-4 py-10">
        <header className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-4">
            <h1 className="font-display text-4xl tracking-tight">
              Conversational BI <span className="text-ink-600">Dashboard</span>
            </h1>
            <Pill>
              <Sparkles className="h-3.5 w-3.5" />
              Prototype mode
            </Pill>
          </div>
          <p className="text-ink-700 max-w-2xl">
            Upload a CSV (or use the demo dataset), ask a plain-English question, and get KPIs + multi-chart dashboards
            with SQL transparency.
          </p>
        </header>

        <section className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div className="space-y-4">
            <div className="rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="font-display text-lg tracking-tight">Dataset</div>
                  <div className="text-sm text-ink-600">Pick demo or upload your own CSV</div>
                </div>
                {!!selectedDataset && (
                  <Pill>
                    {selectedDataset.original_filename ?? selectedDataset.table_name}
                  </Pill>
                )}
              </div>

              <div className="mt-4 grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-3">
                <select
                  className="w-full rounded-xl border border-ink-100 bg-white/80 px-3 py-2 text-sm"
                  value={datasetId}
                  onChange={(e) => {
                    setDatasetId(e.target.value)
                    const next = datasets.find((d) => d.dataset_id === e.target.value) ?? null
                    setDatasetProfile(next)
                  }}
                  disabled={busy}
                >
                  <option value="" disabled>
                    Select a dataset
                  </option>
                  {datasets.map((d) => (
                    <option key={d.dataset_id} value={d.dataset_id}>
                      {d.original_filename ?? d.table_name}
                    </option>
                  ))}
                </select>
                <div className="text-xs text-ink-600 self-center sm:text-right">
                  {selectedDataset ? `${selectedDataset.row_count.toLocaleString()} rows` : ''}
                </div>
              </div>

              {selectedDataset?.columns?.length ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  <Pill>Columns: {selectedDataset.column_count}</Pill>
                  {selectedDataset.date_columns?.length ? <Pill>Date: {selectedDataset.date_columns[0]}</Pill> : null}
                  {selectedDataset.numeric_columns?.length ? <Pill>Numeric: {selectedDataset.numeric_columns[0]}</Pill> : null}
                  {selectedDataset.categorical_columns?.length ? (
                    <Pill>Category: {selectedDataset.categorical_columns[0]}</Pill>
                  ) : null}
                </div>
              ) : null}
            </div>

            <FileUpload onUploadComplete={handleUploadComplete} />

            {selectedDataset?.preview_rows?.length ? (
              <div className="rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft p-5">
                <div className="font-display text-lg tracking-tight">Preview</div>
                <div className="text-sm text-ink-600">A few rows (as profiled on ingest)</div>
                <DataTable rows={selectedDataset.preview_rows} className="mt-4" />
              </div>
            ) : null}
          </div>

          <div className="space-y-4">
            <div className="rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-display text-lg tracking-tight">Ask a question</div>
                  <div className="text-sm text-ink-600">Example: monthly revenue trend by region, top category, etc.</div>
                </div>
                {busy ? <Pill>Working...</Pill> : <Pill>LLM + SQL</Pill>}
              </div>

              <textarea
                className="mt-4 w-full min-h-28 resize-y rounded-xl border border-ink-100 bg-white/80 px-3 py-2 text-sm"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                disabled={busy}
                placeholder="e.g., Show monthly revenue trend for Q3 broken down by region and highlight the top product category"
              />

              <div className="mt-4 flex items-center justify-between gap-3">
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="text-xs rounded-full border border-ink-100 bg-white/70 px-3 py-1 hover:bg-white"
                    onClick={() =>
                      setPrompt('Show monthly revenue trend for Q3 broken down by region and highlight the top product category')
                    }
                    disabled={busy}
                  >
                    Try Q3 trend
                  </button>
                  <button
                    type="button"
                    className="text-xs rounded-full border border-ink-100 bg-white/70 px-3 py-1 hover:bg-white"
                    onClick={() =>
                      setPrompt('Which region is growing fastest month over month? Include a chart and a KPI for growth rate.')
                    }
                    disabled={busy}
                  >
                    Try growth
                  </button>
                </div>

                <button
                  type="button"
                  onClick={onGenerate}
                  disabled={busy || !datasetId || prompt.trim().length < 3}
                  className={clsx(
                    'rounded-xl px-4 py-2 text-sm font-medium border transition',
                    busy || !datasetId || prompt.trim().length < 3
                      ? 'bg-ink-100 border-ink-100 text-ink-400 cursor-not-allowed'
                      : 'bg-ink-900 border-ink-900 text-white hover:bg-ink-800'
                  )}
                >
                  Generate dashboard
                </button>
              </div>
            </div>

            {error ? (
              <div className="rounded-2xl border border-sand-200 bg-sand-50 shadow-soft p-5">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-sand-700 mt-0.5" />
                  <div>
                    <div className="font-medium text-sand-900">Request failed</div>
                    <div className="text-sm text-sand-800 mt-1">{error}</div>
                  </div>
                </div>
              </div>
            ) : null}

            {warnings?.length ? (
              <div className="rounded-2xl border border-sand-200 bg-sand-50 shadow-soft p-5">
                <div className="font-display text-lg tracking-tight">Warnings</div>
                <div className="mt-2 flex flex-col gap-2">
                  {warnings.map((w, i) => (
                    <Pill key={i} tone="warn">
                      {w}
                    </Pill>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </section>

        {dashboard ? (
          <section className="mt-8 space-y-5 anim-rise">
            <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
              <div>
                <h2 className="font-display text-3xl tracking-tight">{dashboard.title}</h2>
                {dashboard.message ? <p className="text-sm text-ink-600 mt-1">{dashboard.message}</p> : null}
              </div>
              {sessionId ? <Pill>Session: {sessionId}</Pill> : null}
            </div>

            {!!dashboard.summary_cards?.length && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {dashboard.summary_cards.map((c) => (
                  <div
                    key={c.label}
                    className="rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft p-5"
                  >
                    <div className="text-xs uppercase tracking-wide text-ink-500">{c.label}</div>
                    <div className="mt-2 font-display text-2xl tracking-tight">
                      {typeof c.value === 'number' ? c.value.toLocaleString() : String(c.value ?? '')}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!!dashboard.insights?.length && (
              <div className="rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft p-5">
                <div className="font-display text-lg tracking-tight">Executive insights</div>
                <ul className="mt-3 space-y-2 text-sm text-ink-700 list-disc pl-5">
                  {dashboard.insights.map((t, i) => (
                    <li key={i}>{t}</li>
                  ))}
                </ul>
              </div>
            )}

            {!!dashboard.charts?.length && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {dashboard.charts.map((ch) => (
                  <div
                    key={ch.id}
                    className="rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft p-5"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="font-display text-lg tracking-tight truncate">{ch.title}</div>
                        <div className="text-xs text-ink-500 mt-0.5">
                          {ch.chartType}
                          {ch.xKey ? ` - x: ${ch.xKey}` : ''}
                          {ch.yKeys?.length ? ` - y: ${ch.yKeys.join(', ')}` : ''}
                        </div>
                      </div>
                      <Pill>{(ch.data?.length ?? 0).toLocaleString()} rows</Pill>
                    </div>
                    <div className="mt-4">
                      <ChartRenderer spec={ch} />
                    </div>
                  </div>
                ))}
              </div>
            )}

            <SqlPanel queries={dashboard.sql_queries ?? []} />

            <div className="rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft p-5">
              <div className="font-display text-lg tracking-tight">Follow-up</div>
              <div className="text-sm text-ink-600">Refine the dashboard using session memory.</div>
              <div className="mt-4 grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-3">
                <input
                  className="w-full rounded-xl border border-ink-100 bg-white/80 px-3 py-2 text-sm"
                  value={followPrompt}
                  onChange={(e) => setFollowPrompt(e.target.value)}
                  disabled={busy || !sessionId}
                  placeholder={!sessionId ? 'Generate a dashboard first...' : 'e.g., Now filter this to East region'}
                />
                <button
                  type="button"
                  onClick={onFollowUp}
                  disabled={busy || !sessionId || !followPrompt.trim()}
                  className={clsx(
                    'rounded-xl px-4 py-2 text-sm font-medium border transition',
                    busy || !sessionId || !followPrompt.trim()
                      ? 'bg-ink-100 border-ink-100 text-ink-400 cursor-not-allowed'
                      : 'bg-white/70 border-ink-200 text-ink-900 hover:bg-white'
                  )}
                >
                  Apply
                </button>
              </div>
            </div>
          </section>
        ) : null}
      </div>
    </main>
  )
}
