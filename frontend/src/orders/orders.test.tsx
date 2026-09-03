import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import App from '../App'

const EMPTY_DASHBOARD = {
  organization: 1,
  customers: { total: 0 },
  orders: { total: 0, by_status: {} },
  invoices: {
    total: 0,
    by_status: {},
    total_amount: '0.00',
    paid_amount: '0.00',
    outstanding_amount: '0.00',
    overdue_count: 0,
  },
  recent_orders: [],
  recent_invoices: [],
}

/** Render the app and open the Orders tab. */
async function renderApp() {
  render(<App />)
  fireEvent.click(await screen.findByRole('button', { name: 'Orders' }))
}

const USER = {
  id: 1,
  email: 'user@example.com',
  first_name: 'Test',
  last_name: 'User',
  is_active: true,
  date_joined: '2026-01-01T00:00:00Z',
}

interface Org {
  id: number
  name: string
  role: string
  created_at: string
  updated_at: string
}

interface Customer {
  id: number
  organization: number
  name: string
  email: string
  phone: string
  company: string
  address: string
  created_at: string
  updated_at: string
}

interface Order {
  id: number
  organization: number
  customer: number
  status: string
  total_amount: string
  notes: string
  created_at: string
  updated_at: string
}

const ORG_A: Org = { id: 1, name: 'Alpha', role: 'owner', created_at: 'x', updated_at: 'x' }
const ORG_B: Org = { id: 2, name: 'Beta', role: 'owner', created_at: 'x', updated_at: 'x' }

function makeCustomer(partial: Pick<Customer, 'id' | 'organization' | 'name'>): Customer {
  return {
    email: '',
    phone: '',
    company: '',
    address: '',
    created_at: 'x',
    updated_at: 'x',
    ...partial,
  }
}

function makeOrder(
  partial: Pick<Order, 'id' | 'organization' | 'customer'> & Partial<Order>,
): Order {
  return {
    status: 'draft',
    total_amount: '10.00',
    notes: '',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: 'x',
    ...partial,
  }
}

function json(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => (body === undefined ? '' : JSON.stringify(body)),
  }
}

function pathOf(url: string) {
  return url.split('?')[0]
}

function queryOf(url: string) {
  return new URLSearchParams(url.split('?')[1] ?? '')
}

interface BackendOptions {
  orgs: Org[]
  customers?: Customer[]
  orders?: Order[]
  ordersListStatus?: number
  createStatus?: number
  holdOrders?: boolean
  /** Never resolve the orders GET for this one organization id. */
  holdOrdersForOrg?: number
}

function installBackend(opts: BackendOptions) {
  const orgs = [...opts.orgs]
  const customers = [...(opts.customers ?? [])]
  const orders = [...(opts.orders ?? [])]
  let nextId = orders.reduce((max, o) => Math.max(max, o.id), 500) + 1
  const listStatus = opts.ordersListStatus ?? 200
  const createStatus = opts.createStatus ?? 201

  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET'
    const body = init?.body ? (JSON.parse(init.body as string) as Record<string, unknown>) : {}
    const path = pathOf(url)
    const query = queryOf(url)

    if (path.endsWith('/auth/refresh/')) return json(200, { access: 'access-token' })
    if (path.endsWith('/auth/me/')) return json(200, USER)
    if (path.includes('/dashboard/')) return json(200, EMPTY_DASHBOARD)
    if (path.endsWith('/organizations/') && method === 'GET') {
      return json(
        200,
        [...orgs].sort((a, b) => a.name.localeCompare(b.name)),
      )
    }
    if (path.endsWith('/customers/') && method === 'GET') return json(200, customers)
    if (path.includes('/invoices/') && method === 'GET') return json(200, [])

    if (path.endsWith('/orders/') && method === 'GET') {
      if (opts.holdOrders) return new Promise<never>(() => {})
      const orgId = query.get('organization')
      if (opts.holdOrdersForOrg != null && orgId === String(opts.holdOrdersForOrg)) {
        return new Promise<never>(() => {})
      }
      if (listStatus !== 200) return json(listStatus, { detail: 'boom' })
      const status = query.get('status')
      const dateFrom = query.get('date_from')
      const dateTo = query.get('date_to')
      let scoped = orgId ? orders.filter((o) => String(o.organization) === orgId) : orders
      if (status) scoped = scoped.filter((o) => o.status === status)
      if (dateFrom) scoped = scoped.filter((o) => o.created_at.slice(0, 10) >= dateFrom)
      if (dateTo) scoped = scoped.filter((o) => o.created_at.slice(0, 10) <= dateTo)
      return json(200, scoped)
    }
    if (path.endsWith('/orders/') && method === 'POST') {
      if (createStatus !== 201) {
        return json(createStatus, { total_amount: ['A valid number is required.'] })
      }
      const created = makeOrder({
        id: nextId++,
        organization: Number(body.organization),
        customer: Number(body.customer),
        status: String(body.status ?? 'draft'),
        total_amount: String(body.total_amount ?? '0'),
        notes: String(body.notes ?? ''),
        created_at: `2026-02-0${nextId}T00:00:00Z`,
      })
      orders.push(created)
      return json(201, created)
    }

    const match = path.match(/\/orders\/(\d+)\/$/)
    if (match && method === 'PATCH') {
      const target = orders.find((o) => o.id === Number(match[1]))
      if (!target) return json(404, { detail: 'not found' })
      Object.assign(target, {
        customer: body.customer ?? target.customer,
        status: body.status ?? target.status,
        total_amount: body.total_amount ?? target.total_amount,
        notes: body.notes ?? target.notes,
      })
      return json(200, target)
    }
    if (match && method === 'DELETE') {
      const index = orders.findIndex((o) => o.id === Number(match[1]))
      if (index === -1) return json(404, { detail: 'not found' })
      orders.splice(index, 1)
      return json(204, undefined)
    }

    return json(404, { detail: 'not found' })
  })

  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

