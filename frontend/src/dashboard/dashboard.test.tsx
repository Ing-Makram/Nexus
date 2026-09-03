import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import App from '../App'
import type { DashboardStats, DashboardTimeseries } from '../types/dashboard'

const USER = {
  id: 1,
  email: 'user@example.com',
  first_name: 'Test',
  last_name: 'User',
  is_active: true,
  date_joined: '2026-01-01T00:00:00Z',
}

const ORG = { id: 1, name: 'Acme', role: 'owner', created_at: 'x', updated_at: 'x' }

const STATS: DashboardStats = {
  organization: 1,
  customers: { total: 4 },
  orders: { total: 6, by_status: { draft: 2, completed: 4 } },
  invoices: {
    total: 5,
    by_status: { paid: 2, sent: 2, overdue: 1 },
    total_amount: '12340.00',
    paid_amount: '5000.00',
    outstanding_amount: '7340.00',
    overdue_count: 1,
  },
  recent_orders: [
    {
      id: 9,
      customer: 'Globex',
      status: 'completed',
      total_amount: '250.00',
      created_at: '2026-03-01T00:00:00Z',
    },
  ],
  recent_invoices: [
    {
      id: 3,
      invoice_number: 'INV-0003',
      customer: 'Globex',
      status: 'overdue',
      total_amount: '90.00',
      issue_date: '2026-02-01',
      due_date: '2026-02-15',
    },
  ],
}

function makeTimeseries(days: 30 | 90): DashboardTimeseries {
  const points = Array.from({ length: days }, (_, i) => {
    const d = new Date(2026, 0, 1 + i)
    return {
      date: d.toISOString().slice(0, 10),
      orders: i % 3,
      invoices: i % 2,
      customers: i === 5 ? 2 : 0,
      invoiced_amount: `${i * 100}.00`,
      paid_amount: `${i * 40}.00`,
    }
  })
  return { organization: 1, start: points[0].date, end: points[days - 1].date, days, points }
}

function json(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => (body === undefined ? '' : JSON.stringify(body)),
  }
}

