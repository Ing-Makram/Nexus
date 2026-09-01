export interface AuthUser {
  id: number
  email: string
  first_name: string
  last_name: string
  is_active: boolean
  date_joined: string
}

export interface TokenPair {
  access: string
  refresh: string
}

export interface LoginResponse extends TokenPair {
  user: AuthUser
}

export interface RegisterPayload {
  email: string
  password: string
  first_name?: string
  last_name?: string
}

export interface AccessTokenResponse {
  access: string
}
