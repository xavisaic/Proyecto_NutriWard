import { Card, CardContent, Stack, Typography } from '@mui/material'
import { ReactNode } from 'react'

interface SectionCardProps {
  children: ReactNode
  title?: string
  description?: string
  actions?: ReactNode
  labelledBy?: string
}

export function SectionCard({ children, title, description, actions, labelledBy }: SectionCardProps) {
  const titleId = labelledBy ?? (title ? `section-${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}` : undefined)
  return (
    <Card component="section" variant="outlined" aria-labelledby={title ? titleId : undefined}>
      <CardContent>
        {(title || description || actions) && (
          <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={1.5} sx={{ mb: 2 }}>
            <div>
              {title && <Typography id={titleId} component="h2" variant="h6">{title}</Typography>}
              {description && <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>{description}</Typography>}
            </div>
            {actions}
          </Stack>
        )}
        {children}
      </CardContent>
    </Card>
  )
}
