import {
  IconButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Tooltip,
} from '@mui/material'
import { Check, Monitor, Moon, Sun } from 'lucide-react'
import { MouseEvent, useState } from 'react'

import { AppearancePreference, useAppearance } from '../../app/theme/AppearanceContext'

const options: Array<{
  value: AppearancePreference
  label: string
  description: string
  icon: typeof Sun
}> = [
  { value: 'light', label: 'Claro', description: 'Fondo claro para uso habitual', icon: Sun },
  { value: 'dark', label: 'Oscuro', description: 'Menor luminancia ambiental', icon: Moon },
  { value: 'system', label: 'Según el sistema', description: 'Sigue la preferencia del dispositivo', icon: Monitor },
]

export function AppearanceMenu() {
  const { preference, resolvedMode, setPreference } = useAppearance()
  const [anchor, setAnchor] = useState<HTMLElement | null>(null)
  const CurrentIcon = resolvedMode === 'dark' ? Moon : Sun

  function choose(nextPreference: AppearancePreference) {
    setPreference(nextPreference)
    setAnchor(null)
  }

  return (
    <>
      <Tooltip title={`Apariencia: ${preference === 'system' ? 'Según el sistema' : preference === 'dark' ? 'Oscuro' : 'Claro'}`}>
        <IconButton
          aria-label="Cambiar apariencia"
          aria-haspopup="menu"
          aria-expanded={Boolean(anchor)}
          onClick={(event: MouseEvent<HTMLButtonElement>) => setAnchor(event.currentTarget)}
        >
          <CurrentIcon size={19} aria-hidden="true" />
        </IconButton>
      </Tooltip>
      <Menu
        anchorEl={anchor}
        open={Boolean(anchor)}
        onClose={() => setAnchor(null)}
        MenuListProps={{ 'aria-label': 'Preferencia de apariencia' }}
      >
        {options.map((option) => {
          const Icon = option.icon
          const selected = preference === option.value
          return (
            <MenuItem
              key={option.value}
              role="menuitemradio"
              aria-checked={selected}
              selected={selected}
              onClick={() => choose(option.value)}
              sx={{ minWidth: 260, gap: 1 }}
            >
              <ListItemIcon><Icon size={18} aria-hidden="true" /></ListItemIcon>
              <ListItemText primary={option.label} secondary={option.description} />
              {selected && <Check size={17} aria-label="Seleccionado" />}
            </MenuItem>
          )
        })}
      </Menu>
    </>
  )
}
