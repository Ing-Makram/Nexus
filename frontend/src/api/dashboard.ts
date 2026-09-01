import type { AuthorizedRequest } from '../auth/context'
import type { DashboardStats } from '../types/dashboard'

/** Aggregate figures for one organization (`GET /dashboard/?organization=<id>`). */
export function getDashboard(
  request: AuthorizedRequest,
  organizationId: number,
): Promise<DashboardStats> {
  return request<DashboardStats>(`/dashboard/?organization=${organizationId}`)
}