async function ordersRegion() {
  return within(await screen.findByRole('region', { name: 'Orders' }))
}

/** The order rows, excluding the status-filter select and the add form. */
async function ordersList() {
  const region = await ordersRegion()
  return within(await region.findByRole('list'))
}

function patchBodies(fetchMock: ReturnType<typeof vi.fn>) {
  return fetchMock.mock.calls
    .filter(([, init]) => (init as RequestInit | undefined)?.method === 'PATCH')
    .map(([, init]) => JSON.parse((init as RequestInit).body as string))
}

function methodsUsed(fetchMock: ReturnType<typeof vi.fn>) {
  return fetchMock.mock.calls.map(([, init]) => (init as RequestInit | undefined)?.method ?? 'GET')
}

function orderListUrls(fetchMock: ReturnType<typeof vi.fn>) {
  return fetchMock.mock.calls
    .filter(
      ([url, init]) =>
        typeof url === 'string' &&
        pathOf(url).endsWith('/orders/') &&
        ((init as RequestInit | undefined)?.method ?? 'GET') === 'GET',
    )
    .map(([url]) => url as string)
}

beforeEach(() => {
  localStorage.clear()
  localStorage.setItem('nexus.auth.refresh', 'stored-refresh')
  vi.spyOn(window, 'confirm').mockReturnValue(true)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test('shows the current organization orders with the customer name', async () => {
  installBackend({
    orgs: [ORG_A, ORG_B],
    customers: [
      makeCustomer({ id: 11, organization: 1, name: 'Acme Ltd' }),
      makeCustomer({ id: 21, organization: 2, name: 'Beedle Inc' }),
    ],
    orders: [
      makeOrder({
        id: 101,
        organization: 1,
        customer: 11,
        status: 'pending',
        total_amount: '99.00',
      }),
      makeOrder({ id: 201, organization: 2, customer: 21 }),
    ],
  })
  await renderApp()

  const list = await ordersList()
  expect(await list.findByText('Acme Ltd')).toBeInTheDocument()
  expect(list.getByText(/pending/i)).toBeInTheDocument()
  expect(list.getByText(/99\.00/)).toBeInTheDocument()
})

test('hides orders that belong to another organization', async () => {
  installBackend({
    orgs: [ORG_A, ORG_B],
    customers: [
      makeCustomer({ id: 11, organization: 1, name: 'Acme Ltd' }),
      makeCustomer({ id: 21, organization: 2, name: 'Beedle Inc' }),
    ],
    orders: [
      makeOrder({ id: 101, organization: 1, customer: 11 }),
      makeOrder({ id: 201, organization: 2, customer: 21 }),
    ],
  })
  await renderApp()

  const region = await ordersRegion()
  await region.findByText('Acme Ltd')
  expect(region.queryByText('Beedle Inc')).not.toBeInTheDocument()
})

test('the list request is scoped to the current organization', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [makeCustomer({ id: 11, organization: 1, name: 'Acme Ltd' })],
    orders: [makeOrder({ id: 101, organization: 1, customer: 11 })],
  })
  await renderApp()

  await (await ordersList()).findByText('Acme Ltd')
  expect(orderListUrls(fetchMock).every((url) => url.includes('organization=1'))).toBe(true)
})

