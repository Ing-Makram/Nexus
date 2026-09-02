import { createContext } from 'react'
import type { Invoice, InvoiceInput, InvoiceStatus } from '../types/invoice'

export type InvoicesStatus = 'loading' | 'ready' | 'error'

export interface InvoicesContextValue {
  status: InvoicesStatus
  /** Invoices of the current org (status-filtered server-side) matching the search. */
  invoices: Invoice[]
  /** Whether the current status view has any invoices at all (ignores search). */
  hasAny: boolean
  /** Active server-side status filter, or `null` for "all statuses". */
  statusFilter: InvoiceStatus | null
  setStatusFilter: (status: InvoiceStatus | null) => void
  /** Inclusive server-side bounds on `issue_date` (`YYYY-MM-DD`), or `null`. */
  dateFrom: string | null
  dateTo: string | null
  setDateRange: (from: string | null, to: string | null) => void
  searchQuery: string
  setSearchQuery: (query: string) => void
  createInvoice: (input: InvoiceInput) => Promise<Invoice>
  updateInvoice: (id: number, input: InvoiceInput) => Promise<Invoice>
  deleteInvoice: (id: number) => Promise<void>
  reload: () => Promise<void>
}

export const InvoicesContext = createContext<InvoicesContextValue | null>(null)
