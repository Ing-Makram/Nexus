import { useState } from 'react'
import { useOrders } from '../orders/useOrders'
import { useOrganizations } from '../organizations/useOrganizations'
import { ORDER_STATUSES } from '../types/order'
import { DateRangeFilter } from './DateRangeFilter'
import { OrderForm } from './OrderForm'
import { OrderList } from './OrderList'
import { StatusFilter } from './StatusFilter'

export function OrderManager() {
  const { currentOrganization } = useOrganizations()
  const { createOrder, statusFilter, setStatusFilter, dateFrom, dateTo, setDateRange } = useOrders()
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

      <div className="section__filters">
        <StatusFilter statuses={ORDER_STATUSES} value={statusFilter} onChange={setStatusFilter} />
        <DateRangeFilter legend="order date" from={dateFrom} to={dateTo} onChange={setDateRange} />
      </div>

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
