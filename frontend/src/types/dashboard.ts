export interface DashboardRecentOrder {
  id: number
  customer: string
  status: string
  total_amount: string
  created_at: string
}

export interface DashboardRecentInvoice {
  id: number
  invoice_number: string
  customer: string
  status: string
  total_amount: string
  issue_date: string
  due_date: string | null
}

export interface DashboardTimeseriesPoint {
  date: string
  orders: number
  invoices: number
  customers: number
  invoiced_amount: string
  paid_amount: string
}

export interface DashboardTimeseries {
  organization: number
  start: string
  end: string
  days: number
  points: DashboardTimeseriesPoint[]
}

export interface DashboardStats {
  organization: number
  customers: { total: number }
  orders: {
    total: number
    by_status: Record<string, number>
  }
  invoices: {
    total: number
    by_status: Record<string, number>
    total_amount: string
    paid_amount: string
    outstanding_amount: string
    overdue_count: number
  }
  recent_orders: DashboardRecentOrder[]
  recent_invoices: DashboardRecentInvoice[]
}
