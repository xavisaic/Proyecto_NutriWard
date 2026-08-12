import { Chip, ChipProps, SxProps, Theme } from '@mui/material'
import { ReactElement } from 'react'

export type StatusTone = 'neutral' | 'success' | 'warning' | 'error' | 'info' | 'transfer'

interface StatusBadgeProps {
  label: string
  tone?: StatusTone
  icon?: ReactElement
  size?: ChipProps['size']
  title?: string
  sx?: SxProps<Theme>
}

export function StatusBadge({ label, tone = 'neutral', icon, size = 'small', title, sx }: StatusBadgeProps) {
  const muiColor = tone === 'neutral' || tone === 'transfer' ? 'default' : tone
  return (
    <Chip
      label={label}
      icon={icon}
      size={size}
      color={muiColor}
      variant="outlined"
      title={title}
      sx={[
        (theme) => ({
          ...(tone === 'neutral' && {
          color: 'text.secondary',
          borderColor: 'divider',
          bgcolor: theme.nutriward.colors.background.subtle,
          }),
          ...(tone === 'transfer' && {
          color: theme.nutriward.colors.transfer.dark,
          borderColor: theme.nutriward.colors.transfer.border,
          bgcolor: theme.nutriward.colors.transfer.light,
          '& .MuiChip-icon': { color: theme.nutriward.colors.transfer.main },
          }),
        }),
        ...(Array.isArray(sx) ? sx : sx ? [sx] : []),
      ]}
    />
  )
}
