import { ThemeProvider } from '@mui/material'
import { cleanup, render as rtlRender, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ReactElement } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { nutriwardTheme } from '../../app/theme/theme'
import { BedMap, HospitalStructure } from '../../shared/services/api'
import { BedMapDashboard, classifyRoomBeds } from './BedMapDashboard'

function render(ui: ReactElement) {
  return rtlRender(<ThemeProvider theme={nutriwardTheme}>{ui}</ThemeProvider>)
}

const MED_ID = '22000000-0000-0000-0000-000000000001'
const UCI_ID = '22000000-0000-0000-0000-000000000002'
const ROOM_A_ID = '21000000-0000-0000-0000-000000000001'
const ROOM_B_ID = '21000000-0000-0000-0000-000000000002'

const serviceBase = {
  description: null,
  is_active: true,
  rooms: [],
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
}

const structure: HospitalStructure = {
  total: 2,
  items: [
    { ...serviceBase, id: UCI_ID, code: 'UCI', name: 'Unidad de Cuidados Intensivos' },
    { ...serviceBase, id: MED_ID, code: 'MED', name: 'Medicina' },
  ],
}

function occupancy(
  id: string,
  displayName: string,
  identityStatus: 'identified' | 'provisional' | 'unidentified',
  ageYears: number | null,
  estimated = false,
) {
  return {
    patient: {
      id,
      display_name: displayName,
      identity_status: identityStatus,
      age_years: ageYears,
      age_is_estimated: estimated,
    },
    admission: {
      id: `30000000-0000-0000-0000-${id.slice(-12)}`,
      admission_identifier: `ADM-${id.slice(-4)}`,
      status: 'active' as const,
      admitted_at: '2026-08-01T10:00:00Z',
    },
    pending_transfer: null,
  }
}

const map: BedMap = {
  generated_at: '2026-08-01T15:30:00Z',
  service: { id: MED_ID, code: 'MED', name: 'Medicina' },
  rooms: [
    {
      id: ROOM_A_ID,
      code: 'SALA-A',
      name: 'Sala A',
      floor: '2',
      beds: [
        {
          id: 'bed-free', code: '01', label: 'Cama 01', status: 'free',
          layout: { grid_x: 0, grid_y: 0, width: 1, height: 1 }, occupancy: null,
        },
        {
          id: 'bed-occupied', code: '02', label: 'Cama 02', status: 'occupied',
          layout: { grid_x: 2, grid_y: 0, width: 2, height: 1 },
          occupancy: occupancy('patient-0001', 'Ana Pérez', 'identified', 26, true),
        },
        {
          id: 'bed-unpositioned', code: '03', label: null, status: 'occupied', layout: null,
          occupancy: occupancy('patient-0002', 'Paciente NN · NN-2026-001', 'unidentified', null),
        },
        {
          id: 'bed-conflict-a', code: '04', label: 'Cama 04', status: 'occupied',
          layout: { grid_x: 5, grid_y: 0, width: 2, height: 1 },
          occupancy: occupancy('patient-0003', 'Nombre Provisorio', 'provisional', 40),
        },
        {
          id: 'bed-conflict-b', code: '05', label: 'Cama 05', status: 'free',
          layout: { grid_x: 6, grid_y: 0, width: 1, height: 1 }, occupancy: null,
        },
      ],
    },
    { id: ROOM_B_ID, code: 'SALA-B', name: 'Sala B', floor: '3', beds: [] },
  ],
}

const uciMap: BedMap = {
  generated_at: '2026-08-01T15:31:00Z',
  service: { id: UCI_ID, code: 'UCI', name: 'Unidad de Cuidados Intensivos' },
  rooms: [],
}

function response(payload: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  }))
}

function mockApi(mapResponses: Array<BedMap | { error: string }> = [map]) {
  let mapIndex = 0
  return vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    const url = String(input)
    if (url.includes('/hospital/structure')) return response(structure)
    if (url.includes('/bed-map')) {
      const selected = mapResponses[Math.min(mapIndex++, mapResponses.length - 1)]
      return 'error' in selected
        ? response({ detail: selected.error }, 503)
        : response(selected)
    }
    return response({})
  })
}

