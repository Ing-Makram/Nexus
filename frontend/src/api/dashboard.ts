import type { AuthorizedRequest } from '../auth/context'
import type { DashboardStats, DashboardTimeseries } from '../types/dashboard'

/** Aggregate figures for one organization (`GET /dashboard/?organization=<id>`). */
export function getDashboard(
  request: AuthorizedRequest,
  organizationId: number,
): Promise<DashboardStats> {
  return request<DashboardStats>(`/dashboard/?organization=${organizationId}`)
}

export type DashboardRange = 30 | 90

/** Daily activity over the last `days` days (`GET /dashboard/timeseries/`). */
export function getDashboardTimeseries(
  request: AuthorizedRequest,
  organizationId: number,
  days: DashboardRange,
): Promise<DashboardTimeseries> {
  return request<DashboardTimeseries>(
    `/dashboard/timeseries/?organization=${organizationId}&days=${days}`,
  )
}
