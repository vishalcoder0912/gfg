export default function NotFound() {
  return (
    <main className="min-h-screen bg-[color:var(--bg)] text-ink-900 grid place-items-center p-6">
      <div className="w-full max-w-xl rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft p-6">
        <h1 className="font-display text-2xl tracking-tight">Page not found</h1>
        <p className="mt-2 text-sm text-ink-600">The page you requested doesn’t exist.</p>
        <a
          href="/"
          className="inline-flex mt-5 rounded-xl px-4 py-2 text-sm font-medium border bg-white/70 border-ink-200 text-ink-900 hover:bg-white transition"
        >
          Go home
        </a>
      </div>
    </main>
  )
}

