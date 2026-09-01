import type { AuthorizedRequest } from '../auth/context'
import type { Order, OrderInput, OrderStatus } from '../types/order'

/**
 * List orders for one organization (the backend supports `?organization=` and
 * an optional `?status=`). Tenant scoping stays server-side.
 */
export function listOrders(
  request: AuthorizedRequest,
  organizationId: number,
  status?: OrderStatus,
): Promise<Order[]> {
  const query = new URLSearchParams({ organization: String(organizationId) })
  if (status) query.set('status', status)
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