afterEach(() => {
  cleanup()
  window.sessionStorage.clear()
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('mapa de camas', () => {
  it('selecciona inicialmente un servicio activo asignado al nutricionista', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input)
      if (url.includes('/hospital/structure')) return response(structure)
      if (url.includes('/nutritionist-service-assignments/me')) {
        return response({
          items: [{
            id: 'assignment-uci',
            nutritionist_user_id: 'nutritionist-1',
            nutritionist_name: 'Nutricionista Demo',
            nutritionist_email: 'nutricionista@nutriward.local',
            service_id: UCI_ID,
            service_code: 'UCI',
            service_name: 'Unidad de Cuidados Intensivos',
            is_active: true,
            created_at: '2026-08-01T10:00:00Z',
            updated_at: '2026-08-01T10:00:00Z',
          }],
          total: 1,
        })
      }
      if (url.includes('/bed-map')) return response(url.includes(UCI_ID) ? uciMap : map)
      return response({})
    })

    render(<BedMapDashboard userId="nutritionist-1" isNutritionist />)

    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: 'Servicio' })).toHaveTextContent('UCI')
    })
    expect(screen.getByRole('combobox', { name: 'Servicio' })).toHaveTextContent('Asignado')
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(`/bed-map?service_id=${encodeURIComponent(UCI_ID)}`),
      expect.anything(),
    )
  })

  it('restaura el último servicio asignado al volver al mapa', async () => {
    const assignments = {
      items: [MED_ID, UCI_ID].map((serviceId, index) => ({
        id: `assignment-${index}`,
        nutritionist_user_id: 'nutritionist-1',
        nutritionist_name: 'Nutricionista Demo',
        nutritionist_email: 'nutricionista@nutriward.local',
        service_id: serviceId,
        service_code: serviceId === MED_ID ? 'MED' : 'UCI',
        service_name: serviceId === MED_ID ? 'Medicina' : 'Unidad de Cuidados Intensivos',
        is_active: true,
        created_at: '2026-08-01T10:00:00Z',
        updated_at: '2026-08-01T10:00:00Z',
      })),
      total: 2,
    }
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input)
      if (url.includes('/hospital/structure')) return response(structure)
      if (url.includes('/nutritionist-service-assignments/me')) return response(assignments)
      if (url.includes('/bed-map')) return response(url.includes(UCI_ID) ? uciMap : map)
      return response({})
    })

    const firstVisit = render(
      <BedMapDashboard userId="nutritionist-1" isNutritionist />,
    )
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: 'Servicio' })).toHaveTextContent('MED')
    })
    await userEvent.click(screen.getByRole('combobox', { name: 'Servicio' }))
    await userEvent.click(await screen.findByRole('option', { name: /UCI/ }))
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: 'Servicio' })).toHaveTextContent('UCI')
    })
    firstVisit.unmount()

    render(<BedMapDashboard userId="nutritionist-1" isNutritionist />)
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: 'Servicio' })).toHaveTextContent('UCI')
    })
    expect(window.sessionStorage.getItem(
      'nutriward:bed-map:service:nutritionist-1',
    )).toBe(UCI_ID)
  })

  it('selecciona el primer servicio estable y representa camas, edades y régimen visual', async () => {
    mockApi()
    render(<BedMapDashboard />)

    expect(await screen.findByRole('button', { name: 'Cama 01, libre' })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Servicio' })).toHaveTextContent('MED · Medicina')
    expect(screen.getByRole('combobox', { name: 'Sala' })).toHaveTextContent('Todas las salas')
    expect(screen.getByRole('button', { name: 'Cama 02, ocupada por Ana Pérez' })).toHaveTextContent('26 años · estimada')
    expect(screen.getByRole('button', { name: /Cama 03, ocupada por Paciente NN/ })).toHaveTextContent('Edad no registrada')
    expect(screen.getByText('Nombre Provisorio')).toBeInTheDocument()
    expect(screen.getAllByText('Régimen: No disponible en esta fase').length).toBeGreaterThan(0)
    expect(screen.getByLabelText('Resumen del mapa')).toHaveTextContent('Camas activas')
    expect(screen.getByLabelText('Leyenda de estados de camas')).toHaveTextContent('Traslado pendiente')
  })

  it('distingue en la cama de origen los dos estados de traslado pendiente', async () => {
    const pendingMap = structuredClone(map)
    const receptionBed = pendingMap.rooms[0].beds.find((bed) => bed.id === 'bed-occupied')!
    const pendingBed = pendingMap.rooms[0].beds.find((bed) => bed.id === 'bed-unpositioned')!
    receptionBed.occupancy!.pending_transfer = {
      id: 'transfer-reception',
      status: 'pending_reception',
      destination_service_id: UCI_ID,
      destination_service_code: 'UCI',
      destination_service_name: 'Unidad de Cuidados Intensivos',
      requested_at: '2026-08-12T10:00:00Z',
    }
    pendingBed.occupancy!.pending_transfer = {
      id: 'transfer-bed',
      status: 'pending_bed',
      destination_service_id: UCI_ID,
      destination_service_code: 'UCI',
      destination_service_name: 'Unidad de Cuidados Intensivos',
      requested_at: '2026-08-12T10:05:00Z',
    }
    mockApi([pendingMap])
    render(<BedMapDashboard />)

    const reception = await screen.findByRole('button', { name: /Cama 02, ocupada por Ana Pérez, Traslado solicitado · UCI/ })
    expect(within(reception).getByText('Traslado solicitado · UCI')).toBeInTheDocument()
    expect(screen.getByText('Aceptado · espera cama · UCI')).toBeInTheDocument()

    await userEvent.click(reception)
    const panel = await screen.findByRole('region', { name: 'Detalle de ocupación' })
    expect(within(panel).getByText(/Destino: Unidad de Cuidados Intensivos/)).toBeInTheDocument()
    expect(within(panel).getByText(/continúa ocupando esta cama/)).toBeInTheDocument()
  })

  it('aplica coordenadas y dimensiones, separa camas sin posición y retira superposiciones del grid', async () => {
    mockApi()
    render(<BedMapDashboard />)
    const positioned = await screen.findByRole('button', { name: 'Cama 02, ocupada por Ana Pérez' })
    expect(positioned).toHaveStyle({ gridColumn: '3 / span 2', gridRow: '1 / span 1' })

    expect(screen.getByRole('heading', { name: 'Sin posición configurada' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Posición conflictiva' })).toBeInTheDocument()
    expect(screen.getByText(/Corrija la configuración desde Estructura hospitalaria/)).toBeInTheDocument()
    const grid = screen.getByTestId(`room-grid-${ROOM_A_ID}`)
    expect(within(grid).queryByRole('button', { name: /Cama 04/ })).not.toBeInTheDocument()
    expect(within(grid).queryByRole('button', { name: /Cama 05/ })).not.toBeInTheDocument()
    expect(classifyRoomBeds(map.rooms[0]).conflicting.map((bed) => bed.id)).toEqual([
      'bed-conflict-a', 'bed-conflict-b',
    ])
  })

  it('filtra por sala y reinicia a Todas las salas al cambiar de servicio', async () => {
    mockApi([map, uciMap])
    render(<BedMapDashboard />)
    await screen.findByRole('heading', { name: /SALA-A/ })

    await userEvent.click(screen.getByRole('combobox', { name: 'Sala' }))
    await userEvent.click(await screen.findByRole('option', { name: /SALA-B/ }))
    expect(screen.queryByRole('heading', { name: /SALA-A/ })).not.toBeInTheDocument()
    expect(screen.getByText('Esta sala no tiene camas activas.')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('combobox', { name: 'Servicio' }))
    await userEvent.click(await screen.findByRole('option', { name: /UCI/ }))
    expect(await screen.findByText('El servicio seleccionado no tiene salas activas.')).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Sala' })).toHaveTextContent('Todas las salas')
  })

  it('abre el panel con teclado, no consulta fichas generales y devuelve el foco al cerrar', async () => {
    const fetchMock = mockApi()
    render(<BedMapDashboard />)
    const bed = await screen.findByRole('button', { name: 'Cama 02, ocupada por Ana Pérez' })
    bed.focus()
    await userEvent.keyboard('{Enter}')

    const panel = await screen.findByRole('region', { name: 'Detalle de ocupación' })
    expect(bed).toHaveAttribute('aria-pressed', 'true')
    expect(within(panel).getByText('ADM-0001')).toBeInTheDocument()
    expect(within(panel).getByText('Tipo de identidad: Identificado')).toBeInTheDocument()
    expect(within(panel).queryByText(/RUT|teléfono|fecha de nacimiento/i)).not.toBeInTheDocument()
    expect(fetchMock.mock.calls.every(([url]) => !/\/patients\/|\/admissions\//.test(String(url)))).toBe(true)

    await userEvent.click(within(panel).getByRole('button', { name: 'Cerrar panel de ocupación' }))
    await waitFor(() => expect(bed).toHaveFocus())
    expect(bed).toHaveAttribute('aria-pressed', 'false')
  })

  it('muestra a Alimentación sólo el riesgo alimentario mínimo en el panel', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input)
      if (url.includes('/hospital/structure')) return response(structure)
      if (url.includes('/bed-map')) return response(map)
      if (url.includes('/food-safety-allergies')) return response({
        admission_id: map.rooms[0].beds[1].occupancy!.admission.id,
        review_status: 'active_food_risks',
        items: [{
          id: 'risk-1', substance_name: 'Maní', allergy_type: 'allergy', criticality: 'high',
          reactions: [{ manifestation: 'Anafilaxia', severity: 'severe' }],
        }],
      })
      return response({})
    })
    render(<BedMapDashboard canReadFoodSafety />)
    await userEvent.click(await screen.findByRole('button', { name: 'Cama 02, ocupada por Ana Pérez' }))
    const panel = await screen.findByRole('region', { name: 'Detalle de ocupación' })
    expect(await within(panel).findByText('Riesgo alimentario activo')).toBeInTheDocument()
    expect(within(panel).getByText(/Maní · Alergia · criticidad alta/)).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/food-safety-allergies'))).toBe(true)
    expect(within(panel).queryByText(/fuente|penicilina/i)).not.toBeInTheDocument()
  })

  it('una cama libre es operable por teclado sin abrir panel ni lanzar consultas', async () => {
    const fetchMock = mockApi()
    render(<BedMapDashboard />)
    const bed = await screen.findByRole('button', { name: 'Cama 01, libre' })
    const requests = fetchMock.mock.calls.length
    bed.focus()
    await userEvent.keyboard('{Enter}')
    expect(screen.queryByRole('region', { name: 'Detalle de ocupación' })).not.toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(requests)
  })

  it('actualiza manualmente conservando el mapa y cierra el panel si cambia la ocupación', async () => {
    const freed = structuredClone(map)
    freed.generated_at = '2026-08-01T15:32:00Z'
    const bed = freed.rooms[0].beds.find((item) => item.id === 'bed-occupied')!
    bed.status = 'free'
    bed.occupancy = null
    mockApi([map, freed])
    render(<BedMapDashboard />)
    await userEvent.click(await screen.findByRole('button', { name: /Cama 02, ocupada/ }))
    expect(await screen.findByRole('region', { name: 'Detalle de ocupación' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar', hidden: true }))

    expect(await screen.findByRole('button', { name: 'Cama 02, libre' })).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Detalle de ocupación' })).not.toBeInTheDocument()
    expect(await screen.findByText('La ocupación cambió y la cama ahora está libre.')).toBeInTheDocument()
  })

  it('mantiene el mapa anterior durante una actualización y ante un error no bloqueante', async () => {
    let rejectRefresh!: (reason: unknown) => void
    const pending = new Promise<Response>((_, reject) => { rejectRefresh = reject })
    let bedCalls = 0
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input)
      if (url.includes('/hospital/structure')) return response(structure)
      if (bedCalls++ === 0) return response(map)
      return pending
    })
    render(<BedMapDashboard />)
    expect(await screen.findByRole('button', { name: 'Cama 01, libre' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar' }))
    expect(screen.getByRole('button', { name: 'Cama 01, libre' })).toBeInTheDocument()
    expect(screen.getByLabelText('Actualizando mapa')).toBeInTheDocument()
    rejectRefresh(new Error('red caída'))
    expect(await screen.findByText(/Se conserva la última información válida/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cama 01, libre' })).toBeInTheDocument()
  })

  it('muestra error inicial y permite reintentar', async () => {
    mockApi([{ error: 'Servicio temporalmente no disponible' }, map])
    render(<BedMapDashboard />)
    expect(await screen.findByText('Servicio temporalmente no disponible')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByRole('button', { name: 'Cama 01, libre' })).toBeInTheDocument()
  })

  it('descarta la respuesta obsoleta cuando el servicio cambia rápidamente', async () => {
    let resolveMed!: (response: Response) => void
    const delayedMed = new Promise<Response>((resolve) => { resolveMed = resolve })
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input)
      if (url.includes('/hospital/structure')) return response(structure)
      if (url.includes(MED_ID)) return delayedMed
      if (url.includes(UCI_ID)) return response(uciMap)
      return response({})
    })
    render(<BedMapDashboard />)
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Servicio' })).toHaveTextContent('MED'))
    await userEvent.click(screen.getByRole('combobox', { name: 'Servicio' }))
    await userEvent.click(await screen.findByRole('option', { name: /UCI/ }))
    expect(await screen.findByText('El servicio seleccionado no tiene salas activas.')).toBeInTheDocument()
    resolveMed(await response(map))
    await Promise.resolve()
    expect(screen.queryByRole('button', { name: 'Cama 01, libre' })).not.toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Servicio' })).toHaveTextContent('UCI')
  })

  it('refresca cada 45 segundos, pausa oculta y actualiza al recuperar visibilidad', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const fetchMock = mockApi([map])
    render(<BedMapDashboard />)
    await screen.findByRole('button', { name: 'Cama 01, libre' })
    const bedMapCalls = () => fetchMock.mock.calls.filter(([url]) => String(url).includes('/bed-map')).length
    expect(bedMapCalls()).toBe(1)

    await vi.advanceTimersByTimeAsync(45_000)
    await waitFor(() => expect(bedMapCalls()).toBe(2))

    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' })
    await vi.advanceTimersByTimeAsync(45_000)
    expect(bedMapCalls()).toBe(2)

    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' })
    document.dispatchEvent(new Event('visibilitychange'))
    await waitFor(() => expect(bedMapCalls()).toBe(3))
  })

  it('maneja la ausencia total de servicios activos', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => response({ items: [], total: 0 }))
    render(<BedMapDashboard />)
    expect(await screen.findByText('No hay servicios activos disponibles.')).toBeInTheDocument()
  })
})
