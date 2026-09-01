import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import * as ordersApi from '../api/orders'
import { useAuth } from '../auth/useAuth'
import { changedFields } from '../lib/changedFields'
import { useOrganizations } from '../organizations/useOrganizations'
import type { Order, OrderInput, OrderStatus } from '../types/order'
import { OrdersContext, type OrdersContextValue, type OrdersStatus } from './context'

/**
 * Loads orders for the currently selected organization using the backend's
 * `?organization=` filter (and `?status=` when a status filter is active), and
 * reloads whenever either changes. Mirrors the Invoices provider: nothing is
 * ever fetched for other organizations.
 */
export function OrdersProvider({ children }: { children: ReactNode }) {
  const { authorizedRequest } = useAuth()
  const { currentOrganization } = useOrganizations()
  const organizationId = currentOrganization?.id ?? null

  const [status, setStatus] = useState<OrdersStatus>('loading')
  const [orders, setOrders] = useState<Order[]>([])
  const [statusFilter, setStatusFilter] = useState<OrderStatus | null>(null)

  // Switching organization clears the filter and the previous organization's
  // orders, so a render never attributes stale (wrong-tenant) rows to the
  // newly selected organization while the new fetch is in flight. Adjusting
  // state during render (rather than in an effect) avoids a throwaway fetch
  // with the previous filter and avoids a synchronous setState-in-effect.
  const [filterOrg, setFilterOrg] = useState(organizationId)
  if (organizationId !== filterOrg) {
    setFilterOrg(organizationId)
    setStatusFilter(null)
    setOrders([])
    setStatus('loading')
  }

  useEffect(() => {
    if (organizationId == null) return
    let cancelled = false
    void (async () => {
      try {
        const list = await ordersApi.listOrders(
          authorizedRequest,
          organizationId,
          statusFilter ?? undefined,
        )
        if (cancelled) return
        setOrders(list)
        setStatus('ready')
      } catch {
        if (cancelled) return
        setStatus('error')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [authorizedRequest, organizationId, statusFilter])

  const reload = useCallback(async () => {
    if (organizationId == null) return
    setStatus('loading')
    try {
      setOrders(
        await ordersApi.listOrders(authorizedRequest, organizationId, statusFilter ?? undefined),
      )
      setStatus('ready')
    } catch {
      setStatus('error')
    }
  }, [authorizedRequest, organizationId, statusFilter])

  const createOrder = useCallback(
    async (input: OrderInput) => {
      if (organizationId == null) {
        throw new Error('No organization selected')
      }
      const created = await ordersApi.createOrder(authorizedRequest, {
        ...input,
        organization: organizationId,
      })
      setOrders((prev) => [created, ...prev])
      return created
    },
    [authorizedRequest, organizationId],
  )

  const updateOrder = useCallback(
    async (id: number, input: OrderInput) => {
      const current = orders.find((order) => order.id === id)
      const patch = current ? changedFields(current, input) : input
      // Nothing actually changed - don't send a pointless request.
      if (current && Object.keys(patch).length === 0) {
        return current
      }
      const updated = await ordersApi.updateOrder(authorizedRequest, id, patch)
      setOrders((prev) => prev.map((order) => (order.id === id ? updated : order)))
      return updated
    },
    [authorizedRequest, orders],
  )

  const deleteOrder = useCallback(
    async (id: number) => {
      await ordersApi.deleteOrder(authorizedRequest, id)
      setOrders((prev) => prev.filter((order) => order.id !== id))
    },
    [authorizedRequest],
  )

  const value = useMemo<OrdersContextValue>(
    () => ({
      status,
      orders,
      statusFilter,
      setStatusFilter,
      createOrder,
      updateOrder,
      deleteOrder,
      reload,
    }),
    [status, orders, statusFilter, createOrder, updateOrder, deleteOrder, reload],
  )

  return <OrdersContext value={value}>{children}</OrdersContext>
}
