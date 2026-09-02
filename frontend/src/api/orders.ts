import type { AuthorizedRequest } from '../auth/context'
import type { Order, OrderInput, OrderStatus } from '../types/order'

export interface OrderListFilters {
  status?: OrderStatus
  /** Inclusive lower bound on the order date (`YYYY-MM-DD`). */
  dateFrom?: string
  /** Inclusive upper bound on the order date (`YYYY-MM-DD`). */
  dateTo?: string
}

/**
 * List orders for one organization. The backend supports `?organization=` plus
 * optional `?status=`, `?date_from=` and `?date_to=`. Tenant scoping stays
 * server-side.
 */
export function listOrders(
  request: AuthorizedRequest,
  organizationId: number,
  filters: OrderListFilters = {},
): Promise<Order[]> {
  const query = new URLSearchParams({ organization: String(organizationId) })
  if (filters.status) query.set('status', filters.status)
  if (filters.dateFrom) query.set('date_from', filters.dateFrom)
  if (filters.dateTo) query.set('date_to', filters.dateTo)
  return request<Order[]>(`/orders/?${query.toString()}`)
}

export function createOrder(
  request: AuthorizedRequest,
  input: OrderInput & { organization: number },
): Promise<Order> {
  return request<Order>('/orders/', { method: 'POST', body: input })
}

export function updateOrder(
  request: AuthorizedRequest,
  id: number,
  input: Partial<OrderInput>,
): Promise<Order> {
  return request<Order>(`/orders/${id}/`, { method: 'PATCH', body: input })
}

export function deleteOrder(request: AuthorizedRequest, id: number): Promise<void> {
  return request<void>(`/orders/${id}/`, { method: 'DELETE' })
}
