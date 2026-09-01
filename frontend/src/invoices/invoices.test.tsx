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

/** Render the app and open the Invoices tab. */
async function openInvoices() {
  render(<App />)
  fireEvent.click(await screen.findByRole('button', { name: 'Invoices' }))
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
}

interface Order {
  id: number
  organization: number
  customer: number
  status: string
  total_amount?: string
}

interface Invoice {
  id: number
  organization: number
  customer: number
  order: number | null
  invoice_number: string
  status: string
  issue_date: string
  due_date: string | null
  total_amount: string
  notes: string
  created_by: string | null
  created_at: string
  updated_at: string
}

const ORG_A: Org = { id: 1, name: 'Alpha', role: 'owner', created_at: 'x', updated_at: 'x' }
const ORG_B: Org = { id: 2, name: 'Beta', role: 'owner', created_at: 'x', updated_at: 'x' }

function makeInvoice(
  p: Pick<Invoice, 'id' | 'organization' | 'customer'> & Partial<Invoice>,
): Invoice {
  return {
    order: null,
    invoice_number: `INV-000${p.id}`,
    status: 'draft',
    issue_date: '2026-01-01',
    due_date: null,
    total_amount: '100.00',
    notes: '',
    created_by: 'user@example.com',
    created_at: `2026-01-0${p.id}T00:00:00Z`,
    updated_at: 'x',
    ...p,
  }
}

function json(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => (body === undefined ? '' : JSON.stringify(body)),
  }
}

interface BackendOptions {
  orgs: Org[]
  customers?: Customer[]
  orders?: Order[]
  invoices?: Invoice[]
  listStatus?: number
  createStatus?: number
  holdInvoices?: boolean
  /** Never resolve the invoices GET for this one organization id. */
  holdInvoicesForOrg?: number
}

function pathOf(url: string) {
  return url.split('?')[0]
}

function queryOf(url: string) {
  return new URLSearchParams(url.split('?')[1] ?? '')
}

function installBackend(opts: BackendOptions) {
  const orgs = [...opts.orgs]
  const customers = [...(opts.customers ?? [])]
  const orders = [...(opts.orders ?? [])]
  const invoices = [...(opts.invoices ?? [])]
  let nextId = invoices.reduce((max, i) => Math.max(max, i.id), 700) + 1
  const listStatus = opts.listStatus ?? 200
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
    if (path.endsWith('/orders/') && method === 'GET') {
      const orgId = query.get('organization')
      return json(200, orgId ? orders.filter((o) => String(o.organization) === orgId) : orders)
    }

    if (path.endsWith('/invoices/') && method === 'GET') {
      if (opts.holdInvoices) return new Promise<never>(() => {})
      const orgId = query.get('organization')
      if (opts.holdInvoicesForOrg != null && orgId === String(opts.holdInvoicesForOrg)) {
        return new Promise<never>(() => {})
      }
      if (listStatus !== 200) return json(listStatus, { detail: 'boom' })
      const statusFilter = query.get('status')
      let scoped = orgId ? invoices.filter((i) => String(i.organization) === orgId) : invoices
      if (statusFilter) scoped = scoped.filter((i) => i.status === statusFilter)
      return json(200, scoped)
    }
    if (path.endsWith('/invoices/') && method === 'POST') {
      if (createStatus !== 201) {
        return json(createStatus, { total_amount: ['A valid number is required.'] })
      }
      const created = makeInvoice({
        id: nextId,
        organization: Number(body.organization),
        customer: Number(body.customer),
        order: body.order == null ? null : Number(body.order),
        invoice_number: String(body.invoice_number ?? '').trim() || `INV-000${nextId}`,
        status: String(body.status ?? 'draft'),
        issue_date: String(body.issue_date ?? '2026-01-01'),
        due_date: (body.due_date as string | null) ?? null,
        total_amount: String(body.total_amount ?? '0'),
        notes: String(body.notes ?? ''),
      })
      nextId += 1
      invoices.unshift(created)
      return json(201, created)
    }

    const match = path.match(/\/invoices\/(\d+)\/$/)
    if (match && method === 'PATCH') {
      const target = invoices.find((i) => i.id === Number(match[1]))
      if (!target) return json(404, { detail: 'not found' })
      Object.assign(target, {
        customer: body.customer ?? target.customer,
        order: body.order === undefined ? target.order : body.order,
        status: body.status ?? target.status,
        total_amount: body.total_amount ?? target.total_amount,
        notes: body.notes ?? target.notes,
      })
      return json(200, target)
    }
    if (match && method === 'DELETE') {
      const index = invoices.findIndex((i) => i.id === Number(match[1]))
      if (index === -1) return json(404, { detail: 'not found' })
      invoices.splice(index, 1)
      return json(204, undefined)
    }

    return json(404, { detail: 'not found' })
  })

  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

