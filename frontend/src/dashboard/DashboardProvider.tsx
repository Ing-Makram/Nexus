import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { getDashboard, getDashboardTimeseries, type DashboardRange } from '../api/dashboard'
import { useAuth } from '../auth/useAuth'
import { useOrganizations } from '../organizations/useOrganizations'
import type { DashboardStats, DashboardTimeseries } from '../types/dashboard'
import { DashboardContext, type DashboardContextValue, type DashboardStatus } from './context'

/**
 * Fetches the aggregate figures for the current organization from the backend
 * `/dashboard/` endpoint (a single query - the figures are never derived from
 * the list providers, which apply their own filters), plus the daily
 * `/dashboard/timeseries/` series for the date-range charts.
 */
export function DashboardProvider({ children }: { children: ReactNode }) {
  const { authorizedRequest } = useAuth()
  const { currentOrganization } = useOrganizations()
  const organizationId = currentOrganization?.id ?? null

  // Lets an in-flight manual reload detect that the organization changed under
  // it and drop its (now wrong-tenant) result instead of overwriting state.
  const currentOrgRef = useRef(organizationId)
  useEffect(() => {
    currentOrgRef.current = organizationId
  }, [organizationId])

  const [status, setStatus] = useState<DashboardStatus>('loading')
  const [stats, setStats] = useState<DashboardStats | null>(null)

  const [range, setRange] = useState<DashboardRange>(30)
  const [timeseries, setTimeseries] = useState<DashboardTimeseries | null>(null)
  const [timeseriesStatus, setTimeseriesStatus] = useState<DashboardStatus>('loading')

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

  // The timeseries reloads on an organization *or* range change; the same
  // render-time reset keeps a stale series from showing under a new selection.
  const seriesKey = `${organizationId}:${range}`
  const [loadedSeriesKey, setLoadedSeriesKey] = useState(seriesKey)
  if (seriesKey !== loadedSeriesKey) {
    setLoadedSeriesKey(seriesKey)
    setTimeseries(null)
    setTimeseriesStatus('loading')
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

  useEffect(() => {
    if (organizationId == null) return
    let cancelled = false
    void (async () => {
      try {
        const data = await getDashboardTimeseries(authorizedRequest, organizationId, range)
        if (cancelled) return
        setTimeseries(data)
        setTimeseriesStatus('ready')
      } catch {
        if (cancelled) return
        setTimeseriesStatus('error')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [authorizedRequest, organizationId, range])

  const reload = useCallback(async () => {
    if (organizationId == null) return
    const forOrg = organizationId
    setStatus('loading')
    setTimeseriesStatus('loading')
    try {
      const [next, series] = await Promise.all([
        getDashboard(authorizedRequest, forOrg),
        getDashboardTimeseries(authorizedRequest, forOrg, range),
      ])
      if (currentOrgRef.current !== forOrg) return
      setStats(next)
      setStatus('ready')
      setTimeseries(series)
      setTimeseriesStatus('ready')
    } catch {
      if (currentOrgRef.current !== forOrg) return
      setStatus('error')
      setTimeseriesStatus('error')
    }
  }, [authorizedRequest, organizationId, range])

  const value = useMemo<DashboardContextValue>(
    () => ({ status, stats, reload, timeseries, timeseriesStatus, range, setRange }),
    [status, stats, reload, timeseries, timeseriesStatus, range],
  )

  return <DashboardContext value={value}>{children}</DashboardContext>
}
