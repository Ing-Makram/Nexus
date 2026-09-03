import { useState } from 'react'
import { ApiError, firstApiError } from '../api/client'
import { useCustomers } from '../customers/useCustomers'
import type { Customer } from '../types/customer'
import { CustomerForm } from './CustomerForm'

export function CustomerList() {
  const { status, customers, hasAny, searchQuery, updateCustomer, deleteCustomer } = useCustomers()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [rowError, setRowError] = useState<string | null>(null)

  if (status === 'loading') {
    return <p className="section__status">Loading customers…</p>
  }
  if (status === 'error') {
    return (
      <p role="alert" className="auth-error">
        Could not load customers.
      </p>
    )
  }
  if (customers.length === 0) {
    return (
      <p className="section__status empty">
        {hasAny || searchQuery.trim()
          ? 'No customers match your search.'
          : 'No customers yet. Add your first one.'}
      </p>
    )
  }

  async function handleDelete(customer: Customer) {
    if (
      !window.confirm(
        `Delete ${customer.name}? Their orders and invoices are deleted too. This cannot be undone.`,
      )
    ) {
      return
    }
    setRowError(null)
    setDeletingId(customer.id)
    try {
      await deleteCustomer(customer.id)
    } catch (error) {
      const reason = error instanceof ApiError ? firstApiError(error.data) : null
      setRowError(reason ?? `Could not delete ${customer.name}. Please try again.`)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <>
      {rowError && (
        <p role="alert" className="auth-error">
          {rowError}
        </p>
      )}
      <ul className="customer-list">
        {customers.map((customer) =>
          editingId === customer.id ? (
            <li key={customer.id}>
              <CustomerForm
                initial={customer}
                submitLabel="Save"
                busyLabel="Saving…"
                onCancel={() => setEditingId(null)}
                onSubmit={async (input) => {
                  await updateCustomer(customer.id, input)
                  setEditingId(null)
                }}
              />
            </li>
          ) : (
            <li key={customer.id} className="customer-list__row list__row">
              <div>
                <div className="list__title">
                  <strong>{customer.name}</strong>
                  {customer.company && <span className="list__sub">{customer.company}</span>}
                </div>
                <div className="customer-list__contact list__meta">
                  {customer.email || '—'} · {customer.phone || '—'}
                </div>
              </div>
              <div className="customer-list__actions list__actions">
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => setEditingId(customer.id)}
                >
                  Edit
                </button>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => handleDelete(customer)}
                  disabled={deletingId === customer.id}
                >
                  {deletingId === customer.id ? 'Deleting…' : 'Delete'}
                </button>
              </div>
            </li>
          ),
        )}
      </ul>
    </>
  )
}
