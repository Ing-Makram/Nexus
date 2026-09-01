type Tone = 'neutral' | 'info' | 'success' | 'danger'

const ORDER_TONES: Record<string, Tone> = {
  draft: 'neutral',
  pending: 'info',
  confirmed: 'info',
  completed: 'success',
  cancelled: 'danger',
}

const INVOICE_TONES: Record<string, Tone> = {
  draft: 'neutral',
  sent: 'info',
  paid: 'success',
  overdue: 'danger',
  void: 'neutral',
}

interface StatusBadgeProps {
  kind: 'order' | 'invoice'
  status: string
}

/** A small coloured pill for an order or invoice status. Text is the raw
 * status value (CSS capitalises it). */
export function StatusBadge({ kind, status }: StatusBadgeProps) {
  const tones = kind === 'order' ? ORDER_TONES : INVOICE_TONES
  const tone = tones[status] ?? 'neutral'
  return <span className={`badge badge--${tone}`}>{status}</span>
}
