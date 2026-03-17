'use client'

import { useMemo, useState } from 'react'
import { ChevronDown, Code2 } from 'lucide-react'
import clsx from 'clsx'

import type { SqlQuerySpec } from '../lib/types'

type Props = {
  queries: SqlQuerySpec[]
}

export function SqlPanel({ queries }: Props) {
  const [open, setOpen] = useState(false)
  const countLabel = useMemo(() => `${queries.length} SQL quer${queries.length === 1 ? 'y' : 'ies'}`, [queries.length])

  if (!queries.length) return null

  return (
    <div className="rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft">
      <button
        type="button"
        className="w-full flex items-center justify-between gap-3 px-5 py-4"
        onClick={() => setOpen((v) => !v)}
      >
        <div className="flex items-center gap-2">
          <span className="h-9 w-9 rounded-xl bg-ink-50 grid place-items-center border border-ink-100">
            <Code2 className="h-5 w-5 text-ink-700" />
          </span>
          <div className="text-left">
            <div className="font-display text-lg tracking-tight">SQL Transparency</div>
            <div className="text-sm text-ink-600">{countLabel}</div>
          </div>
        </div>
        <ChevronDown className={clsx('h-5 w-5 text-ink-700 transition', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="border-t border-ink-100 px-5 py-4 anim-rise">
          <div className="space-y-4">
            {queries.map((q) => (
              <div key={q.id} className="rounded-xl border border-ink-100 bg-white/70">
                <div className="px-4 py-3 border-b border-ink-100">
                  <div className="font-medium text-ink-800">{q.title}</div>
                  <div className="text-xs text-ink-500">{q.intent}</div>
                </div>
                <pre className="px-4 py-3 text-xs overflow-auto">
                  <code>{q.sql}</code>
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

