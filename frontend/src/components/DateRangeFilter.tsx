interface DateRangeFilterProps {
  /** What the dates apply to, e.g. "order date" or "issue date". */
  legend: string
  from: string | null
  to: string | null
  onChange: (from: string | null, to: string | null) => void
}

/**
 * A "from / to" date pair shared by the Orders and Invoices lists. It only
 * reports the selected range; the provider owns the (server-side) refetch.
 */
export function DateRangeFilter({ legend, from, to, onChange }: DateRangeFilterProps) {
  const clearable = from !== null || to !== null
  return (
    <fieldset className="date-filter">
      <legend>Filter by {legend}</legend>
      <label>
        From
        <input
          type="date"
          value={from ?? ''}
          max={to ?? undefined}
          onChange={(event) => onChange(event.target.value || null, to)}
        />
      </label>
      <label>
        To
        <input
          type="date"
          value={to ?? ''}
          min={from ?? undefined}
          onChange={(event) => onChange(from, event.target.value || null)}
        />
      </label>
      {clearable && (
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() => onChange(null, null)}
        >
          Clear
        </button>
      )}
    </fieldset>
  )
}
