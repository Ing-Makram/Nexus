import { useContext } from 'react'
import { InvoicesContext, type InvoicesContextValue } from './context'

export function useInvoices(): InvoicesContextValue {
  const context = useContext(InvoicesContext)
  if (!context) {
    throw new Error('useInvoices must be used within an <InvoicesProvider>')
  }
  return context
}
