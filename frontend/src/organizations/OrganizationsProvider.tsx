import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import * as orgApi from '../api/organizations'
import type { AuthorizedRequest } from '../auth/context'
import { useAuth } from '../auth/useAuth'
import type { Organization } from '../types/organization'
import {
  OrganizationsContext,
  type OrganizationsContextValue,
  type OrganizationsStatus,
} from './context'
import { readCurrentOrganizationId, writeCurrentOrganizationId } from './storage'

function byName(a: Organization, b: Organization): number {
  return a.name.localeCompare(b.name)
}

async function loadOrganizations(request: AuthorizedRequest): Promise<Organization[]> {
  const list = await orgApi.listOrganizations(request)
  return [...list].sort(byName)
}

export function OrganizationsProvider({ children }: { children: ReactNode }) {
  const { authorizedRequest } = useAuth()
  const [status, setStatus] = useState<OrganizationsStatus>('loading')
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [currentId, setCurrentId] = useState<number | null>(() => readCurrentOrganizationId())

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const list = await loadOrganizations(authorizedRequest)
        if (cancelled) return
        setOrganizations(list)
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
      setOrganizations(await loadOrganizations(authorizedRequest))
      setStatus('ready')
    } catch {
      setStatus('error')
    }
  }, [authorizedRequest])

  const selectOrganization = useCallback((id: number) => {
    setCurrentId(id)
    writeCurrentOrganizationId(id)
  }, [])

  const createOrganization = useCallback(
    async (name: string) => {
      const created = await orgApi.createOrganization(authorizedRequest, name)
      setOrganizations((prev) => [...prev, created].sort(byName))
      setCurrentId(created.id)
      writeCurrentOrganizationId(created.id)
      return created
    },
    [authorizedRequest],
  )

  const renameOrganization = useCallback(
    async (id: number, name: string) => {
      const updated = await orgApi.updateOrganization(authorizedRequest, id, name)
      setOrganizations((prev) =>
        prev.map((org) => (org.id === id ? { ...org, ...updated } : org)).sort(byName),
      )
      return updated
    },
    [authorizedRequest],
  )

  const deleteOrganization = useCallback(
    async (id: number) => {
      await orgApi.deleteOrganization(authorizedRequest, id)
      setOrganizations((prev) => prev.filter((org) => org.id !== id))
      // Clearing currentId lets `currentOrganization` fall back to the first
      // remaining organization (see the memo below).
      setCurrentId((current) => (current === id ? null : current))
      if (readCurrentOrganizationId() === id) {
        writeCurrentOrganizationId(null)
      }
    },
    [authorizedRequest],
  )

  const currentOrganization = useMemo<Organization | null>(() => {
    if (organizations.length === 0) return null
    return organizations.find((org) => org.id === currentId) ?? organizations[0]
  }, [organizations, currentId])

  const value = useMemo<OrganizationsContextValue>(
    () => ({
      status,
      organizations,
      currentOrganization,
      selectOrganization,
      createOrganization,
      renameOrganization,
      deleteOrganization,
      reload,
    }),
    [
      status,
      organizations,
      currentOrganization,
      selectOrganization,
      createOrganization,
      renameOrganization,
      deleteOrganization,
      reload,
    ],
  )

  return <OrganizationsContext value={value}>{children}</OrganizationsContext>
}
