import { useContext } from 'react'
import { OrganizationsContext, type OrganizationsContextValue } from './context'

export function useOrganizations(): OrganizationsContextValue {
  const context = useContext(OrganizationsContext)
  if (!context) {
    throw new Error('useOrganizations must be used within an <OrganizationsProvider>')
  }
  return context
}
