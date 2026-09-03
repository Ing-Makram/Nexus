import { useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { ApiError, firstApiError } from '../api/client'
import { useCustomers } from '../customers/useCustomers'
import { formatAmount } from '../lib/format'
import { useOrders } from '../orders/useOrders'
import { INVOICE_STATUSES, type InvoiceInput, type InvoiceStatus } from '../types/invoice'

interface FormState {
  customer: string
  order: string
  invoice_number: string
  status: InvoiceStatus
  issue_date: string
  due_date: string
  total_amount: string
  notes: string
}

const BLANK: FormState = {
  customer: '',
  order: '',
  invoice_number: '',
  status: 'draft',
  issue_date: '',
  due_date: '',
  total_amount: '',
  notes: '',
}

interface InvoiceFormProps {
  initial?: Partial<FormState>
  submitLabel: string
  busyLabel: string
  resetOnSuccess?: boolean
  onSubmit: (input: InvoiceInput) => Promise<void>
  onCancel?: () => void
}

export function InvoiceForm({
  initial,
  submitLabel,
  busyLabel,
  resetOnSuccess = false,
  onSubmit,
  onCancel,
}: InvoiceFormProps) {
  const { customers } = useCustomers()
  // The Invoices workspace tab mounts its own OrdersProvider with no status
  // filter UI, so `orders` here is always the full current-organization list -
  // an Orders-tab status filter can never narrow the options below.
  const { orders } = useOrders()
  const customerName = (id: number) =>
    customers.find((customer) => customer.id === id)?.name ?? `Customer #${id}`
  const [form, setForm] = useState<FormState>({ ...BLANK, ...initial })
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  // Guards against a rapid double-click firing a second request before the
  // disabled state has re-rendered.
  const inFlight = useRef(false)

  function update(field: keyof FormState) {
    return (event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
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
        customer: Number(form.customer),
        order: form.order === '' ? null : Number(form.order),
        invoice_number: form.invoice_number.trim(),
        status: form.status,
        issue_date: form.issue_date,
        due_date: form.due_date === '' ? null : form.due_date,
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
      inFlight.current = false
      setSubmitting(false)
    }
  }

  return (
    <form className="invoice-form" onSubmit={handleSubmit} noValidate>
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
        Order
        <select name="order" value={form.order} onChange={update('order')}>
          <option value="">No order</option>
          {orders.map((order) => (
            <option key={order.id} value={order.id}>
              #{order.id} · {customerName(order.customer)} · {formatAmount(order.total_amount)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Invoice number
        <input
          name="invoice_number"
          placeholder="auto-generated"
          value={form.invoice_number}
          onChange={update('invoice_number')}
        />
      </label>
      <label>
        Status
        <select name="status" value={form.status} onChange={update('status')}>
          {INVOICE_STATUSES.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
      </label>
      <label>
        Issue date
        <input
          name="issue_date"
          type="date"
          required
          value={form.issue_date}
          onChange={update('issue_date')}
        />
      </label>
      <label>
        Due date
        <input name="due_date" type="date" value={form.due_date} onChange={update('due_date')} />
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
      <div className="invoice-form__actions">
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
