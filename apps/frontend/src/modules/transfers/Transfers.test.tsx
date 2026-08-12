import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { MovePatientDialog, ReceptionTray } from './Transfers'

const MED = '22000000-0000-0000-0000-000000000001'
const UCI = '22000000-0000-0000-0000-000000000002'
const services: any[] = [
  { id: MED, code: 'MED', name: 'Medicina', is_active: true, rooms: [] },
  { id: UCI, code: 'UCI', name: 'Cuidados intensivos', is_active: true, rooms: [] },
]
const admission = {
  id: '30000000-0000-0000-0000-000000000001',
  current_location: { service_id: MED, care_unit_id: 'bed-med-1' },
}
const baseTransfer: any = {
  id: '70000000-0000-0000-0000-000000000001',
  admission_id: admission.id,
  transfer_mode: 'reception_tray',
  status: 'pending_reception',
  request_reason: 'Mayor complejidad operacional ficticia.',
  requested_by_user_id: 'user-1',
  requested_at: new Date(Date.now() - 60_000).toISOString(),
  completed_at: null,
  created_at: '2026-08-12T10:00:00Z',
  updated_at: '2026-08-12T10:00:00Z',
  origin_service: { id: MED, code: 'MED', name: 'Medicina' },
  destination_service: { id: UCI, code: 'UCI', name: 'Cuidados intensivos' },
  origin_care_unit_id: 'bed-med-1',
  destination_care_unit_id: null,
  current_origin_location: {
    care_unit_id: 'bed-med-1', care_unit_code: '01', care_unit_label: 'Cama 01',
    room_id: 'room-med', room_code: 'A101', room_name: 'Sala A101',
    service_id: MED, service_code: 'MED', service_name: 'Medicina',
  },
  patient: {
    id: 'patient-1', display_name: 'Paciente NN · NN-DEMO', identity_status: 'unidentified',
    age_years: 52, age_is_estimated: true,
  },
  admission: { id: admission.id, admission_identifier: 'ADM-DEMO', status: 'active', admitted_at: '2026-08-10T10:00:00Z' },
  has_coverage_support: true,
  status_history: [],
}

function json(payload: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  }))
}

function bedMap(serviceId: string) {
  const service = services.find((item) => item.id === serviceId)!
  return {
    generated_at: '2026-08-12T10:00:00Z',
    service: { id: service.id, code: service.code, name: service.name },
    rooms: [{
      id: `room-${service.code}`, code: `${service.code}-A`, name: `Sala ${service.code}`, floor: null,
      beds: [
        { id: `bed-${service.code}-free`, code: '02', label: 'Cama 02', status: 'free', layout: null, occupancy: null },
        { id: `bed-${service.code}-occupied`, code: '03', label: 'Cama 03', status: 'occupied', layout: null, occupancy: {} },
      ],
    }],
  }
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.useRealTimers()
})

