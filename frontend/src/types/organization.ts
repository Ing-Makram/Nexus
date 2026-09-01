export type OrganizationRole = 'owner' | 'admin' | 'member'

/** Roles that can be assigned when adding or changing a member (never "owner"). */
export type AssignableRole = 'admin' | 'member'

export interface Organization {
  id: number
  name: string
  role: OrganizationRole | null
  created_at: string
  updated_at: string
}

export interface OrganizationMemberUser {
  id: number
  email: string
  first_name: string
  last_name: string
  is_active: boolean
  date_joined: string
}

export interface OrganizationMember {
  user: OrganizationMemberUser
  role: OrganizationRole
  created_at: string
  updated_at: string
}
