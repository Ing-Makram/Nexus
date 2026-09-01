import { createContext } from 'react'
import type { Customer, CustomerInput } from '../types/customer'

export type CustomersStatus = 'loading' | 'ready' | 'error'

export interface CustomersContextValue {
  status: CustomersStatus
  /** Customers of the current organization matching the search query, by name. */
  customers: Customer[]
  /** Whether the current organization has any customers at all (ignores search). */
  hasAny: boolean
  searchQuery: string
  setSearchQuery: (query: string) => void
  createCustomer: (input: CustomerInput) => Promise<Customer>
  updateCustomer: (id: number, input: CustomerInput) => Promise<Customer>
  deleteCustomer: (id: number) => Promise<void>
  reload: () => Promise<void>
}

export const CustomersContext = createContext<CustomersContextValue | null>(null)
