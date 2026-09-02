import { createContext } from 'react'
import type { DashboardRange } from '../api/dashboard'
import type { DashboardStats, DashboardTimeseries } from '../types/dashboard'

export type DashboardStatus = 'loading' | 'ready' | 'error'

export interface DashboardContextValue {
  status: DashboardStatus
  stats: DashboardStats | null
  reload: () => Promise<void>
  timeseries: DashboardTimeseries | null
  timeseriesStatus: DashboardStatus
  range: DashboardRange
  setRange: (range: DashboardRange) => void
}

export const DashboardContext = createContext<DashboardContextValue | null>(null)
