export type DatasetProfile = {
  dataset_id: string
  table_name: string
  source: 'demo' | 'upload'
  original_filename?: string | null
  row_count: number
  column_count: number
  columns: string[]
  numeric_columns: string[]
  categorical_columns: string[]
  date_columns: string[]
  preview_rows: Record<string, unknown>[]
}

export type SummaryCard = {
  label: string
  value: unknown
}

export type SqlQuerySpec = {
  id: string
  title: string
  intent: string
  sql: string
}

export type ChartSpec = {
  id: string
  title: string
  chartType: 'line' | 'bar' | 'stacked_bar' | 'area' | 'pie' | 'table'
  xKey?: string | null
  yKeys: string[]
  data: Record<string, unknown>[]
  columns: string[]
}

export type DashboardSpec = {
  title: string
  summary_cards: SummaryCard[]
  charts: ChartSpec[]
  insights: string[]
  sql_queries: SqlQuerySpec[]
  message?: string | null
}

export type GenerateDashboardResponse = {
  dashboard: DashboardSpec
  session_id: string
  warnings: string[]
}

export type FollowUpResponse = {
  dashboard: DashboardSpec
  warnings: string[]
}

export type DatasetsListResponse = {
  datasets: DatasetProfile[]
}

