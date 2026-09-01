import { createContext } from 'react'
import type { Organization } from '../types/organization'

export type OrganizationsStatus = 'loading' | 'ready' | 'error'

export interface OrganizationsContextValue {
  status: OrganizationsStatus
  organizations: Organization[]
  currentOrganization: Organization | null
  selectOrganization: (id: number) => void
  createOrganization: (name: string) => Promise<Organization>
  renameOrganization: (id: number, name: string) => Promise<Organization>
  deleteOrganization: (id: number) => Promise<void>
  reload: () => Promise<void>
}

export const OrganizationsContext = createContext<OrganizationsContextValue | null>(null)
