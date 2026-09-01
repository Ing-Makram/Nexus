import { useState } from 'react'
import { useOrders } from '../orders/useOrders'
import { useOrganizations } from '../organizations/useOrganizations'
import { ORDER_STATUSES } from '../types/order'
import { OrderForm } from './OrderForm'
import { OrderList } from './OrderList'
import { StatusFilter } from './StatusFilter'

export function OrderManager() {
  const { currentOrganization } = useOrganizations()
  const { createOrder, statusFilter, setStatusFilter } = useOrders()
  const [adding, setAdding] = useState(false)

  const role = currentOrganization?.role
  const canManage = role === 'owner' || role === 'admin'

  return (
    <section className="orders section" aria-label="Orders">
      <div className="section__head">
        <h2>Orders</h2>
        {canManage && !adding && (
          <button type="button" className="btn btn--primary" onClick={() => setAdding(true)}>
            Add order
          </button>
        )}
      </div>

      <StatusFilter statuses={ORDER_STATUSES} value={statusFilter} onChange={setStatusFilter} />

      {canManage && adding && (
        <OrderForm
          submitLabel="Add order"
          busyLabel="Adding…"
          resetOnSuccess
          onCancel={() => setAdding(false)}
          onSubmit={async (input) => {
            await createOrder(input)
          }}
        />
      )}

      <OrderList canManage={canManage} />
    </section>
  )
}
