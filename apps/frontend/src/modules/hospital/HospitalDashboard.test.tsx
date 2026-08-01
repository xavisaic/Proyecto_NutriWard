import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { HospitalDashboard } from './HospitalDashboard'

const structure = {
  items: [
    {
      id: '10000000-0000-0000-0000-000000000010',
      code: 'MED',
      name: 'Medicina',
      description: 'Hospitalización médico-quirúrgica.',
      is_active: true,
      created_at: '2026-07-27T00:00:00Z',
      updated_at: '2026-07-27T00:00:00Z',
      rooms: [
        {
          id: '10000000-0000-0000-0000-000000000020',
          service_id: '10000000-0000-0000-0000-000000000010',
          code: 'A101',
          name: 'Sala A101',
          floor: 'Piso 1',
          notes: 'Sector de observación',
          is_active: true,
          created_at: '2026-07-27T00:00:00Z',
          updated_at: '2026-07-27T00:00:00Z',
          care_units: [
            {
              id: '10000000-0000-0000-0000-000000000030',
              room_id: '10000000-0000-0000-0000-000000000020',
              code: '01',
              label: 'Cama 01',
              unit_type: 'bed',
              is_active: true,
              created_at: '2026-07-27T00:00:00Z',
              updated_at: '2026-07-27T00:00:00Z',
              layout: {
                id: '10000000-0000-0000-0000-000000000040',
                care_unit_id: '10000000-0000-0000-0000-000000000030',
                grid_x: 2,
                grid_y: 1,
                width: 1,
                height: 1,
                created_at: '2026-07-27T00:00:00Z',
                updated_at: '2026-07-27T00:00:00Z',
              },
            },
          ],
        },
      ],
    },
  ],
  total: 1,
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('estructura hospitalaria', () => {
  it('muestra servicios colapsados con contadores y expansión accesible', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(structure), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    render(<HospitalDashboard canEdit={false} canDelete={false} csrfToken="csrf-demo" />)

    expect(await screen.findByText('Medicina')).toBeInTheDocument()
    expect(screen.getByText('1 salas')).toBeInTheDocument()
    expect(screen.getByText('1 ubicaciones')).toBeInTheDocument()
    expect(screen.getByText('1 camas')).toBeInTheDocument()
    expect(screen.queryByText('Sala A101')).not.toBeInTheDocument()
    const expandButton = screen.getByRole('button', { name: 'Expandir servicio Medicina' })
    expect(expandButton).toHaveAttribute('aria-expanded', 'false')
    expect(expandButton).toHaveAttribute('aria-controls', `service-panel-${structure.items[0].id}`)
    await userEvent.click(expandButton)

    expect(await screen.findByText('Sala A101')).toBeInTheDocument()
    expect(screen.getByText('Sector de observación')).toBeInTheDocument()
    expect(screen.getByText('Cama 01')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Nuevo servicio' })).not.toBeInTheDocument()
    expect(screen.getByText('Posición 2, 1')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Colapsar servicio Medicina' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
  })

  it('permite a un editor abrir y enviar el formulario de servicio', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ items: [], total: 0 }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: '10000000-0000-0000-0000-000000000050',
            code: 'PED',
            name: 'Pediatría',
            description: null,
            is_active: true,
            rooms: [],
            created_at: '2026-07-27T00:00:00Z',
            updated_at: '2026-07-27T00:00:00Z',
          }),
          {
            status: 201,
            headers: { 'Content-Type': 'application/json' },
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(structure), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )

    render(<HospitalDashboard canEdit canDelete csrfToken="csrf-demo" />)
    await screen.findByText('No hay servicios para mostrar. Crea el primer servicio para comenzar.')
    await userEvent.click(screen.getByRole('button', { name: 'Nuevo servicio' }))
    const dialog = await screen.findByRole('dialog', { hidden: true })
    await userEvent.type(within(dialog).getByLabelText(/Código/), 'PED')
    await userEvent.type(within(dialog).getByLabelText(/Nombre/), 'Pediatría')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear servicio' }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/hospital/services'),
        expect.objectContaining({
          credentials: 'include',
          method: 'POST',
          headers: expect.any(Headers),
        }),
      )
    })
    const request = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/hospital/services'))
    expect((request?.[1]?.headers as Headers).get('X-CSRF-Token')).toBe('csrf-demo')
  })

  it('sugiere el código de ubicación y permite escoger su tipo', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(structure), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    render(<HospitalDashboard canEdit canDelete csrfToken="csrf-demo" />)
    await screen.findByText('Medicina')
    await userEvent.click(screen.getByRole('button', { name: 'Expandir servicio Medicina' }))
    await screen.findByText('Sala A101')
    await userEvent.click(
      screen.getByRole('button', { name: 'Agregar ubicación a Sala A101' }),
    )

    const dialog = await screen.findByRole('dialog', { hidden: true })
    const codeInput = within(dialog).getByLabelText('Código')
    expect(codeInput).toHaveValue('02')
    await userEvent.clear(codeInput)
    await userEvent.type(codeInput, 'MED-101-B')
    expect(codeInput).toHaveValue('MED-101-B')
    expect(within(dialog).getByRole('combobox', { name: 'Tipo' })).toHaveTextContent('Cama')
  })

  it('abre la edición de una ubicación con tipo, datos y posición actuales', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(structure), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    render(<HospitalDashboard canEdit canDelete csrfToken="csrf-demo" />)
    await screen.findByText('Medicina')
    await userEvent.click(screen.getByRole('button', { name: 'Expandir servicio Medicina' }))
    await screen.findByText('Cama 01')
    await userEvent.click(
      screen.getByRole('button', { name: 'Editar ubicación Cama 01' }),
    )

    const dialog = await screen.findByRole('dialog', { hidden: true })
    expect(within(dialog).getByLabelText(/Código/)).toHaveValue('01')
    expect(within(dialog).getByLabelText('Etiqueta')).toHaveValue('Cama 01')
    expect(within(dialog).getByRole('combobox', { name: 'Tipo' })).toHaveTextContent('Cama')
    expect(within(dialog).getByLabelText('Columna')).toHaveValue(2)
    expect(within(dialog).getByLabelText('Fila')).toHaveValue(1)
  })

  it('permite expandir y colapsar todos los servicios', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(structure), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    render(<HospitalDashboard canEdit canDelete csrfToken="csrf-demo" />)
    await screen.findByText('Medicina')
    expect(screen.queryByText('Sala A101')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Expandir todos' }))
    expect(await screen.findByText('Sala A101')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Expandir todos' })).toBeDisabled()

    await userEvent.click(screen.getByRole('button', { name: 'Colapsar todos' }))
    await waitFor(() => expect(screen.queryByText('Sala A101')).not.toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Colapsar todos' })).toBeDisabled()
  })

  it('muestra un estado vacío dentro de un servicio sin salas', async () => {
    const emptyService = {
      items: [{ ...structure.items[0], rooms: [] }],
      total: 1,
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(emptyService), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    render(<HospitalDashboard canEdit canDelete csrfToken="csrf-demo" />)
    await screen.findByText('Medicina')
    await userEvent.click(screen.getByRole('button', { name: 'Expandir servicio Medicina' }))

    expect(await screen.findByText('Sin salas registradas')).toBeInTheDocument()
    expect(screen.getByText('Este servicio todavía no contiene salas o sectores.')).toBeInTheDocument()
  })
})
