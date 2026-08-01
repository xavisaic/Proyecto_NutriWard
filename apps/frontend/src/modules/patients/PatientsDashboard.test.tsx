import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { PatientsDashboard } from './PatientsDashboard'

const location = {
  id: '40000000-0000-0000-0000-000000000001',
  admission_id: '30000000-0000-0000-0000-000000000001',
  care_unit_id: '20000000-0000-0000-0000-000000000001',
  started_at: '2026-07-31T12:00:00Z',
  ended_at: null,
  reason: 'Cama inicial',
  assigned_by_user_id: '10000000-0000-0000-0000-000000000001',
  ended_by_user_id: null,
  created_at: '2026-07-31T12:00:00Z',
  care_unit_code: '01',
  care_unit_label: 'Cama 01',
  room_id: '21000000-0000-0000-0000-000000000001',
  room_code: 'A101',
  room_name: 'Sala A101',
  service_id: '22000000-0000-0000-0000-000000000001',
  service_code: 'MED',
  service_name: 'Medicina',
}

const admission = {
  id: '30000000-0000-0000-0000-000000000001',
  patient_id: '50000000-0000-0000-0000-000000000001',
  admission_identifier: 'ADM-20260731-ABC123',
  status: 'active',
  admitted_at: '2026-07-31T12:00:00Z',
  ended_at: null,
  end_reason: null,
  created_at: '2026-07-31T12:00:00Z',
  updated_at: '2026-07-31T12:00:00Z',
  current_location: location,
  status_history: [],
  location_history: [location],
}

const nnPatient = {
  id: '50000000-0000-0000-0000-000000000001',
  identity_status: 'unidentified',
  temporary_identifier: 'NN-20260731-ABCD',
  rut: null,
  given_names: null,
  first_surname: null,
  second_surname: null,
  date_of_birth: null,
  date_of_birth_is_estimated: true,
  sex: 'unknown',
  hospital_identifier: 'URG-001',
  phone: null,
  provisional_description: 'Persona adulta de identidad desconocida.',
  identified_at: null,
  merged_into_patient_id: null,
  is_active: true,
  created_at: '2026-07-31T11:30:00Z',
  updated_at: '2026-07-31T11:30:00Z',
  active_admission: admission,
  admissions: [admission],
}

const structure = {
  total: 1,
  items: [{
    id: '22000000-0000-0000-0000-000000000001',
    code: 'MED',
    name: 'Medicina',
    description: null,
    is_active: true,
    created_at: '2026-07-01T00:00:00Z',
    updated_at: '2026-07-01T00:00:00Z',
    rooms: [{
      id: '21000000-0000-0000-0000-000000000001',
      service_id: '22000000-0000-0000-0000-000000000001',
      code: 'A101',
      name: 'Sala A101',
      floor: 'Piso 1',
      notes: null,
      is_active: true,
      created_at: '2026-07-01T00:00:00Z',
      updated_at: '2026-07-01T00:00:00Z',
      care_units: [
        {
          id: '20000000-0000-0000-0000-000000000001',
          room_id: '21000000-0000-0000-0000-000000000001',
          code: '01',
          label: 'Cama 01',
          unit_type: 'bed',
          is_active: true,
          layout: null,
          created_at: '2026-07-01T00:00:00Z',
          updated_at: '2026-07-01T00:00:00Z',
        },
        {
          id: '20000000-0000-0000-0000-000000000002',
          room_id: '21000000-0000-0000-0000-000000000001',
          code: '02',
          label: 'Cama 02',
          unit_type: 'bed',
          is_active: true,
          layout: null,
          created_at: '2026-07-01T00:00:00Z',
          updated_at: '2026-07-01T00:00:00Z',
        },
      ],
    }],
  }],
}

function json(payload: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  }))
}

