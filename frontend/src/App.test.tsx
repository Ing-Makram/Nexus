import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import App from './App'

const USER = {
  id: 1,
  email: 'user@example.com',
  first_name: 'Test',
  last_name: 'User',
  is_active: true,
  date_joined: '2026-01-01T00:00:00Z',
}

const LOGIN_RESPONSE = { access: 'access-token', refresh: 'refresh-token', user: USER }

function json(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => (body === undefined ? '' : JSON.stringify(body)),
  }
}

/** Fetch stub: auth endpoints behave, the user has no organizations. */
function stubFetch({ loginStatus = 200, registerStatus = 201, logoutStatus = 205 } = {}) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET'
    if (url.endsWith('/auth/login/')) {
      return loginStatus === 200 ? json(200, LOGIN_RESPONSE) : json(loginStatus, { detail: 'no' })
    }
    if (url.endsWith('/auth/register/')) {
      return registerStatus === 201
        ? json(201, LOGIN_RESPONSE)
        : json(registerStatus, { email: ['A user with this email already exists.'] })
    }
    if (url.endsWith('/auth/refresh/')) return json(200, { access: 'access-token' })
    if (url.endsWith('/auth/me/')) return json(200, USER)
    if (url.endsWith('/auth/logout/')) {
      return logoutStatus === 205 ? json(205, undefined) : json(logoutStatus, { detail: 'nope' })
    }
    if (url.endsWith('/organizations/') && method === 'GET') return json(200, [])
    return json(404, { detail: 'not found' })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

async function signIn(password = 'secret') {
  fireEvent.change(await screen.findByLabelText(/email/i), {
    target: { value: 'user@example.com' },
  })
  fireEvent.change(screen.getByLabelText(/password/i), { target: { value: password } })
  fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
}

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

test('shows the login page when there is no stored session', async () => {
  stubFetch()
  render(<App />)

  expect(await screen.findByRole('heading', { name: /sign in to nexus/i })).toBeInTheDocument()
})

test('after signing in, the user is prompted to create their first organization', async () => {
  stubFetch()
  render(<App />)
  await signIn()

  expect(
    await screen.findByRole('heading', { name: /create your first organization/i }),
  ).toBeInTheDocument()
  expect(screen.getByText(/signed in as/i)).toBeInTheDocument()
  expect(localStorage.getItem('nexus.auth.refresh')).toBe('refresh-token')
})

test('shows an error when credentials are rejected', async () => {
  stubFetch({ loginStatus: 401 })
  render(<App />)
  await signIn('wrong')

  expect(await screen.findByRole('alert')).toHaveTextContent(/invalid email or password/i)
})

test('a visitor can switch to the sign-up form and create an account', async () => {
  stubFetch()
  render(<App />)

  fireEvent.click(await screen.findByRole('button', { name: /^sign up$/i }))

  expect(
    await screen.findByRole('heading', { name: /create your nexus account/i }),
  ).toBeInTheDocument()

  fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'new@example.com' } })
  fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'sp1ral-galaxy-42' } })
  fireEvent.click(screen.getByRole('button', { name: /create account/i }))

  expect(
    await screen.findByRole('heading', { name: /create your first organization/i }),
  ).toBeInTheDocument()
  expect(localStorage.getItem('nexus.auth.refresh')).toBe('refresh-token')
})

test('sign-up surfaces a server validation error', async () => {
  stubFetch({ registerStatus: 400 })
  render(<App />)

  fireEvent.click(await screen.findByRole('button', { name: /^sign up$/i }))
  fireEvent.change(await screen.findByLabelText(/email/i), {
    target: { value: 'taken@example.com' },
  })
  fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'sp1ral-galaxy-42' } })
  fireEvent.click(screen.getByRole('button', { name: /create account/i }))

  expect(await screen.findByRole('alert')).toHaveTextContent(/already exists/i)
})

test('signing out returns to the login page and clears the stored token', async () => {
  stubFetch()
  render(<App />)
  await signIn()

  fireEvent.click(await screen.findByRole('button', { name: /sign out/i }))

  expect(await screen.findByRole('heading', { name: /sign in to nexus/i })).toBeInTheDocument()
  expect(localStorage.getItem('nexus.auth.refresh')).toBeNull()
})

test('signing out calls the backend blacklist endpoint with the refresh token', async () => {
  const fetchMock = stubFetch()
  render(<App />)
  await signIn()

  fireEvent.click(await screen.findByRole('button', { name: /sign out/i }))
  await screen.findByRole('heading', { name: /sign in to nexus/i })

  const logoutCall = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/auth/logout/'))
  expect(logoutCall).toBeDefined()
  const init = logoutCall![1] as RequestInit
  expect(init.method).toBe('POST')
  expect(JSON.parse(init.body as string)).toEqual({ refresh: 'refresh-token' })
  expect(String(init.body)).not.toContain('access-token')
})

test('signing out still clears the local session when the backend logout fails', async () => {
  stubFetch({ logoutStatus: 503 })
  render(<App />)
  await signIn()

  fireEvent.click(await screen.findByRole('button', { name: /sign out/i }))

  expect(await screen.findByRole('heading', { name: /sign in to nexus/i })).toBeInTheDocument()
  expect(localStorage.getItem('nexus.auth.refresh')).toBeNull()
})

test('signing out makes no logout request when there is no stored refresh token', async () => {
  const fetchMock = stubFetch()
  render(<App />)
  await signIn()
  await screen.findByRole('button', { name: /sign out/i })

  // Simulate the refresh token already being gone from storage.
  localStorage.removeItem('nexus.auth.refresh')
  fireEvent.click(screen.getByRole('button', { name: /sign out/i }))

  await screen.findByRole('heading', { name: /sign in to nexus/i })
  expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/auth/logout/'))).toBe(false)
})
