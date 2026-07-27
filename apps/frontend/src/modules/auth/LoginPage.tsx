import { FormEvent, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Container,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { LockKeyhole } from 'lucide-react'
import { Redirect, useLocation } from 'wouter'

import { ApiError } from '../../shared/services/api'
import { useAuth } from './AuthContext'

export function LoginPage() {
  const { isLoading, login, session } = useAuth()
  const [, navigate] = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!isLoading && session) {
    return <Redirect to="/" replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : 'No fue posible conectar con NutriWard.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Box
      component="main"
      sx={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        bgcolor: '#f4f7f9',
        py: 4,
      }}
    >
      <Container maxWidth="xs">
        <Stack spacing={3} alignItems="center">
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="h3" component="h1" fontWeight={750} color="primary.dark">
              NutriWard
            </Typography>
            <Typography color="text.secondary">Gestión nutricional clínica</Typography>
          </Box>

          <Paper
            component="form"
            onSubmit={handleSubmit}
            elevation={0}
            sx={{ width: '100%', p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}
          >
            <Stack spacing={2.5}>
              <Stack direction="row" spacing={1.25} alignItems="center">
                <LockKeyhole size={21} aria-hidden="true" />
                <Typography variant="h6" component="h2">
                  Iniciar sesión
                </Typography>
              </Stack>
              {error && <Alert severity="error">{error}</Alert>}
              <TextField
                label="Correo"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="username"
                required
                fullWidth
              />
              <TextField
                label="Contraseña"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
                fullWidth
              />
              <Button type="submit" variant="contained" size="large" disabled={isSubmitting}>
                {isSubmitting ? <CircularProgress size={24} color="inherit" /> : 'Ingresar'}
              </Button>
            </Stack>
          </Paper>
        </Stack>
      </Container>
    </Box>
  )
}
