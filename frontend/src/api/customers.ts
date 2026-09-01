import type { AuthorizedRequest } from '../auth/context'
import type { Customer, CustomerInput } from '../types/customer'

export function listCustomers(request: AuthorizedRequest): Promise<Customer[]> {
  return request<Customer[]>('/customers/')
}

export function createCustomer(
  request: AuthorizedRequest,
  input: CustomerInput & { organization: number },
): Promise<Customer> {
  return request<Customer>('/customers/', { method: 'POST', body: input })
}

export function updateCustomer(
  request: AuthorizedRequest,
  id: number,
  input: Partial<CustomerInput>,
): Promise<Customer> {
  return request<Customer>(`/customers/${id}/`, { method: 'PATCH', body: input })
}

export function deleteCustomer(request: AuthorizedRequest, id: number): Promise<void> {
  return request<void>(`/customers/${id}/`, { method: 'DELETE' })
}
