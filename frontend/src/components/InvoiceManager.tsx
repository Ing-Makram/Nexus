import { useState } from 'react'
import { useInvoices } from '../invoices/useInvoices'
import { useOrganizations } from '../organizations/useOrganizations'
import { INVOICE_STATUSES } from '../types/invoice'
import { InvoiceForm } from './InvoiceForm'
import { InvoiceList } from './InvoiceList'
import { SearchInput } from './SearchInput'
import { StatusFilter } from './StatusFilter'

export function InvoiceManager() {
  const { currentOrganization } = useOrganizations()
  const { createInvoice, hasAny, statusFilter, setStatusFilter, searchQuery, setSearchQuery } =
    useInvoices()
  const [adding, setAdding] = useState(false)

  const role = currentOrganization?.role
  const canManage = role === 'owner' || role === 'admin'

  return (
    <section className="invoices section" aria-label="Invoices">
      <div className="section__head">
        <h2>Invoices</h2>
        {canManage && !adding && (
          <button type="button" className="btn btn--primary" onClick={() => setAdding(true)}>
            Add invoice
          </button>
        )}
      </div>

      <div className="section__filters">
        <StatusFilter statuses={INVOICE_STATUSES} value={statusFilter} onChange={setStatusFilter} />
        {hasAny && (
          <SearchInput
            label="Search invoices"
            placeholder="Invoice number or notes"
            value={searchQuery}
            onChange={setSearchQuery}
          />
        )}
      </div>

      {canManage && adding && (
        <InvoiceForm
          submitLabel="Add invoice"
          busyLabel="Adding…"
          resetOnSuccess
          onCancel={() => setAdding(false)}
          onSubmit={async (input) => {
            await createInvoice(input)
          }}
        />
      )}

      <InvoiceList canManage={canManage} />
    </section>
  )
}
