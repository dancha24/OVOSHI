import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth, canAccessLeaderCabinet, canManageSettings } from './hooks/useAuth'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Profile from './pages/Profile'
import AdminSettings from './pages/AdminSettings'
import AdminParticipants from './pages/AdminParticipants'
import AdminApplications from './pages/AdminApplications'
import AdminShopLots from './pages/AdminShopLots'
import LeaderCabinetEntry from './pages/LeaderCabinetEntry'

function ProtectedRoute({ children, requireLeader }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center p-5 text-muted">
        <span className="spinner-border spinner-border-sm me-2" role="status" />
        Загрузка…
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  if (user.role === 'guest') return <Navigate to="/login?cabinet_guest=1" replace />
  if (requireLeader && !canAccessLeaderCabinet(user)) return <Navigate to="/profile" replace />
  return children
}

function RequireManageSettings({ children }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center p-5 text-muted">
        <span className="spinner-border spinner-border-sm me-2" role="status" />
        Загрузка…
      </div>
    )
  }
  if (!canManageSettings(user)) return <Navigate to="/profile" replace />
  return children
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Landing />} />
          <Route path="login" element={<Login />} />
          <Route path="profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
          <Route
            path="leader"
            element={(
              <ProtectedRoute requireLeader>
                <LeaderCabinetEntry />
              </ProtectedRoute>
            )}
          />
          <Route
            path="leader/settings"
            element={(
              <ProtectedRoute requireLeader>
                <RequireManageSettings><AdminSettings /></RequireManageSettings>
              </ProtectedRoute>
            )}
          />
          <Route path="leader/participants" element={<ProtectedRoute requireLeader><AdminParticipants /></ProtectedRoute>} />
          <Route path="leader/lots" element={<ProtectedRoute requireLeader><AdminShopLots /></ProtectedRoute>} />
          <Route path="leader/applications" element={<ProtectedRoute requireLeader><AdminApplications /></ProtectedRoute>} />
          <Route path="admin/settings" element={<Navigate to="/leader/settings" replace />} />
          <Route path="admin/participants" element={<Navigate to="/leader/participants" replace />} />
          <Route path="admin/applications" element={<Navigate to="/leader/applications" replace />} />
          <Route path="admin/lots" element={<Navigate to="/leader/lots" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </AuthProvider>
  )
}
