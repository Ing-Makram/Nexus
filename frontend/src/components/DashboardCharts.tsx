import { useMemo } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useDashboard } from '../dashboard/useDashboard'
import { formatAmount } from '../lib/format'
import type { DashboardTimeseriesPoint } from '../types/dashboard'

interface Row {
  label: string
  invoiced: number
  paid: number
  orders: number
  invoices: number
  customers: number
}

function toRow(point: DashboardTimeseriesPoint): Row {
  const [, month, day] = point.date.split('-')
  return {
    label: `${Number(month)}/${Number(day)}`,
    invoiced: Number(point.invoiced_amount),
    paid: Number(point.paid_amount),
    orders: point.orders,
    invoices: point.invoices,
    customers: point.customers,
  }
}

const AXIS = { fontSize: 12, fill: 'var(--text-muted)' }

const money = (value: unknown) => formatAmount(String(value ?? 0))

export function DashboardCharts() {
  const { timeseries, timeseriesStatus, range, setRange } = useDashboard()

  const rows = useMemo<Row[]>(() => (timeseries?.points ?? []).map(toRow), [timeseries])
  const tickGap = range === 90 ? 24 : 12

  return (
    <section className="card charts" aria-label="Activity over time">
      <div className="charts__head">
        <h3>Activity over time</h3>
        <div className="charts__range" role="group" aria-label="Date range">
          {([30, 90] as const).map((value) => (
            <button
              key={value}
              type="button"
              className="btn btn--ghost btn--sm"
              aria-pressed={range === value}
              onClick={() => setRange(value)}
            >
              {value} days
            </button>
          ))}
        </div>
      </div>

      {timeseriesStatus === 'loading' && <p className="section__status">Loading charts…</p>}
      {timeseriesStatus === 'error' && (
        <p role="alert" className="empty">
          Could not load the charts.
        </p>
      )}

      {timeseriesStatus === 'ready' && (
        <div className="charts__grid">
          <figure className="charts__item">
            <figcaption>Revenue — invoiced vs paid</figcaption>
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="label" tick={AXIS} minTickGap={tickGap} />
                <YAxis tick={AXIS} width={64} tickFormatter={money} />
                <Tooltip formatter={money} />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="invoiced"
                  name="Invoiced"
                  stroke="var(--brand)"
                  fill="var(--brand)"
                  fillOpacity={0.15}
                />
                <Area
                  type="monotone"
                  dataKey="paid"
                  name="Paid"
                  stroke="var(--success)"
                  fill="var(--success)"
                  fillOpacity={0.15}
                />
              </AreaChart>
            </ResponsiveContainer>
          </figure>

          <figure className="charts__item">
            <figcaption>Orders, invoices &amp; new customers</figcaption>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="label" tick={AXIS} minTickGap={tickGap} />
                <YAxis tick={AXIS} width={32} allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="orders"
                  name="Orders"
                  stroke="var(--brand)"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="invoices"
                  name="Invoices"
                  stroke="var(--info)"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="customers"
                  name="New customers"
                  stroke="var(--warn)"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </figure>
        </div>
      )}
    </section>
  )
}
