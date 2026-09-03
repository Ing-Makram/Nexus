import { useState } from 'react'
import { useAuth } from '../auth/useAuth'
import { CustomerManager } from '../components/CustomerManager'
import { Dashboard } from '../components/Dashboard'
import { InvoiceManager } from '../components/InvoiceManager'
import { OrderManager } from '../components/OrderManager'
import { OrganizationSettings } from '../components/OrganizationSettings'
import { OrganizationSwitcher } from '../components/OrganizationSwitcher'
import { RequireOrganization } from '../components/RequireOrganization'
import { CustomersProvider } from '../customers/CustomersProvider'
import { DashboardProvider } from '../dashboard/DashboardProvider'
import { InvoicesProvider } from '../invoices/InvoicesProvider'
import { OrdersProvider } from '../orders/OrdersProvider'
import { useOrganizations } from '../organizations/useOrganizations'

type View = 'overview' | 'customers' | 'orders' | 'invoices' | 'settings'

const TABS: { id: View; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'customers', label: 'Customers' },
  { id: 'orders', label: 'Orders' },
  { id: 'invoices', label: 'Invoices' },
  { id: 'settings', label: 'Settings' },
]

/**
 * The organization workspace. Each tab mounts its own provider tree, so
 * switching to a tab always shows current data (nothing is fetched until its
 * tab is opened). The form-bearing tabs keep the Customers/Orders providers
 * mounted because the Order and Invoice forms read from them.
 */
function Workspace() {
  const [view, setView] = useState<View>('overview')

  return (
    <>
      <nav className="tabs" aria-label="Sections">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={view === tab.id ? 'tab tab--active' : 'tab'}
            aria-current={view === tab.id ? 'page' : undefined}
            onClick={() => setView(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <div className="workspace-body">
        {view === 'overview' && (
          <DashboardProvider>
            <Dashboard />
          </DashboardProvider>
        )}
        {view === 'customers' && (
          <CustomersProvider>
            <CustomerManager />
          </CustomersProvider>
        )}
        {view === 'orders' && (
          <CustomersProvider>
            <OrdersProvider>
              <OrderManager />
            </OrdersProvider>
          </CustomersProvider>
        )}
        {view === 'invoices' && (
          // OrdersProvider here has no StatusFilter UI, so `useOrders().orders`
          // inside InvoiceForm is the full current-organization order list - the
          // Orders tab's status filter cannot leak into the invoice form.
          <CustomersProvider>
            <OrdersProvider>
              <InvoicesProvider>
                <InvoiceManager />
              </InvoicesProvider>
            </OrdersProvider>
          </CustomersProvider>
        )}
        {view === 'settings' && <OrganizationSettings />}
      </div>
    </>
  )
}

function WorkspaceHeader() {
  const { currentOrganization } = useOrganizations()
  if (!currentOrganization) return null
  return (
    <div className="workspace-head">
      <h1>{currentOrganization.name}</h1>
      <span className="role-pill" title="Your role in this organization">
        {currentOrganization.role}
      </span>
    </div>
  )
}

export function HomePage() {
  const { user, logout } = useAuth()
  const { organizations } = useOrganizations()

  return (
    <div className="app-shell">
      <header className="topbar">
        <span className="topbar__brand">NEXUS</span>
        {organizations.length > 0 && <OrganizationSwitcher />}
        <span className="topbar__user" title={user?.email}>
          {user?.email}
        </span>
        <button type="button" className="btn btn--ghost btn--sm" onClick={() => void logout()}>
          Sign out
        </button>
      </header>

      <main className="app-main">
        <RequireOrganization>
          <WorkspaceHeader />
          <Workspace />
        </RequireOrganization>
      </main>
    </div>
  )
}
