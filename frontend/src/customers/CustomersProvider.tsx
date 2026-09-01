import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import * as customersApi from '../api/customers'
import { useAuth } from '../auth/useAuth'
import { changedFields } from '../lib/changedFields'
import { useOrganizations } from '../organizations/useOrganizations'
import type { Customer, CustomerInput } from '../types/customer'
import { CustomersContext, type CustomersContextValue, type CustomersStatus } from './context'

/**
 * Loads the caller's customers once and derives the list for the currently
 * selected organization. The backend `/customers/` endpoint returns customers
 * across every organization the user belongs to; the selected organization
 * decides which of them are shown and where new ones are created.
 */
export function CustomersProvider({ children }: { children: ReactNode }) {
  const { authorizedRequest } = useAuth()
  const { currentOrganization } = useOrganizations()
  const organizationId = currentOrganization?.id ?? null

  const [status, setStatus] = useState<CustomersStatus>('loading')
  const [allCustomers, setAllCustomers] = useState<Customer[]>([])
  const [searchQuery, setSearchQuery] = useState('')

  // Reset the search when the organization changes (mirrors the Orders/Invoices
  // status filter). Adjusting state during render avoids a stale first paint.
  const [searchOrg, setSearchOrg] = useState(organizationId)
  if (organizationId !== searchOrg) {
    setSearchOrg(organizationId)
    setSearchQuery('')
  }

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const list = await customersApi.listCustomers(authorizedRequest)
        if (cancelled) return
        setAllCustomers(list)
        setStatus('ready')
      } catch {
        if (cancelled) return
        setStatus('error')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [authorizedRequest])

  const reload = useCallback(async () => {
    setStatus('loading')
    try {
      setAllCustomers(await customersApi.listCustomers(authorizedRequest))
      setStatus('ready')
    } catch {
      setStatus('error')
    }
  }, [authorizedRequest])

  const createCustomer = useCallback(
    async (input: CustomerInput) => {
      if (organizationId == null) {
        throw new Error('No organization selected')
      }
      const created = await customersApi.createCustomer(authorizedRequest, {
        ...input,
        organization: organizationId,
      })
      setAllCustomers((prev) => [...prev, created])
      return created
    },
    [authorizedRequest, organizationId],
  )

  const updateCustomer = useCallback(
    async (id: number, input: CustomerInput) => {
      const current = allCustomers.find((customer) => customer.id === id)
      const patch = current ? changedFields(current, input) : input
      // Nothing actually changed - don't send a pointless request.
      if (current && Object.keys(patch).length === 0) {
        return current
      }
      const updated = await customersApi.updateCustomer(authorizedRequest, id, patch)
      setAllCustomers((prev) => prev.map((customer) => (customer.id === id ? updated : customer)))
      return updated
    },
    [authorizedRequest, allCustomers],
  )

  const deleteCustomer = useCallback(
    async (id: number) => {
      await customersApi.deleteCustomer(authorizedRequest, id)
      setAllCustomers((prev) => prev.filter((customer) => customer.id !== id))
    },
    [authorizedRequest],
  )

  const orgCustomers = useMemo(() => {
    if (organizationId == null) return []
    return allCustomers
      .filter((customer) => customer.organization === organizationId)
      .sort((a, b) => a.name.localeCompare(b.name))
  }, [allCustomers, organizationId])

  const customers = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    if (!query) return orgCustomers
    return orgCustomers.filter((customer) =>
      `${customer.name} ${customer.email} ${customer.company}`.toLowerCase().includes(query),
    )
  }, [orgCustomers, searchQuery])

  const value = useMemo<CustomersContextValue>(
    () => ({
      status,
      customers,
      hasAny: orgCustomers.length > 0,
      searchQuery,
      setSearchQuery,
      createCustomer,
      updateCustomer,
      deleteCustomer,
      reload,
    }),
    [
      status,
      customers,
      orgCustomers.length,
      searchQuery,
      createCustomer,
      updateCustomer,
      deleteCustomer,
      reload,
    ],
  )

  return <CustomersContext value={value}>{children}</CustomersContext>
}
