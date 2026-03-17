'use client'

import clsx from 'clsx'

type Props = {
  rows: Record<string, unknown>[]
  className?: string
}

function getColumns(rows: Record<string, unknown>[]) {
  const set = new Set<string>()
  for (const r of rows) {
    for (const k of Object.keys(r)) set.add(k)
  }
  return Array.from(set)
}

function renderCell(v: unknown) {
  if (v === null || v === undefined) return ''
  if (typeof v === 'number') return Number.isFinite(v) ? v.toLocaleString() : String(v)
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

export function DataTable({ rows, className }: Props) {
  const cols = getColumns(rows)
  if (!rows.length) {
    return <div className={clsx('text-sm text-ink-600', className)}>No rows</div>
  }

  return (
    <div className={clsx('overflow-auto rounded-xl border border-ink-100 bg-white/70', className)}>
      <table className="min-w-full text-sm">
        <thead className="sticky top-0 bg-white/90 backdrop-blur border-b border-ink-100">
          <tr>
            {cols.map((c) => (
              <th key={c} className="text-left font-medium text-ink-800 px-3 py-2 whitespace-nowrap">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => (
            <tr key={idx} className={idx % 2 ? 'bg-ink-50/40' : 'bg-transparent'}>
              {cols.map((c) => (
                <td key={c} className="px-3 py-2 text-ink-700 whitespace-nowrap">
                  {renderCell(r[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

