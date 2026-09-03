const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1').replace(/\/$/, '')

/** Error thrown for any non-2xx API response. */
export class ApiError extends Error {
  readonly status: number
  readonly data: unknown

  constructor(status: number, data: unknown) {
    super(`API request failed with status ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  accessToken?: string | null
  signal?: AbortSignal
}

/** Thin JSON fetch wrapper. Callers own token lifecycle (see AuthProvider). */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, accessToken, signal } = options

  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  })

  const raw = await response.text()
  let data: unknown = null
  if (raw) {
    try {
      data = JSON.parse(raw)
    } catch {
      // A non-JSON body (e.g. a proxy/server 500 HTML page). Keep the raw text
      // so the status is still reported as an ApiError rather than a parse throw.
      data = raw
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, data)
  }
  return data as T
}

/**
 * Pull the first human-readable message out of a DRF error body, which looks
 * like `{ field: ["message", ...], ... }` or `{ detail: "message" }`.
 */
export function firstApiError(data: unknown): string | null {
  if (typeof data === 'string') return data
  if (data && typeof data === 'object') {
    for (const value of Object.values(data as Record<string, unknown>)) {
      if (typeof value === 'string') return value
      if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
    }
  }
  return null
}
