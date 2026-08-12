import { useTheme } from '@mui/material'
import { act, cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AppearanceMenu } from '../../shared/components'
import { AppearanceProvider, appearanceStorageKey, useAppearance } from './AppearanceContext'

function AppearanceProbe() {
  const { preference, resolvedMode } = useAppearance()
  const theme = useTheme()
  return (
    <output data-testid="appearance-probe">
      {preference}:{resolvedMode}:{theme.palette.mode}
    </output>
  )
}

function renderAppearance(userId = 'user-a') {
  return render(
    <AppearanceProvider userId={userId}>
      <AppearanceMenu />
      <AppearanceProbe />
    </AppearanceProvider>,
  )
}

beforeEach(() => {
  window.localStorage.clear()
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  window.localStorage.clear()
  document.documentElement.style.colorScheme = ''
  delete document.documentElement.dataset.colorScheme
})

describe('preferencia de apariencia', () => {
  it('cambia a oscuro y conserva la elección de forma independiente por usuario', async () => {
    const { rerender } = renderAppearance()

    await userEvent.click(screen.getByRole('button', { name: 'Cambiar apariencia' }))
    const darkOption = screen.getByRole('menuitemradio', { name: /Oscuro/ })
    await userEvent.click(darkOption)

    expect(screen.getByTestId('appearance-probe')).toHaveTextContent('dark:dark:dark')
    expect(document.documentElement).toHaveAttribute('data-color-scheme', 'dark')
    expect(window.localStorage.getItem(appearanceStorageKey('user-a'))).toBe('dark')

    rerender(
      <AppearanceProvider userId="user-b">
        <AppearanceMenu />
        <AppearanceProbe />
      </AppearanceProvider>,
    )
    await waitFor(() => expect(screen.getByTestId('appearance-probe')).toHaveTextContent('light:light:light'))
    expect(window.localStorage.getItem(appearanceStorageKey('user-b'))).toBe('light')
  })

  it('resuelve Según el sistema y mantiene visible la elección seleccionada', async () => {
    let mediaListener: ((event: MediaQueryListEvent) => void) | undefined
    vi.stubGlobal('matchMedia', vi.fn().mockImplementation(() => ({
      matches: true,
      media: '(prefers-color-scheme: dark)',
      addEventListener: vi.fn((_event, listener) => { mediaListener = listener }),
      removeEventListener: vi.fn(),
    })))
    window.localStorage.setItem(appearanceStorageKey('user-a'), 'system')
    renderAppearance()

    expect(await screen.findByTestId('appearance-probe')).toHaveTextContent('system:dark:dark')
    await userEvent.click(screen.getByRole('button', { name: 'Cambiar apariencia' }))
    expect(screen.getByRole('menuitemradio', { name: /Según el sistema/ })).toHaveAttribute('aria-checked', 'true')

    act(() => mediaListener?.({ matches: false } as MediaQueryListEvent))
    expect(screen.getByTestId('appearance-probe')).toHaveTextContent('system:light:light')
  })
})
