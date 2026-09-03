import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import App from '../App'

const USER = {
  id: 1,
  email: 'user@example.com',
  first_name: 'Test',
  last_name: 'User',
  is_active: true,
  date_joined: '2026-01-01T00:00:00Z',
}

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

interface Org {
  id: number
  name: string
  role: string
  created_at: string
  updated_at: string
}

interface Member {
  user: {
    id: number
    email: string
    first_name: string
    last_name: string
    is_active: boolean
    date_joined: string
  }
  role: string
  created_at: string
  updated_at: string
}

function member(id: number, email: string, role: string): Member {
  return {
    user: { id, email, first_name: '', last_name: '', is_active: true, date_joined: 'x' },
    role,
    created_at: 'x',
    updated_at: 'x',
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
  members?: Member[]
}

/** Stateful backend stub for an already-authenticated user. */
function installBackend(initial: Org[], opts: BackendOptions = {}) {
  const orgs = [...initial]
  const members = [...(opts.members ?? [])]
  let nextId = orgs.reduce((max, o) => Math.max(max, o.id), 0) + 1

  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET'
    const body = init?.body ? (JSON.parse(init.body as string) as Record<string, unknown>) : {}
    const path = url.split('?')[0]

    if (path.endsWith('/auth/refresh/')) return json(200, { access: 'access-token' })
    if (path.endsWith('/auth/me/')) return json(200, USER)
    if (path.includes('/dashboard/')) return json(200, EMPTY_DASHBOARD)
    if (path.includes('/customers/') && method === 'GET') return json(200, [])
    if (path.includes('/orders/') && method === 'GET') return json(200, [])
    if (path.includes('/invoices/') && method === 'GET') return json(200, [])

    const memberItem = path.match(/\/organizations\/\d+\/members\/(\d+)\/$/)
    if (memberItem) {
      const userId = Number(memberItem[1])
      const index = members.findIndex((m) => m.user.id === userId)
      if (method === 'PATCH') {
        if (index === -1) return json(404, { detail: 'not found' })
        members[index] = { ...members[index], role: String(body.role) }
        return json(200, members[index])
      }
      if (method === 'DELETE') {
        if (index === -1) return json(404, { detail: 'not found' })
        members.splice(index, 1)
        return json(204, undefined)
      }
    }
    if (path.match(/\/organizations\/\d+\/members\/$/)) {
      if (method === 'GET') return json(200, members)
      if (method === 'POST') {
        const email = String(body.email ?? '')
        if (members.some((m) => m.user.email === email)) {
          return json(400, { email: ['This user is already a member.'] })
        }
        const created = member(nextId++, email, String(body.role))
        members.push(created)
        return json(201, created)
      }
    }

    const orgItem = path.match(/\/organizations\/(\d+)\/$/)
    if (orgItem) {
      const id = Number(orgItem[1])
      const index = orgs.findIndex((o) => o.id === id)
      if (method === 'PATCH') {
        if (index === -1) return json(404, { detail: 'not found' })
        orgs[index] = { ...orgs[index], name: String(body.name ?? '').trim() }
        return json(200, orgs[index])
      }
      if (method === 'DELETE') {
        if (index === -1) return json(404, { detail: 'not found' })
        orgs.splice(index, 1)
        return json(204, undefined)
      }
    }

    if (path.endsWith('/organizations/') && method === 'GET') {
      return json(
        200,
        [...orgs].sort((a, b) => a.name.localeCompare(b.name)),
      )
    }
    if (path.endsWith('/organizations/') && method === 'POST') {
      const name = String(body.name ?? '').trim()
      if (name.length < 2) return json(400, { name: ['Organization name is too short.'] })
      const org: Org = { id: nextId++, name, role: 'owner', created_at: 'now', updated_at: 'now' }
      orgs.push(org)
      return json(201, org)
    }
    return json(404, { detail: 'not found' })
  })

  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

async function openSettings() {
  render(<App />)
  fireEvent.click(await screen.findByRole('button', { name: 'Settings' }))
}

const ALPHA: Org = { id: 1, name: 'Alpha', role: 'owner', created_at: 'x', updated_at: 'x' }
const BETA: Org = { id: 2, name: 'Beta', role: 'member', created_at: 'x', updated_at: 'x' }

