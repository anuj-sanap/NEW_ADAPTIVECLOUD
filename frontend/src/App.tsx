// frontend/src/App.tsx
// Root application router.

import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import LoginPage from '@/pages/LoginPage'
import DashboardPage from '@/pages/DashboardPage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.accessToken)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <DashboardPage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