async function region() {
  return within(await screen.findByRole('region', { name: 'Invoices' }))
}

/** The invoice rows, excluding the status-filter select and the add form. */
async function invoiceList() {
  const r = await region()
  return within(await r.findByRole('list'))
}

function invoiceListUrls(fetchMock: ReturnType<typeof vi.fn>) {
  return fetchMock.mock.calls
    .filter(
      ([url, init]) =>
        typeof url === 'string' &&
        pathOf(url).endsWith('/invoices/') &&
        ((init as RequestInit | undefined)?.method ?? 'GET') === 'GET',
    )
    .map(([url]) => url as string)
}

function patchBodies(fetchMock: ReturnType<typeof vi.fn>) {
  return fetchMock.mock.calls
    .filter(([, init]) => (init as RequestInit | undefined)?.method === 'PATCH')
    .map(([, init]) => JSON.parse((init as RequestInit).body as string))
}

function methodsUsed(fetchMock: ReturnType<typeof vi.fn>) {
  return fetchMock.mock.calls.map(([, init]) => (init as RequestInit | undefined)?.method ?? 'GET')
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

test('shows the current organization invoices and requests them scoped by organization', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A, ORG_B],
    customers: [
      { id: 11, organization: 1, name: 'Acme Ltd' },
      { id: 21, organization: 2, name: 'Beedle Inc' },
    ],
    invoices: [
      makeInvoice({ id: 1, organization: 1, customer: 11, status: 'sent', total_amount: '250.00' }),
      makeInvoice({ id: 2, organization: 2, customer: 21 }),
    ],
  })
  await openInvoices()

  const r = await region()
  expect(await r.findByText('INV-0001')).toBeInTheDocument()
  expect(r.getByText(/Acme Ltd/)).toBeInTheDocument()
  expect(r.getByText(/250\.00/)).toBeInTheDocument()
  expect(r.queryByText('INV-0002')).not.toBeInTheDocument()

  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining('/invoices/?organization=1'),
    expect.anything(),
  )
})

test('switching organization reloads invoices for the newly selected organization', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A, ORG_B],
    customers: [
      { id: 11, organization: 1, name: 'Acme Ltd' },
      { id: 21, organization: 2, name: 'Beedle Inc' },
    ],
    invoices: [
      makeInvoice({ id: 1, organization: 1, customer: 11 }),
      makeInvoice({ id: 2, organization: 2, customer: 21 }),
    ],
  })
  await openInvoices()

  const r = await region()
  await r.findByText('INV-0001')

  fireEvent.change(screen.getByRole('combobox', { name: /organization/i }), {
    target: { value: '2' },
  })

  expect(await r.findByText('INV-0002')).toBeInTheDocument()
  expect(r.queryByText('INV-0001')).not.toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining('/invoices/?organization=2'),
    expect.anything(),
  )
})

test('switching organization never shows the previous organization while the new list is loading', async () => {
  installBackend({
    orgs: [ORG_A, ORG_B],
    customers: [
      { id: 11, organization: 1, name: 'Acme Ltd' },
      { id: 21, organization: 2, name: 'Beedle Inc' },
    ],
    invoices: [makeInvoice({ id: 1, organization: 1, customer: 11, invoice_number: 'INV-0001' })],
    // Org 2's request hangs forever, so if org 1's invoice were still showing
    // when we assert, that would prove it leaked across the switch.
    holdInvoicesForOrg: 2,
  })
  await openInvoices()

  const r = await region()
  expect(await r.findByText('INV-0001')).toBeInTheDocument()

  fireEvent.change(screen.getByRole('combobox', { name: /organization/i }), {
    target: { value: '2' },
  })

  // Org 1's invoice must disappear immediately - not linger until org 2 loads.
  await waitFor(() => expect(r.queryByText('INV-0001')).not.toBeInTheDocument())
  expect(await r.findByText(/loading invoices/i)).toBeInTheDocument()
})

