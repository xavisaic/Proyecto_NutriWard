import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ActiveTreatmentsTab } from './ActiveTreatmentsTab'

const emptyContext = {
  admission_id: 'adm-1',
  review_status: 'not_reviewed',
  latest_review: null,
  items: [],
  counts: { active: 0, on_hold: 0, pending_verification: 0, historical: 0 },
}

const impact = {
  admission_id: 'adm-1',
  potential_energy_kcal_day: '211.20',
  energy_source_count: 1,
  items: [{
    treatment_id: 'tx-1', treatment_name: 'Propofol 2%',
    rule_code: 'potential_prescribed_energy', kind: 'potential_energy', severity: 'info',
    message: 'Aporte energético prescrito/potencial: 211.20 kcal/día.',
  }],
  disclaimer: 'Resumen informativo; no confirma administración efectiva.',
}

const propofolCatalog = {
  code: '100002090',
  alternate_code: '100002090',
  display_name: 'PROPOFOL FA 2% SOL INY 50 ML',
  route: null,
  available_inpatient: true,
  available_outpatient: false,
  restriction: null,
  clinical_profile: 'continuous_infusion',
  default_category: 'sedative_analgesic',
  source_version: 'arsenal-2025',
}

const version = {
  id: 'version-1', treatment_id: 'tx-1', version: 1, previous_version_id: null,
  medication_catalog_code: '100002090', raw_medication_text: 'Propofol',
  name: 'Propofol 2%', category: 'sedative_analgesic',
  prescription_text: 'Infusión continua según receta',
  concentration_value: '20.0000', concentration_unit: 'mg/mL', diluent_volume_ml: null,
  dose_value: null, dose_unit: null, route: 'EV', modality: 'Infusión continua',
  frequency: 'Continua', rate_value: '8.0000', rate_unit: 'mL/h',
  infusion_duration_hours: '12.00', administered_volume_ml: '90.00',
  estimated_volume_ml: '96.00', medication_catalog: propofolCatalog,
  prescribed_energy_kcal_day: '211.20', starts_at: '2026-08-19T08:00:00Z',
  planned_ends_at: null, indication: 'Sedación', order_status: 'active',
  source_type: 'medical_order', source_reference: 'Receta 08:00',
  observed_at: '2026-08-19T08:30:00Z', verification_status: 'verified',
  verified_at: '2026-08-19T08:35:00Z', verified_by_user_id: 'user-1',
  verifier_name: 'Nutricionista Demo', nutritional_note: 'Considerar energía potencial.',
  change_reason: 'Registro inicial del tratamiento.', created_by_user_id: 'user-1',
  author_name: 'Nutricionista Demo', created_at: '2026-08-19T08:35:00Z',
}

const populatedContext = {
  admission_id: 'adm-1', review_status: 'reviewed_with_findings',
  latest_review: {
    id: 'review-1', admission_id: 'adm-1', assertion: 'reviewed_with_findings',
    source_type: 'medical_order', note: null, recorded_by_user_id: 'user-1',
    author_name: 'Nutricionista Demo', recorded_at: '2026-08-19T08:35:00Z',
  },
  items: [{
    id: 'tx-1', admission_id: 'adm-1', kind: 'medication',
    created_by_user_id: 'user-1', created_at: '2026-08-19T08:35:00Z',
    current: version, history: [version],
  }],
  counts: { active: 1, on_hold: 0, pending_verification: 0, historical: 0 },
}

