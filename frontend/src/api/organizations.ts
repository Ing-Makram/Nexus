import type { AuthorizedRequest } from '../auth/context'
import type { AssignableRole, Organization, OrganizationMember } from '../types/organization'

export function listOrganizations(request: AuthorizedRequest): Promise<Organization[]> {
  return request<Organization[]>('/organizations/')
}

export function createOrganization(
  request: AuthorizedRequest,
  name: string,
): Promise<Organization> {
  return request<Organization>('/organizations/', { method: 'POST', body: { name } })
}

export function updateOrganization(
  request: AuthorizedRequest,
  id: number,
  name: string,
): Promise<Organization> {
  return request<Organization>(`/organizations/${id}/`, { method: 'PATCH', body: { name } })
}

export function deleteOrganization(request: AuthorizedRequest, id: number): Promise<void> {
  return request<void>(`/organizations/${id}/`, { method: 'DELETE' })
}

// --- Members ---------------------------------------------------------------

export function listMembers(
  request: AuthorizedRequest,
  organizationId: number,
): Promise<OrganizationMember[]> {
  return request<OrganizationMember[]>(`/organizations/${organizationId}/members/`)
}

export function addMember(
  request: AuthorizedRequest,
  organizationId: number,
  email: string,
  role: AssignableRole,
): Promise<OrganizationMember> {
  return request<OrganizationMember>(`/organizations/${organizationId}/members/`, {
    method: 'POST',
    body: { email, role },
  })
}

export function changeMemberRole(
  request: AuthorizedRequest,
  organizationId: number,
  userId: number,
  role: AssignableRole,
): Promise<OrganizationMember> {
  return request<OrganizationMember>(`/organizations/${organizationId}/members/${userId}/`, {
    method: 'PATCH',
    body: { role },
  })
}

export function removeMember(
  request: AuthorizedRequest,
  organizationId: number,
  userId: number,
): Promise<void> {
  return request<void>(`/organizations/${organizationId}/members/${userId}/`, {
    method: 'DELETE',
  })
}
