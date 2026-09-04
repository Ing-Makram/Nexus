import { useState } from 'react'
import { LoginPage } from '../pages/LoginPage'
import { SignUpPage } from '../pages/SignUpPage'

type Mode = 'login' | 'signup'

/**
 * Unauthenticated shell: an animated business backdrop with the login or
 * sign-up card on top.
 */
export function AuthScreen() {
  const [mode, setMode] = useState<Mode>('login')

  return (
    <div className="auth-screen">
      <div className="auth-screen__bg" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>

      <div className="auth-screen__content">
        <div className="auth-brand">
          <h1>NEXUS</h1>
          <p>Customers, orders, invoices and business metrics — one place per organization.</p>
        </div>

        {mode === 'login' ? (
          <LoginPage onSwitchToSignUp={() => setMode('signup')} />
        ) : (
          <SignUpPage onSwitchToLogin={() => setMode('login')} />
        )}
      </div>
    </div>
  )
}