function response(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function mockReads(context: unknown = emptyContext) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) =>
    String(input).includes('treatment-impact-summary') ? response(impact) : response(context),
  )
}

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('Tratamientos activos', () => {
  it('diferencia una lista nunca conciliada de una revisión sin tratamientos', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      if (init?.method === 'POST') return response({})
      if (String(input).includes('treatment-impact-summary')) return response({ ...impact, potential_energy_kcal_day: 0, energy_source_count: 0, items: [] })
      return response(emptyContext)
    })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(<ActiveTreatmentsTab admissionId="adm-1" historical={false} csrfToken="csrf-demo" />)
    expect(await screen.findByText(/todavía no ha sido conciliada/)).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Una lista vacía no confirma ausencia de tratamientos.')
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar sin tratamientos relevantes' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(true))
    const request = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    expect(String(request?.[0])).toContain('/admissions/adm-1/treatments/review')
    expect(JSON.parse(String(request?.[1]?.body))).toMatchObject({ assertion: 'no_known', source_type: 'clinical_record' })
    expect(new Headers(request?.[1]?.headers).get('X-CSRF-Token')).toBe('csrf-demo')
  })

  it('pega, concilia y registra una infusión sin confundir volumen estimado con administrado', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      if (String(input).includes('/medication-catalog/match')) return response({
        items: [{ source_text: 'Propofol', status: 'matched', match: propofolCatalog, suggestions: [] }],
      })
      if (String(input).includes('/treatments/bulk') && init?.method === 'POST') {
        return response({ admission_id: 'adm-1', items: populatedContext.items }, 201)
      }
      return String(input).includes('treatment-impact-summary') ? response(impact) : response(emptyContext)
    })
    render(<ActiveTreatmentsTab admissionId="adm-1" historical={false} csrfToken="csrf-create" />)
    await userEvent.click(await screen.findByRole('button', { name: 'Agregar medicamentos' }))
    const dialog = screen.getByRole('dialog')
    await userEvent.type(within(dialog).getByRole('textbox', { name: 'Listado de medicamentos' }), 'Propofol')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Separar y revisar' }))
    expect(await within(dialog).findByText('PROPOFOL FA 2% SOL INY 50 ML')).toBeInTheDocument()
    await userEvent.type(within(dialog).getByRole('spinbutton', { name: 'Velocidad (mL/h)' }), '8')
    await userEvent.type(within(dialog).getByRole('spinbutton', { name: 'Duración (horas)' }), '12')
    await userEvent.type(within(dialog).getByRole('spinbutton', { name: 'Volumen informado (mL)' }), '90')
    expect(within(dialog).getByText(/96 mL/)).toBeInTheDocument()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar 1 medicamento' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => String(input).includes('/treatments/bulk'))).toBe(true))
    const request = fetchMock.mock.calls.find(([input]) => String(input).includes('/treatments/bulk'))
    const body = JSON.parse(String(request?.[1]?.body))
    expect(body.items[0]).toMatchObject({
      medication_catalog_code: '100002090', raw_medication_text: 'Propofol',
      name: 'PROPOFOL FA 2% SOL INY 50 ML', category: 'sedative_analgesic',
      rate_value: 8, rate_unit: 'mL/h', infusion_duration_hours: 12,
      administered_volume_ml: 90, source_type: 'medical_order',
    })
    expect(new Headers(request?.[1]?.headers).get('X-CSRF-Token')).toBe('csrf-create')
  })

  it('muestra tratamiento, energía potencial, detalle e historial versionado', async () => {
    mockReads(populatedContext)
    render(<ActiveTreatmentsTab admissionId="adm-1" historical={false} csrfToken="csrf" />)
    expect((await screen.findAllByText('Propofol 2%')).length).toBeGreaterThan(0)
    expect(screen.getByText(/^211[.,]2 kcal\/día$/)).toBeInTheDocument()
    expect(screen.getByText(/no confirma administración efectiva/)).toBeInTheDocument()
    await userEvent.click(screen.getAllByText('Propofol 2%')[0])
    expect(await screen.findByText('Historial de versiones (1)')).toBeInTheDocument()
    expect(screen.getByText(/Versión 1/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Actualizar tratamiento' })).toBeInTheDocument()
  })

  it('bloquea acciones de edición en episodios históricos', async () => {
    mockReads(populatedContext)
    render(<ActiveTreatmentsTab admissionId="adm-old" historical csrfToken="csrf" />)
    expect(await screen.findByText(/modo de sólo lectura/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Agregar medicamentos' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirmar sin tratamientos relevantes' })).not.toBeInTheDocument()
    await userEvent.click(screen.getAllByText('Propofol 2%')[0])
    expect(screen.queryByRole('button', { name: 'Actualizar tratamiento' })).not.toBeInTheDocument()
  })

  it('advierte antes de cerrar un formulario con cambios sin guardar', async () => {
    mockReads()
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    render(<ActiveTreatmentsTab admissionId="adm-1" historical={false} csrfToken="csrf" />)
    await userEvent.click(await screen.findByRole('button', { name: 'Agregar medicamentos' }))
    await userEvent.type(screen.getByRole('textbox', { name: 'Listado de medicamentos' }), 'Furosemida')
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(confirm).toHaveBeenCalledWith('Hay cambios sin guardar. ¿Desea cerrar el formulario?')
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    confirm.mockReturnValue(true)
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })
})
