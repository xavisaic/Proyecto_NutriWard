import {
  AppBar,
  Avatar,
  Box,
  Button,
  Chip,
  Container,
  Paper,
  Stack,
  Tab,
  Tabs,
  Toolbar,
  Typography,
} from '@mui/material'
import { LogOut, ShieldCheck } from 'lucide-react'
import { useState } from 'react'

import { AdministrationDashboard } from '../modules/administration/AdministrationDashboard'
import { useAuth } from '../modules/auth/AuthContext'
import { HospitalDashboard } from '../modules/hospital/HospitalDashboard'

export function HomePage() {
  const { logout, session } = useAuth()
  const user = session!.user
  const canEdit = user.roles.some((role) => role === 'administrador' || role === 'jefatura')
  const canDelete = user.roles.includes('administrador')
  const canReadAdministration = user.roles.some(
    (role) => role === 'administrador' || role === 'jefatura',
  )
  const [module, setModule] = useState<'hospital' | 'administration'>('hospital')

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#f7f9fa' }}>
      <AppBar
        position="static"
        color="inherit"
        elevation={0}
        sx={{ borderBottom: '1px solid', borderColor: 'divider' }}
      >
        <Toolbar sx={{ gap: 2, minHeight: 68 }}>
          <ShieldCheck size={24} color="#126b5b" aria-hidden="true" />
          <Typography variant="h6" component="div" fontWeight={750} sx={{ flexGrow: 1 }}>
            NutriWard
          </Typography>
          <Stack
            direction="row"
            spacing={1.25}
            alignItems="center"
            sx={{ display: { xs: 'none', sm: 'flex' } }}
          >
            <Avatar sx={{ width: 34, height: 34, bgcolor: 'primary.main', fontSize: 15 }}>
              {user.full_name.charAt(0)}
            </Avatar>
            <Box>
              <Typography variant="body2" component="h2" fontWeight={750} lineHeight={1.2}>
                {user.full_name}
              </Typography>
              <Typography variant="caption" color="text.secondary" lineHeight={1.1}>
                {user.email}
              </Typography>
              <Stack direction="row" spacing={0.5} sx={{ mt: 0.25 }}>
                {user.roles.map((role) => (
                  <Chip
                    key={role}
                    label={role}
                    size="small"
                    variant="outlined"
                    sx={{ height: 19, fontSize: 10 }}
                  />
                ))}
              </Stack>
            </Box>
          </Stack>
          <Button onClick={() => void logout()} color="inherit" startIcon={<LogOut size={18} />}>
            Cerrar sesión
          </Button>
        </Toolbar>
      </AppBar>

      <Container component="main" maxWidth="xl" sx={{ py: { xs: 3, md: 5 } }}>
        {canReadAdministration && (
          <Paper variant="outlined" sx={{ mb: 3 }}>
            <Tabs
              value={module}
              onChange={(_, nextModule) => setModule(nextModule)}
              aria-label="Módulos de NutriWard"
            >
              <Tab value="hospital" label="Estructura hospitalaria" />
              <Tab value="administration" label="Administración" />
            </Tabs>
          </Paper>
        )}
        {module === 'hospital' ? (
          <HospitalDashboard
            canEdit={canEdit}
            canDelete={canDelete}
            csrfToken={session!.csrf_token}
          />
        ) : (
          <AdministrationDashboard
            canManage={canDelete}
            csrfToken={session!.csrf_token}
          />
        )}
      </Container>
    </Box>
  )
}
