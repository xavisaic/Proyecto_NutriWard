import { Box, CircularProgress } from '@mui/material'
import { Redirect } from 'wouter'

import { useAuth } from './AuthContext'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isLoading, session } = useAuth()

  if (isLoading) {
    return (
      <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
        <CircularProgress aria-label="Cargando sesión" size={32} />
      </Box>
    )
  }
  return session ? children : <Redirect to="/login" replace />
}
