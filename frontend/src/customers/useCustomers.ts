import { useContext } from 'react'
import { CustomersContext, type CustomersContextValue } from './context'

export function useCustomers(): CustomersContextValue {
  const context = useContext(CustomersContext)
  if (!context) {
    throw new Error('useCustomers must be used within a <CustomersProvider>')
  }
  return context
}
