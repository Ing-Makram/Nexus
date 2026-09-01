import { createContext } from 'react'
import type { DashboardStats } from '../types/dashboard'

export type DashboardStatus = 'loading' | 'ready' | 'error'

export interface DashboardContextValue {
  status: DashboardStatus
  stats: DashboardStats | null
  reload: () => Promise<void>
}

export const DashboardContext = createContext<DashboardContextValue | null>(null)
