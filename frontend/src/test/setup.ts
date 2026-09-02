import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { afterEach, vi } from 'vitest'

afterEach(() => {
  cleanup()
})

// Recharts' ResponsiveContainer measures its parent, which is 0x0 under jsdom,
// so charts never draw. Give it a fixed size in tests.
vi.mock('recharts', async (importActual) => {
  const actual = await importActual<typeof import('recharts')>()
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactNode }) =>
      createElement('div', { style: { width: 800, height: 240 } }, children),
  }
})
