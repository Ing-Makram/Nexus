import { useState } from 'react'
import { useCustomers } from '../customers/useCustomers'
import { CustomerForm } from './CustomerForm'
import { CustomerList } from './CustomerList'
import { SearchInput } from './SearchInput'

export function CustomerManager() {
  const { createCustomer, hasAny, searchQuery, setSearchQuery } = useCustomers()
  const [adding, setAdding] = useState(false)

  return (
    <section className="customers section" aria-label="Customers">
      <div className="section__head">
        <h2>Customers</h2>
        {!adding && (
          <button type="button" className="btn btn--primary" onClick={() => setAdding(true)}>
            Add customer
          </button>
        )}
      </div>

      {hasAny && (
        <SearchInput
          label="Search customers"
          placeholder="Name, email or company"
          value={searchQuery}
          onChange={setSearchQuery}
        />
      )}

      {adding && (
        <CustomerForm
          submitLabel="Add customer"
          busyLabel="Adding…"
          resetOnSuccess
          onCancel={() => setAdding(false)}
          onSubmit={async (input) => {
            await createCustomer(input)
          }}
        />
      )}

      <CustomerList />
    </section>
  )
}
