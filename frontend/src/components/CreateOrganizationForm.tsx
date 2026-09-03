import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { useOrganizations } from '../organizations/useOrganizations'

export function CreateOrganizationForm() {
  const { createOrganization } = useOrganizations()
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await createOrganization(name)
      setName('')
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 400
          ? 'Enter a valid organization name (2-120 characters).'
          : 'Could not create the organization. Please try again.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="org-create" onSubmit={handleSubmit} noValidate>
      <label>
        Organization name
        <input
          name="organization-name"
          required
          minLength={2}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </label>
      {error && (
        <p role="alert" className="auth-error">
          {error}
        </p>
      )}
      <button type="submit" className="btn btn--primary" disabled={submitting}>
        {submitting ? 'Creating…' : 'Create organization'}
      </button>
    </form>
  )
}