beforeEach(() => {
  localStorage.clear()
  localStorage.setItem('nexus.auth.refresh', 'stored-refresh')
  vi.spyOn(window, 'confirm').mockReturnValue(true)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test('a user with no organizations can create their first one and it becomes current', async () => {
  installBackend([])
  render(<App />)

  expect(
    await screen.findByRole('heading', { name: /create your first organization/i }),
  ).toBeInTheDocument()

  fireEvent.change(screen.getByLabelText(/organization name/i), { target: { value: 'Acme Inc' } })
  fireEvent.click(screen.getByRole('button', { name: /create organization/i }))

  expect(await screen.findByRole('heading', { name: 'Acme Inc' })).toBeInTheDocument()
  expect(screen.getByTitle(/your role/i)).toHaveTextContent(/owner/i)
  expect(localStorage.getItem('nexus.org.current')).toBe('1')
})

test('the switcher changes the current organization and persists the choice', async () => {
  installBackend([ALPHA, BETA])
  render(<App />)

  expect(await screen.findByRole('heading', { name: 'Alpha' })).toBeInTheDocument()

  fireEvent.change(screen.getByRole('combobox', { name: /organization/i }), {
    target: { value: '2' },
  })

  expect(await screen.findByRole('heading', { name: 'Beta' })).toBeInTheDocument()
  expect(localStorage.getItem('nexus.org.current')).toBe('2')
})

test('settings lists every organization the user belongs to', async () => {
  installBackend([ALPHA, BETA])
  await openSettings()

  const region = within(await screen.findByRole('region', { name: /your organizations/i }))
  const alpha = region.getByText('Alpha').closest('li') as HTMLElement
  expect(within(alpha).getByText('owner')).toBeInTheDocument()
  const beta = region.getByText('Beta').closest('li') as HTMLElement
  expect(within(beta).getByText('member')).toBeInTheDocument()
})

test('shows a validation error when the organization name is rejected', async () => {
  installBackend([])
  render(<App />)

  await screen.findByRole('heading', { name: /create your first organization/i })
  fireEvent.change(screen.getByLabelText(/organization name/i), { target: { value: 'A' } })
  fireEvent.click(screen.getByRole('button', { name: /create organization/i }))

  expect(await screen.findByRole('alert')).toHaveTextContent(/valid organization name/i)
})

test('an owner can rename the organization', async () => {
  const fetchMock = installBackend([ALPHA], { members: [member(1, 'user@example.com', 'owner')] })
  await openSettings()

  const details = within(await screen.findByRole('region', { name: /organization details/i }))
  fireEvent.change(details.getByLabelText(/organization name/i), {
    target: { value: 'Alpha Renamed' },
  })
  fireEvent.click(details.getByRole('button', { name: /save name/i }))

  expect(
    await screen.findByRole('heading', { level: 1, name: 'Alpha Renamed' }),
  ).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining('/organizations/1/'),
    expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ name: 'Alpha Renamed' }) }),
  )
})

test('an owner can add and remove a member', async () => {
  const fetchMock = installBackend([ALPHA], { members: [member(1, 'user@example.com', 'owner')] })
  await openSettings()

  const members = within(await screen.findByRole('region', { name: 'Members' }))
  fireEvent.change(await members.findByLabelText(/add member by email/i), {
    target: { value: 'new@example.com' },
  })
  fireEvent.click(members.getByRole('button', { name: /add member/i }))

  expect(await members.findByText('new@example.com')).toBeInTheDocument()

  const row = (await members.findByText('new@example.com')).closest('li') as HTMLElement
  fireEvent.click(within(row).getByRole('button', { name: /remove/i }))

  await screen.findByRole('button', { name: 'Settings' })
  expect(members.queryByText('new@example.com')).not.toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining('/organizations/1/members/'),
    expect.objectContaining({ method: 'POST' }),
  )
})

test('a member sees the member list but no management controls', async () => {
  installBackend([BETA], {
    members: [member(1, 'user@example.com', 'member'), member(2, 'owner@example.com', 'owner')],
  })
  localStorage.setItem('nexus.org.current', '2')
  await openSettings()

  const members = within(await screen.findByRole('region', { name: 'Members' }))
  expect(await members.findByText('owner@example.com')).toBeInTheDocument()
  expect(members.queryByRole('button', { name: /add member/i })).not.toBeInTheDocument()
  expect(members.queryByRole('button', { name: /remove/i })).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /delete organization/i })).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /save name/i })).not.toBeInTheDocument()
})

test('an owner can delete the organization', async () => {
  const fetchMock = installBackend([ALPHA, BETA], {
    members: [member(1, 'user@example.com', 'owner')],
  })
  await openSettings()

  fireEvent.click(await screen.findByRole('button', { name: /delete organization/i }))

  // Falls back to the other organization.
  expect(await screen.findByRole('heading', { level: 1, name: 'Beta' })).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining('/organizations/1/'),
    expect.objectContaining({ method: 'DELETE' }),
  )
})
