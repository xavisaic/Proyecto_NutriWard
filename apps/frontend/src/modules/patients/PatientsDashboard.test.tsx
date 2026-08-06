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
    if (url.includes('/patients/potential-matches')) return json({ items: [], total: 0 })
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
    await userEvent.type(within(dialog).getByLabelText('Nombres informados (opcional)'), 'Nombre NN')
    await userEvent.type(within(dialog).getByLabelText('Primer apellido informado (opcional)'), 'Apellido NN')
    await userEvent.type(within(dialog).getByLabelText('Edad estimada (opcional)'), '52')
    await userEvent.type(within(dialog).getByLabelText('Descripción provisoria'), 'Paciente sin documentos')
    expect(within(dialog).getByLabelText('Número de ficha (opcional)')).toBeInTheDocument()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear paciente NN' }))

    await waitFor(() => {
      const request = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/patients/unidentified'))
      expect(request).toBeTruthy()
      expect((request?.[1]?.headers as Headers).get('X-CSRF-Token')).toBe('csrf-demo')
      expect(JSON.parse(String(request?.[1]?.body))).toEqual(expect.objectContaining({
        given_names: 'Nombre NN',
        first_surname: 'Apellido NN',
        age_years: 52,
      }))
    })
  })

  it('bloquea una nueva ficha cuando RUT o número de ficha ya existen', async () => {
    const existing = {
      ...nnPatient,
      identity_status: 'identified',
      temporary_identifier: null,
      rut: '12345678-5',
      given_names: 'Persona',
      first_surname: 'Existente',
      active_admission: null,
      admissions: [],
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      const url = String(input)
      if (url.includes('/hospital/structure')) return json(structure)
      if (url.includes('/admissions/active')) return json({ items: [], total: 0 })
      if (url.includes('/patients/potential-matches')) return json({ items: [existing], total: 1 })
      if (url.endsWith(`/patients/${existing.id}`)) return json(existing)
      if (url.includes('/patients?')) return json({ items: [existing], total: 1, page: 1, page_size: 10 })
      return json({})
    })
    render(<PatientsDashboard canMutate csrfToken="csrf-demo" />)
    await screen.findByText('Persona Existente')
    await userEvent.click(screen.getByRole('button', { name: 'Crear paciente' }))
    const dialog = await screen.findByRole('dialog', { hidden: true })
    await userEvent.type(within(dialog).getByRole('textbox', { name: /^RUT/ }), '12.345.678-5')
    await userEvent.type(within(dialog).getByRole('textbox', { name: /^Nombres/ }), 'Persona')
    await userEvent.type(within(dialog).getByRole('textbox', { name: /^Primer apellido/ }), 'Existente')
    await userEvent.type(within(dialog).getByLabelText('Número de ficha (opcional)'), 'urg-001')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear paciente' }))

    expect(await within(dialog).findByText(/Ya existe una ficha con el mismo RUT o número de ficha/)).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'Crear ficha diferente' })).toBeDisabled()
    expect(fetchMock.mock.calls.some(([url, options]) => (
      String(url).endsWith('/patients') && options?.method === 'POST'
    ))).toBe(false)
  })

  it('permite confirmar una coincidencia sólo nominal y normaliza el número de ficha', async () => {
    const similar = { ...nnPatient, active_admission: null, admissions: [] }
    const created = {
      ...similar,
      id: '50000000-0000-0000-0000-000000000098',
      identity_status: 'identified',
      temporary_identifier: null,
      rut: '10000004-0',
      given_names: 'Nombre',
      first_surname: 'Similar',
      hospital_identifier: 'FICHA-X1',
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      const url = String(input)
      if (url.includes('/hospital/structure')) return json(structure)
      if (url.includes('/admissions/active')) return json({ items: [], total: 0 })
      if (url.includes('/patients/potential-matches')) return json({ items: [similar], total: 1 })
      if (url.endsWith('/patients') && init?.method === 'POST') return json(created, 201)
      if (url.includes('/patients?')) return json({ items: [similar], total: 1, page: 1, page_size: 10 })
      if (url.endsWith(`/patients/${similar.id}`)) return json(similar)
      return json({})
    })
    render(<PatientsDashboard canMutate csrfToken="csrf-demo" />)
    await screen.findByText(`Paciente NN · ${nnPatient.temporary_identifier}`)
    await userEvent.click(screen.getByRole('button', { name: 'Crear paciente' }))
    const dialog = await screen.findByRole('dialog', { hidden: true })
    await userEvent.type(within(dialog).getByRole('textbox', { name: /^RUT/ }), '10.000.004-0')
    await userEvent.type(within(dialog).getByRole('textbox', { name: /^Nombres/ }), 'Nombre')
    await userEvent.type(within(dialog).getByRole('textbox', { name: /^Primer apellido/ }), 'Similar')
    await userEvent.type(within(dialog).getByLabelText('Número de ficha (opcional)'), 'ficha-x1')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear paciente' }))
    await userEvent.click(await within(dialog).findByRole('checkbox', {
      name: /Revisé las coincidencias/,
    }))
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear ficha diferente' }))

    await waitFor(() => {
      const request = fetchMock.mock.calls.find(([url, options]) => (
        String(url).endsWith('/patients') && options?.method === 'POST'
      ))
      expect(request).toBeTruthy()
      expect(JSON.parse(String(request?.[1]?.body)).hospital_identifier).toBe('FICHA-X1')
    })
  })

  it('muestra el nombre informado y la edad estimada de un paciente NN', async () => {
    const namedNn = {
      ...nnPatient,
      given_names: 'Nombre',
      first_surname: 'Informado',
      date_of_birth: '1974-08-05',
      date_of_birth_is_estimated: true,
    }
    mockApi(namedNn)
    render(<PatientsDashboard canMutate csrfToken="csrf-demo" />)

    await userEvent.click(await screen.findByText(`Nombre Informado · ${nnPatient.temporary_identifier}`))
    expect(await screen.findByText(/Edad: 52 años · edad estimada/)).toBeInTheDocument()
    expect(screen.getByText('N.º ficha: URG-001')).toBeInTheDocument()
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

  it('compara y concilia explícitamente una ficha NN con un RUT histórico', async () => {
    const historicalAdmission = {
      ...admission,
      id: '30000000-0000-0000-0000-000000000099',
      admission_identifier: 'ADM-HIST-001',
      status: 'discharged',
      ended_at: '2026-01-10T10:00:00Z',
      current_location: null,
      location_history: [],
    }
    const canonical = {
      ...nnPatient,
      id: '50000000-0000-0000-0000-000000000088',
      identity_status: 'identified',
      temporary_identifier: null,
      rut: '12345678-5',
      given_names: 'Persona',
      first_surname: 'Histórica',
      date_of_birth: '1980-02-10',
      date_of_birth_is_estimated: false,
      hospital_identifier: 'FICHA-ANTIGUA',
      active_admission: null,
      admissions: [historicalAdmission],
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      const url = String(input)
      if (url.includes('/hospital/structure')) return json(structure)
      if (url.includes('/admissions/active')) return json({ items: [admission], total: 1 })
      if (url.endsWith(`/patients/${nnPatient.id}/identity`) && init?.method === 'PATCH') {
        return json({ detail: 'El RUT ya pertenece a otro paciente; debe realizar una conciliación explícita.' }, 409)
      }
      if (url.endsWith(`/patients/${nnPatient.id}/reconcile`) && init?.method === 'POST') {
        return json({ ...canonical, active_admission: admission, admissions: [admission, historicalAdmission] })
      }
      if (url.endsWith(`/patients/${canonical.id}`)) return json(canonical)
      if (url.includes('/patients?q=')) return json({ items: [canonical], total: 1, page: 1, page_size: 20 })
      if (url.endsWith(`/patients/${nnPatient.id}`)) return json(nnPatient)
      if (url.includes('/patients?')) return json({ items: [nnPatient], total: 1, page: 1, page_size: 10 })
      return json({})
    })
    render(<PatientsDashboard canMutate csrfToken="csrf-demo" />)
    await userEvent.click(await screen.findByText(`Paciente NN · ${nnPatient.temporary_identifier}`))
    await userEvent.click(await screen.findByRole('button', { name: 'Identificar paciente' }))
    const dialog = await screen.findByRole('dialog', { hidden: true })
    await userEvent.type(within(dialog).getByRole('textbox', { name: /RUT confirmado/ }), '12.345.678-5')
    await userEvent.type(within(dialog).getByRole('textbox', { name: /Nombres/ }), 'Persona')
    await userEvent.type(within(dialog).getByRole('textbox', { name: /Primer apellido/ }), 'Histórica')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Confirmar identidad' }))

    expect(await within(dialog).findByText('Conciliación requerida')).toBeInTheDocument()
    expect(within(dialog).getByText('Ficha NN actual')).toBeInTheDocument()
    expect(within(dialog).getByText('Ficha histórica principal')).toBeInTheDocument()
    expect(within(dialog).getByText(/FICHA-ANTIGUA/)).toBeInTheDocument()
    expect(within(dialog).getByText(/1 hospitalización registrada/)).toBeInTheDocument()
    expect(within(dialog).getByText(/La ficha histórica seguirá siendo la principal/)).toBeInTheDocument()

    const reconcileButton = within(dialog).getByRole('button', { name: 'Conciliar y conservar historial' })
    expect(reconcileButton).toBeDisabled()
    await userEvent.type(
      within(dialog).getByRole('textbox', { name: /Motivo de conciliación/ }),
      'Identidad confirmada con antecedentes institucionales.',
    )
    await userEvent.click(within(dialog).getByRole('checkbox', {
      name: 'Confirmo que ambas fichas corresponden a la misma persona.',
    }))
    expect(reconcileButton).toBeEnabled()
    await userEvent.click(reconcileButton)

    await waitFor(() => {
      const request = fetchMock.mock.calls.find(([url, options]) => (
        String(url).endsWith(`/patients/${nnPatient.id}/reconcile`)
        && options?.method === 'POST'
      ))
      expect(request).toBeTruthy()
      expect(JSON.parse(String(request?.[1]?.body))).toEqual({
        rut: canonical.rut,
        reason: 'Identidad confirmada con antecedentes institucionales.',
      })
    })
  })

  it('bloquea la conciliación visual si ambas fichas tienen ingresos activos', async () => {
    const canonical = {
      ...nnPatient,
      id: '50000000-0000-0000-0000-000000000077',
      identity_status: 'identified',
      temporary_identifier: null,
      rut: '12345678-5',
      given_names: 'Paciente',
      first_surname: 'Existente',
      active_admission: { ...admission, id: '30000000-0000-0000-0000-000000000077' },
      admissions: [{ ...admission, id: '30000000-0000-0000-0000-000000000077' }],
    }
    vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      const url = String(input)
      if (url.includes('/hospital/structure')) return json(structure)
      if (url.includes('/admissions/active')) return json({ items: [admission], total: 1 })
      if (url.endsWith(`/patients/${nnPatient.id}/identity`) && init?.method === 'PATCH') {
        return json({ detail: 'El RUT ya pertenece a otro paciente.' }, 409)
      }
      if (url.endsWith(`/patients/${canonical.id}`)) return json(canonical)
      if (url.includes('/patients?q=')) return json({ items: [canonical], total: 1, page: 1, page_size: 20 })
      if (url.endsWith(`/patients/${nnPatient.id}`)) return json(nnPatient)
      if (url.includes('/patients?')) return json({ items: [nnPatient], total: 1, page: 1, page_size: 10 })
      return json({})
    })
    render(<PatientsDashboard canMutate csrfToken="csrf-demo" />)
    await userEvent.click(await screen.findByText(`Paciente NN · ${nnPatient.temporary_identifier}`))
    await userEvent.click(await screen.findByRole('button', { name: 'Identificar paciente' }))
    const dialog = await screen.findByRole('dialog', { hidden: true })
    await userEvent.type(within(dialog).getByRole('textbox', { name: /RUT confirmado/ }), '12.345.678-5')
    await userEvent.type(within(dialog).getByRole('textbox', { name: /Nombres/ }), 'Paciente')
    await userEvent.type(within(dialog).getByRole('textbox', { name: /Primer apellido/ }), 'Existente')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Confirmar identidad' }))

    expect(await within(dialog).findByText(/Ambas fichas tienen hospitalizaciones activas/)).toBeInTheDocument()
    await userEvent.type(
      within(dialog).getByRole('textbox', { name: /Motivo de conciliación/ }),
      'Coincidencia revisada por el equipo responsable.',
    )
    await userEvent.click(within(dialog).getByRole('checkbox', {
      name: 'Confirmo que ambas fichas corresponden a la misma persona.',
    }))
    expect(within(dialog).getByRole('button', { name: 'Conciliar y conservar historial' })).toBeDisabled()
  })

  it('permite a jefatura cerrar administrativamente un ingreso duplicado y conciliar', async () => {
    const canonicalAdmission = {
      ...admission,
      id: '30000000-0000-0000-0000-000000000077',
      admission_identifier: 'ADM-CANONICA',
    }
    const canonical = {
      ...nnPatient,
      id: '50000000-0000-0000-0000-000000000077',
      identity_status: 'identified',
      temporary_identifier: null,
      rut: '12345678-5',
      given_names: 'Paciente',
      first_surname: 'Existente',
      active_admission: canonicalAdmission,
      admissions: [canonicalAdmission],
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      const url = String(input)
      if (url.includes('/hospital/structure')) return json(structure)
      if (url.includes('/admissions/active')) return json({ items: [admission, canonicalAdmission], total: 2 })
      if (url.endsWith(`/patients/${nnPatient.id}/identity`) && init?.method === 'PATCH') {
        return json({ detail: 'El RUT ya pertenece a otro paciente.' }, 409)
      }
      if (url.endsWith(`/patients/${nnPatient.id}/reconcile-active-conflict`) && init?.method === 'POST') {
        return json({ ...canonical, active_admission: canonicalAdmission, admissions: [canonicalAdmission] })
      }
      if (url.endsWith(`/patients/${canonical.id}`)) return json(canonical)
      if (url.includes('/patients?q=')) return json({ items: [canonical], total: 1, page: 1, page_size: 20 })
      if (url.endsWith(`/patients/${nnPatient.id}`)) return json(nnPatient)
      if (url.includes('/patients?')) return json({ items: [nnPatient], total: 1, page: 1, page_size: 10 })
      return json({})
    })
    render(
      <PatientsDashboard
        canMutate
        canResolveActiveConflicts
        csrfToken="csrf-demo"
      />,
    )
    await userEvent.click(await screen.findByText(`Paciente NN · ${nnPatient.temporary_identifier}`))
    await userEvent.click(await screen.findByRole('button', { name: 'Identificar paciente' }))
    const dialog = await screen.findByRole('dialog', { hidden: true })
    await userEvent.type(within(dialog).getByRole('textbox', { name: /RUT confirmado/ }), '12.345.678-5')
    await userEvent.type(within(dialog).getByRole('textbox', { name: /Nombres/ }), 'Paciente')
    await userEvent.type(within(dialog).getByRole('textbox', { name: /Primer apellido/ }), 'Existente')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Confirmar identidad' }))

    const selector = await within(dialog).findByRole('combobox', {
      name: 'Ingreso duplicado que se cerrará',
    })
    await userEvent.click(selector)
    await userEvent.click(await screen.findByRole('option', {
      name: `${admission.admission_identifier} · ficha NN actual`,
    }))
    await userEvent.type(
      within(dialog).getByRole('textbox', { name: /Motivo de conciliación/ }),
      'Duplicidad confirmada por jefatura responsable.',
    )
    await userEvent.click(within(dialog).getByRole('checkbox', {
      name: 'Confirmo que ambas fichas corresponden a la misma persona.',
    }))
    await userEvent.click(within(dialog).getByRole('button', {
      name: 'Resolver duplicidad y conciliar',
    }))

    await waitFor(() => {
      const request = fetchMock.mock.calls.find(([url, options]) => (
        String(url).endsWith(`/patients/${nnPatient.id}/reconcile-active-conflict`)
        && options?.method === 'POST'
      ))
      expect(request).toBeTruthy()
      expect(JSON.parse(String(request?.[1]?.body))).toEqual(expect.objectContaining({
        admission_to_close_id: admission.id,
        rut: canonical.rut,
      }))
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
