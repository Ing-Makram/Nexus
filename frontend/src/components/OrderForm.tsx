import { useState, type ChangeEvent, type FormEvent } from 'react'
import { ApiError, firstApiError } from '../api/client'
import { useCustomers } from '../customers/useCustomers'
import { ORDER_STATUSES, type OrderInput, type OrderStatus } from '../types/order'

interface FormState {
  customer: string
  status: OrderStatus
  total_amount: string
  notes: string
}

const BLANK: FormState = { customer: '', status: 'draft', total_amount: '', notes: '' }

interface OrderFormProps {
  initial?: Partial<FormState>
  submitLabel: string
  busyLabel: string
  resetOnSuccess?: boolean
  onSubmit: (input: OrderInput) => Promise<void>
  onCancel?: () => void
}

export function OrderForm({
  initial,
  submitLabel,
  busyLabel,
  resetOnSuccess = false,
  onSubmit,
  onCancel,
}: OrderFormProps) {
  const { customers } = useCustomers()
  const [form, setForm] = useState<FormState>({ ...BLANK, ...initial })
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  function update(field: keyof FormState) {
    return (event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
      setForm((current) => ({ ...current, [field]: event.target.value }))
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await onSubmit({
        customer: Number(form.customer),
        status: form.status,
        total_amount: form.total_amount.trim(),
        notes: form.notes.trim(),
      })
      if (resetOnSuccess) setForm(BLANK)
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setError(firstApiError(err.data) ?? 'Please check the form and try again.')
      } else {
        setError('Something went wrong. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="order-form" onSubmit={handleSubmit} noValidate>
      <label>
        Customer
        <select name="customer" required value={form.customer} onChange={update('customer')}>
          <option value="">Select a customer…</option>
          {customers.map((customer) => (
            <option key={customer.id} value={customer.id}>
              {customer.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Status
        <select name="status" value={form.status} onChange={update('status')}>
          {ORDER_STATUSES.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
      </label>
      <label>
        Total amount
        <input
          name="total_amount"
          required
          inputMode="decimal"
          value={form.total_amount}
          onChange={update('total_amount')}
        />
      </label>
      <label>
        Notes
        <textarea name="notes" rows={2} value={form.notes} onChange={update('notes')} />
      </label>
      {error && (
        <p role="alert" className="auth-error">
          {error}
        </p>
      )}
      <div className="order-form__actions">
        <button type="submit" disabled={submitting}>
          {submitting ? busyLabel : submitLabel}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} disabled={submitting}>
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}
