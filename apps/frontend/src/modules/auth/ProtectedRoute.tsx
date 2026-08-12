import { Redirect } from 'wouter'

import { LoadingState } from '../../shared/components'
import { useAuth } from './AuthContext'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isLoading, session } = useAuth()

  if (isLoading) {
    return (
      <div style={{ maxWidth: 960, margin: '0 auto', padding: 32 }}>
        <LoadingState label="Cargando sesión" rows={4} />
      </div>
    )
  }
  return session ? children : <Redirect to="/login" replace />
}
