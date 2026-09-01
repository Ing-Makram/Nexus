export type OrderStatus = 'draft' | 'pending' | 'confirmed' | 'cancelled' | 'completed'

export const ORDER_STATUSES: OrderStatus[] = [
  'draft',
  'pending',
  'confirmed',
  'cancelled',
  'completed',
]

export interface Order {
  id: number
  organization: number
  customer: number
  status: OrderStatus
  total_amount: string
  notes: string
  created_at: string
  updated_at: string
}

/** Editable order fields sent to the API. */
export interface OrderInput {
  customer: number
  status?: OrderStatus
  total_amount: string
  notes?: string
}
