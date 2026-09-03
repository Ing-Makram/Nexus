import { useMemo } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
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
const GRID = 'var(--border)'
const TOOLTIP = {
  border: '1px solid var(--border-strong)',
  borderRadius: 8,
  fontSize: 12,
}

const money = (value: unknown) => formatAmount(String(value ?? 0))
const compactMoney = (value: number) =>
  value >= 1000 ? `$${Math.round(value / 1000)}k` : `$${value}`

export function DashboardCharts() {
  const { timeseries, timeseriesStatus, range, setRange } = useDashboard()

  const rows = useMemo<Row[]>(() => (timeseries?.points ?? []).map(toRow), [timeseries])
  // Roughly six labels on the axis whatever the window length.
  const tickInterval = Math.max(0, Math.ceil(rows.length / 6) - 1)

  return (
    <section className="card charts" aria-label="Activity over time">
      <div className="charts__head">
        <h3>Activity over time</h3>
        <div className="segmented" role="group" aria-label="Date range">
          {([30, 90] as const).map((value) => (
            <button
              key={value}
              type="button"
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
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={rows} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={AXIS}
                  interval={tickInterval}
                  tickLine={false}
                  axisLine={{ stroke: GRID }}
                />
                <YAxis
                  tick={AXIS}
                  width={40}
                  tickLine={false}
                  axisLine={false}
                  tickCount={4}
                  tickFormatter={compactMoney}
                />
                <Tooltip formatter={money} contentStyle={TOOLTIP} />
                <Legend iconType="plainline" wrapperStyle={{ fontSize: 12 }} />
                <Area
                  type="monotone"
                  dataKey="invoiced"
                  name="Invoiced"
                  stroke="var(--brand)"
                  strokeWidth={2}
                  fill="var(--brand)"
                  fillOpacity={0.1}
                  activeDot={{ r: 3 }}
                />
                <Area
                  type="monotone"
                  dataKey="paid"
                  name="Paid"
                  stroke="var(--success)"
                  strokeWidth={2}
                  fill="var(--success)"
                  fillOpacity={0.1}
                  activeDot={{ r: 3 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </figure>

          <figure className="charts__item">
            <figcaption>Orders, invoices &amp; new customers</figcaption>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={rows} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={AXIS}
                  interval={tickInterval}
                  tickLine={false}
                  axisLine={{ stroke: GRID }}
                />
                <YAxis
                  tick={AXIS}
                  width={28}
                  tickLine={false}
                  axisLine={false}
                  allowDecimals={false}
                />
                <Tooltip contentStyle={TOOLTIP} cursor={{ fill: 'var(--surface-2)' }} />
                <Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="orders" name="Orders" stackId="a" fill="#6366f1" maxBarSize={22} />
                <Bar
                  dataKey="invoices"
                  name="Invoices"
                  stackId="a"
                  fill="#0ea5e9"
                  maxBarSize={22}
                />
                <Bar
                  dataKey="customers"
                  name="New customers"
                  stackId="a"
                  fill="#f59e0b"
                  maxBarSize={22}
                  radius={[2, 2, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </figure>
        </div>
      )}
    </section>
  )
}
