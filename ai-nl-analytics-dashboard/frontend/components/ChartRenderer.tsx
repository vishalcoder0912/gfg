'use client'

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { ChartSpec } from '../lib/types'
import { DataTable } from './DataTable'

function asNumber(v: unknown): number | null {
  if (typeof v === 'number' && Number.isFinite(v)) return v
  if (typeof v === 'string' && v.trim()) {
    const n = Number(v)
    return Number.isFinite(n) ? n : null
  }
  return null
}

function tooltipFormatter(value: unknown) {
  const n = asNumber(value)
  if (n === null) return String(value ?? '')
  return n.toLocaleString()
}

const PALETTE = ['#ff8f1a', '#365163', '#2a3f4e', '#748898', '#e86f00', '#1d2c36']

export function ChartRenderer({ spec }: { spec: ChartSpec }) {
  if (spec.chartType === 'table') return <DataTable rows={spec.data} />
  if (!spec.data?.length) return <div className="text-sm text-ink-600">No data returned</div>

  const xKey = spec.xKey || undefined
  const yKeys = spec.yKeys || []

  if (spec.chartType === 'pie') {
    const nameKey = xKey ?? spec.columns?.[0] ?? 'name'
    const valueKey = yKeys[0] ?? spec.columns?.[1] ?? 'value'

    return (
      <div className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip formatter={tooltipFormatter} />
            <Legend />
            <Pie data={spec.data} dataKey={valueKey} nameKey={nameKey} outerRadius={92}>
              {/* Recharts auto-colors per cell if you pass Cells; keep it simple here */}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
    )
  }

  if (spec.chartType === 'line') {
    return (
      <div className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={spec.data}>
            <CartesianGrid strokeDasharray="4 4" opacity={0.35} />
            {xKey && <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />}
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip formatter={tooltipFormatter} />
            <Legend />
            {yKeys.map((k, i) => (
              <Line key={k} type="monotone" dataKey={k} stroke={PALETTE[i % PALETTE.length]} strokeWidth={2} dot={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    )
  }

  if (spec.chartType === 'area') {
    return (
      <div className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={spec.data}>
            <CartesianGrid strokeDasharray="4 4" opacity={0.35} />
            {xKey && <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />}
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip formatter={tooltipFormatter} />
            <Legend />
            {yKeys.map((k, i) => (
              <Area
                key={k}
                type="monotone"
                dataKey={k}
                stroke={PALETTE[i % PALETTE.length]}
                fill={PALETTE[i % PALETTE.length]}
                fillOpacity={0.18}
                strokeWidth={2}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // bar / stacked_bar
  const stacked = spec.chartType === 'stacked_bar'
  return (
    <div className="h-[280px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={spec.data}>
          <CartesianGrid strokeDasharray="4 4" opacity={0.35} />
          {xKey && <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />}
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip formatter={tooltipFormatter} />
          <Legend />
          {yKeys.map((k, i) => (
            <Bar
              key={k}
              dataKey={k}
              fill={PALETTE[i % PALETTE.length]}
              radius={[8, 8, 0, 0]}
              stackId={stacked ? 'a' : undefined}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

