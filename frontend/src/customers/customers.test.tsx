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

/** Render the app and open the Customers tab. */
async function renderApp() {
  render(<App />)
  fireEvent.click(await screen.findByRole('button', { name: 'Customers' }))
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

const ORG_A: Org = { id: 1, name: 'Alpha', role: 'owner', created_at: 'x', updated_at: 'x' }
const ORG_B: Org = { id: 2, name: 'Beta', role: 'admin', created_at: 'x', updated_at: 'x' }

function customer(
  partial: Partial<Customer> & Pick<Customer, 'id' | 'organization' | 'name'>,
): Customer {
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
  listStatus?: number
  createStatus?: number
  holdCustomers?: boolean
  deleteError?: { status: number; body: unknown }
}

function installBackend(opts: BackendOptions) {
  const orgs = [...opts.orgs]
  const customers = [...(opts.customers ?? [])]
  let nextId = customers.reduce((max, c) => Math.max(max, c.id), 100) + 1
  const listStatus = opts.listStatus ?? 200
  const createStatus = opts.createStatus ?? 201

  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET'
    const body = init?.body ? (JSON.parse(init.body as string) as Record<string, unknown>) : {}

    if (url.endsWith('/auth/refresh/')) return json(200, { access: 'access-token' })
    if (url.endsWith('/auth/me/')) return json(200, USER)
    if (url.includes('/dashboard/')) return json(200, EMPTY_DASHBOARD)
    if (url.includes('/orders/') && method === 'GET') return json(200, [])
    if (url.includes('/invoices/') && method === 'GET') return json(200, [])
    if (url.endsWith('/organizations/') && method === 'GET') {
      return json(
        200,
        [...orgs].sort((a, b) => a.name.localeCompare(b.name)),
      )
    }

    if (url.endsWith('/customers/') && method === 'GET') {
      if (opts.holdCustomers) return new Promise<never>(() => {})
      if (listStatus !== 200) return json(listStatus, { detail: 'boom' })
      return json(200, customers)
    }
    if (url.endsWith('/customers/') && method === 'POST') {
      if (createStatus !== 201) {
        return json(createStatus, { name: ['This field may not be blank.'] })
      }
      const created = customer({
        id: nextId++,
        organization: Number(body.organization),
        name: String(body.name ?? '').trim(),
        email: String(body.email ?? ''),
        phone: String(body.phone ?? ''),
        company: String(body.company ?? ''),
        address: String(body.address ?? ''),
      })
      customers.push(created)
      return json(201, created)
    }

    const match = url.match(/\/customers\/(\d+)\/$/)
    if (match && method === 'PATCH') {
      const target = customers.find((c) => c.id === Number(match[1]))
      if (!target) return json(404, { detail: 'not found' })
      Object.assign(target, {
        name: body.name ?? target.name,
        email: body.email ?? target.email,
        phone: body.phone ?? target.phone,
        company: body.company ?? target.company,
        address: body.address ?? target.address,
      })
      return json(200, target)
    }
    if (match && method === 'DELETE') {
      const index = customers.findIndex((c) => c.id === Number(match[1]))
      if (index === -1) return json(404, { detail: 'not found' })
      if (opts.deleteError) return json(opts.deleteError.status, opts.deleteError.body)
      customers.splice(index, 1)
      return json(204, undefined)
    }

    return json(404, { detail: 'not found' })
  })

  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
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

test('shows the current organization customers', async () => {
  installBackend({
    orgs: [ORG_A, ORG_B],
    customers: [
      customer({ id: 101, organization: 1, name: 'Acme Ltd', email: 'a@acme.test' }),
      customer({ id: 102, organization: 2, name: 'Beedle Inc' }),
    ],
  })
  await renderApp()

  expect(await screen.findByText('Acme Ltd')).toBeInTheDocument()
  expect(screen.queryByText('Beedle Inc')).not.toBeInTheDocument()
})

