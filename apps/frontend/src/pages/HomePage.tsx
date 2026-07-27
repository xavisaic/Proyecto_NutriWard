import { AppBar, Avatar, Box, Button, Chip, Container, Stack, Toolbar, Typography } from '@mui/material'
import { LogOut, ShieldCheck } from 'lucide-react'

import { useAuth } from '../modules/auth/AuthContext'

export function HomePage() {
  const { logout, session } = useAuth()
  const user = session!.user

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#f7f9fa' }}>
      <AppBar position="static" color="inherit" elevation={0} sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
        <Toolbar sx={{ gap: 2 }}>
          <ShieldCheck size={24} color="#126b5b" aria-hidden="true" />
          <Typography variant="h6" component="div" fontWeight={750} sx={{ flexGrow: 1 }}>
            NutriWard
          </Typography>
          <Button onClick={() => void logout()} color="inherit" startIcon={<LogOut size={18} />}>
            Cerrar sesión
          </Button>
        </Toolbar>
      </AppBar>

      <Container component="main" maxWidth="lg" sx={{ py: 5 }}>
        <Stack spacing={4}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'center' }}>
            <Avatar sx={{ width: 52, height: 52, bgcolor: 'primary.main' }}>
              {user.full_name.charAt(0)}
            </Avatar>
            <Box>
              <Typography variant="h4" component="h1" fontWeight={700}>
                {user.full_name}
              </Typography>
              <Typography color="text.secondary">{user.email}</Typography>
            </Box>
          </Stack>

          <Box sx={{ borderTop: '1px solid', borderColor: 'divider', pt: 3 }}>
            <Typography variant="overline" color="text.secondary">
              Roles activos
            </Typography>
            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1 }}>
              {user.roles.map((role) => (
                <Chip key={role} label={role} color="primary" variant="outlined" />
              ))}
            </Stack>
          </Box>
        </Stack>
      </Container>
    </Box>
  )
}
