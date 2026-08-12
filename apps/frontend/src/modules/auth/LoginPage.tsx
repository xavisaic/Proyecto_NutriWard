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
import { HeartPulse, LockKeyhole, ShieldCheck } from 'lucide-react'
import { Redirect, useLocation } from 'wouter'

import { ApiError } from '../../shared/services/api'
import { AppearanceMenu } from '../../shared/components'
import { useAuth } from './AuthContext'

export function LoginPage() {
  const { isLoading, login, session } = useAuth()
  const [, navigate] = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!isLoading && session) return <Redirect to="/" replace />

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'No fue posible conectar con NutriWard.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Box
      component="main"
      sx={(theme) => ({
        minHeight: '100vh',
        position: 'relative',
        display: 'grid',
        alignItems: 'center',
        bgcolor: 'background.default',
        backgroundImage: `linear-gradient(135deg, ${theme.nutriward.colors.primary.light} 0%, transparent 42%), linear-gradient(315deg, ${theme.nutriward.colors.secondary.light} 0%, transparent 38%)`,
        py: { xs: 3, md: 5 },
      })}
    >
      <Box sx={{ position: 'absolute', top: { xs: 12, sm: 20 }, right: { xs: 12, sm: 20 } }}>
        <AppearanceMenu />
      </Box>
      <Container maxWidth="md">
        <Paper
          elevation={0}
          sx={(theme) => ({
            overflow: 'hidden',
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: { xs: 2, md: 3 },
            boxShadow: theme.nutriward.shadows.medium,
          })}
        >
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '0.9fr 1.1fr' } }}>
            <Stack
              spacing={3}
              justifyContent="space-between"
              sx={(theme) => ({
                p: { xs: 3, md: 5 },
                color: 'primary.contrastText',
                bgcolor: 'primary.dark',
                backgroundImage: `linear-gradient(160deg, ${theme.nutriward.colors.primary.main}, ${theme.nutriward.colors.primary.dark})`,
              })}
            >
              <Box>
                <Stack direction="row" spacing={1.25} alignItems="center">
                  <Box
                    aria-hidden="true"
                    sx={{ display: 'grid', placeItems: 'center', width: 44, height: 44, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.14)' }}
                  >
                    <ShieldCheck size={26} />
                  </Box>
                  <Typography variant="h4" component="div" color="inherit">NutriWard</Typography>
                </Stack>
                <Typography variant="h5" component="p" color="inherit" sx={{ mt: 4, maxWidth: 320 }}>
                  Cuidado nutricional conectado con la realidad hospitalaria.
                </Typography>
                <Typography sx={{ mt: 1.5, opacity: 0.82, maxWidth: 360 }}>
                  Información operacional clara para acompañar decisiones clínicas seguras y oportunas.
                </Typography>
              </Box>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ opacity: 0.78 }}>
                <HeartPulse size={18} aria-hidden="true" />
                <Typography variant="caption">Entorno clínico protegido</Typography>
              </Stack>
            </Stack>

            <Box
              component="form"
              onSubmit={handleSubmit}
              aria-labelledby="login-title"
              sx={{ p: { xs: 3, sm: 4, md: 5 }, bgcolor: 'background.paper' }}
            >
              <Stack spacing={2.5}>
                <Box>
                  <Stack direction="row" spacing={1.25} alignItems="center">
                    <LockKeyhole size={21} color="currentColor" aria-hidden="true" />
                    <Typography id="login-title" variant="h5" component="h1">Iniciar sesión</Typography>
                  </Stack>
                  <Typography color="text.secondary" sx={{ mt: 0.75 }}>
                    Ingresa con tus credenciales institucionales.
                  </Typography>
                </Box>
                {error && <Alert severity="error">{error}</Alert>}
                <TextField
                  label="Correo"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  autoComplete="username"
                  autoFocus
                  required
                  fullWidth
                  disabled={isSubmitting}
                />
                <TextField
                  label="Contraseña"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                  required
                  fullWidth
                  disabled={isSubmitting}
                />
                <Button type="submit" variant="contained" size="large" disabled={isSubmitting} sx={{ minHeight: 46 }}>
                  {isSubmitting ? (
                    <Stack direction="row" spacing={1} alignItems="center">
                      <CircularProgress size={19} color="inherit" />
                      <span>Ingresando…</span>
                    </Stack>
                  ) : 'Ingresar'}
                </Button>
              </Stack>
            </Box>
          </Box>
        </Paper>
      </Container>
    </Box>
  )
}