test('empty state', async () => {
  installBackend({ orgs: [ORG_A], invoices: [] })
  await openInvoices()
  expect(await (await region()).findByText(/no invoices yet/i)).toBeInTheDocument()
})

test('loading state', async () => {
  installBackend({ orgs: [ORG_A], holdInvoices: true })
  await openInvoices()
  expect(await (await region()).findByText(/loading invoices/i)).toBeInTheDocument()
})

test('error state', async () => {
  installBackend({ orgs: [ORG_A], listStatus: 500 })
  await openInvoices()
  expect(await (await region()).findByText(/could not load invoices/i)).toBeInTheDocument()
})

test('the customer select is scoped to the current organization', async () => {
  installBackend({
    orgs: [ORG_A],
    customers: [
      { id: 11, organization: 1, name: 'Acme Ltd' },
      { id: 12, organization: 1, name: 'Globex' },
    ],
    orders: [{ id: 5, organization: 1, customer: 11, status: 'draft', total_amount: '250.00' }],
    invoices: [],
  })
  await openInvoices()

  const r = await region()
  fireEvent.click(await r.findByRole('button', { name: /add invoice/i }))

  const customerSelect = r.getByLabelText('Customer')
  const options = within(customerSelect)
    .getAllByRole('option')
    .map((o) => o.textContent)
  expect(options).toEqual(['Select a customer…', 'Acme Ltd', 'Globex'])

  const orderSelect = r.getByLabelText('Order')
  const orderOptions = within(orderSelect)
    .getAllByRole('option')
    .map((o) => o.textContent)
  expect(orderOptions[0]).toBe('No order')
  expect(orderOptions[1]).toContain('#5')
  expect(orderOptions[1]).toContain('Acme Ltd')
})

test('the invoice order dropdown shows every current-org order regardless of status', async () => {
  installBackend({
    orgs: [ORG_A],
    customers: [{ id: 11, organization: 1, name: 'Acme Ltd' }],
    orders: [
      { id: 1, organization: 1, customer: 11, status: 'draft', total_amount: '10.00' },
      { id: 2, organization: 1, customer: 11, status: 'completed', total_amount: '20.00' },
      { id: 3, organization: 2, customer: 99, status: 'draft', total_amount: '30.00' },
    ],
    invoices: [],
  })
  await openInvoices()

  const r = await region()
  fireEvent.click(await r.findByRole('button', { name: /add invoice/i }))

  const orderOptions = within(r.getByLabelText('Order'))
    .getAllByRole('option')
    .map((o) => o.textContent)
  // Both the draft and the completed order appear; the other org's order does not.
  expect(orderOptions.some((o) => o?.includes('#1'))).toBe(true)
  expect(orderOptions.some((o) => o?.includes('#2'))).toBe(true)
  expect(orderOptions.some((o) => o?.includes('#3'))).toBe(false)
})

test('creates an invoice and shows the backend-assigned number', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [{ id: 11, organization: 1, name: 'Acme Ltd' }],
    invoices: [],
  })
  await openInvoices()

  const r = await region()
  fireEvent.click(await r.findByRole('button', { name: /add invoice/i }))
  fireEvent.change(r.getByLabelText('Customer'), { target: { value: '11' } })
  fireEvent.change(r.getByLabelText('Issue date'), { target: { value: '2026-03-01' } })
  fireEvent.change(r.getByLabelText('Total amount'), { target: { value: '480.00' } })
  fireEvent.click(r.getByRole('button', { name: /add invoice/i }))

  expect(await r.findByText('INV-000701')).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining('/invoices/'),
    expect.objectContaining({
      method: 'POST',
      body: expect.stringContaining('"organization":1'),
    }),
  )
})

