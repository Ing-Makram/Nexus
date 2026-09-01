interface StatusFilterProps<T extends string> {
  /** Allowed status values (e.g. ORDER_STATUSES, INVOICE_STATUSES). */
  statuses: readonly T[]
  /** Current filter, or `null` for "all statuses". */
  value: T | null
  onChange: (value: T | null) => void
}

/**
 * A tiny "filter by status" select shared by the Orders and Invoices managers.
 * It only reports the selected value; the provider owns the actual (server-side)
 * refetch.
 */
export function StatusFilter<T extends string>({
  statuses,
  value,
  onChange,
}: StatusFilterProps<T>) {
  return (
    <label className="status-filter">
      Filter by status
      <select
        value={value ?? ''}
        onChange={(event) => onChange((event.target.value || null) as T | null)}
      >
        <option value="">All statuses</option>
        {statuses.map((status) => (
          <option key={status} value={status}>
            {status}
          </option>
        ))}
      </select>
    </label>
  )
}
