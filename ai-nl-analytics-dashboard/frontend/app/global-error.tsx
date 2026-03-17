'use client'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html lang="en">
      <body>
        <main className="min-h-screen bg-white text-gray-900 grid place-items-center p-6">
          <div className="w-full max-w-xl rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
            <h1 className="text-2xl font-semibold">Application error</h1>
            <p className="mt-2 text-sm text-gray-600 break-words">{error?.message || 'Unknown error'}</p>
            <button
              type="button"
              onClick={() => reset()}
              className="mt-5 rounded-xl px-4 py-2 text-sm font-medium border border-gray-200 hover:bg-gray-50"
            >
              Try again
            </button>
          </div>
        </main>
      </body>
    </html>
  )
}

