import { useState } from 'react'
import { useCustomers } from '../customers/useCustomers'
import { formatAmount, formatDate } from '../lib/format'
import { useOrders } from '../orders/useOrders'
import type { Order } from '../types/order'
import { OrderForm } from './OrderForm'
import { StatusBadge } from './StatusBadge'

interface OrderListProps {
  canManage: boolean
}

export function OrderList({ canManage }: OrderListProps) {
  const { status, orders, statusFilter, updateOrder, deleteOrder } = useOrders()
  const { customers } = useCustomers()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [rowError, setRowError] = useState<string | null>(null)

  const customerName = (id: number) =>
    customers.find((customer) => customer.id === id)?.name ?? `Customer #${id}`

  if (status === 'loading') {
    return <p className="orders__status">Loading orders…</p>
  }
  if (status === 'error') {
    return (
      <p role="alert" className="auth-error">
        Could not load orders.
      </p>
    )
  }
  if (orders.length === 0) {
    return (
      <p className="orders__status empty">
        {statusFilter ? `No ${statusFilter} orders.` : 'No orders yet.'}
      </p>
    )
  }

  async function handleDelete(order: Order) {
    if (!window.confirm(`Delete order #${order.id}? This cannot be undone.`)) {
      return
    }
    setRowError(null)
    setDeletingId(order.id)
    try {
      await deleteOrder(order.id)
    } catch {
      setRowError(`Could not delete order #${order.id}. Please try again.`)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <>
      {rowError && (
        <p role="alert" className="auth-error">
          {rowError}
        </p>
      )}
      <ul className="order-list list">
        {orders.map((order) =>
          canManage && editingId === order.id ? (
            <li key={order.id}>
              <OrderForm
                initial={{
                  customer: String(order.customer),
                  status: order.status,
                  total_amount: order.total_amount,
                  notes: order.notes,
                }}
                submitLabel="Save"
                busyLabel="Saving…"
                onCancel={() => setEditingId(null)}
                onSubmit={async (input) => {
                  await updateOrder(order.id, input)
                  setEditingId(null)
                }}
              />
            </li>
          ) : (
            <li key={order.id} className="order-list__row list__row">
              <div>
                <div className="list__title">
                  <strong>{customerName(order.customer)}</strong>
                  <StatusBadge kind="order" status={order.status} />
                </div>
                <div className="order-list__meta list__meta">
                  {formatAmount(order.total_amount)} · {formatDate(order.created_at)}
                </div>
                {order.notes && <div className="order-list__notes">{order.notes}</div>}
              </div>
              {canManage && (
                <div className="order-list__actions list__actions">
                  <button
                    type="button"
                    className="btn btn--ghost"
                    onClick={() => setEditingId(order.id)}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost"
                    onClick={() => handleDelete(order)}
                    disabled={deletingId === order.id}
                  >
                    {deletingId === order.id ? 'Deleting…' : 'Delete'}
                  </button>
                </div>
              )}
            </li>
          ),
        )}
      </ul>
    </>
  )
}