test('empty state when the organization has no customers', async () => {
  installBackend({ orgs: [ORG_A], customers: [] })
  await renderApp()

  expect(await screen.findByText(/no customers yet/i)).toBeInTheDocument()
})

test('loading state while customers are being fetched', async () => {
  installBackend({ orgs: [ORG_A], holdCustomers: true })
  await renderApp()

  expect(await screen.findByText(/loading customers/i)).toBeInTheDocument()
})

test('error state when the customer request fails', async () => {
  installBackend({ orgs: [ORG_A], listStatus: 500 })
  await renderApp()

  expect(await screen.findByRole('alert')).toHaveTextContent(/could not load customers/i)
})

test('creates a customer for the selected organization', async () => {
  const fetchMock = installBackend({ orgs: [ORG_A], customers: [] })
  await renderApp()

  fireEvent.click(await screen.findByRole('button', { name: /add customer/i }))
  fireEvent.change(screen.getByLabelText('Name'), { target: { value: '  New Client  ' } })
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'new@client.test' } })
  fireEvent.click(screen.getByRole('button', { name: /add customer/i }))

  expect(await screen.findByText('New Client')).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining('/customers/'),
    expect.objectContaining({
      method: 'POST',
      body: expect.stringContaining('"organization":1'),
    }),
  )
})

test('shows a validation error returned by the API on create', async () => {
  installBackend({ orgs: [ORG_A], customers: [], createStatus: 400 })
  await renderApp()

  fireEvent.click(await screen.findByRole('button', { name: /add customer/i }))
  fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'x' } })
  fireEvent.click(screen.getByRole('button', { name: /add customer/i }))

  expect(await screen.findByRole('alert')).toHaveTextContent(/may not be blank/i)
})

test('edits a customer', async () => {
  installBackend({
    orgs: [ORG_A],
    customers: [customer({ id: 101, organization: 1, name: 'Acme Ltd' })],
  })
  await renderApp()

  fireEvent.click(await screen.findByRole('button', { name: /edit/i }))
  fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Acme Renamed' } })
  fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

  expect(await screen.findByText('Acme Renamed')).toBeInTheDocument()
  expect(screen.queryByText('Acme Ltd')).not.toBeInTheDocument()
})

test('deletes a customer', async () => {
  installBackend({
    orgs: [ORG_A],
    customers: [
      customer({ id: 101, organization: 1, name: 'Acme Ltd' }),
      customer({ id: 102, organization: 1, name: 'Globex' }),
    ],
  })
  await renderApp()

  const acmeRow = (await screen.findByText('Acme Ltd')).closest('li') as HTMLElement
  fireEvent.click(within(acmeRow).getByRole('button', { name: /delete/i }))

  await waitFor(() => expect(screen.queryByText('Acme Ltd')).not.toBeInTheDocument())
  expect(screen.getByText('Globex')).toBeInTheDocument()
})

test('a delete rejected by the backend shows the reason it gave', async () => {
  installBackend({
    orgs: [ORG_A],
    customers: [customer({ id: 101, organization: 1, name: 'Acme Ltd' })],
    deleteError: {
      status: 403,
      body: { detail: 'You are not a member of this organization.' },
    },
  })
  await renderApp()

  const row = (await screen.findByText('Acme Ltd')).closest('li') as HTMLElement
  fireEvent.click(within(row).getByRole('button', { name: /delete/i }))

  expect(await screen.findByText(/not a member of this organization/i)).toBeInTheDocument()
  expect(screen.getByText('Acme Ltd')).toBeInTheDocument()
})

test('switching organization changes the visible customers', async () => {
  installBackend({
    orgs: [ORG_A, ORG_B],
    customers: [
      customer({ id: 101, organization: 1, name: 'Acme Ltd' }),
      customer({ id: 102, organization: 2, name: 'Beedle Inc' }),
    ],
  })
  await renderApp()

  expect(await screen.findByText('Acme Ltd')).toBeInTheDocument()

  fireEvent.change(screen.getByRole('combobox', { name: /organization/i }), {
    target: { value: '2' },
  })

  expect(await screen.findByText('Beedle Inc')).toBeInTheDocument()
  expect(screen.queryByText('Acme Ltd')).not.toBeInTheDocument()
})

