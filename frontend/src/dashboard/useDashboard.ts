import { useContext } from 'react'
import { DashboardContext, type DashboardContextValue } from './context'

export function useDashboard(): DashboardContextValue {
  const context = useContext(DashboardContext)
  if (!context) {
    throw new Error('useDashboard must be used within a <DashboardProvider>')
  }
  return context
}
