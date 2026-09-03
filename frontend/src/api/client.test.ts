import { afterEach, expect, test, vi } from 'vitest'
import { ApiError, apiRequest, firstApiError } from './client'

afterEach(() => {
  vi.unstubAllGlobals()
})

function response(status: number, text: string) {
  return { ok: status >= 200 && status < 300, status, text: async () => text }
}

test('a non-JSON error body still rejects with an ApiError carrying the status', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => response(502, '<html><body>502 Bad Gateway</body></html>')),
  )

  await expect(apiRequest('/anything')).rejects.toBeInstanceOf(ApiError)
  await expect(apiRequest('/anything')).rejects.toMatchObject({ status: 502 })
})

test('a JSON error body is parsed and exposed on the ApiError', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => response(400, JSON.stringify({ email: ['already taken'] }))),
  )

  try {
    await apiRequest('/register')
    throw new Error('expected a rejection')
  } catch (error) {
    expect(error).toBeInstanceOf(ApiError)
    expect(firstApiError((error as ApiError).data)).toBe('already taken')
  }
})

test('an empty successful body resolves to null', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => response(205, '')),
  )

  await expect(apiRequest('/logout')).resolves.toBeNull()
})