function installBackend({
  stats = STATS,
  dashboardStatus = 200,
}: { stats?: DashboardStats; dashboardStatus?: number } = {}) {
  const fetchMock = vi.fn(async (url: string) => {
    const path = url.split('?')[0]
    if (path.endsWith('/auth/refresh/')) return json(200, { access: 'access-token' })
    if (path.endsWith('/auth/me/')) return json(200, USER)
    if (path.endsWith('/organizations/')) return json(200, [ORG])
    if (path.includes('/dashboard/timeseries/')) {
      const days = url.includes('days=90') ? 90 : 30
      return json(200, makeTimeseries(days))
    }
    if (path.includes('/dashboard/')) {
      return dashboardStatus === 200 ? json(200, stats) : json(dashboardStatus, { detail: 'boom' })
    }
    return json(200, [])
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

beforeEach(() => {
  localStorage.clear()
  localStorage.setItem('nexus.auth.refresh', 'stored-refresh')
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test('the overview shows figures derived from the backend dashboard endpoint', async () => {
  const fetchMock = installBackend()
  render(<App />)

  // The overview is the default tab.
  expect(await screen.findByRole('heading', { name: 'Overview' })).toBeInTheDocument()

  const stat = (label: string) =>
    within(screen.getByText(label, { selector: '.stat__label' }).closest('.stat') as HTMLElement)
  expect(stat('Customers').getByText('4')).toBeInTheDocument()
  expect(stat('Orders').getByText('6')).toBeInTheDocument()
  expect(stat('Invoiced').getByText('$12,340.00')).toBeInTheDocument()
  expect(stat('Paid').getByText('$5,000.00')).toBeInTheDocument()
  expect(stat('Outstanding').getByText('$7,340.00')).toBeInTheDocument()

  const recentInvoices = within(screen.getByRole('region', { name: 'Recent invoices' }))
  expect(recentInvoices.getByText('INV-0003')).toBeInTheDocument()

  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining('/dashboard/?organization=1'),
    expect.anything(),
  )
})

test('renders the activity charts and refetches the series when the range changes', async () => {
  const fetchMock = installBackend()
  render(<App />)

  // <DashboardCharts> is lazy-loaded, so allow for the dynamic import.
  const heading = await screen.findByText('Activity over time', {}, { timeout: 5000 })
  const charts = within(heading.closest('.charts') as HTMLElement)
  expect(charts.getByText(/revenue — invoiced vs paid/i)).toBeInTheDocument()
  expect(charts.getByText(/orders, invoices & new customers/i)).toBeInTheDocument()

  const timeseriesCalls = () =>
    fetchMock.mock.calls.filter(([u]) => String(u).includes('/dashboard/timeseries/'))
  await vi.waitFor(() => expect(timeseriesCalls().length).toBeGreaterThan(0))
  expect(timeseriesCalls().every(([u]) => String(u).includes('days=30'))).toBe(true)

  fireEvent.click(charts.getByRole('button', { name: '90 days' }))

  await vi.waitFor(() =>
    expect(timeseriesCalls().some(([u]) => String(u).includes('days=90'))).toBe(true),
  )
  expect(charts.getByRole('button', { name: '90 days' })).toHaveAttribute('aria-pressed', 'true')
})

test('shows an empty overview when the organization has no data', async () => {
  installBackend({
    stats: {
      ...STATS,
      customers: { total: 0 },
      orders: { total: 0, by_status: {} },
      invoices: { ...STATS.invoices, total: 0 },
      recent_orders: [],
      recent_invoices: [],
    },
  })
  render(<App />)

  expect(await screen.findByText(/nothing here yet/i)).toBeInTheDocument()
})

test('shows an error state with a retry when the overview fails to load', async () => {
  const fetchMock = installBackend({ dashboardStatus: 500 })
  render(<App />)

  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent(/could not load the overview/i)

  const callsBefore = fetchMock.mock.calls.filter(([u]) => String(u).includes('/dashboard/')).length
  fireEvent.click(within(alert).getByRole('button', { name: /retry/i }))
  await vi.waitFor(() =>
    expect(
      fetchMock.mock.calls.filter(([u]) => String(u).includes('/dashboard/')).length,
    ).toBeGreaterThan(callsBefore),
  )
})

test('switching organization never shows the previous organization while the new figures are loading', async () => {
  const ORG_2 = { id: 2, name: 'Beedle', role: 'owner', created_at: 'x', updated_at: 'x' }
  const fetchMock = vi.fn(async (url: string) => {
    const path = url.split('?')[0]
    const orgId = new URLSearchParams(url.split('?')[1] ?? '').get('organization')
    if (path.endsWith('/auth/refresh/')) return json(200, { access: 'access-token' })
    if (path.endsWith('/auth/me/')) return json(200, USER)
    if (path.endsWith('/organizations/')) return json(200, [ORG, ORG_2])
    if (path.includes('/dashboard/timeseries/')) {
      if (orgId === '2') return new Promise<never>(() => {})
      return json(200, makeTimeseries(30))
    }
    if (path.includes('/dashboard/')) {
      // Org 2's request hangs forever, so if org 1's figures were still
      // showing when we assert, that would prove they leaked across the switch.
      if (orgId === '2') return new Promise<never>(() => {})
      return json(200, STATS)
    }
    return json(200, [])
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<App />)

  expect(await screen.findByRole('heading', { name: 'Overview' })).toBeInTheDocument()
  const stat = (label: string) =>
    within(screen.getByText(label, { selector: '.stat__label' }).closest('.stat') as HTMLElement)
  expect(stat('Invoiced').getByText('$12,340.00')).toBeInTheDocument()

  fireEvent.change(screen.getByRole('combobox', { name: /organization/i }), {
    target: { value: '2' },
  })

  // Org 1's figures must disappear immediately - not linger until org 2 loads.
  await waitFor(() => expect(screen.queryByText('$12,340.00')).not.toBeInTheDocument())
  expect(await screen.findByText(/loading overview/i)).toBeInTheDocument()
})

test('a manual Refresh started for one organization cannot overwrite another after a switch', async () => {
  const ORG_2 = { id: 2, name: 'Beedle', role: 'owner', created_at: 'x', updated_at: 'x' }
  const STATS_2: DashboardStats = {
    ...STATS,
    organization: 2,
    customers: { total: 77 },
    invoices: { ...STATS.invoices, total_amount: '55555.00' },
  }

  let releaseRefresh = () => {}
  let org1DashCalls = 0
  const fetchMock = vi.fn(async (url: string) => {
    const path = url.split('?')[0]
    const orgId = new URLSearchParams(url.split('?')[1] ?? '').get('organization')
    if (path.endsWith('/auth/refresh/')) return json(200, { access: 'access-token' })
    if (path.endsWith('/auth/me/')) return json(200, USER)
    if (path.endsWith('/organizations/')) return json(200, [ORG, ORG_2])
    if (path.includes('/dashboard/timeseries/')) {
      return json(200, makeTimeseries(orgId === '2' ? 30 : 30))
    }
    if (path.includes('/dashboard/')) {
      if (orgId === '2') return json(200, STATS_2)
      org1DashCalls += 1
      if (org1DashCalls === 1) return json(200, STATS) // initial load
      // The Refresh call: hang until the test releases it.
      await new Promise<void>((resolve) => {
        releaseRefresh = () => resolve()
      })
      return json(200, STATS)
    }
    return json(200, [])
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<App />)

  const stat = (label: string) =>
    within(screen.getByText(label, { selector: '.stat__label' }).closest('.stat') as HTMLElement)
  expect((await screen.findAllByText('$12,340.00')).length).toBeGreaterThan(0)

  fireEvent.click(screen.getByRole('button', { name: /refresh/i }))
  await vi.waitFor(() => expect(org1DashCalls).toBe(2))

  fireEvent.change(screen.getByRole('combobox', { name: /organization/i }), {
    target: { value: '2' },
  })
  await waitFor(() => expect(stat('Customers').getByText('77')).toBeInTheDocument())

  // Release org 1's stale Refresh response - it must not reappear under org 2.
  releaseRefresh()
  await new Promise((r) => setTimeout(r, 0))
  expect(stat('Customers').getByText('77')).toBeInTheDocument()
  expect(stat('Invoiced').getByText('$55,555.00')).toBeInTheDocument()
  expect(screen.queryByText('$12,340.00')).not.toBeInTheDocument()
})
