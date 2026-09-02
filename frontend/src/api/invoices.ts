import type { AuthorizedRequest } from '../auth/context'
import type { Invoice, InvoiceInput, InvoiceStatus } from '../types/invoice'

export interface InvoiceListFilters {
  status?: InvoiceStatus
  /** Inclusive lower bound on `issue_date` (`YYYY-MM-DD`). */
  dateFrom?: string
  /** Inclusive upper bound on `issue_date` (`YYYY-MM-DD`). */
  dateTo?: string
}

/**
 * List invoices for one organization. The backend supports `?organization=`
 * plus optional `?status=`, `?date_from=` and `?date_to=`. Tenant scoping stays
 * server-side.
 */
export function listInvoices(
  request: AuthorizedRequest,
  organizationId: number,
  filters: InvoiceListFilters = {},
): Promise<Invoice[]> {
  const query = new URLSearchParams({ organization: String(organizationId) })
  if (filters.status) query.set('status', filters.status)
  if (filters.dateFrom) query.set('date_from', filters.dateFrom)
  if (filters.dateTo) query.set('date_to', filters.dateTo)
  return request<Invoice[]>(`/invoices/?${query.toString()}`)
}

export function createInvoice(
  request: AuthorizedRequest,
  input: InvoiceInput & { organization: number },
): Promise<Invoice> {
  return request<Invoice>('/invoices/', { method: 'POST', body: input })
}

export function updateInvoice(
  request: AuthorizedRequest,
  id: number,
  input: Partial<InvoiceInput>,
): Promise<Invoice> {
  return request<Invoice>(`/invoices/${id}/`, { method: 'PATCH', body: input })
}

export function deleteInvoice(request: AuthorizedRequest, id: number): Promise<void> {
  return request<void>(`/invoices/${id}/`, { method: 'DELETE' })
}