test('empty state when the organization has no orders', async () => {
  installBackend({ orgs: [ORG_A], orders: [] })
  await renderApp()

  const region = await ordersRegion()
  expect(await region.findByText(/no orders yet/i)).toBeInTheDocument()
})

test('loading state while orders are being fetched', async () => {
  installBackend({ orgs: [ORG_A], holdOrders: true })
  await renderApp()

  const region = await ordersRegion()
  expect(await region.findByText(/loading orders/i)).toBeInTheDocument()
})

test('error state when the orders request fails', async () => {
  installBackend({ orgs: [ORG_A], ordersListStatus: 500 })
  await renderApp()

  const region = await ordersRegion()
  expect(await region.findByText(/could not load orders/i)).toBeInTheDocument()
})

test('creates an order for the current organization', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [makeCustomer({ id: 11, organization: 1, name: 'Acme Ltd' })],
    orders: [],
  })
  await renderApp()

  const region = await ordersRegion()
  fireEvent.click(await region.findByRole('button', { name: /add order/i }))
  fireEvent.change(region.getByLabelText('Customer'), { target: { value: '11' } })
  fireEvent.change(region.getByLabelText('Total amount'), { target: { value: '150.00' } })
  fireEvent.click(region.getByRole('button', { name: /add order/i }))

  expect(await (await ordersList()).findByText('Acme Ltd')).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining('/orders/'),
    expect.objectContaining({
      method: 'POST',
      body: expect.stringContaining('"organization":1'),
    }),
  )
})

test('a double-click on the create button only sends one order request', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [makeCustomer({ id: 11, organization: 1, name: 'Acme Ltd' })],
    orders: [],
  })
  await renderApp()

  const region = await ordersRegion()
  fireEvent.click(await region.findByRole('button', { name: /add order/i }))
  fireEvent.change(region.getByLabelText('Customer'), { target: { value: '11' } })
  fireEvent.change(region.getByLabelText('Total amount'), { target: { value: '150.00' } })

  const submit = region.getByRole('button', { name: /add order/i })
  fireEvent.click(submit)
  fireEvent.click(submit)

  await (await ordersList()).findByText('Acme Ltd')
  const posts = fetchMock.mock.calls.filter(
    ([u, init]) =>
      String(u).includes('/orders/') && (init as RequestInit | undefined)?.method === 'POST',
  )
  expect(posts).toHaveLength(1)
})

test('surfaces an API validation error when creating an order', async () => {
  installBackend({
    orgs: [ORG_A],
    customers: [makeCustomer({ id: 11, organization: 1, name: 'Acme Ltd' })],
    orders: [],
    createStatus: 400,
  })
  await renderApp()

  const region = await ordersRegion()
  fireEvent.click(await region.findByRole('button', { name: /add order/i }))
  fireEvent.change(region.getByLabelText('Customer'), { target: { value: '11' } })
  fireEvent.change(region.getByLabelText('Total amount'), { target: { value: 'abc' } })
  fireEvent.click(region.getByRole('button', { name: /add order/i }))

  expect(await region.findByRole('alert')).toHaveTextContent(/valid number is required/i)
})

test('an edit sends only the fields that actually changed', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [makeCustomer({ id: 11, organization: 1, name: 'Acme Ltd' })],
    orders: [
      makeOrder({
        id: 101,
        organization: 1,
        customer: 11,
        status: 'draft',
        total_amount: '10.00',
        notes: 'keep',
      }),
    ],
  })
  await renderApp()

  const region = await ordersRegion()
  fireEvent.click(await region.findByRole('button', { name: /edit/i }))
  fireEvent.change(region.getByLabelText('Status'), { target: { value: 'confirmed' } })
  fireEvent.click(region.getByRole('button', { name: /^save$/i }))

  await waitFor(() => expect(patchBodies(fetchMock)).toHaveLength(1))
  expect(patchBodies(fetchMock)[0]).toEqual({ status: 'confirmed' })
})