function mockApi(patient: any = nnPatient, activeItems: any[] = [admission]) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
    const url = String(input)
    if (url.includes('/hospital/structure')) return json(structure)
    if (url.includes('/admissions/active')) return json({ items: activeItems, total: activeItems.length })
    if (url.includes(`/patients/${patient.id}`)) return json(patient)
    if (url.includes('/patients?')) {
      return json({ items: [patient], total: 1, page: 1, page_size: 10 })
    }
    if (url.endsWith('/patients/unidentified') && init?.method === 'POST') {
      return json({ ...nnPatient, id: '50000000-0000-0000-0000-000000000099', active_admission: null }, 201)
    }
    return json({})
  })
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('pacientes', () => {
  it('renderiza el listado, el indicador NN y permite buscar', async () => {
    const fetchMock = mockApi()
    render(<PatientsDashboard canMutate csrfToken="csrf-demo" />)

    expect(await screen.findByText(`Paciente NN · ${nnPatient.temporary_identifier}`)).toBeInTheDocument()
    expect(screen.getAllByText('Paciente NN').length).toBeGreaterThan(0)
    const search = screen.getByLabelText('Buscar por nombre, RUT o identificador')
    await userEvent.type(search, nnPatient.temporary_identifier)
    await userEvent.click(screen.getByRole('button', { name: 'Buscar' }))
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining(`q=${encodeURIComponent(nnPatient.temporary_identifier)}`),
        expect.anything(),
      )
    })
  })

  it('muestra la ficha, hospitalización y ubicación actual', async () => {
    mockApi()
    render(<PatientsDashboard canMutate csrfToken="csrf-demo" />)
    await userEvent.click(await screen.findByText(`Paciente NN · ${nnPatient.temporary_identifier}`))

    expect(await screen.findByText('ADM-20260731-ABC123')).toBeInTheDocument()
    expect(screen.getAllByText(/Medicina · Sala A101 · Cama 01/).length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: 'Trasladar de cama' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Terminar hospitalización' })).toBeInTheDocument()
  })

  it('crea un paciente NN enviando CSRF', async () => {
    const fetchMock = mockApi()
    render(<PatientsDashboard canMutate csrfToken="csrf-demo" />)
    await screen.findByText(`Paciente NN · ${nnPatient.temporary_identifier}`)
    await userEvent.click(screen.getByRole('button', { name: 'Crear paciente' }))
    const dialog = await screen.findByRole('dialog', { hidden: true })
    await userEvent.click(within(dialog).getByRole('combobox', { name: 'Tipo de ficha' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Paciente NN' }))
    await userEvent.type(within(dialog).getByLabelText('Descripción provisoria'), 'Paciente sin documentos')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear paciente NN' }))

    await waitFor(() => {
      const request = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/patients/unidentified'))
      expect(request).toBeTruthy()
      expect((request?.[1]?.headers as Headers).get('X-CSRF-Token')).toBe('csrf-demo')
    })
  })

  it('distingue cama ocupada y disponible al trasladar', async () => {
    const fetchMock = mockApi()
    render(<PatientsDashboard canMutate csrfToken="csrf-demo" />)
    await userEvent.click(await screen.findByText(`Paciente NN · ${nnPatient.temporary_identifier}`))
    await userEvent.click(await screen.findByRole('button', { name: 'Trasladar de cama' }))
    const dialog = await screen.findByRole('dialog', { hidden: true })
    await userEvent.click(within(dialog).getByRole('combobox', { name: 'Cama' }))

    expect(await screen.findByText(/Cama 01 — Ocupada|Cama 01 — Ubicación actual/)).toBeInTheDocument()
    expect(screen.getByText(/Cama 02 — Disponible/)).toBeInTheDocument()
    await userEvent.click(screen.getByText(/Cama 02 — Disponible/))
    await userEvent.type(within(dialog).getByLabelText('Motivo'), 'Traslado de prueba')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Confirmar traslado' }))
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining(`/admissions/${admission.id}/location`),
        expect.objectContaining({ method: 'POST' }),
      )
    })
  })

  it('abre la identificación posterior sin perder el identificador temporal', async () => {
    const fetchMock = mockApi()
    render(<PatientsDashboard canMutate csrfToken="csrf-demo" />)
    await userEvent.click(await screen.findByText(`Paciente NN · ${nnPatient.temporary_identifier}`))
    await userEvent.click(await screen.findByRole('button', { name: 'Identificar paciente' }))
    const dialog = await screen.findByRole('dialog', { hidden: true })
    expect(within(dialog).getByText(new RegExp(nnPatient.temporary_identifier))).toBeInTheDocument()
    await userEvent.type(within(dialog).getByRole('textbox', { name: /RUT confirmado/ }), '12345678-5')
    await userEvent.type(within(dialog).getByRole('textbox', { name: /Nombres/ }), 'Persona')
    await userEvent.type(within(dialog).getByRole('textbox', { name: /Primer apellido/ }), 'Identificada')
    expect(within(dialog).getByRole('button', { name: 'Confirmar identidad' })).toBeInTheDocument()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Confirmar identidad' }))
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining(`/patients/${nnPatient.id}/identity`),
        expect.objectContaining({ method: 'PATCH' }),
      )
    })
  })

  it('crea una hospitalización desde una ficha sin ingreso activo', async () => {
    const withoutAdmission = {
      ...nnPatient,
      active_admission: null,
      admissions: [],
    }
    const fetchMock = mockApi(withoutAdmission, [])
    render(<PatientsDashboard canMutate csrfToken="csrf-demo" />)
    await userEvent.click(await screen.findByText(`Paciente NN · ${nnPatient.temporary_identifier}`))
    await userEvent.click(await screen.findByRole('button', { name: 'Crear hospitalización' }))
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringMatching(/\/admissions$/),
        expect.objectContaining({ method: 'POST' }),
      )
    })
  })

  it('deja la ficha en modo sólo lectura cuando el rol no puede mutar', async () => {
    mockApi()
    render(<PatientsDashboard canMutate={false} csrfToken="csrf-demo" />)

    expect(await screen.findByText(`Paciente NN · ${nnPatient.temporary_identifier}`)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Crear paciente' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByText(`Paciente NN · ${nnPatient.temporary_identifier}`))

    expect(await screen.findByText('ADM-20260731-ABC123')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Identificar paciente' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Trasladar de cama' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Terminar hospitalización' })).not.toBeInTheDocument()
  })
})
