import { Alert, Box, Button, Skeleton, Stack, Typography } from '@mui/material'
import { CircleAlert, Inbox, RotateCcw } from 'lucide-react'
import { ReactNode } from 'react'

export function EmptyState({
  title,
  description,
  action,
  icon = <Inbox size={28} />,
}: {
  title: string
  description?: string
  action?: ReactNode
  icon?: ReactNode
}) {
  return (
    <Box sx={{ py: { xs: 4, md: 5 }, px: 2, textAlign: 'center' }}>
      <Box aria-hidden="true" sx={{ color: 'text.secondary', mb: 1 }}>{icon}</Box>
      <Typography variant="h6" component="h2">{title}</Typography>
      {description && <Typography color="text.secondary" sx={{ mt: 0.5 }}>{description}</Typography>}
      {action && <Box sx={{ mt: 2 }}>{action}</Box>}
    </Box>
  )
}

export function LoadingState({ label = 'Cargando contenido', rows = 3 }: { label?: string; rows?: number }) {
  return (
    <Stack role="status" aria-label={label} spacing={1.5} sx={{ py: 1 }}>
      <Skeleton variant="rounded" height={72} animation="wave" />
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} variant="rounded" height={116} animation="wave" />
      ))}
      <Typography variant="caption" color="text.secondary" sx={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden' }}>
        {label}…
      </Typography>
    </Stack>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Alert
      severity="error"
      icon={<CircleAlert size={20} aria-hidden="true" />}
      action={onRetry ? (
        <Button color="inherit" size="small" startIcon={<RotateCcw size={16} />} onClick={onRetry}>
          Reintentar
        </Button>
      ) : undefined}
    >
      {message}
    </Alert>
  )
}