test('surfaces an API validation error on create', async () => {
  installBackend({
    orgs: [ORG_A],
    customers: [{ id: 11, organization: 1, name: 'Acme Ltd' }],
    invoices: [],
    createStatus: 400,
  })
  await openInvoices()

  const r = await region()
  fireEvent.click(await r.findByRole('button', { name: /add invoice/i }))
  fireEvent.change(r.getByLabelText('Customer'), { target: { value: '11' } })
  fireEvent.change(r.getByLabelText('Issue date'), { target: { value: '2026-03-01' } })
  fireEvent.change(r.getByLabelText('Total amount'), { target: { value: 'abc' } })
  fireEvent.click(r.getByRole('button', { name: /add invoice/i }))

  expect(await r.findByRole('alert')).toHaveTextContent(/valid number is required/i)
})

test('edits an invoice', async () => {
  installBackend({
    orgs: [ORG_A],
    customers: [{ id: 11, organization: 1, name: 'Acme Ltd' }],
    invoices: [makeInvoice({ id: 1, organization: 1, customer: 11, status: 'draft' })],
  })
  await openInvoices()

  const r = await region()
  fireEvent.click(await r.findByRole('button', { name: /edit/i }))
  fireEvent.change(r.getByLabelText('Status'), { target: { value: 'paid' } })
  fireEvent.click(r.getByRole('button', { name: /^save$/i }))

  const list = await invoiceList()
  await waitFor(() => expect(list.getByText(/paid/i)).toBeInTheDocument())
})

test('an edit sends only the fields that actually changed', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [{ id: 11, organization: 1, name: 'Acme Ltd' }],
    invoices: [
      makeInvoice({ id: 1, organization: 1, customer: 11, status: 'draft', notes: 'keep me' }),
    ],
  })
  await openInvoices()

  const r = await region()
  fireEvent.click(await r.findByRole('button', { name: /edit/i }))
  fireEvent.change(r.getByLabelText('Status'), { target: { value: 'sent' } })
  fireEvent.click(r.getByRole('button', { name: /^save$/i }))

  await waitFor(() => expect(patchBodies(fetchMock)).toHaveLength(1))
  expect(patchBodies(fetchMock)[0]).toEqual({ status: 'sent' })
})

test('saving an edit with no changes does not send a PATCH', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [{ id: 11, organization: 1, name: 'Acme Ltd' }],
    invoices: [makeInvoice({ id: 1, organization: 1, customer: 11 })],
  })
  await openInvoices()

  const r = await region()
  fireEvent.click(await r.findByRole('button', { name: /edit/i }))
  fireEvent.click(r.getByRole('button', { name: /^save$/i }))

  await r.findByRole('button', { name: /edit/i })
  expect(methodsUsed(fetchMock)).not.toContain('PATCH')
})

test('deletes an invoice', async () => {
  installBackend({
    orgs: [ORG_A],
    customers: [{ id: 11, organization: 1, name: 'Acme Ltd' }],
    invoices: [
      makeInvoice({ id: 1, organization: 1, customer: 11, invoice_number: 'INV-A' }),
      makeInvoice({ id: 2, organization: 1, customer: 11, invoice_number: 'INV-B' }),
    ],
  })
  await openInvoices()

  const r = await region()
  const row = (await r.findByText('INV-A')).closest('li') as HTMLElement
  fireEvent.click(within(row).getByRole('button', { name: /delete/i }))

  await waitFor(() => expect(r.queryByText('INV-A')).not.toBeInTheDocument())
  expect(r.getByText('INV-B')).toBeInTheDocument()
})

test('delete asks for confirmation and does nothing when cancelled', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(false)
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [{ id: 11, organization: 1, name: 'Acme Ltd' }],
    invoices: [makeInvoice({ id: 1, organization: 1, customer: 11, invoice_number: 'INV-A' })],
  })
  await openInvoices()

  const r = await region()
  const row = (await r.findByText('INV-A')).closest('li') as HTMLElement
  fireEvent.click(within(row).getByRole('button', { name: /delete/i }))

  expect(window.confirm).toHaveBeenCalled()
  expect(r.getByText('INV-A')).toBeInTheDocument()
  expect(methodsUsed(fetchMock)).not.toContain('DELETE')
})

