import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Router } from 'wouter'
import { memoryLocation } from 'wouter/memory-location'

import { AppRouter } from '../../app/router'
import { AuthProvider } from './AuthContext'

const demoSession = {
  user: {
    id: '10000000-0000-0000-0000-000000000001',
    email: 'administrador@nutriward.local',
    full_name: 'Administrador Demo',
    is_active: true,
    roles: ['administrador'],
    created_at: '2026-07-27T00:00:00Z',
    updated_at: '2026-07-27T00:00:00Z',
  },
  csrf_token: 'csrf-demo',
}

const emptyStructure = { items: [], total: 0 }
const emptyPatients = { items: [], total: 0, page: 1, page_size: 10 }
const emptyAdmissions = { items: [], total: 0 }

function renderApp(path = '/') {
  const { hook } = memoryLocation({ path })
  return render(
    <Router hook={hook}>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </Router>,
  )
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('flujo de autenticación', () => {
  it('redirige a login y permite autenticar al usuario', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Sin sesión' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(demoSession), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(emptyStructure), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )

    renderApp('/')
    await screen.findByRole('heading', { name: 'Iniciar sesión' })

    await userEvent.type(screen.getByLabelText(/Correo/), demoSession.user.email)
    await userEvent.type(screen.getByLabelText(/Contraseña/), 'demo-password')
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar' }))

    expect(await screen.findByRole('heading', { name: 'Administrador Demo' })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/auth/login'),
      expect.objectContaining({ credentials: 'include', method: 'POST' }),
    )
  })

  it('restaura una sesión y muestra los roles activos', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url.includes('/hospital/structure')) return jsonResponse(emptyStructure)
      if (url.includes('/patients?')) return jsonResponse(emptyPatients)
      if (url.includes('/admissions/active')) return jsonResponse(emptyAdmissions)
      return jsonResponse(demoSession)
    })

    renderApp('/')

    expect(await screen.findByText('administrador')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText(demoSession.user.email)).toBeInTheDocument())
    expect(screen.getByRole('heading', { name: 'Estructura hospitalaria' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('tab', { name: 'Pacientes' }))
    expect(await screen.findByRole('heading', { name: 'Pacientes' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Crear paciente' })).not.toBeInTheDocument()
  })

  it('muestra un error genérico cuando las credenciales no son válidas', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Sin sesión' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Correo o contraseña incorrectos.' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }),
      )

    renderApp('/login')
    await screen.findByRole('heading', { name: 'Iniciar sesión' })
    await userEvent.type(screen.getByLabelText(/Correo/), demoSession.user.email)
    await userEvent.type(screen.getByLabelText(/Contraseña/), 'incorrecta')
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Correo o contraseña incorrectos.')
  })

  it('muestra pacientes a nutricionista y lo oculta a alimentación', async () => {
    const nutritionistSession = {
      ...demoSession,
      user: { ...demoSession.user, roles: ['nutricionista'] },
    }
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url.includes('/auth/me')) return jsonResponse(nutritionistSession)
      if (url.includes('/patients?')) return jsonResponse(emptyPatients)
      if (url.includes('/admissions/active')) return jsonResponse(emptyAdmissions)
      return jsonResponse(emptyStructure)
    })
    renderApp('/')
    expect(await screen.findByRole('heading', { name: 'Pacientes' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Pacientes' })).toBeInTheDocument()

    cleanup()
    vi.restoreAllMocks()
    const foodSession = {
      ...demoSession,
      user: { ...demoSession.user, roles: ['alimentacion'] },
    }
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      return jsonResponse(url.includes('/auth/me') ? foodSession : emptyStructure)
    })
    renderApp('/')
    expect(await screen.findByRole('heading', { name: 'Estructura hospitalaria' })).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: 'Pacientes' })).not.toBeInTheDocument()
  })
})

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}