describe('traslados y bandeja', () => {
  it('envía a bandeja sin solicitar cama ni motivo y exige confirmación', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(() => json(baseTransfer, 201))
    render(
      <MovePatientDialog
        open admission={admission} services={services} csrfToken="csrf-demo"
        onClose={() => undefined} onCompleted={() => undefined}
      />,
    )
    const dialog = screen.getByRole('dialog', { hidden: true })
    await userEvent.click(within(dialog).getByRole('combobox', { name: 'Servicio destino' }))
    await userEvent.click(await screen.findByRole('option', { name: /UCI/ }))
    await userEvent.click(within(dialog).getByRole('combobox', { name: 'Modalidad' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Enviar a bandeja de recepción' }))
    expect(within(dialog).queryByRole('combobox', { name: 'Cama destino' })).not.toBeInTheDocument()
    const submit = within(dialog).getByRole('button', { name: 'Enviar a bandeja' })
    expect(submit).toBeDisabled()
    expect(within(dialog).getByRole('textbox', { name: /Motivo del traslado \(opcional\)/ })).toHaveValue('')
    await userEvent.click(within(dialog).getByRole('checkbox'))
    await userEvent.click(submit)
    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/transfer-requests'))
      expect(call).toBeTruthy()
      const payload = JSON.parse(String(call?.[1]?.body))
      expect(payload).toMatchObject({ transfer_mode: 'reception_tray', destination_care_unit_id: null, reason: null })
      expect(new Headers(call?.[1]?.headers).get('X-CSRF-Token')).toBe('csrf-demo')
    })
  })

  it('en traslado directo muestra sólo camas libres y conserva el formulario ante 409', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input)
      if (url.includes('/bed-map')) return json(bedMap(UCI))
      return json({ detail: 'La cama fue ocupada.' }, 409)
    })
    render(
      <MovePatientDialog
        open admission={admission} services={services} csrfToken="csrf-demo"
        onClose={() => undefined} onCompleted={() => undefined}
      />,
    )
    const dialog = screen.getByRole('dialog', { hidden: true })
    await userEvent.click(within(dialog).getByRole('combobox', { name: 'Servicio destino' }))
    await userEvent.click(await screen.findByRole('option', { name: /UCI/ }))
    await waitFor(() => expect(within(dialog).getByRole('combobox', { name: 'Cama destino' })).toBeEnabled())
    await userEvent.click(within(dialog).getByRole('combobox', { name: 'Cama destino' }))
    expect(screen.queryByRole('option', { name: /Cama 03/ })).not.toBeInTheDocument()
    await userEvent.click(await screen.findByRole('option', { name: /Cama 02/ }))
    expect(within(dialog).getByRole('textbox', { name: /Motivo del traslado \(opcional\)/ })).toHaveValue('')
    await userEvent.click(within(dialog).getByRole('checkbox'))
    await userEvent.click(within(dialog).getByRole('button', { name: 'Confirmar traslado directo' }))
    expect(await within(dialog).findByText(/disponibilidad o el estado cambió/i)).toBeInTheDocument()
    expect(within(dialog).getByRole('textbox', { name: /Motivo del traslado \(opcional\)/ })).toHaveValue('')
  })

  it('muestra ambos estados, contador, privacidad y sólo lectura sin controles', async () => {
    const pendingBed = {
      ...baseTransfer,
      id: 'transfer-2',
      status: 'pending_bed',
      request_reason: null,
      has_coverage_support: false,
    }
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => json({
      items: [baseTransfer, pendingBed], total: 2, page: 1, page_size: 100,
    }))
    render(
      <ReceptionTray serviceId={UCI} canMutate={false} csrfToken="csrf" onMutation={() => undefined} />,
    )
    expect(await screen.findByText('2 pendientes')).toBeInTheDocument()
    expect(screen.getByText('Pendientes de recepción (1)')).toBeInTheDocument()
    expect(screen.getByText('Aceptados, pendientes de cama (1)')).toBeInTheDocument()
    expect(screen.getAllByText('Paciente NN · NN-DEMO')).toHaveLength(2)
    expect(screen.getByText('Cobertura/apoyo')).toBeInTheDocument()
    expect(screen.getByText('Sin motivo informado')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Aceptar|Asignar|Rechazar|Devolver|Cancelar solicitud/ })).not.toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/RUT|teléfono|fecha de nacimiento|historial clínico/i)
  })

  it('acepta sin cama y refresca coordinadamente después de la mutación', async () => {
    let trayReads = 0
    const onMutation = vi.fn()
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      const url = String(input)
      if (url.includes('/reception-tray')) {
        trayReads += 1
        return json({ items: trayReads === 1 ? [baseTransfer] : [], total: trayReads === 1 ? 1 : 0, page: 1, page_size: 100 })
      }
      if (url.endsWith('/accept') && init?.method === 'POST') return json({ ...baseTransfer, status: 'pending_bed' })
      return json({})
    })
    render(
      <ReceptionTray serviceId={UCI} canMutate csrfToken="csrf-demo" onMutation={onMutation} />,
    )
    await userEvent.click(await screen.findByRole('button', { name: 'Aceptar sin cama' }))
    const dialog = await screen.findByRole('dialog', { hidden: true })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Aceptar y dejar pendiente de cama' }))
    await waitFor(() => expect(onMutation).toHaveBeenCalled())
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(`/transfer-requests/${baseTransfer.id}/accept`),
      expect.objectContaining({ method: 'POST' }),
    )
    expect(await screen.findByText('No hay solicitudes pendientes para este servicio.')).toBeInTheDocument()
  })

  it('rechazo exige motivo y conserva últimos datos válidos ante error de refresco', async () => {
    let reads = 0
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input)
      if (url.includes('/reception-tray')) {
        reads += 1
        return reads === 1
          ? json({ items: [baseTransfer], total: 1, page: 1, page_size: 100 })
          : json({ detail: 'Falla temporal.' }, 503)
      }
      return json({ ...baseTransfer, status: 'rejected' })
    })
    const { rerender } = render(
      <ReceptionTray serviceId={UCI} canMutate csrfToken="csrf" refreshToken={0} onMutation={() => undefined} />,
    )
    await userEvent.click(await screen.findByRole('button', { name: 'Rechazar' }))
    const dialog = await screen.findByRole('dialog', { hidden: true })
    const reject = within(dialog).getByRole('button', { name: 'Rechazar solicitud' })
    expect(reject).toBeDisabled()
    await userEvent.type(within(dialog).getByRole('textbox', { name: /Motivo obligatorio/ }), 'Motivo de rechazo')
    expect(reject).toBeEnabled()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Volver' }))
    rerender(<ReceptionTray serviceId={UCI} canMutate csrfToken="csrf" refreshToken={1} onMutation={() => undefined} />)
    expect(await screen.findByText(/se conservan los últimos datos válidos/i)).toBeInTheDocument()
    expect(screen.getByText('Paciente NN · NN-DEMO')).toBeInTheDocument()
  })
})
