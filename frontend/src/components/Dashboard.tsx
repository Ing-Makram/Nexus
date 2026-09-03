import { lazy, Suspense } from 'react'
import { useDashboard } from '../dashboard/useDashboard'
import { daysUntil, formatAmount, formatDate } from '../lib/format'
import { INVOICE_STATUSES } from '../types/invoice'
import type { DashboardRecentInvoice, DashboardRecentOrder } from '../types/dashboard'
import { ORDER_STATUSES } from '../types/order'
import { StatusBadge } from './StatusBadge'

// The charting library is heavy and only the overview needs it; keep it out of
// the initial bundle (the login screen and other tabs never load it).
const DashboardCharts = lazy(() =>
  import('./DashboardCharts').then((m) => ({ default: m.DashboardCharts })),
)

function Stat({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone?: 'success' | 'warning' | 'danger'
}) {
  return (
    <div className={`stat${tone ? ` stat--${tone}` : ''}`}>
      <span className="stat__value">{value}</span>
      <span className="stat__label">{label}</span>
    </div>
  )
}

const ORDER_TONE: Record<string, string> = {
  draft: 'neutral',
  pending: 'info',
  confirmed: 'info',
  completed: 'success',
  cancelled: 'danger',
}
const INVOICE_TONE: Record<string, string> = {
  draft: 'neutral',
  sent: 'info',
  paid: 'success',
  overdue: 'danger',
  void: 'neutral',
}

function Distribution({
  title,
  kind,
  counts,
}: {
  title: string
  kind: 'order' | 'invoice'
  counts: Record<string, number>
}) {
  const order = kind === 'order' ? ORDER_STATUSES : INVOICE_STATUSES
  const tones = kind === 'order' ? ORDER_TONE : INVOICE_TONE
  const total = Object.values(counts).reduce((sum, n) => sum + n, 0)
  const rows = order.filter((status) => (counts[status] ?? 0) > 0)

  return (
    <section className="card" aria-label={title}>
      <h3>{title}</h3>
      {rows.length === 0 ? (
        <p className="empty">None yet.</p>
      ) : (
        <ul className="distribution">
          {rows.map((status) => {
            const n = counts[status] ?? 0
            return (
              <li key={status}>
                <StatusBadge kind={kind} status={status} />
                <span className="distribution__track" aria-hidden="true">
                  <span
                    className={`distribution__fill distribution__fill--${tones[status] ?? 'neutral'}`}
                    style={{ width: `${total ? Math.max(4, (n / total) * 100) : 0}%` }}
                  />
                </span>
                <span className="distribution__count">
                  {n}
                  <span className="visually-hidden"> of {total}</span>
                </span>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

function RecentOrders({ rows }: { rows: DashboardRecentOrder[] }) {
  return (
    <section className="card" aria-label="Recent orders">
      <h3>Recent orders</h3>
      {rows.length === 0 ? (
        <p className="empty">No orders yet.</p>
      ) : (
        <ul className="recent-list">
          {rows.map((order) => (
            <li key={order.id}>
              <span className="recent-list__main">
                <span className="recent-list__title">{order.customer}</span>
                <StatusBadge kind="order" status={order.status} />
              </span>
              <span className="recent-list__figure">
                <span className="recent-list__amount">{formatAmount(order.total_amount)}</span>
                <span className="recent-list__meta">{formatDate(order.created_at)}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function RecentInvoices({ rows }: { rows: DashboardRecentInvoice[] }) {
  return (
    <section className="card" aria-label="Recent invoices">
      <h3>Recent invoices</h3>
      {rows.length === 0 ? (
        <p className="empty">No invoices yet.</p>
      ) : (
        <ul className="recent-list">
          {rows.map((invoice) => {
            const due = daysUntil(invoice.due_date)
            const overdue =
              invoice.status !== 'paid' && invoice.status !== 'void' && due !== null && due < 0
            return (
              <li key={invoice.id}>
                <span className="recent-list__main">
                  <span className="recent-list__title">{invoice.invoice_number}</span>
                  <StatusBadge kind="invoice" status={invoice.status} />
                  <span className="list__sub">{invoice.customer}</span>
                </span>
                <span className="recent-list__figure">
                  <span className="recent-list__amount">{formatAmount(invoice.total_amount)}</span>
                  {invoice.due_date && (
                    <span className={`recent-list__meta${overdue ? ' text-danger' : ''}`}>
                      due {formatDate(invoice.due_date)}
                    </span>
                  )}
                </span>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

export function Dashboard() {
  const { status, stats, reload } = useDashboard()

  if (status === 'loading') {
    return <p className="section__status">Loading overview…</p>
  }
  if (status === 'error' || !stats) {
    return (
      <p role="alert" className="auth-error">
        Could not load the overview.{' '}
        <button type="button" className="link-button" onClick={() => void reload()}>
          Retry
        </button>
      </p>
    )
  }

  const { customers, orders, invoices, recent_orders, recent_invoices } = stats
  const isEmpty = customers.total === 0 && orders.total === 0 && invoices.total === 0
  const outstanding = Number(invoices.outstanding_amount)

  return (
    <div className="dashboard">
      <div className="section__head">
        <h2>Overview</h2>
        <button type="button" className="btn btn--ghost btn--sm" onClick={() => void reload()}>
          Refresh
        </button>
      </div>

      {isEmpty ? (
        <p className="empty">
          Nothing here yet. Add customers, orders and invoices and this overview fills in.
        </p>
      ) : (
        <>
          <div className="stat-grid">
            <Stat label="Customers" value={String(customers.total)} />
            <Stat label="Orders" value={String(orders.total)} />
            <Stat label="Invoiced" value={formatAmount(invoices.total_amount)} />
            <Stat label="Paid" value={formatAmount(invoices.paid_amount)} tone="success" />
            <Stat
              label="Outstanding"
              value={formatAmount(invoices.outstanding_amount)}
              tone={outstanding > 0 ? 'warning' : undefined}
            />
            <Stat
              label="Overdue invoices"
              value={String(invoices.overdue_count)}
              tone={invoices.overdue_count > 0 ? 'danger' : undefined}
            />
          </div>

          <Suspense fallback={<p className="section__status">Loading charts…</p>}>
            <DashboardCharts />
          </Suspense>

          <div className="dashboard__cols">
            <Distribution title="Orders by status" kind="order" counts={orders.by_status} />
            <Distribution title="Invoices by status" kind="invoice" counts={invoices.by_status} />
          </div>

          <div className="dashboard__cols">
            <RecentOrders rows={recent_orders} />
            <RecentInvoices rows={recent_invoices} />
          </div>
        </>
      )}
    </div>
  )
}
