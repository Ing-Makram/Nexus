import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { getDashboard } from '../api/dashboard'
import { useAuth } from '../auth/useAuth'
import { useOrganizations } from '../organizations/useOrganizations'
import type { DashboardStats } from '../types/dashboard'
import { DashboardContext, type DashboardContextValue, type DashboardStatus } from './context'

/**
 * Fetches the aggregate figures for the current organization from the backend
 * `/dashboard/` endpoint (a single query - the figures are never derived from
 * the list providers, which apply their own filters).
 */
export function DashboardProvider({ children }: { children: ReactNode }) {
  const { authorizedRequest } = useAuth()
  const { currentOrganization } = useOrganizations()
  const organizationId = currentOrganization?.id ?? null

  const [status, setStatus] = useState<DashboardStatus>('loading')
  const [stats, setStats] = useState<DashboardStats | null>(null)

  // Switching organization clears the previous organization's figures, so a
  // render never attributes stale (wrong-tenant) totals to the newly selected
  // organization while the new fetch is in flight. Adjusting state during
  // render (rather than in an effect) avoids a synchronous setState-in-effect.
  const [statsOrg, setStatsOrg] = useState(organizationId)
  if (organizationId !== statsOrg) {
    setStatsOrg(organizationId)
    setStats(null)
    setStatus('loading')
  }

  useEffect(() => {
    if (organizationId == null) return
    let cancelled = false
    void (async () => {
      try {
        const data = await getDashboard(authorizedRequest, organizationId)
        if (cancelled) return
        setStats(data)
        setStatus('ready')
      } catch {
        if (cancelled) return
        setStatus('error')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [authorizedRequest, organizationId])

  const reload = useCallback(async () => {
    if (organizationId == null) return
    setStatus('loading')
    try {
      setStats(await getDashboard(authorizedRequest, organizationId))
      setStatus('ready')
    } catch {
      setStatus('error')
    }
  }, [authorizedRequest, organizationId])

  const value = useMemo<DashboardContextValue>(
    () => ({ status, stats, reload }),
    [status, stats, reload],
  )

  return <DashboardContext value={value}>{children}</DashboardContext>
}
