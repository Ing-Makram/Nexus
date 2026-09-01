const CURRENT_ORG_KEY = 'nexus.org.current'

export function readCurrentOrganizationId(): number | null {
  try {
    const raw = localStorage.getItem(CURRENT_ORG_KEY)
    if (!raw) return null
    const parsed = Number(raw)
    return Number.isInteger(parsed) ? parsed : null
  } catch {
    return null
  }
}

export function writeCurrentOrganizationId(id: number | null): void {
  try {
    if (id === null) {
      localStorage.removeItem(CURRENT_ORG_KEY)
    } else {
      localStorage.setItem(CURRENT_ORG_KEY, String(id))
    }
  } catch {
    // Storage unavailable - the selection just will not persist across reloads.
  }
}
