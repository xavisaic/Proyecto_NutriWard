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
  it('muestra la jerarquía y sus contadores', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(structure), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    render(<HospitalDashboard canEdit={false} canDelete={false} csrfToken="csrf-demo" />)

    expect(await screen.findByText('Medicina')).toBeInTheDocument()
    expect(screen.getByText('Sala A101')).toBeInTheDocument()
    expect(screen.getByText('Sector de observación')).toBeInTheDocument()
    expect(screen.getByText('Cama 01')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Nuevo servicio' })).not.toBeInTheDocument()
    expect(screen.getByText('2, 1')).toBeInTheDocument()
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
})
