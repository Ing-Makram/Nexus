import type { ReactNode } from 'react'
import { useAuth } from '../auth/useAuth'
import { AuthScreen } from './AuthScreen'

/**
 * Route guard for a single-page app: renders its children only for an
 * authenticated user, otherwise shows the login / sign-up screen.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth()

  if (status === 'loading') {
    return <p className="auth-status">Loading…</p>
  }
  if (status !== 'authenticated') {
    return <AuthScreen />
  }
  return <>{children}</>
}
