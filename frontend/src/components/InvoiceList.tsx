import { useState } from 'react'
import { useCustomers } from '../customers/useCustomers'
import { useInvoices } from '../invoices/useInvoices'
import { daysUntil, formatAmount, formatDate } from '../lib/format'
import type { Invoice } from '../types/invoice'
import { InvoiceForm } from './InvoiceForm'
import { StatusBadge } from './StatusBadge'

interface InvoiceListProps {
  canManage: boolean
}

function dueLabel(invoice: Invoice): { text: string; overdue: boolean } {
  if (!invoice.due_date) return { text: 'no due date', overdue: false }
  const days = daysUntil(invoice.due_date)
  const settled = invoice.status === 'paid' || invoice.status === 'void'
  const overdue = !settled && days !== null && days < 0
  return { text: `due ${formatDate(invoice.due_date)}`, overdue }
}

export function InvoiceList({ canManage }: InvoiceListProps) {
  const { status, invoices, statusFilter, searchQuery, updateInvoice, deleteInvoice } =
    useInvoices()
  const { customers } = useCustomers()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [rowError, setRowError] = useState<string | null>(null)

  const customerName = (id: number) =>
    customers.find((customer) => customer.id === id)?.name ?? `Customer #${id}`

  if (status === 'loading') {
    return <p className="invoices__status">Loading invoices…</p>
  }
  if (status === 'error') {
    return (
      <p role="alert" className="auth-error">
        Could not load invoices.
      </p>
    )
  }
  if (invoices.length === 0) {
    let message = 'No invoices yet.'
    if (searchQuery.trim()) message = 'No invoices match your search.'
    else if (statusFilter) message = `No ${statusFilter} invoices.`
    return <p className="invoices__status empty">{message}</p>
  }

  async function handleDelete(invoice: Invoice) {
    if (!window.confirm(`Delete ${invoice.invoice_number}? This cannot be undone.`)) {
      return
    }
    setRowError(null)
    setDeletingId(invoice.id)
    try {
      await deleteInvoice(invoice.id)
    } catch {
      setRowError(`Could not delete ${invoice.invoice_number}. Please try again.`)
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
      <ul className="invoice-list list">
        {invoices.map((invoice) =>
          canManage && editingId === invoice.id ? (
            <li key={invoice.id}>
              <InvoiceForm
                initial={{
                  customer: String(invoice.customer),
                  order: invoice.order == null ? '' : String(invoice.order),
                  invoice_number: invoice.invoice_number,
                  status: invoice.status,
                  issue_date: invoice.issue_date,
                  due_date: invoice.due_date ?? '',
                  total_amount: invoice.total_amount,
                  notes: invoice.notes,
                }}
                submitLabel="Save"
                busyLabel="Saving…"
                onCancel={() => setEditingId(null)}
                onSubmit={async (input) => {
                  await updateInvoice(invoice.id, input)
                  setEditingId(null)
                }}
              />
            </li>
          ) : (
            <li key={invoice.id} className="invoice-list__row list__row">
              <div>
                <div className="list__title">
                  <strong>{invoice.invoice_number}</strong>
                  <StatusBadge kind="invoice" status={invoice.status} />
                  <span className="list__amount">{formatAmount(invoice.total_amount)}</span>
                </div>
                <div className="invoice-list__meta list__meta">
                  {customerName(invoice.customer)}
                  {invoice.order != null && <> · order #{invoice.order}</>} · issued{' '}
                  {formatDate(invoice.issue_date)}
                  {(() => {
                    const due = dueLabel(invoice)
                    return (
                      <>
                        {' · '}
                        <span className={due.overdue ? 'text-danger' : undefined}>{due.text}</span>
                      </>
                    )
                  })()}
                </div>
                {invoice.notes && <div className="invoice-list__notes">{invoice.notes}</div>}
              </div>
              {canManage && (
                <div className="invoice-list__actions list__actions">
                  <button
                    type="button"
                    className="btn btn--ghost"
                    onClick={() => setEditingId(invoice.id)}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost"
                    onClick={() => handleDelete(invoice)}
                    disabled={deletingId === invoice.id}
                  >
                    {deletingId === invoice.id ? 'Deleting…' : 'Delete'}
                  </button>
                </div>
              )}
            </li>
          ),
        )}
      </ul>
    </>
  )
}
