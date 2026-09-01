/**
 * Shallow diff for flat PATCH payloads.
 *
 * Returns only the keys of `next` whose value differs from `original`. The
 * Customers, Orders and Invoices providers all need the exact same "send just
 * what changed" logic on update, so it lives here once rather than being copied
 * three times. It is deliberately tiny and has no feature knowledge: callers
 * pass an `*Input` object as `next`, so `organization`, `id`, timestamps and
 * `created_by` are never part of the comparison and can never be sent.
 */
export function changedFields<T extends object>(original: Partial<T>, next: T): Partial<T> {
  const patch: Partial<T> = {}
  for (const key of Object.keys(next) as (keyof T)[]) {
    if (!Object.is(next[key], original[key])) {
      patch[key] = next[key]
    }
  }
  return patch
}