test('the status filter requests the backend and clearing it removes the parameter', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [{ id: 11, organization: 1, name: 'Acme Ltd' }],
    invoices: [
      makeInvoice({
        id: 1,
        organization: 1,
        customer: 11,
        status: 'draft',
        invoice_number: 'INV-D',
      }),
      makeInvoice({
        id: 2,
        organization: 1,
        customer: 11,
        status: 'paid',
        invoice_number: 'INV-P',
      }),
    ],
  })
  await openInvoices()

  const r = await region()
  await (await invoiceList()).findByText('INV-D')

  expect(
    invoiceListUrls(fetchMock).some(
      (url) => url.includes('organization=1') && !url.includes('status='),
    ),
  ).toBe(true)

  const filter = r.getByLabelText(/filter by status/i)
  fireEvent.change(filter, { target: { value: 'paid' } })

  await waitFor(() =>
    expect(
      invoiceListUrls(fetchMock).some((url) => url.includes('organization=1&status=paid')),
    ).toBe(true),
  )
  expect(await (await invoiceList()).findByText('INV-P')).toBeInTheDocument()
  expect((await invoiceList()).queryByText('INV-D')).not.toBeInTheDocument()

  fireEvent.change(filter, { target: { value: 'draft' } })
  await waitFor(() =>
    expect(
      invoiceListUrls(fetchMock).some((url) => url.includes('organization=1&status=draft')),
    ).toBe(true),
  )

  const beforeClear = invoiceListUrls(fetchMock).length
  fireEvent.change(filter, { target: { value: '' } })
  await waitFor(() => expect(invoiceListUrls(fetchMock).length).toBeGreaterThan(beforeClear))
  const last = invoiceListUrls(fetchMock).at(-1) as string
  expect(last).toContain('organization=1')
  expect(last).not.toContain('status=')
})

test('switching organization resets the status filter', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A, ORG_B],
    customers: [
      { id: 11, organization: 1, name: 'Acme Ltd' },
      { id: 21, organization: 2, name: 'Beedle Inc' },
    ],
    invoices: [
      makeInvoice({
        id: 1,
        organization: 1,
        customer: 11,
        status: 'paid',
        invoice_number: 'INV-1',
      }),
      makeInvoice({
        id: 2,
        organization: 2,
        customer: 21,
        status: 'draft',
        invoice_number: 'INV-2',
      }),
    ],
  })
  await openInvoices()

  const r = await region()
  await r.findByText('INV-1')

  fireEvent.change(r.getByLabelText(/filter by status/i), { target: { value: 'paid' } })
  await waitFor(() =>
    expect(invoiceListUrls(fetchMock).some((url) => url.includes('status=paid'))).toBe(true),
  )

  fireEvent.change(screen.getByRole('combobox', { name: /organization/i }), {
    target: { value: '2' },
  })

  expect(await r.findByText('INV-2')).toBeInTheDocument()
  expect((r.getByLabelText(/filter by status/i) as HTMLSelectElement).value).toBe('')
  const last = invoiceListUrls(fetchMock).at(-1) as string
  expect(last).toContain('organization=2')
  expect(last).not.toContain('status=')
})

test('a member sees invoices but no management controls', async () => {
  installBackend({
    orgs: [{ ...ORG_A, role: 'member' }],
    customers: [{ id: 11, organization: 1, name: 'Acme Ltd' }],
    invoices: [makeInvoice({ id: 1, organization: 1, customer: 11, invoice_number: 'INV-X' })],
  })
  await openInvoices()

  const r = await region()
  expect(await r.findByText('INV-X')).toBeInTheDocument()
  expect(r.queryByRole('button', { name: /add invoice/i })).not.toBeInTheDocument()
  expect(r.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument()
  expect(r.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument()
})

test('the search box filters invoices client-side by number without another request', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [{ id: 11, organization: 1, name: 'Acme Ltd' }],
    invoices: [
      makeInvoice({ id: 1, organization: 1, customer: 11, invoice_number: 'INV-AAA' }),
      makeInvoice({ id: 2, organization: 1, customer: 11, invoice_number: 'INV-BBB' }),
    ],
  })
  await openInvoices()

  const r = await region()
  await r.findByText('INV-AAA')
  const callsBefore = fetchMock.mock.calls.length

  fireEvent.change(r.getByLabelText(/search invoices/i), { target: { value: 'bbb' } })

  expect(r.getByText('INV-BBB')).toBeInTheDocument()
  expect(r.queryByText('INV-AAA')).not.toBeInTheDocument()
  expect(fetchMock.mock.calls.length).toBe(callsBefore)
})