test('saving an edit with no changes does not send a PATCH', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [makeCustomer({ id: 11, organization: 1, name: 'Acme Ltd' })],
    orders: [makeOrder({ id: 101, organization: 1, customer: 11 })],
  })
  await renderApp()

  const region = await ordersRegion()
  fireEvent.click(await region.findByRole('button', { name: /edit/i }))
  fireEvent.click(region.getByRole('button', { name: /^save$/i }))

  await region.findByRole('button', { name: /edit/i })
  expect(methodsUsed(fetchMock)).not.toContain('PATCH')
})

test('deletes an order', async () => {
  installBackend({
    orgs: [ORG_A],
    customers: [
      makeCustomer({ id: 11, organization: 1, name: 'Acme Ltd' }),
      makeCustomer({ id: 12, organization: 1, name: 'Globex' }),
    ],
    orders: [
      makeOrder({ id: 101, organization: 1, customer: 11 }),
      makeOrder({ id: 102, organization: 1, customer: 12 }),
    ],
  })
  await renderApp()

  const list = await ordersList()
  const row = (await list.findByText('Acme Ltd')).closest('li') as HTMLElement
  fireEvent.click(within(row).getByRole('button', { name: /delete/i }))

  await waitFor(() => expect(list.queryByText('Acme Ltd')).not.toBeInTheDocument())
  expect(list.getByText('Globex')).toBeInTheDocument()
})

test('delete asks for confirmation and does nothing when cancelled', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(false)
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [makeCustomer({ id: 11, organization: 1, name: 'Acme Ltd' })],
    orders: [makeOrder({ id: 101, organization: 1, customer: 11 })],
  })
  await renderApp()

  const list = await ordersList()
  const row = (await list.findByText('Acme Ltd')).closest('li') as HTMLElement
  fireEvent.click(within(row).getByRole('button', { name: /delete/i }))

  expect(window.confirm).toHaveBeenCalled()
  expect(list.getByText('Acme Ltd')).toBeInTheDocument()
  expect(methodsUsed(fetchMock)).not.toContain('DELETE')
})

test('switching organization requests the new organization and drops the old results', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A, ORG_B],
    customers: [
      makeCustomer({ id: 11, organization: 1, name: 'Acme Ltd' }),
      makeCustomer({ id: 21, organization: 2, name: 'Beedle Inc' }),
    ],
    orders: [
      makeOrder({ id: 101, organization: 1, customer: 11 }),
      makeOrder({ id: 201, organization: 2, customer: 21 }),
    ],
  })
  await renderApp()

  const region = await ordersRegion()
  expect(await region.findByText('Acme Ltd')).toBeInTheDocument()

  fireEvent.change(screen.getByRole('combobox', { name: /organization/i }), {
    target: { value: '2' },
  })

  expect(await region.findByText('Beedle Inc')).toBeInTheDocument()
  expect(region.queryByText('Acme Ltd')).not.toBeInTheDocument()
  expect(orderListUrls(fetchMock).some((url) => url.includes('organization=2'))).toBe(true)
})

test('switching organization never shows the previous organization while the new list is loading', async () => {
  installBackend({
    orgs: [ORG_A, ORG_B],
    customers: [
      makeCustomer({ id: 11, organization: 1, name: 'Acme Ltd' }),
      makeCustomer({ id: 21, organization: 2, name: 'Beedle Inc' }),
    ],
    orders: [makeOrder({ id: 101, organization: 1, customer: 11 })],
    // Org 2's request hangs forever, so if the previous org's rows were still
    // showing when we assert, that would prove they leaked across the switch.
    holdOrdersForOrg: 2,
  })
  await renderApp()

  const region = await ordersRegion()
  expect(await region.findByText('Acme Ltd')).toBeInTheDocument()

  fireEvent.change(screen.getByRole('combobox', { name: /organization/i }), {
    target: { value: '2' },
  })

  // Org 1's data must disappear immediately - not linger until org 2 loads.
  await waitFor(() => expect(region.queryByText('Acme Ltd')).not.toBeInTheDocument())
  expect(await region.findByText(/loading orders/i)).toBeInTheDocument()
})

