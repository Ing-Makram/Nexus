import { createContext } from 'react'
import type { Order, OrderInput, OrderStatus } from '../types/order'

export type OrdersStatus = 'loading' | 'ready' | 'error'

export interface OrdersContextValue {
  status: OrdersStatus
  /** Orders of the currently selected organization, newest first. */
  orders: Order[]
  /** Active server-side status filter, or `null` for "all statuses". */
  statusFilter: OrderStatus | null
  setStatusFilter: (status: OrderStatus | null) => void
  createOrder: (input: OrderInput) => Promise<Order>
  updateOrder: (id: number, input: OrderInput) => Promise<Order>
  deleteOrder: (id: number) => Promise<void>
  reload: () => Promise<void>
}

export const OrdersContext = createContext<OrdersContextValue | null>(null)
