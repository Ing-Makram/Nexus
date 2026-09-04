/** A shimmering placeholder block. Purely presentational. */
export function Skeleton({ width, height = '1rem' }: { width?: string; height?: string }) {
  return <span className="skeleton" style={{ width, height }} aria-hidden="true" />
}

/**
 * A list-shaped loading placeholder that mirrors the row layout, so the real
 * list drops in without a jump. `label` is announced to screen readers.
 */
export function SkeletonRows({ count = 4, label }: { count?: number; label: string }) {
  return (
    <div className="skeleton-list" role="status" aria-live="polite">
      <span className="visually-hidden">{label}</span>
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="skeleton-row" aria-hidden="true">
          <div className="skeleton-row__main">
            <Skeleton width="40%" height="0.95rem" />
            <Skeleton width="60%" height="0.8rem" />
          </div>
          <Skeleton width="4rem" height="0.95rem" />
        </div>
      ))}
    </div>
  )
}

/** A KPI-grid loading placeholder for the dashboard. */
export function SkeletonStats({ label }: { label: string }) {
  return (
    <div className="stat-grid" role="status" aria-live="polite">
      <span className="visually-hidden">{label}</span>
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i} className="stat" aria-hidden="true">
          <Skeleton width="55%" height="1.5rem" />
          <Skeleton width="35%" height="0.75rem" />
        </div>
      ))}
    </div>
  )
}
