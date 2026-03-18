'use client'

/**
 * Main page — Natural Language → Real-time Dashboard + Chat
 *
 * FIX 1: Removed dead imports (Sidebar, Navbar were imported but never rendered).
 *
 * FIX 2: Added a persistent chat panel that appears below the dashboard after
 *   the first generation. Every chat message:
 *     a) Adds a user bubble immediately (optimistic update)
 *     b) Shows a 3-dot typing indicator
 *     c) Dims the dashboard with chatBusy flag
 *     d) Calls followUp() API
 *     e) Calls setDashboard(res.dashboard) — charts re-render IN PLACE (real-time)
 *     f) Adds an assistant reply bubble confirming what changed
 *
 * Real-time flow:
 *   User types → handleChatSend() → optimistic msg → chatBusy=true
 *   → followUp(sessionId, msg) → setDashboard(res.dashboard)  ← dashboard re-renders
 *   → assistant reply → chatBusy=false → chatInput.focus()
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import clsx from 'clsx'
import {
  BarChart2, Sparkles, AlertTriangle, Loader2, Database,
  ChevronRight, RefreshCw, Send, Bot, User,
} from 'lucide-react'

import FileUpload from '../components/dashboard/FileUpload'
import { SqlPanel } from '../components/SqlPanel'
import { ChartRenderer } from '../components/ChartRenderer'
import { DataTable } from '../components/DataTable'
import { followUp, generateDashboard, listDatasets } from '../lib/api'
import type { DashboardSpec, DatasetProfile } from '../lib/types'

// ─── Example prompts shown before first generation ──────────────────────────
const EXAMPLE_PROMPTS = [
  'Show me which region made the most revenue',
  'What are the top 5 products by sales?',
  'How has revenue trended month by month?',
  'Compare profit across product categories',
  'Which month had the highest units sold?',
]

// ─── Suggestion chips shown in the chat panel ───────────────────────────────
const CHAT_CHIPS = [
  'Filter to East region only',
  'Show top 10 instead',
  'Break it down by category',
  'Show as a table',
  'Compare with profit',
  'Show monthly trend',
]

// ─── Types ───────────────────────────────────────────────────────────────────
type ChatMsg = {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

// ─── Small reusable atoms ────────────────────────────────────────────────────
function Badge({ children, color = 'neutral' }: {
  children: React.ReactNode
  color?: 'neutral' | 'warn' | 'green'
}) {
  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium border',
      color === 'warn'    && 'bg-amber-50 border-amber-200 text-amber-800',
      color === 'green'   && 'bg-emerald-50 border-emerald-200 text-emerald-700',
      color === 'neutral' && 'bg-white/70 border-ink-100 text-ink-600',
    )}>
      {children}
    </span>
  )
}

function KpiCard({ label, value }: { label: string; value: unknown }) {
  const display = typeof value === 'number'
    ? value.toLocaleString(undefined, { maximumFractionDigits: 2 })
    : String(value ?? '')
  return (
    <div className="rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft p-4">
      <p className="text-xs uppercase tracking-widest text-ink-400 font-medium truncate">{label}</p>
      <p className="mt-1.5 font-display text-xl tracking-tight text-ink-900">{display}</p>
    </div>
  )
}

// ─── Main page ───────────────────────────────────────────────────────────────
export default function Home() {
  const [datasets,     setDatasets]     = useState<DatasetProfile[]>([])
  const [datasetId,    setDatasetId]    = useState('')
  const [datasetProf,  setDatasetProf]  = useState<DatasetProfile | null>(null)
  const [prompt,       setPrompt]       = useState('')
  const [chatInput,    setChatInput]    = useState('')
  const [busy,         setBusy]         = useState(false)
  const [chatBusy,     setChatBusy]     = useState(false)   // separate flag for chat updates
  const [error,        setError]        = useState('')
  const [dashboard,    setDashboard]    = useState<DashboardSpec | null>(null)
  const [sessionId,    setSessionId]    = useState('')
  const [warnings,     setWarnings]     = useState<string[]>([])
  const [chatHistory,  setChatHistory]  = useState<ChatMsg[]>([])

  const dashboardRef = useRef<HTMLDivElement>(null)
  const chatEndRef   = useRef<HTMLDivElement>(null)
  const chatInputRef = useRef<HTMLInputElement>(null)

  const selectedDataset = useMemo(
    () => datasets.find(d => d.dataset_id === datasetId) ?? datasetProf,
    [datasets, datasetId, datasetProf],
  )

  // ── Load datasets on mount ─────────────────────────────────────────────────
  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const res = await listDatasets()
        if (!alive) return
        const list = res.datasets ?? []
        setDatasets(list)
        if (list[0]) { setDatasetId(list[0].dataset_id); setDatasetProf(list[0]) }
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : String(e))
      }
    })()
    return () => { alive = false }
  }, [])

  // ── Auto-scroll chat to bottom ──────────────────────────────────────────────
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatHistory, chatBusy])

  // ── Scroll to dashboard after generation ───────────────────────────────────
  useEffect(() => {
    if (dashboard) {
      setTimeout(() => dashboardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)
    }
  }, [dashboard])    // only on first dashboard appearance


  // ── Handlers ──────────────────────────────────────────────────────────────

  async function handleUploadComplete(profile: DatasetProfile) {
    setDatasets(prev => [profile, ...prev.filter(d => d.dataset_id !== profile.dataset_id)])
    setDatasetId(profile.dataset_id)
    setDatasetProf(profile)
    setError('')
  }

  async function handleGenerate() {
    if (!datasetId || !prompt.trim()) return
    setError(''); setBusy(true); setDashboard(null); setWarnings([]); setChatHistory([])
    try {
      const res = await generateDashboard(datasetId, prompt.trim())
      setDashboard(res.dashboard)
      setSessionId(res.session_id)
      setWarnings(res.warnings ?? [])
      // Seed the chat with a welcome message
      setChatHistory([{
        role: 'assistant',
        content: `Dashboard ready for: "${prompt.trim()}". Ask me to filter, compare, or drill down.`,
        timestamp: new Date(),
      }])
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function handleChatSend() {
    const msg = chatInput.trim()
    if (!msg || !sessionId || chatBusy) return

    // 1. Add user message immediately (optimistic update)
    const userMsg: ChatMsg = { role: 'user', content: msg, timestamp: new Date() }
    setChatHistory(prev => [...prev, userMsg])
    setChatInput('')
    setChatBusy(true)
    setError('')

    try {
      // 2. Call API — Gemini interprets + writes new SQL
      let res = await followUp(sessionId, msg).catch(async (err: unknown) => {
        // ── Auto-recovery: session lost after backend restart ────────────────
        const errMsg = err instanceof Error ? err.message : String(err)
        const isSessionLost =
          errMsg.includes('Unknown session_id') ||
          errMsg.includes('Session expired') ||
          errMsg.includes('Generate a dashboard first')

        if (isSessionLost && datasetId && prompt.trim()) {
          // Silently regenerate the dashboard to get a fresh session_id
          const regen = await generateDashboard(datasetId, prompt.trim())
          setDashboard(regen.dashboard)
          setSessionId(regen.session_id)
          setWarnings(regen.warnings ?? [])
          // Now retry the follow-up with the new session
          return followUp(regen.session_id, msg)
        }
        throw err  // bubble up any other errors
      })

      // 3. Update dashboard IN PLACE — charts re-render without any page reload
      setDashboard(res.dashboard)
      setWarnings(res.warnings ?? [])

      // 4. Add assistant reply
      const meaningful = res.warnings?.filter(
        w => !w.includes('auto-generating') && !w.includes('fallback') && !w.includes('Gemini')
      )
      const replyText = meaningful?.length
        ? `Updated. ${meaningful.slice(0, 2).join(' ')}`
        : 'Dashboard updated based on your request.'
      setChatHistory(prev => [...prev, {
        role: 'assistant', content: replyText, timestamp: new Date(),
      }])
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : String(e)
      setError(errMsg)
      setChatHistory(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, something went wrong: ${errMsg}`,
        timestamp: new Date(),
      }])
    } finally {
      setChatBusy(false)
      chatInputRef.current?.focus()
    }
  }


  function applyChip(chip: string) {
    setChatInput(chip)
    chatInputRef.current?.focus()
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <main className="min-h-screen">
      <div className="mx-auto max-w-6xl px-4 py-10 space-y-8">

        {/* ── Header ──────────────────────────────────────────────────────── */}
        <header>
          <div className="flex items-center gap-3 mb-2">
            <div className="h-9 w-9 rounded-xl bg-ink-900 grid place-items-center">
              <BarChart2 className="h-5 w-5 text-white" />
            </div>
            <h1 className="font-display text-3xl tracking-tight">
              Data Analyst <span className="text-ink-500">Dashboard</span>
            </h1>
            <Badge color="green"><Sparkles className="h-3 w-3" />Gemini AI</Badge>
          </div>
          <p className="text-ink-600 max-w-xl text-sm">
            Ask questions in plain English — Gemini writes the SQL, runs it on your
            data, and builds the dashboard. Chat below to refine in real time.
          </p>
        </header>

        {/* ── Dataset + Prompt ──────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-5">

          {/* Left: dataset picker */}
          <div className="space-y-4">
            <div className="rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft p-5 space-y-4">
              <div>
                <p className="font-display text-base tracking-tight">Dataset</p>
                <p className="text-xs text-ink-500 mt-0.5">Pick demo or upload a CSV</p>
              </div>
              <select
                className="w-full rounded-xl border border-ink-100 bg-white/80 px-3 py-2 text-sm"
                value={datasetId}
                onChange={e => {
                  setDatasetId(e.target.value)
                  setDatasetProf(datasets.find(d => d.dataset_id === e.target.value) ?? null)
                }}
                disabled={busy}
              >
                <option value="" disabled>Select a dataset…</option>
                {datasets.map(d => (
                  <option key={d.dataset_id} value={d.dataset_id}>
                    {d.original_filename ?? d.table_name}
                  </option>
                ))}
              </select>

              {selectedDataset && (
                <div className="flex flex-wrap gap-2">
                  <Badge><Database className="h-3 w-3" />{selectedDataset.row_count.toLocaleString()} rows</Badge>
                  <Badge>{selectedDataset.column_count} cols</Badge>
                  {selectedDataset.numeric_columns.slice(0, 2).map(c => (
                    <Badge key={c}>#{c}</Badge>
                  ))}
                </div>
              )}
            </div>

            <FileUpload onUploadComplete={handleUploadComplete} />

            {selectedDataset?.preview_rows?.length ? (
              <div className="rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft p-5">
                <p className="font-display text-sm tracking-tight mb-3 text-ink-700">Sample rows</p>
                <DataTable rows={selectedDataset.preview_rows.slice(0, 4)} />
              </div>
            ) : null}
          </div>

          {/* Right: prompt input */}
          <div className="rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft p-6 space-y-4">
            <div>
              <p className="font-display text-base tracking-tight">Ask a question</p>
              <p className="text-xs text-ink-500 mt-0.5">Plain English — Gemini writes the SQL</p>
            </div>

            <textarea
              className="w-full min-h-[90px] resize-y rounded-xl border border-ink-100 bg-white/80 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-ink-300 transition placeholder-ink-300"
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleGenerate() }}
              disabled={busy}
              placeholder="e.g. Which product category had the highest revenue last quarter?"
            />

            <div>
              <p className="text-xs text-ink-400 mb-2">Try an example:</p>
              <div className="flex flex-wrap gap-2">
                {EXAMPLE_PROMPTS.map(p => (
                  <button key={p} type="button" onClick={() => setPrompt(p)} disabled={busy}
                    className="text-xs rounded-full border border-ink-100 bg-white/70 px-3 py-1 hover:bg-white hover:border-ink-300 transition disabled:opacity-40">
                    {p}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between">
              <p className="text-xs text-ink-400">⌘+Enter to generate</p>
              <button type="button" onClick={handleGenerate}
                disabled={busy || !datasetId || prompt.trim().length < 3}
                className={clsx(
                  'flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium border transition',
                  busy || !datasetId || prompt.trim().length < 3
                    ? 'bg-ink-100 border-ink-100 text-ink-400 cursor-not-allowed'
                    : 'bg-ink-900 border-ink-900 text-white hover:bg-ink-700',
                )}>
                {busy
                  ? <><Loader2 className="h-4 w-4 animate-spin" />Analysing…</>
                  : <><Sparkles className="h-4 w-4" />Generate</>}
              </button>
            </div>
          </div>
        </div>

        {/* ── Error ───────────────────────────────────────────────────────── */}
        {error && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-5 flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium text-red-900 text-sm">Request failed</p>
              <p className="text-sm text-red-700 mt-1 break-words">{error}</p>
            </div>
          </div>
        )}

        {/* ── Warnings ────────────────────────────────────────────────────── */}
        {warnings.length > 0 && (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 space-y-2">
            <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide">Notices</p>
            <div className="flex flex-wrap gap-2">
              {warnings.map((w, i) => <Badge key={i} color="warn">{w}</Badge>)}
            </div>
          </div>
        )}

        {/* ── Loading skeleton ─────────────────────────────────────────────── */}
        {busy && !dashboard && (
          <div className="space-y-4">
            <div className="flex items-center gap-3 text-ink-500 text-sm">
              <Loader2 className="h-5 w-5 animate-spin" />
              Gemini is converting your question to SQL and building the dashboard…
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[1,2,3,4].map(i => <div key={i} className="h-20 rounded-2xl bg-ink-100/60 animate-pulse" />)}
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {[1,2].map(i => <div key={i} className="h-72 rounded-2xl bg-ink-100/60 animate-pulse" />)}
            </div>
          </div>
        )}

        {/* ── Dashboard ────────────────────────────────────────────────────── */}
        {dashboard && (
          <div
            ref={dashboardRef}
            className={clsx(
              "space-y-6 anim-rise",
              chatBusy && "opacity-70 pointer-events-none transition-opacity duration-300",
            )}
          >
            {/* Title + regenerate */}
            <div className="flex items-end justify-between gap-4 flex-wrap">
              <div>
                <h2 className="font-display text-3xl tracking-tight flex items-center gap-2">
                  {dashboard.title}
                  {chatBusy && <Loader2 className="h-5 w-5 animate-spin text-ink-400" />}
                </h2>
                {dashboard.message && <p className="text-sm text-ink-500 mt-1">{dashboard.message}</p>}
              </div>
              <button type="button" onClick={handleGenerate} disabled={busy}
                className="flex items-center gap-1.5 text-sm text-ink-600 hover:text-ink-900 transition">
                <RefreshCw className="h-4 w-4" />Regenerate
              </button>
            </div>

            {/* KPI cards */}
            {dashboard.summary_cards?.length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {dashboard.summary_cards.map(c => <KpiCard key={c.label} label={c.label} value={c.value} />)}
              </div>
            )}

            {/* Key findings */}
            {dashboard.insights?.length > 0 && (
              <div className="rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="h-4 w-4 text-ink-500" />
                  <p className="font-display text-base tracking-tight">Key Findings</p>
                </div>
                <ul className="space-y-2">
                  {dashboard.insights.map((ins, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-ink-700">
                      <ChevronRight className="h-4 w-4 text-ink-400 mt-0.5 flex-shrink-0" />
                      {ins}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Charts grid */}
            {dashboard.charts?.length > 0 && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {dashboard.charts.map(ch => (
                  <div key={ch.id} className="rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft p-5">
                    <div className="flex items-start justify-between gap-3 mb-4">
                      <div className="min-w-0">
                        <p className="font-display text-base tracking-tight truncate">{ch.title}</p>
                        <p className="text-xs text-ink-400 mt-0.5">
                          {ch.chartType}
                          {ch.xKey  ? ` · x: ${ch.xKey}` : ''}
                          {ch.yKeys?.length ? ` · y: ${ch.yKeys.join(', ')}` : ''}
                        </p>
                      </div>
                      <Badge>{(ch.data?.length ?? 0).toLocaleString()} rows</Badge>
                    </div>
                    <ChartRenderer spec={ch} />
                  </div>
                ))}
              </div>
            )}

            {/* SQL transparency */}
            <SqlPanel queries={dashboard.sql_queries ?? []} />
          </div>
        )}

        {/* ── Chat panel ───────────────────────────────────────────────────── */}
        {/* Appears after the first dashboard is generated and stays for the session */}
        {sessionId && (
          <div className="rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft overflow-hidden">

            {/* Chat header */}
            <div className="flex items-center gap-2 px-5 py-3 border-b border-ink-100 bg-ink-50/50">
              <Bot className="h-4 w-4 text-ink-600" />
              <p className="font-display text-sm tracking-tight">Refine your analysis</p>
              {chatBusy && (
                <span className="ml-auto flex items-center gap-1.5 text-xs text-ink-500">
                  <Loader2 className="h-3 w-3 animate-spin" />Updating dashboard…
                </span>
              )}
            </div>

            {/* Chat history */}
            <div className="px-5 py-4 space-y-3 max-h-64 overflow-y-auto">
              {chatHistory.length === 0 && (
                <p className="text-sm text-ink-400 text-center py-4">
                  Ask anything — filters, comparisons, chart type changes, drilldowns…
                </p>
              )}
              {chatHistory.map((msg, i) => (
                <div key={i} className={clsx("flex gap-2.5", msg.role === 'user' && "flex-row-reverse")}>
                  <div className={clsx(
                    "h-7 w-7 rounded-full grid place-items-center flex-shrink-0",
                    msg.role === 'user' ? "bg-ink-900" : "bg-ink-100",
                  )}>
                    {msg.role === 'user'
                      ? <User className="h-3.5 w-3.5 text-white" />
                      : <Bot  className="h-3.5 w-3.5 text-ink-600" />}
                  </div>
                  <div className={clsx(
                    "rounded-2xl px-4 py-2.5 text-sm max-w-[80%]",
                    msg.role === 'user'
                      ? "bg-ink-900 text-white rounded-tr-sm"
                      : "bg-ink-50 text-ink-800 border border-ink-100 rounded-tl-sm",
                  )}>
                    {msg.content}
                  </div>
                </div>
              ))}

              {/* Typing indicator */}
              {chatBusy && (
                <div className="flex gap-2.5">
                  <div className="h-7 w-7 rounded-full bg-ink-100 grid place-items-center">
                    <Bot className="h-3.5 w-3.5 text-ink-600" />
                  </div>
                  <div className="rounded-2xl rounded-tl-sm bg-ink-50 border border-ink-100 px-4 py-3">
                    <div className="flex gap-1">
                      <span className="h-2 w-2 rounded-full bg-ink-400 animate-bounce" style={{animationDelay:'0ms'}} />
                      <span className="h-2 w-2 rounded-full bg-ink-400 animate-bounce" style={{animationDelay:'150ms'}} />
                      <span className="h-2 w-2 rounded-full bg-ink-400 animate-bounce" style={{animationDelay:'300ms'}} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Quick suggestion chips */}
            <div className="px-5 pb-2 flex flex-wrap gap-2">
              {CHAT_CHIPS.map(chip => (
                <button key={chip} type="button" onClick={() => applyChip(chip)}
                  disabled={chatBusy}
                  className="text-xs rounded-full border border-ink-100 bg-white/70 px-3 py-1 hover:bg-white hover:border-ink-300 transition disabled:opacity-40">
                  {chip}
                </button>
              ))}
            </div>

            {/* Chat input */}
            <div className="px-5 pb-4 pt-2">
              <div className="flex gap-2">
                <input
                  ref={chatInputRef}
                  className="flex-1 rounded-xl border border-ink-100 bg-white/80 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ink-300 transition"
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleChatSend()
                    }
                  }}
                  disabled={chatBusy}
                  placeholder={
                    chatBusy
                      ? 'Updating dashboard…'
                      : 'e.g. Show only Electronics, or filter to Q3 2025…'
                  }
                />
                <button type="button" onClick={handleChatSend}
                  disabled={chatBusy || !chatInput.trim()}
                  className={clsx(
                    'flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium border transition',
                    chatBusy || !chatInput.trim()
                      ? 'bg-ink-100 border-ink-100 text-ink-400 cursor-not-allowed'
                      : 'bg-ink-900 border-ink-900 text-white hover:bg-ink-700',
                  )}>
                  {chatBusy
                    ? <Loader2 className="h-4 w-4 animate-spin" />
                    : <Send className="h-4 w-4" />}
                </button>
              </div>
            </div>

          </div>
        )}

      </div>
    </main>
  )
}