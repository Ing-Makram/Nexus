import './App.css'
import { AuthProvider } from './auth/AuthProvider'
import { RequireAuth } from './components/RequireAuth'
import { OrganizationsProvider } from './organizations/OrganizationsProvider'
import { HomePage } from './pages/HomePage'

function App() {
  return (
    <AuthProvider>
      <RequireAuth>
        <OrganizationsProvider>
          <HomePage />
        </OrganizationsProvider>
      </RequireAuth>
    </AuthProvider>
  )
}

export default App
