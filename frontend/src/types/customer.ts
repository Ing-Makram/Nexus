export interface Customer {
  id: number
  organization: number
  name: string
  email: string
  phone: string
  company: string
  address: string
  created_at: string
  updated_at: string
}

/** Editable customer fields sent to the API. */
export interface CustomerInput {
  name: string
  email?: string
  phone?: string
  company?: string
  address?: string
}
