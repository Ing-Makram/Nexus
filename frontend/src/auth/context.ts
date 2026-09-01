import { createContext } from 'react'
import type { AuthUser, RegisterPayload } from '../types/auth'

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated'

export interface AuthorizedRequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  signal?: AbortSignal
}

/**
 * Makes an authenticated API request, transparently refreshing the access
 * token once on a 401. This is the shared client for every authenticated
 * business module (organizations, and future ones).
 */
export type AuthorizedRequest = <T>(path: string, options?: AuthorizedRequestOptions) => Promise<T>

export interface AuthContextValue {
  status: AuthStatus
  user: AuthUser | null
  login: (email: string, password: string) => Promise<void>
  register: (payload: RegisterPayload) => Promise<void>
  /**
   * Best-effort: blacklists the refresh token server-side, then clears the
   * local session. The local session is always cleared, even if the backend
   * call fails or is unreachable.
   */
  logout: () => Promise<void>
  authorizedRequest: AuthorizedRequest
}

export const AuthContext = createContext<AuthContextValue | null>(null)
