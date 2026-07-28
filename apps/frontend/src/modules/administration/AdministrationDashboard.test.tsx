import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AdministrationDashboard } from './AdministrationDashboard'

const users = {
  items: [
    {
      id: '10000000-0000-0000-0000-000000000001',
      email: 'nutricionista@nutriward.local',
      full_name: 'Nutricionista Demo',
      is_active: true,
      roles: ['nutricionista'],
      created_at: '2026-07-28T00:00:00Z',
      updated_at: '2026-07-28T00:00:00Z',
    },
    {
      id: '10000000-0000-0000-0000-000000000002',
      email: 'jefatura@nutriward.local',
      full_name: 'Jefatura Demo',
      is_active: false,
      roles: ['jefatura'],
      created_at: '2026-07-28T00:00:00Z',
      updated_at: '2026-07-28T00:00:00Z',
    },
  ],
  total: 2,
}

const roles = {
  items: [
    {
      id: '20000000-0000-0000-0000-000000000001',
      name: 'nutricionista',
      description: 'Atención nutricional clínica.',
      created_at: '2026-07-28T00:00:00Z',
      updated_at: '2026-07-28T00:00:00Z',
    },
    {
      id: '20000000-0000-0000-0000-000000000002',
      name: 'jefatura',
      description: 'Supervisión clínica.',
      created_at: '2026-07-28T00:00:00Z',
      updated_at: '2026-07-28T00:00:00Z',
    },
  ],
  total: 2,
}

const assignments = {
  items: [
    {
      id: '30000000-0000-0000-0000-000000000001',
      nutritionist_user_id: users.items[0].id,
      nutritionist_name: 'Nutricionista Demo',
      nutritionist_email: 'nutricionista@nutriward.local',
      service_id: '40000000-0000-0000-0000-000000000001',
      service_code: 'MED',
      service_name: 'Medicina',
      is_active: true,
      created_at: '2026-07-28T00:00:00Z',
      updated_at: '2026-07-28T00:00:00Z',
    },
  ],
  total: 1,
}

const structure = {
  items: [
    {
      id: assignments.items[0].service_id,
      code: 'MED',
      name: 'Medicina',
      description: null,
      is_active: true,
      rooms: [],
      created_at: '2026-07-28T00:00:00Z',
      updated_at: '2026-07-28T00:00:00Z',
    },
  ],
  total: 1,
}

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function mockAdministrationApi() {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (init?.method === 'DELETE') {
      return new Response(null, { status: 204 })
    }
    if (url.includes('/nutritionist-service-assignments')) {
      return jsonResponse(assignments)
    }
    if (url.includes('/roles')) {
      return jsonResponse(roles)
    }
    if (url.includes('/users')) {
      return jsonResponse(users)
    }
    if (url.includes('/hospital/structure')) {
      return jsonResponse(structure)
    }
    return jsonResponse({ detail: 'Ruta inesperada' }, 404)
  })
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('administración de usuarios y asignaciones', () => {
  it('renderiza la lista de usuarios y sus estados', async () => {
    mockAdministrationApi()
    render(<AdministrationDashboard canManage csrfToken="csrf-demo" />)

    expect(await screen.findByText('Nutricionista Demo')).toBeInTheDocument()
    expect(screen.getByText('nutricionista@nutriward.local')).toBeInTheDocument()
    expect(screen.getByText('Inactivo')).toBeInTheDocument()
  })

  it('muestra los roles asociados a cada usuario', async () => {
    mockAdministrationApi()
    render(<AdministrationDashboard canManage={false} csrfToken="csrf-demo" />)

    expect(await screen.findByText('nutricionista')).toBeInTheDocument()
    expect(screen.getByText('jefatura')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Crear usuario' })).not.toBeInTheDocument()
  })

  it('renderiza asignaciones y explica que la cobertura no es exclusiva', async () => {
    mockAdministrationApi()
    render(<AdministrationDashboard canManage csrfToken="csrf-demo" />)
    await screen.findByText('Nutricionista Demo')
    await userEvent.click(
      screen.getByRole('tab', { name: 'Asignaciones de servicios' }),
    )

    expect(screen.getByText('Medicina')).toBeInTheDocument()
    expect(screen.getByText(/\(MED\)/)).toBeInTheDocument()
    expect(screen.getByText(/no son exclusivas/i)).toBeInTheDocument()
  })

  it('inactiva una asignación con CSRF cuando el usuario puede administrar', async () => {
    const fetchMock = mockAdministrationApi()
    render(<AdministrationDashboard canManage csrfToken="csrf-demo" />)
    await screen.findByText('Nutricionista Demo')
    await userEvent.click(
      screen.getByRole('tab', { name: 'Asignaciones de servicios' }),
    )
    await userEvent.click(screen.getByRole('button', { name: 'Inactivar' }))

    await waitFor(() => {
      const request = fetchMock.mock.calls.find(
        ([url, init]) =>
          String(url).endsWith(`/nutritionist-service-assignments/${assignments.items[0].id}`)
          && init?.method === 'DELETE',
      )
      expect(request).toBeDefined()
      expect((request?.[1]?.headers as Headers).get('X-CSRF-Token')).toBe(
        'csrf-demo',
      )
    })
  })
})
