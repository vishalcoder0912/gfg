'use client'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <main className="min-h-screen bg-[color:var(--bg)] text-ink-900 grid place-items-center p-6">
      <div className="w-full max-w-xl rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft p-6">
        <h1 className="font-display text-2xl tracking-tight">Something went wrong</h1>
        <p className="mt-2 text-sm text-ink-600 break-words">{error?.message || 'Unknown error'}</p>
        <div className="mt-5 flex items-center gap-3">
          <button
            type="button"
            onClick={() => reset()}
            className="rounded-xl px-4 py-2 text-sm font-medium border bg-white/70 border-ink-200 text-ink-900 hover:bg-white transition"
          >
            Try again
          </button>
          <a
            href="/"
            className="rounded-xl px-4 py-2 text-sm font-medium border bg-ink-50 border-ink-200 text-ink-900 hover:bg-white transition"
          >
            Go home
          </a>
        </div>
      </div>
    </main>
  )
}

