import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ClinicalContextTab, parseClinicalPaste } from './ClinicalContextTab'

const emptyContext = { admission_id: 'adm-1', patient_id: 'patient-1', episode_history: null, diagnoses: [], conditions: [] }

function response(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), { status, headers: { 'Content-Type': 'application/json' } })
}

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('Diagnósticos y antecedentes', () => {
  it('convierte listas, viñetas, numeración y punto y coma en filas únicas', () => {
    expect(parseClinicalPaste('• HTA\n2. DM2; ERC\nhta\n\n- Dislipidemia')).toEqual([
      'HTA', 'DM2', 'ERC', 'Dislipidemia',
    ])
  })

  it('permite pegar y revisar varios diagnósticos antes de guardarlos', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      if (init?.method === 'POST') return response([], 201)
      return response(emptyContext)
    })
    render(<ClinicalContextTab admissionId="adm-1" patientId="patient-1" historical={false} csrfToken="csrf-demo" onChanged={vi.fn()} />)
    await screen.findByText('Sin diagnósticos registrados')
    await userEvent.click(screen.getByRole('button', { name: 'Agregar diagnósticos' }))
    await userEvent.type(screen.getByRole('textbox', { name: 'Diagnósticos' }), 'Neumonía{enter}Sepsis; Insuficiencia renal aguda')
    await userEvent.click(screen.getByRole('button', { name: 'Preparar registros' }))
    expect(screen.getByText('3 registros detectados')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Neumonía')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Guardar 3 registros' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([input, init]) =>
      String(input).includes('/admissions/adm-1/diagnoses') && init?.method === 'POST',
    )).toBe(true))
    const request = fetchMock.mock.calls.find(([input, init]) => String(input).includes('/diagnoses') && init?.method === 'POST')
    const body = JSON.parse(String(request?.[1]?.body))
    expect(body.items.map((item: { diagnosis_name: string }) => item.diagnosis_name)).toEqual([
      'Neumonía', 'Sepsis', 'Insuficiencia renal aguda',
    ])
    expect(new Headers(request?.[1]?.headers).get('X-CSRF-Token')).toBe('csrf-demo')
  })

  it('registra una historia narrativa sin convertirla en diagnósticos', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      if (init?.method === 'POST') return response({}, 201)
      return response(emptyContext)
    })
    render(<ClinicalContextTab admissionId="adm-1" patientId="patient-1" historical={false} csrfToken="csrf-history" onChanged={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Registrar historia' }))
    const narrative = 'Paciente presenta cinco días de vómitos.\n\nConsulta por deterioro progresivo.'
    await userEvent.type(screen.getByRole('textbox', { name: 'Historia del episodio actual' }), narrative)
    await userEvent.click(screen.getByRole('button', { name: 'Guardar historia' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([input, init]) =>
      String(input).includes('/admissions/adm-1/clinical-history') && init?.method === 'POST',
    )).toBe(true))
    const request = fetchMock.mock.calls.find(([input, init]) => String(input).includes('/clinical-history') && init?.method === 'POST')
    expect(JSON.parse(String(request?.[1]?.body))).toMatchObject({ narrative, source: 'clinical_record', event_start_date: null })
    expect(new Headers(request?.[1]?.headers).get('X-CSRF-Token')).toBe('csrf-history')
  })

  it('actualiza la historia creando una nueva versión con motivo', async () => {
    const current = {
      id: 'history-1', admission_id: 'adm-1', version: 1,
      narrative: 'Relato inicial del episodio actual.', event_start_date: '2026-08-10',
      source: 'patient', change_reason: null, recorded_by_user_id: 'user-1',
      author_name: 'Nutricionista Demo', recorded_at: '2026-08-16T10:00:00Z',
    }
    const context = { ...emptyContext, episode_history: { admission_id: 'adm-1', current, versions: [current] } }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) =>
      init?.method === 'PATCH' ? response({}) : response(context),
    )
    render(<ClinicalContextTab admissionId="adm-1" patientId="patient-1" historical={false} csrfToken="csrf" onChanged={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Actualizar historia' }))
    const narrative = screen.getByRole('textbox', { name: 'Historia del episodio actual' })
    await userEvent.clear(narrative)
    await userEvent.type(narrative, 'Relato actualizado con información de urgencia.')
    await userEvent.type(screen.getByRole('textbox', { name: 'Motivo de la actualización' }), 'Se agrega epicrisis de urgencia.')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar nueva versión' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH')).toBe(true))
    const request = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')
    expect(JSON.parse(String(request?.[1]?.body))).toMatchObject({
      version: 1,
      narrative: 'Relato actualizado con información de urgencia.',
      change_reason: 'Se agrega epicrisis de urgencia.',
    })
  })

  it('actualiza libremente el estado con fuente, motivo y versión', async () => {
    const diagnosis = {
      id: 'dx-1', admission_id: 'adm-1', diagnosis_name: 'Neumonía', code_system: null, code: null,
      diagnosis_type: 'principal', clinical_status: 'active', verification_status: 'provisional',
      present_on_admission: true, diagnosed_at: '2026-08-13T10:00:00Z', resolved_at: null,
      source: 'care_team', note: null, version: 4, history: [],
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) =>
      init?.method === 'PATCH' ? response({ ...diagnosis, clinical_status: 'resolved', version: 5 }) : response({ ...emptyContext, diagnoses: [diagnosis] }),
    )
    render(<ClinicalContextTab admissionId="adm-1" patientId="patient-1" historical={false} csrfToken="csrf" onChanged={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Actualizar Neumonía' }))
    await userEvent.click(screen.getByRole('combobox', { name: 'Estado clínico' }))
    await userEvent.click(screen.getByRole('option', { name: 'Resuelto' }))
    await userEvent.type(screen.getByRole('textbox', { name: 'Motivo del cambio' }), 'Resuelto según evolución.')
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH')).toBe(true))
    const request = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')
    expect(JSON.parse(String(request?.[1]?.body))).toMatchObject({ version: 4, clinical_status: 'resolved' })
  })

  it('muestra episodios históricos como solo lectura', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(response(emptyContext))
    render(<ClinicalContextTab admissionId="adm-old" patientId="patient-1" historical csrfToken="csrf" onChanged={vi.fn()} />)
    expect(await screen.findByText(/Los antecedentes mostrados son longitudinales/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Agregar diagnósticos' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Agregar antecedentes' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Registrar historia' })).not.toBeInTheDocument()
  })
})
