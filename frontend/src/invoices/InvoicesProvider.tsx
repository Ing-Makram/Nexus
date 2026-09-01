import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import * as invoicesApi from '../api/invoices'
import { useAuth } from '../auth/useAuth'
import { changedFields } from '../lib/changedFields'
import { useOrganizations } from '../organizations/useOrganizations'
import type { Invoice, InvoiceInput, InvoiceStatus } from '../types/invoice'
import { InvoicesContext, type InvoicesContextValue, type InvoicesStatus } from './context'

/**
 * Loads invoices for the currently selected organization using the backend's
 * `?organization=` filter (and `?status=` when a status filter is active), and
 * reloads whenever either changes. Nothing is fetched for other organizations.
 */
export function InvoicesProvider({ children }: { children: ReactNode }) {
  const { authorizedRequest } = useAuth()
  const { currentOrganization } = useOrganizations()
  const organizationId = currentOrganization?.id ?? null

  const [status, setStatus] = useState<InvoicesStatus>('loading')
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  // Switching organization clears the filter, search and the previous
  // organization's invoices, so a render never attributes stale (wrong-tenant)
  // rows to the newly selected organization while the new fetch is in flight.
  // Adjusting state during render (rather than in an effect) avoids a
  // throwaway fetch with the previous filter and a synchronous setState-in-effect.
  const [filterOrg, setFilterOrg] = useState(organizationId)
  if (organizationId !== filterOrg) {
    setFilterOrg(organizationId)
    setStatusFilter(null)
    setSearchQuery('')
    setInvoices([])
    setStatus('loading')
  }

  useEffect(() => {
    if (organizationId == null) return
    let cancelled = false
    void (async () => {
      try {
        const list = await invoicesApi.listInvoices(
          authorizedRequest,
          organizationId,
          statusFilter ?? undefined,
        )
        if (cancelled) return
        setInvoices(list)
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
      setInvoices(
        await invoicesApi.listInvoices(
          authorizedRequest,
          organizationId,
          statusFilter ?? undefined,
        ),
      )
      setStatus('ready')
    } catch {
      setStatus('error')
    }
  }, [authorizedRequest, organizationId, statusFilter])

  const createInvoice = useCallback(
    async (input: InvoiceInput) => {
      if (organizationId == null) {
        throw new Error('No organization selected')
      }
      const created = await invoicesApi.createInvoice(authorizedRequest, {
        ...input,
        organization: organizationId,
      })
      setInvoices((prev) => [created, ...prev])
      return created
    },
    [authorizedRequest, organizationId],
  )

  const updateInvoice = useCallback(
    async (id: number, input: InvoiceInput) => {
      const current = invoices.find((invoice) => invoice.id === id)
      const patch = current ? changedFields(current, input) : input
      // Nothing actually changed - don't send a pointless request.
      if (current && Object.keys(patch).length === 0) {
        return current
      }
      const updated = await invoicesApi.updateInvoice(authorizedRequest, id, patch)
      setInvoices((prev) => prev.map((invoice) => (invoice.id === id ? updated : invoice)))
      return updated
    },
    [authorizedRequest, invoices],
  )

  const deleteInvoice = useCallback(
    async (id: number) => {
      await invoicesApi.deleteInvoice(authorizedRequest, id)
      setInvoices((prev) => prev.filter((invoice) => invoice.id !== id))
    },
    [authorizedRequest],
  )

  const visibleInvoices = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    if (!query) return invoices
    return invoices.filter((invoice) =>
      `${invoice.invoice_number} ${invoice.notes}`.toLowerCase().includes(query),
    )
  }, [invoices, searchQuery])

  const value = useMemo<InvoicesContextValue>(
    () => ({
      status,
      invoices: visibleInvoices,
      hasAny: invoices.length > 0,
      statusFilter,
      setStatusFilter,
      searchQuery,
      setSearchQuery,
      createInvoice,
      updateInvoice,
      deleteInvoice,
      reload,
    }),
    [
      status,
      visibleInvoices,
      invoices.length,
      statusFilter,
      searchQuery,
      createInvoice,
      updateInvoice,
      deleteInvoice,
      reload,
    ],
  )

  return <InvoicesContext value={value}>{children}</InvoicesContext>
}
