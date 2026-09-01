import { useContext } from 'react'
import { OrdersContext, type OrdersContextValue } from './context'

export function useOrders(): OrdersContextValue {
  const context = useContext(OrdersContext)
  if (!context) {
    throw new Error('useOrders must be used within an <OrdersProvider>')
  }
  return context
}
