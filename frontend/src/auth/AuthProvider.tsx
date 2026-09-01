import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import * as authApi from '../api/auth'
import { ApiError, apiRequest } from '../api/client'
import type { AuthUser, RegisterPayload } from '../types/auth'
import {
  AuthContext,
  type AuthContextValue,
  type AuthorizedRequestOptions,
  type AuthStatus,
} from './context'
import { readRefreshToken, writeRefreshToken } from './storage'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>(() =>
    readRefreshToken() ? 'loading' : 'unauthenticated',
  )
  const [user, setUser] = useState<AuthUser | null>(null)
  // Access token lives only in memory for the lifetime of the tab.
  const accessTokenRef = useRef<string | null>(null)

  // Drop the local session. Synchronous and network-free so the UI can never
  // get stuck; used both by an explicit logout and by a failed token refresh.
  const clearSession = useCallback(() => {
    accessTokenRef.current = null
    writeRefreshToken(null)
    setUser(null)
    setStatus('unauthenticated')
  }, [])

  const logout = useCallback(async () => {
    const refreshToken = readRefreshToken()
    const accessToken = accessTokenRef.current
    clearSession()
    if (!refreshToken) {
      return
    }
    try {
      await authApi.logout(accessToken, refreshToken)
    } catch {
      // Best effort: the local session is already gone. Never surface token
      // values through logs or errors.
    }
  }, [clearSession])

  const login = useCallback(async (email: string, password: string) => {
    const result = await authApi.login(email, password)
    accessTokenRef.current = result.access
    writeRefreshToken(result.refresh)
    setUser(result.user)
    setStatus('authenticated')
  }, [])

  const register = useCallback(async (payload: RegisterPayload) => {
    const result = await authApi.register(payload)
    accessTokenRef.current = result.access
    writeRefreshToken(result.refresh)
    setUser(result.user)
    setStatus('authenticated')
  }, [])

  const authorizedRequest = useCallback(
    async <T,>(path: string, options: AuthorizedRequestOptions = {}): Promise<T> => {
      const send = (token: string | null) => apiRequest<T>(path, { ...options, accessToken: token })

      try {
        return await send(accessTokenRef.current)
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 401) {
          throw error
        }
        const refreshToken = readRefreshToken()
        if (!refreshToken) {
          clearSession()
          throw error
        }
        try {
          const { access } = await authApi.refresh(refreshToken)
          accessTokenRef.current = access
          return await send(access)
        } catch {
          clearSession()
          throw error
        }
      }
    },
    [clearSession],
  )

  // On first mount, try to restore a session from a persisted refresh token.
  // When there is no token the initial status is already "unauthenticated".
  useEffect(() => {
    const refreshToken = readRefreshToken()
    if (!refreshToken) {
      return
    }

    let cancelled = false
    void (async () => {
      try {
        const { access } = await authApi.refresh(refreshToken)
        const currentUser = await authApi.me(access)
        if (cancelled) return
        accessTokenRef.current = access
        setUser(currentUser)
        setStatus('authenticated')
      } catch {
        if (cancelled) return
        writeRefreshToken(null)
        setStatus('unauthenticated')
      }
    })()

    return () => {
      cancelled = true
    }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, login, register, logout, authorizedRequest }),
    [status, user, login, register, logout, authorizedRequest],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}
