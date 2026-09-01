import { expect, test } from 'vitest'
import { changedFields } from './changedFields'

test('returns only the keys whose value changed', () => {
  const original = { name: 'Acme', email: 'a@acme.test', phone: '' }
  const next = { name: 'Acme Renamed', email: 'a@acme.test', phone: '' }

  expect(changedFields(original, next)).toEqual({ name: 'Acme Renamed' })
})

test('returns an empty object when nothing changed', () => {
  const shape = { customer: 3, status: 'draft', total_amount: '10.00', notes: '' }

  expect(changedFields(shape, { ...shape })).toEqual({})
})

test('treats a field cleared to an empty string as a real change', () => {
  expect(changedFields({ notes: 'old note' }, { notes: '' })).toEqual({ notes: '' })
})

test('handles numeric and null values', () => {
  const original = { customer: 1, order: 5 as number | null, total_amount: '100.00' }
  const next = { customer: 2, order: null as number | null, total_amount: '100.00' }

  expect(changedFields(original, next)).toEqual({ customer: 2, order: null })
})

test('only compares keys present on `next`', () => {
  const original = { name: 'Acme', id: 99, organization: 1 } as Record<string, unknown>
  const next = { name: 'Acme' }

  expect(changedFields(original, next)).toEqual({})
})