test('the status filter requests the backend and clearing it removes the parameter', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [
      makeCustomer({ id: 11, organization: 1, name: 'Acme Ltd' }),
      makeCustomer({ id: 12, organization: 1, name: 'Globex' }),
    ],
    orders: [
      makeOrder({ id: 101, organization: 1, customer: 11, status: 'draft' }),
      makeOrder({ id: 102, organization: 1, customer: 12, status: 'completed' }),
    ],
  })
  await renderApp()

  const region = await ordersRegion()
  await (await ordersList()).findByText('Acme Ltd')

  // Initial list request carries the organization and no status.
  const initial = orderListUrls(fetchMock)
  expect(initial.some((url) => url.includes('organization=1') && !url.includes('status='))).toBe(
    true,
  )

  const filter = region.getByLabelText(/filter by status/i)
  fireEvent.change(filter, { target: { value: 'completed' } })
  await waitFor(() =>
    expect(
      orderListUrls(fetchMock).some((url) => url.includes('organization=1&status=completed')),
    ).toBe(true),
  )

  fireEvent.change(filter, { target: { value: 'draft' } })
  await waitFor(() =>
    expect(
      orderListUrls(fetchMock).some((url) => url.includes('organization=1&status=draft')),
    ).toBe(true),
  )

  const beforeClear = orderListUrls(fetchMock).length
  fireEvent.change(filter, { target: { value: '' } })
  await waitFor(() => expect(orderListUrls(fetchMock).length).toBeGreaterThan(beforeClear))
  const last = orderListUrls(fetchMock).at(-1) as string
  expect(last).toContain('organization=1')
  expect(last).not.toContain('status=')
})

test('the date range filter is sent to the backend and narrows the list', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [
      makeCustomer({ id: 11, organization: 1, name: 'Acme Ltd' }),
      makeCustomer({ id: 12, organization: 1, name: 'Globex' }),
    ],
    orders: [
      makeOrder({ id: 101, organization: 1, customer: 11, created_at: '2026-01-05T00:00:00Z' }),
      makeOrder({ id: 102, organization: 1, customer: 12, created_at: '2026-06-05T00:00:00Z' }),
    ],
  })
  await renderApp()

  const region = await ordersRegion()
  await (await ordersList()).findByText('Acme Ltd')

  fireEvent.change(region.getByLabelText('From'), { target: { value: '2026-03-01' } })

  await waitFor(() =>
    expect(orderListUrls(fetchMock).some((url) => url.includes('date_from=2026-03-01'))).toBe(true),
  )
  await waitFor(async () =>
    expect((await ordersList()).queryByText('Acme Ltd')).not.toBeInTheDocument(),
  )
  expect((await ordersList()).getByText('Globex')).toBeInTheDocument()

  const beforeClear = orderListUrls(fetchMock).length
  fireEvent.click(region.getByRole('button', { name: /clear/i }))
  await waitFor(() => expect(orderListUrls(fetchMock).length).toBeGreaterThan(beforeClear))
  expect(orderListUrls(fetchMock).at(-1)).not.toContain('date_from=')
})

test('switching organization resets the status filter', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A, ORG_B],
    customers: [
      makeCustomer({ id: 11, organization: 1, name: 'Acme Ltd' }),
      makeCustomer({ id: 21, organization: 2, name: 'Beedle Inc' }),
    ],
    orders: [
      makeOrder({ id: 101, organization: 1, customer: 11, status: 'completed' }),
      makeOrder({ id: 201, organization: 2, customer: 21, status: 'draft' }),
    ],
  })
  await renderApp()

  const region = await ordersRegion()
  await region.findByText('Acme Ltd')

  fireEvent.change(region.getByLabelText(/filter by status/i), { target: { value: 'completed' } })
  await waitFor(() =>
    expect(orderListUrls(fetchMock).some((url) => url.includes('status=completed'))).toBe(true),
  )

  fireEvent.change(screen.getByRole('combobox', { name: /organization/i }), {
    target: { value: '2' },
  })

  expect(await region.findByText('Beedle Inc')).toBeInTheDocument()
  expect((region.getByLabelText(/filter by status/i) as HTMLSelectElement).value).toBe('')
  const last = orderListUrls(fetchMock).at(-1) as string
  expect(last).toContain('organization=2')
  expect(last).not.toContain('status=')
})

test('a member sees orders but no management controls', async () => {
  installBackend({
    orgs: [{ ...ORG_A, role: 'member' }],
    customers: [makeCustomer({ id: 11, organization: 1, name: 'Acme Ltd' })],
    orders: [makeOrder({ id: 101, organization: 1, customer: 11 })],
  })
  await renderApp()

  const region = await ordersRegion()
  expect(await region.findByText('Acme Ltd')).toBeInTheDocument()
  expect(region.queryByRole('button', { name: /add order/i })).not.toBeInTheDocument()
  expect(region.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument()
  expect(region.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument()
})
