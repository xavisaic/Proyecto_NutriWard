import { Box, Button, Container, Paper, Stack, Typography } from '@mui/material'

export function HomePage() {
  return (
    <Container maxWidth="md" sx={{ py: 6 }}>
      <Paper elevation={2} sx={{ p: 4 }}>
        <Stack spacing={2}>
          <Typography variant="h4" fontWeight={700}>
            NutriWard · Fase 2 Bootstrap
          </Typography>
          <Typography color="text.secondary">
            Base técnica inicial: React + TypeScript + Vite + MUI conectable al backend FastAPI.
          </Typography>
          <Box>
            <Button variant="contained">Ir al login (próxima iteración)</Button>
          </Box>
        </Stack>
      </Paper>
    </Container>
  )
}
