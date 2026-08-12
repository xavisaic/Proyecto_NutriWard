import { Box, Card, CardContent, Stack, Typography } from '@mui/material'
import { ReactNode } from 'react'

interface StatCardProps {
  label: string
  value: string | number
  icon: ReactNode
  detail?: string
  tone?: 'primary' | 'success' | 'warning' | 'secondary'
}

export function StatCard({ label, value, icon, detail, tone = 'primary' }: StatCardProps) {
  return (
    <Card variant="outlined" sx={{ height: '100%', boxShadow: 'none' }}>
      <CardContent>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <Box
            aria-hidden="true"
            sx={{
              display: 'grid',
              placeItems: 'center',
              width: 40,
              height: 40,
              flex: '0 0 auto',
              borderRadius: 2,
              color: `${tone}.dark`,
              bgcolor: `${tone}.light`,
            }}
          >
            {icon}
          </Box>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="caption" color="text.secondary">{label}</Typography>
            <Typography variant="h5" component="p">{value}</Typography>
            {detail && <Typography variant="caption" color="text.secondary">{detail}</Typography>}
          </Box>
        </Stack>
      </CardContent>
    </Card>
  )
}
