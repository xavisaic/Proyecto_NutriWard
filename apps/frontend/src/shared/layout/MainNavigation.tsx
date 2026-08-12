import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Stack,
  Typography,
} from '@mui/material'
import { LucideIcon, ShieldCheck, X } from 'lucide-react'
import { ReactNode } from 'react'

export interface AppNavigationItem<Module extends string = string> {
  id: Module
  label: string
  description: string
  icon: LucideIcon
}

interface MainNavigationProps<Module extends string> {
  items: AppNavigationItem<Module>[]
  activeModule: Module
  onNavigate: (module: Module) => void
  onClose?: () => void
  footer?: ReactNode
}

export function MainNavigation<Module extends string>({ items, activeModule, onNavigate, onClose, footer }: MainNavigationProps<Module>) {
  return (
    <Stack sx={{ height: '100%', minHeight: 0 }}>
      <Stack direction="row" spacing={1.25} alignItems="center" sx={{ px: 2.5, minHeight: 72 }}>
        <Box
          aria-hidden="true"
          sx={{
            display: 'grid',
            placeItems: 'center',
            width: 38,
            height: 38,
            borderRadius: 2,
            bgcolor: 'primary.main',
            color: 'primary.contrastText',
          }}
        >
          <ShieldCheck size={22} />
        </Box>
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Typography variant="h6" component="div" lineHeight={1.1}>NutriWard</Typography>
          <Typography variant="caption" color="text.secondary">Gestión nutricional clínica</Typography>
        </Box>
        {onClose && (
          <IconButton aria-label="Cerrar navegación" onClick={onClose}>
            <X size={19} aria-hidden="true" />
          </IconButton>
        )}
      </Stack>

      <Box component="nav" aria-label="Navegación principal" sx={{ px: 1.5, pt: 1, overflowY: 'auto' }}>
        <Typography variant="overline" color="text.secondary" sx={{ px: 1.5 }}>Módulos</Typography>
        <List disablePadding sx={{ mt: 0.5 }}>
          {items.map((item) => {
            const Icon = item.icon
            const selected = item.id === activeModule
            return (
              <ListItem key={item.id} disablePadding sx={{ mb: 0.5 }}>
                <ListItemButton
                  component="button"
                  type="button"
                  selected={selected}
                  aria-current={selected ? 'page' : undefined}
                  onClick={() => onNavigate(item.id)}
                  sx={{
                    width: '100%',
                    border: 0,
                    borderRadius: 2,
                    textAlign: 'left',
                    '&.Mui-selected': {
                      color: 'primary.dark',
                      bgcolor: 'primary.light',
                      '&:hover': { bgcolor: 'primary.light' },
                    },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 38, color: selected ? 'primary.main' : 'text.secondary' }}>
                    <Icon size={20} aria-hidden="true" />
                  </ListItemIcon>
                  <ListItemText
                    primary={item.label}
                    secondary={item.description}
                    primaryTypographyProps={{ fontWeight: selected ? 760 : 680, fontSize: '0.875rem' }}
                    secondaryTypographyProps={{ fontSize: '0.7rem', lineHeight: 1.3, noWrap: true }}
                  />
                </ListItemButton>
              </ListItem>
            )
          })}
        </List>
      </Box>

      <Box sx={{ mt: 'auto', px: 3, py: 2.5 }}>
        {footer}
        <Typography variant="caption" color="text.secondary">
          Entorno clínico · Acceso según rol
        </Typography>
      </Box>
    </Stack>
  )
}
