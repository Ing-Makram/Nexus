import type { AccessTokenResponse, AuthUser, LoginResponse, RegisterPayload } from '../types/auth'
import { apiRequest } from './client'

export function login(email: string, password: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>('/auth/login/', {
    method: 'POST',
    body: { email, password },
  })
}

export function register(payload: RegisterPayload): Promise<LoginResponse> {
  return apiRequest<LoginResponse>('/auth/register/', {
    method: 'POST',
    body: payload,
  })
}

/**
 * Blacklist the caller's refresh token server-side. Requires the access token
 * (the endpoint is authenticated). Returns 205 with no body on success.
 */
export function logout(accessToken: string | null, refreshToken: string): Promise<void> {
  return apiRequest<void>('/auth/logout/', {
    method: 'POST',
    body: { refresh: refreshToken },
    accessToken,
  })
}

export function refresh(refreshToken: string): Promise<AccessTokenResponse> {
  return apiRequest<AccessTokenResponse>('/auth/refresh/', {
    method: 'POST',
    body: { refresh: refreshToken },
  })
}

export function me(accessToken: string): Promise<AuthUser> {
  return apiRequest<AuthUser>('/auth/me/', { accessToken })
}
