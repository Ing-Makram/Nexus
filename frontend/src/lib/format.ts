/**
 * Display formatting helpers. The backend stores plain decimal strings; amounts
 * are shown as USD (e.g. `$1,234.50`).
 *
 * The locale is pinned so every member of an organization sees financial
 * figures and dates in exactly the same, unambiguous format.
 */

const LOCALE = 'en-US'

const amountFormatter = new Intl.NumberFormat(LOCALE, {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const dateFormatter = new Intl.DateTimeFormat(LOCALE, {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
})

const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/

/**
 * Parse a value from the API into a `Date`.
 *
 * A plain `YYYY-MM-DD` string (Django `DateField`, e.g. `issue_date` /
 * `due_date`) has no time or timezone component - `new Date("2026-03-05")`
 * would parse it as UTC midnight, which then renders as the *previous*
 * calendar day for anyone west of UTC. Build it from local Y/M/D components
 * instead so the calendar date is what was stored, in every timezone.
 * Anything else (a full ISO datetime, e.g. `created_at`) is a real instant
 * and is parsed normally so it still displays in the viewer's local time.
 */
function parseApiDate(value: string): Date {
  if (DATE_ONLY.test(value)) {
    const [year, month, day] = value.split('-').map(Number)
    return new Date(year, month - 1, day)
  }
  return new Date(value)
}

/** `"1234.5"` -> `"$1,234.50"`. Non-numeric input is returned unchanged. */
export function formatAmount(value: string | number): string {
  const n = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(n) ? amountFormatter.format(n) : String(value)
}

/** ISO date/datetime -> `"5 Mar 2026"`. `null`/invalid -> `"—"` / the raw value. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const date = parseApiDate(value)
  return Number.isNaN(date.getTime()) ? value : dateFormatter.format(date)
}

/**
 * Whole calendar days from today until `value` (negative = in the past),
 * or `null` when there is no usable date.
 */
export function daysUntil(value: string | null | undefined): number | null {
  if (!value) return null
  const date = parseApiDate(value)
  if (Number.isNaN(date.getTime())) return null
  const startOfToday = new Date()
  startOfToday.setHours(0, 0, 0, 0)
  const target = new Date(date)
  target.setHours(0, 0, 0, 0)
  return Math.round((target.getTime() - startOfToday.getTime()) / 86_400_000)
}
