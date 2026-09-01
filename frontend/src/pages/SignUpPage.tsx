import { useState, type FormEvent } from 'react'
import { ApiError, firstApiError } from '../api/client'
import { useAuth } from '../auth/useAuth'

interface SignUpPageProps {
  onSwitchToLogin: () => void
}

const EMPTY = { email: '', password: '', first_name: '', last_name: '' }

export function SignUpPage({ onSwitchToLogin }: SignUpPageProps) {
  const { register } = useAuth()
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  function update(field: keyof typeof form) {
    return (event: React.ChangeEvent<HTMLInputElement>) => {
      setForm((current) => ({ ...current, [field]: event.target.value }))
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await register({
        email: form.email,
        password: form.password,
        first_name: form.first_name || undefined,
        last_name: form.last_name || undefined,
      })
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setError(firstApiError(err.data) ?? 'Please check the form and try again.')
      } else {
        setError('Unable to sign up right now. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-card">
      <h1>Create your NEXUS account</h1>
      <form onSubmit={handleSubmit} noValidate>
        <label>
          Email
          <input
            type="email"
            name="email"
            autoComplete="username"
            required
            value={form.email}
            onChange={update('email')}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={form.password}
            onChange={update('password')}
          />
        </label>
        <label>
          First name
          <input
            type="text"
            name="first_name"
            autoComplete="given-name"
            value={form.first_name}
            onChange={update('first_name')}
          />
        </label>
        <label>
          Last name
          <input
            type="text"
            name="last_name"
            autoComplete="family-name"
            value={form.last_name}
            onChange={update('last_name')}
          />
        </label>
        {error && (
          <p role="alert" className="auth-error">
            {error}
          </p>
        )}
        <button type="submit" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p className="auth-switch">
        Already have an account?{' '}
        <button type="button" className="link-button" onClick={onSwitchToLogin}>
          Sign in
        </button>
      </p>
    </main>
  )
}
