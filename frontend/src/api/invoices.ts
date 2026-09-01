import type { AuthorizedRequest } from '../auth/context'
import type { Invoice, InvoiceInput, InvoiceStatus } from '../types/invoice'

/**
 * List invoices for one organization (the backend supports `?organization=` and
 * an optional `?status=`). Tenant scoping stays server-side.
 */
export function listInvoices(
  request: AuthorizedRequest,
  organizationId: number,
  status?: InvoiceStatus,
): Promise<Invoice[]> {
  const query = new URLSearchParams({ organization: String(organizationId) })
  if (status) query.set('status', status)
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
