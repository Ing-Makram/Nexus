// The refresh token is persisted so a page reload keeps the user signed in.
// The short-lived access token is kept only in memory (see AuthProvider).
const REFRESH_TOKEN_KEY = 'nexus.auth.refresh'

export function readRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY)
  } catch {
    return null
  }
}

export function writeRefreshToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(REFRESH_TOKEN_KEY, token)
    } else {
      localStorage.removeItem(REFRESH_TOKEN_KEY)
    }
  } catch {
    // Storage unavailable (private mode, blocked cookies) - session simply
    // will not survive a reload.
  }
}
