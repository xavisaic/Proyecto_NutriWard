import {
  AppBar,
  Avatar,
  Box,
  Button,
  Chip,
  Drawer,
  IconButton,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material'
import { LogOut, Menu, ShieldCheck } from 'lucide-react'
import { ReactNode, useState } from 'react'

import { User } from '../services/api'
import { AppearanceMenu } from '../components'
import { AppNavigationItem, MainNavigation } from './MainNavigation'

interface AppShellProps<Module extends string> {
  user: User
  items: AppNavigationItem<Module>[]
  activeModule: Module
  onNavigate: (module: Module) => void
  onLogout: () => void
  children: ReactNode
}

export function AppShell<Module extends string>({
  user,
  items,
  activeModule,
  onNavigate,
  onLogout,
  children,
}: AppShellProps<Module>) {
  const theme = useTheme()
  const desktop = useMediaQuery(theme.breakpoints.up('md'))
  const [mobileOpen, setMobileOpen] = useState(false)
  const navigationWidth = theme.nutriward.layout.navigationWidth
  const activeItem = items.find((item) => item.id === activeModule)

  function navigate(module: Module) {
    onNavigate(module)
    setMobileOpen(false)
  }

  const userFooter = (
    <Box sx={{ mb: 2, pb: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
      <Typography variant="body2" fontWeight={760} noWrap>{user.full_name}</Typography>
      <Typography variant="caption" color="text.secondary" display="block" noWrap>{user.email}</Typography>
      <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap" sx={{ mt: 1 }}>
        {user.roles.map((role) => <Chip key={role} label={role} size="small" variant="outlined" />)}
      </Stack>
    </Box>
  )

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <Box
        component="a"
        href="#main-content"
        sx={{
          position: 'fixed',
          zIndex: theme.zIndex.tooltip + 1,
          top: 8,
          left: 8,
          p: 1,
          bgcolor: 'background.paper',
          color: 'primary.dark',
          borderRadius: 1,
          transform: 'translateY(-150%)',
          '&:focus': { transform: 'translateY(0)' },
        }}
      >
        Saltar al contenido
      </Box>

      <AppBar
        position="fixed"
        sx={{ width: { md: `calc(100% - ${navigationWidth}px)` }, ml: { md: `${navigationWidth}px` } }}
      >
        <Toolbar sx={{ minHeight: `${theme.nutriward.layout.appBarHeight}px !important`, gap: 1.5 }}>
          {!desktop && (
            <IconButton edge="start" aria-label="Abrir navegación" onClick={() => setMobileOpen(true)}>
              <Menu aria-hidden="true" />
            </IconButton>
          )}
          {!desktop && <ShieldCheck size={22} color="currentColor" aria-hidden="true" />}
          <Typography variant="subtitle1" component="div" sx={{ flexGrow: 1, minWidth: 0 }} noWrap>
            {activeItem?.label ?? 'NutriWard'}
          </Typography>

          <Stack direction="row" spacing={1} alignItems="center" sx={{ minWidth: 0 }}>
            <Avatar sx={{ width: 34, height: 34, bgcolor: 'primary.main', fontSize: 14 }}>
              {user.full_name.charAt(0).toUpperCase()}
            </Avatar>
            <Box sx={{ display: { xs: 'none', sm: 'block' }, minWidth: 0, maxWidth: 230 }}>
              <Typography variant="body2" component="h2" fontWeight={760} lineHeight={1.2} noWrap>
                {user.full_name}
              </Typography>
              <Typography variant="caption" color="text.secondary" display="block" noWrap>
                {user.email}
              </Typography>
            </Box>
            <Stack direction="row" spacing={0.5} sx={{ display: { xs: 'none', lg: 'flex' } }}>
              {user.roles.map((role) => <Chip key={role} label={role} size="small" variant="outlined" />)}
            </Stack>
            <AppearanceMenu />
            <Tooltip title="Cerrar sesión">
              <IconButton onClick={onLogout} aria-label="Cerrar sesión">
                <LogOut size={19} aria-hidden="true" />
              </IconButton>
            </Tooltip>
          </Stack>
        </Toolbar>
      </AppBar>

      <Box component="aside" aria-label="Barra lateral">
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', md: 'none' },
            '& .MuiDrawer-paper': { width: navigationWidth, boxSizing: 'border-box' },
          }}
        >
          <MainNavigation
            items={items}
            activeModule={activeModule}
            onNavigate={navigate}
            onClose={() => setMobileOpen(false)}
            footer={userFooter}
          />
        </Drawer>
        <Drawer
          variant="permanent"
          open
          sx={{
            display: { xs: 'none', md: 'block' },
            '& .MuiDrawer-paper': { width: navigationWidth, boxSizing: 'border-box' },
          }}
        >
          <MainNavigation items={items} activeModule={activeModule} onNavigate={navigate} />
        </Drawer>
      </Box>

      <Box
        component="main"
        id="main-content"
        tabIndex={-1}
        sx={{
          ml: { md: `${navigationWidth}px` },
          pt: `${theme.nutriward.layout.appBarHeight}px`,
          minWidth: 0,
        }}
      >
        <Box
          sx={{
            width: '100%',
            maxWidth: theme.nutriward.layout.contentMaxWidth,
            mx: 'auto',
            px: { xs: 2, sm: 3, lg: 4 },
            py: { xs: 2.5, md: 3.5 },
          }}
        >
          {children}
        </Box>
      </Box>
    </Box>
  )
}