test('an edit sends only the fields that actually changed', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [
      customer({
        id: 101,
        organization: 1,
        name: 'Acme Ltd',
        email: 'a@acme.test',
        phone: '555',
        company: 'Acme',
        address: 'HQ',
      }),
    ],
  })
  await renderApp()

  fireEvent.click(await screen.findByRole('button', { name: /edit/i }))
  fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Acme Renamed' } })
  fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

  await screen.findByText('Acme Renamed')
  const patchCall = fetchMock.mock.calls.find(
    ([, init]) => (init as RequestInit | undefined)?.method === 'PATCH',
  )
  expect(patchCall).toBeDefined()
  expect(JSON.parse((patchCall![1] as RequestInit).body as string)).toEqual({
    name: 'Acme Renamed',
  })
})

test('saving an edit with no changes does not send a PATCH', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [customer({ id: 101, organization: 1, name: 'Acme Ltd' })],
  })
  await renderApp()

  fireEvent.click(await screen.findByRole('button', { name: /edit/i }))
  fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

  await screen.findByRole('button', { name: /edit/i })
  expect(
    fetchMock.mock.calls.some(([, init]) => (init as RequestInit | undefined)?.method === 'PATCH'),
  ).toBe(false)
})

test('delete asks for confirmation and does nothing when cancelled', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(false)
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [customer({ id: 101, organization: 1, name: 'Acme Ltd' })],
  })
  await renderApp()

  const row = (await screen.findByText('Acme Ltd')).closest('li') as HTMLElement
  fireEvent.click(within(row).getByRole('button', { name: /delete/i }))

  expect(window.confirm).toHaveBeenCalled()
  expect(screen.getByText('Acme Ltd')).toBeInTheDocument()
  expect(
    fetchMock.mock.calls.some(([, init]) => (init as RequestInit | undefined)?.method === 'DELETE'),
  ).toBe(false)
})

test('the search box filters the list without another request', async () => {
  const fetchMock = installBackend({
    orgs: [ORG_A],
    customers: [
      customer({ id: 1, organization: 1, name: 'Acme Ltd', email: 'hi@acme.test' }),
      customer({ id: 2, organization: 1, name: 'Globex', company: 'Globex Corp' }),
    ],
  })
  await renderApp()
  await screen.findByText('Acme Ltd')
  const callsBefore = fetchMock.mock.calls.length

  fireEvent.change(screen.getByLabelText(/search customers/i), { target: { value: 'glob' } })

  expect(screen.getByText('Globex')).toBeInTheDocument()
  expect(screen.queryByText('Acme Ltd')).not.toBeInTheDocument()
  expect(fetchMock.mock.calls.length).toBe(callsBefore)

  fireEvent.change(screen.getByLabelText(/search customers/i), { target: { value: '' } })
  expect(screen.getByText('Acme Ltd')).toBeInTheDocument()
})

test('the search query resets when the organization changes', async () => {
  installBackend({
    orgs: [ORG_A, ORG_B],
    customers: [
      customer({ id: 1, organization: 1, name: 'Acme Ltd' }),
      customer({ id: 2, organization: 2, name: 'Beedle Inc' }),
    ],
  })
  await renderApp()
  await screen.findByText('Acme Ltd')
  fireEvent.change(screen.getByLabelText(/search customers/i), { target: { value: 'zzz' } })
  expect(screen.queryByText('Acme Ltd')).not.toBeInTheDocument()

  fireEvent.change(screen.getByRole('combobox', { name: /organization/i }), {
    target: { value: '2' },
  })

  expect(await screen.findByText('Beedle Inc')).toBeInTheDocument()
  expect((screen.getByLabelText(/search customers/i) as HTMLInputElement).value).toBe('')
})
