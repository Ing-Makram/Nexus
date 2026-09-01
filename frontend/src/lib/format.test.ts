import { afterEach, expect, test, vi } from 'vitest'
import { daysUntil, formatAmount, formatDate } from './format'

// This file runs under Node (Vitest), not the browser - `process` isn't part
// of the app's ambient types (the app never ships to Node), so it's declared
// narrowly here rather than adding Node globals project-wide.
declare const process: { env: Record<string, string | undefined> }

/**
 * Run `fn` with the process timezone temporarily forced to `tz` and a fresh
 * copy of the module (so its module-level `Intl.DateTimeFormat` is
 * constructed under that timezone too), then restore both.
 */
async function withTimezone<T>(tz: string, fn: (mod: typeof import('./format')) => T): Promise<T> {
  const original = process.env.TZ
  process.env.TZ = tz
  vi.resetModules()
  try {
    const mod = await import('./format')
    return fn(mod)
  } finally {
    process.env.TZ = original
    vi.resetModules()
  }
}

afterEach(() => {
  vi.resetModules()
})

test('formatAmount groups and pads to two decimals', () => {
  expect(formatAmount('1234.5')).toBe('1,234.50')
  expect(formatAmount('0')).toBe('0.00')
  expect(formatAmount(99)).toBe('99.00')
})

test('formatAmount returns non-numeric input unchanged', () => {
  expect(formatAmount('n/a')).toBe('n/a')
})

test('formatDate renders a readable date and handles empty/invalid values', () => {
  expect(formatDate('2026-03-05')).toMatch(/2026/)
  expect(formatDate(null)).toBe('—')
  expect(formatDate('')).toBe('—')
  expect(formatDate('not-a-date')).toBe('not-a-date')
})

test('daysUntil is 0 for today and negative for the past', () => {
  const today = new Date().toISOString().slice(0, 10)
  expect(daysUntil(today)).toBe(0)
  expect(daysUntil('2000-01-01')).toBeLessThan(0)
  expect(daysUntil(null)).toBeNull()
})

// A plain "YYYY-MM-DD" date (issue_date / due_date) has no timezone of its
// own. `new Date("2026-03-05")` parses it as UTC midnight, which is the
// *previous* calendar day almost everywhere west of UTC - so naively it would
// render one day early and could flip an invoice to "overdue" a day sooner
// than the date it was actually assigned. These pin the West/East cases.
test('a date-only string renders as its own calendar day west of UTC', async () => {
  await withTimezone('America/New_York', async ({ formatDate }) => {
    const text = formatDate('2026-03-05')
    expect(text).toContain('5')
    expect(text).not.toContain('Mar 4')
  })
})

test('a date-only string renders as its own calendar day east of UTC', async () => {
  await withTimezone('Asia/Tokyo', async ({ formatDate }) => {
    expect(formatDate('2026-03-05')).toContain('5')
  })
})

test('daysUntil treats a date-only due date as that calendar day, not a UTC instant', () => {
  const original = process.env.TZ
  process.env.TZ = 'America/New_York'
  try {
    // "Now" pinned to noon Eastern on 5 March - unambiguously today there.
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 2, 5, 12, 0, 0))
    expect(daysUntil('2026-03-05')).toBe(0)
    expect(daysUntil('2026-03-06')).toBe(1)
    expect(daysUntil('2026-03-04')).toBe(-1)
  } finally {
    vi.useRealTimers()
    process.env.TZ = original
  }
})
