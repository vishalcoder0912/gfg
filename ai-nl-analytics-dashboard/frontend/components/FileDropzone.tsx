'use client'

import { useCallback, useMemo, useState } from 'react'
import { FileUp, Upload } from 'lucide-react'
import clsx from 'clsx'

type Props = {
  accept?: string
  maxBytes?: number
  onFile: (file: File) => void
  disabled?: boolean
}

function formatBytes(n: number) {
  const units = ['B', 'KB', 'MB', 'GB']
  let v = n
  let i = 0
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

export function FileDropzone({ accept = '.csv,text/csv', maxBytes = 50 * 1024 * 1024, onFile, disabled }: Props) {
  const [dragging, setDragging] = useState(false)
  const hint = useMemo(() => `CSV up to ${formatBytes(maxBytes)}`, [maxBytes])

  const validateAndSend = useCallback(
    (file: File | null) => {
      if (!file) return
      if (maxBytes && file.size > maxBytes) throw new Error(`File too large. Max ${formatBytes(maxBytes)}.`)
      onFile(file)
    },
    [maxBytes, onFile]
  )

  return (
    <label
      className={clsx(
        'block rounded-2xl border border-[color:var(--stroke)] bg-[color:var(--card)] shadow-soft p-5 transition',
        dragging ? 'ring-2 ring-ink-300' : 'hover:shadow-md',
        disabled && 'opacity-60 pointer-events-none'
      )}
      onDragEnter={(e) => {
        e.preventDefault()
        e.stopPropagation()
        setDragging(true)
      }}
      onDragOver={(e) => {
        e.preventDefault()
        e.stopPropagation()
        setDragging(true)
      }}
      onDragLeave={(e) => {
        e.preventDefault()
        e.stopPropagation()
        setDragging(false)
      }}
      onDrop={(e) => {
        e.preventDefault()
        e.stopPropagation()
        setDragging(false)
        try {
          validateAndSend(e.dataTransfer.files?.[0] ?? null)
        } catch (err) {
          // Let caller surface errors; here we fail silently.
        }
      }}
    >
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-xl bg-ink-50 grid place-items-center border border-ink-100">
          {dragging ? <Upload className="h-5 w-5 text-ink-700" /> : <FileUp className="h-5 w-5 text-ink-700" />}
        </div>
        <div className="min-w-0">
          <div className="font-display text-lg tracking-tight">Upload CSV</div>
          <div className="text-sm text-ink-600">{dragging ? 'Drop it here' : hint}</div>
        </div>
      </div>
      <input
        type="file"
        accept={accept}
        className="sr-only"
        onChange={(e) => {
          try {
            validateAndSend(e.target.files?.[0] ?? null)
          } catch (err) {
            // Caller handles; do nothing here.
          } finally {
            // allow re-selecting the same file
            e.target.value = ''
          }
        }}
      />
      <div className="mt-4 text-sm text-ink-700">
        <span className="inline-flex items-center gap-2 rounded-full border border-ink-100 bg-white/70 px-3 py-1">
          <span className="font-medium">Drag & drop</span>
          <span className="text-ink-500">or click to pick</span>
        </span>
      </div>
    </label>
  )
}
