import { useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { ApiError, firstApiError } from '../api/client'
import type { CustomerInput } from '../types/customer'

type FormState = Record<'name' | 'email' | 'phone' | 'company' | 'address', string>

const BLANK: FormState = { name: '', email: '', phone: '', company: '', address: '' }

interface CustomerFormProps {
  initial?: Partial<FormState>
  submitLabel: string
  busyLabel: string
  resetOnSuccess?: boolean
  onSubmit: (input: CustomerInput) => Promise<void>
  onCancel?: () => void
}

export function CustomerForm({
  initial,
  submitLabel,
  busyLabel,
  resetOnSuccess = false,
  onSubmit,
  onCancel,
}: CustomerFormProps) {
  const [form, setForm] = useState<FormState>({ ...BLANK, ...initial })
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  // Guards against a rapid double-click firing a second request before the
  // disabled state has re-rendered.
  const inFlight = useRef(false)

  function update(field: keyof FormState) {
    return (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setForm((current) => ({ ...current, [field]: event.target.value }))
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (inFlight.current) return
    inFlight.current = true
    setError(null)
    setSubmitting(true)
    try {
      await onSubmit({
        name: form.name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
        company: form.company.trim(),
        address: form.address.trim(),
      })
      if (resetOnSuccess) setForm(BLANK)
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setError(firstApiError(err.data) ?? 'Please check the form and try again.')
      } else {
        setError('Something went wrong. Please try again.')
      }
    } finally {
      inFlight.current = false
      setSubmitting(false)
    }
  }

  return (
    <form className="customer-form" onSubmit={handleSubmit} noValidate>
      <label>
        Name
        <input name="name" required value={form.name} onChange={update('name')} />
      </label>
      <label>
        Email
        <input name="email" type="email" value={form.email} onChange={update('email')} />
      </label>
      <label>
        Phone
        <input name="phone" value={form.phone} onChange={update('phone')} />
      </label>
      <label>
        Company
        <input name="company" value={form.company} onChange={update('company')} />
      </label>
      <label>
        Address
        <textarea name="address" rows={2} value={form.address} onChange={update('address')} />
      </label>
      {error && (
        <p role="alert" className="auth-error">
          {error}
        </p>
      )}
      <div className="customer-form__actions">
        <button type="submit" className="btn btn--primary" disabled={submitting}>
          {submitting ? busyLabel : submitLabel}
        </button>
        {onCancel && (
          <button type="button" className="btn btn--ghost" onClick={onCancel} disabled={submitting}>
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}
