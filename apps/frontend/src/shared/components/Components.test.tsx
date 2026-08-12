import { ThemeProvider } from '@mui/material'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CircleCheck } from 'lucide-react'
import { describe, expect, it, vi } from 'vitest'

import { nutriwardTheme } from '../../app/theme/theme'
import { ErrorState, LoadingState, StatusBadge } from './index'

function renderWithTheme(ui: React.ReactElement) {
  return render(<ThemeProvider theme={nutriwardTheme}>{ui}</ThemeProvider>)
}

describe('componentes compartidos de estado', () => {
  it('comunica el estado con texto e icono además del color', () => {
    renderWithTheme(
      <StatusBadge label="Traslado pendiente" tone="transfer" icon={<CircleCheck aria-label="Estado de traslado" />} />,
    )

    expect(screen.getByText('Traslado pendiente')).toBeInTheDocument()
    expect(screen.getByLabelText('Estado de traslado')).toBeInTheDocument()
  })

  it('expone un estado de carga accesible y un reintento operativo', async () => {
    const retry = vi.fn()
    const { rerender } = renderWithTheme(<LoadingState label="Cargando pacientes" rows={2} />)
    expect(screen.getByRole('status', { name: 'Cargando pacientes' })).toBeInTheDocument()

    rerender(
      <ThemeProvider theme={nutriwardTheme}>
        <ErrorState message="No fue posible cargar" onRetry={retry} />
      </ThemeProvider>,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(retry).toHaveBeenCalledOnce()
  })
})
