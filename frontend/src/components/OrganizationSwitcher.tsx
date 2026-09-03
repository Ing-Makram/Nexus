import { useOrganizations } from '../organizations/useOrganizations'

export function OrganizationSwitcher() {
  const { organizations, currentOrganization, selectOrganization } = useOrganizations()

  if (organizations.length === 0) {
    return null
  }

  return (
    <label className="org-switcher">
      <span className="org-switcher__label">Organization</span>
      <select
        value={currentOrganization?.id ?? ''}
        onChange={(event) => selectOrganization(Number(event.target.value))}
      >
        {organizations.map((org) => (
          <option key={org.id} value={org.id}>
            {org.name}
          </option>
        ))}
      </select>
    </label>
  )
}
