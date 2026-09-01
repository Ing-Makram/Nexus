import type { ReactNode } from 'react'
import { useOrganizations } from '../organizations/useOrganizations'
import { CreateOrganizationForm } from './CreateOrganizationForm'

/**
 * Gate for the organization workspace: renders its children only once the user
 * has at least one organization and one is selected as current. Otherwise it
 * shows the matching loading / error / first-run state.
 */
export function RequireOrganization({ children }: { children: ReactNode }) {
  const { status, organizations, currentOrganization } = useOrganizations()

  if (status === 'loading') {
    return <p className="auth-status">Loading organizations…</p>
  }
  if (status === 'error') {
    return (
      <p role="alert" className="auth-error">
        Could not load your organizations.
      </p>
    )
  }
  if (organizations.length === 0) {
    return (
      <section className="org-empty card">
        <h2>Create your first organization</h2>
        <p>You need an organization to continue.</p>
        <CreateOrganizationForm />
      </section>
    )
  }
  if (!currentOrganization) {
    return <p className="auth-status">Select an organization to continue.</p>
  }
  return <>{children}</>
}
