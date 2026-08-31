import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  NutritionActivityCard,
  NutritionClinicalTab,
  NutritionRegisterAction,
  NutritionSummaryCard,
} from './NutritionClinicalTabs'

function response(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), { status, headers: { 'Content-Type': 'application/json' } })
}

const emptyList = { items: [], total: 0, page: 1, page_size: 20 }

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('Ficha nutricional clínica', () => {
  it('crea un borrador explícito, navega secciones y adapta el tamizaje por población', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      if (init?.method === 'POST') return response({ encounter: { id: 'enc-1', admission_id: 'adm-1', encounter_datetime: '2026-08-13T10:00:00Z', encounter_type: 'initial_assessment', author_professional_id: 'user-1', author_name: 'Nutricionista', status: 'draft', clinical_summary: null, finalized_at: null, corrected_encounter_id: null, version: 1, reason_for_assessment: null, information_source: 'combined', correction_reason: null, cancellation_reason: null }, author_name: 'Nutricionista', finalized_by_name: null, assessment: null, context_items: [], anthropometry: [], screenings: [], requirements: [], diagnoses: [], prescription: null, monitoring: [], intake: [], labs: [], alerts: [] }, 201)
      return response(emptyList)
    })
    render(<NutritionRegisterAction admissionId="adm-1" csrfToken="csrf" onSaved={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Registrar' }))
    await userEvent.click(screen.getByRole('button', { name: /Evaluación nutricional inicial/ }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '1' }))
    await userEvent.click(screen.getAllByRole('combobox')[2])
    await userEvent.click(screen.getByRole('option', { name: 'Neonatología' }))
    await userEvent.click(screen.getByRole('button', { name: '4' }))
    expect(screen.getByText(/Predeterminada para Neonatología: none/)).toBeInTheDocument()
    expect(screen.getByRole('combobox')).toHaveTextContent('Sin herramienta definida')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar borrador' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(true))
    const createCall = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    expect(createCall?.[1]?.headers).toBeDefined()
    expect(JSON.parse(String(createCall?.[1]?.body)).screenings[0].tool_code).toBe('none')
  })

  it('impide edición en episodio histórico y muestra sólo lectura', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(response(emptyList))
    render(<NutritionActivityCard admissionId="adm-old" historical csrfToken="csrf" onChanged={vi.fn()} />)
    expect(await screen.findByText('Episodio histórico · Solo lectura. Las evoluciones finalizadas permanecen disponibles.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Registrar' })).not.toBeInTheDocument()
  })

  it('crea un seguimiento rápido sólo con los módulos seleccionados', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      if (init?.method === 'POST') return response({
        encounter: { id: 'enc-follow', status: 'draft', version: 1 },
        assessment: null, context_items: [], anthropometry: [], screenings: [], requirements: [],
        diagnoses: [], prescription: null, monitoring: [], intake: [], labs: [], alerts: [],
      }, 201)
      return response(emptyList)
    })
    render(<NutritionRegisterAction admissionId="adm-1" csrfToken="csrf" onSaved={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Registrar' }))
    await userEvent.click(screen.getByRole('button', { name: /Seguimiento rápido/ }))
    await userEvent.type(screen.getByRole('textbox', { name: 'Motivo de evaluación' }), 'Control diario')
    await userEvent.click(screen.getByRole('button', { name: '10' }))
    await userEvent.type(screen.getByRole('textbox', { name: 'Síntesis clínica' }), 'Paciente tolera parcialmente la alimentación.')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar borrador' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(true))
    const createCall = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    const payload = JSON.parse(String(createCall?.[1]?.body))
    expect(payload.encounter_type).toBe('follow_up')
    expect(payload.screenings).toEqual([])
    expect(payload.diagnoses).toEqual([])
    expect(payload.prescription).toBeNull()
  })

  it('guía el NRS-2002 y calcula el riesgo en tiempo real sin enviar un puntaje autoritativo', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      if (init?.method === 'POST') return response({
        encounter: { id: 'enc-nrs', status: 'draft', version: 1 }, assessment: null,
        context_items: [], anthropometry: [], advanced_measurements: [], screenings: [], requirements: [],
        diagnoses: [], prescription: null, monitoring: [], intake: [], labs: [], alerts: [],
      }, 201)
      return response(emptyList)
    })
    render(<NutritionRegisterAction admissionId="adm-1" csrfToken="csrf" patientDateOfBirth="1950-01-01" patientAgeIsEstimated={false} onSaved={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Registrar' }))
    await userEvent.click(screen.getByRole('button', { name: /Evaluación nutricional inicial/ }))
    await userEvent.click(screen.getByRole('button', { name: '4' }))

    await userEvent.type(screen.getByRole('spinbutton', { name: 'IMC utilizado' }), '19')
    expect(screen.getByText('Sí · calculado')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Sí · ¿Ha perdido peso durante los últimos 3 meses?' }))
    await userEvent.click(screen.getByRole('button', { name: 'Sí · ¿Redujo la ingesta durante la última semana?' }))
    await userEvent.click(screen.getByRole('button', { name: 'No · ¿Está gravemente enfermo o en tratamiento intensivo?' }))

    await userEvent.click(screen.getByRole('combobox', { name: 'Pérdida de peso' }))
    await userEvent.click(screen.getByRole('option', { name: '2 · Más de 5% en 2 meses' }))
    await userEvent.click(screen.getByRole('combobox', { name: 'Ingesta respecto del requerimiento' }))
    await userEvent.click(screen.getByRole('option', { name: '1 · 50–75%' }))
    await userEvent.click(screen.getByRole('button', { name: 'Sí · ¿Existe deterioro del estado general asociado al IMC?' }))
    await userEvent.click(screen.getByRole('button', { name: /2 · Gravedad moderada/ }))

    expect(screen.getByText(/70 años o más · \+1 punto/)).toBeInTheDocument()
    expect(screen.getByText(/Con riesgo nutricional: efectuar valoración completa/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Guardar borrador' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(true))
    const createCall = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    const payload = JSON.parse(String(createCall?.[1]?.body))
    const answers = Object.fromEntries(payload.screenings[0].answers.map((answer: { answer_code: string, answer_value: string }) => [answer.answer_code, answer.answer_value]))
    expect(answers).toMatchObject({
      screening_flow_version: 'v2', initial_bmi_below_20_5: 'true',
      weight_loss_category: 'over_5_2_months', intake_category: '50_75',
      disease_severity_score: '2', age_70_or_more: 'true', age_source: 'patient_record_exact',
    })
    expect(answers.nutritional_status_score).toBeUndefined()
  }, 30_000)

  it('registra circunferencias y la serie bilateral de dinamometría en una evolución', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      if (init?.method === 'POST') return response({
        encounter: { id: 'enc-anthro', status: 'draft', version: 1 }, assessment: null,
        context_items: [], anthropometry: [], advanced_measurements: [], screenings: [], requirements: [],
        diagnoses: [], prescription: null, monitoring: [], intake: [], labs: [], alerts: [],
      }, 201)
      return response(emptyList)
    })
    render(<NutritionRegisterAction admissionId="adm-1" csrfToken="csrf" onSaved={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Registrar' }))
    await userEvent.click(screen.getByRole('button', { name: /Acción específica/ }))
    await userEvent.click(screen.getByText('Antropometría'))
    await userEvent.click(screen.getByRole('button', { name: '3' }))

    expect(screen.getByText('Cuatro pliegues · Durnin–Womersley')).toBeInTheDocument()
    expect(screen.getByText('Bioimpedancia clínica')).toBeInTheDocument()
    await userEvent.type(screen.getByRole('spinbutton', { name: 'Pantorrilla izquierda' }), '31.5')
    await userEvent.type(screen.getByRole('textbox', { name: 'Fabricante del dinamómetro' }), 'Jamar')
    await userEvent.type(screen.getByRole('textbox', { name: 'Modelo del dinamómetro' }), 'Plus+')
    await userEvent.type(screen.getByRole('textbox', { name: 'Posición y protocolo aplicado' }), 'Sentado, codo a 90 grados')
    for (const [label, result] of [
      ['Izquierda · intento 1', '20'], ['Izquierda · intento 2', '22'], ['Izquierda · intento 3', '21'],
      ['Derecha · intento 1', '24'], ['Derecha · intento 2', '25'], ['Derecha · intento 3', '23'],
    ]) await userEvent.type(screen.getByRole('spinbutton', { name: label }), result)

    await userEvent.click(screen.getByRole('button', { name: 'Guardar borrador' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(true))
    const createCall = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    const payload = JSON.parse(String(createCall?.[1]?.body))
    expect(payload.advanced_measurements).toHaveLength(2)
    expect(payload.advanced_measurements[0].values[0]).toMatchObject({ measurement_code: 'calf_circumference', laterality: 'left', value: 31.5, unit: 'cm' })
    expect(payload.advanced_measurements[1]).toMatchObject({ session_type: 'handgrip', protocol_code: 'hospital-handgrip', device_manufacturer: 'Jamar', device_model: 'Plus+' })
    expect(payload.advanced_measurements[1].values).toHaveLength(6)
  }, 30_000)

  it('permite iniciar una modificación de prescripción desde su propio módulo', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(response(emptyList))
    render(<NutritionClinicalTab tab="prescription" admissionId="adm-1" historical={false} csrfToken="csrf" onChanged={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Modificar prescripción' }))
    expect(screen.getByRole('heading', { name: 'Acción específica' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '9' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '3' })).not.toBeInTheDocument()
  })

  it('muestra antropometría avanzada y el historial de tamizajes en pestañas propias', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (String(input).includes('/nutrition-anthropometry')) return response({
        items: [
          { id: 'weight-1', record_type: 'measurement', measurement_type: 'current_weight_measured', value: '72.0000', unit: 'kg', measured_at: '2026-08-13T09:00:00Z', value_nature: 'measured', reliability: 'high' },
          { id: 'bia-1', record_type: 'advanced_session', session_type: 'bioimpedance', measured_at: '2026-08-13T08:00:00Z', protocol_code: 'device-reported-bia', protocol_version: 'v1', algorithm_version: null, device_manufacturer: 'InBody', device_model: 'S10', device_serial: null, technology: 'multifrequency', frequencies_khz: null, position: 'supino', source: 'clinical_record', reliability: 'high', preparation_status: 'standard', fasting_hours: '4.00', recent_exercise: false, bladder_emptied: true, hydration_status: 'usual', edema_present: false, observations: null, values: [{ id: 'fat-1', measurement_code: 'fat_mass', body_site: null, laterality: 'none', attempt_number: null, value: '18.0000', unit: 'kg', value_nature: 'device_reported', observations: null }] },
        ], total: 2, page: 1, page_size: 50,
      })
      if (String(input).includes('/nutrition-screenings')) return response({
        items: [{ id: 'screen-1', tool_code: 'nrs_2002', total_score: '3.00', classification: 'nutritional_risk', algorithm_version: 'espen-nrs2002-v2', applied_at: '2026-08-13T10:00:00Z', answers: [] }], total: 1, page: 1, page_size: 20,
      })
      return response(emptyList)
    })
    const { rerender } = render(<NutritionClinicalTab tab="anthropometry" admissionId="adm-1" historical={false} csrfToken="csrf" onChanged={vi.fn()} />)
    expect(await screen.findByText('Peso actual medido')).toBeInTheDocument()
    expect(screen.getByText('Bioimpedancia clínica')).toBeInTheDocument()
    expect(screen.getByText(/18.0000 kg/)).toBeInTheDocument()
    rerender(<NutritionClinicalTab tab="screening" admissionId="adm-1" historical={false} csrfToken="csrf" onChanged={vi.fn()} />)
    expect(await screen.findByText(/NRS-2002 · Con riesgo nutricional/)).toBeInTheDocument()
    expect(screen.getByText('Puntaje 3.00')).toBeInTheDocument()
  })

  it('reúne requerimientos y diagnósticos PES dentro de evaluación clínica', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => String(input).includes('/nutrition-latest')
      ? response({ admission_id: 'adm-1', latest_encounter: { id: 'enc-1' }, latest_screening: null, nutritional_status: 'Riesgo', active_diagnoses: [{ id: 'pes-1', generated_statement: 'Ingesta insuficiente relacionada con anorexia' }], current_prescription: null, adopted_requirements: [{ id: 'req-1', nutrient_code: 'energy', adopted_result: '1900.00', unit: 'kcal/day', method: 'factorial' }], active_alerts: [], suggested_reassessment_at: null })
      : response({ items: [{ id: 'assessment-1', encounter_id: 'enc-1', observed_at: '2026-08-13T10:00:00Z', population_group: 'adult', nutritional_status: 'Riesgo', clinical_findings: 'Pérdida de peso', digestive_findings: 'Sin síntomas', objectives: 'Cubrir requerimientos', monitoring_plan: 'Control semanal', pending_actions: null }], total: 1, page: 1, page_size: 20 }))
    render(<NutritionClinicalTab tab="assessment" admissionId="adm-1" historical={false} csrfToken="csrf" onChanged={vi.fn()} />)
    expect(await screen.findByText('Requerimientos adoptados')).toBeInTheDocument()
    expect(screen.getByText(/1900.00 kcal\/day/)).toBeInTheDocument()
    expect(screen.getByText('Diagnósticos PES activos')).toBeInTheDocument()
    expect(screen.getByText(/Ingesta insuficiente/)).toBeInTheDocument()
  })

  it('proyecta resumen finalizado, alertas y PES sin exponer auditoría', async () => {
    const latest = {
      admission_id: 'adm-1',
      latest_encounter: { id: 'enc-1', finalized_at: '2026-08-13T10:00:00Z', professional_name: 'Ana Nutricionista' },
      latest_screening: { tool_code: 'nrs_2002', total_score: '3.00' },
      nutritional_status: 'Riesgo nutricional',
      active_diagnoses: [{ id: 'dx-1', generated_statement: 'Ingesta insuficiente relacionado con apetito, evidenciado por consumo bajo' }],
      current_prescription: null,
      adopted_requirements: [],
      active_alerts: [{ id: 'alert-1', severity: 'warning', description: 'Alergia informada', source: 'trakcare_manual', verification_status: 'unverified' }],
      suggested_reassessment_at: '2026-08-15T10:00:00Z',
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(response(latest))
    render(<NutritionSummaryCard admissionId="adm-1" />)
    expect(await screen.findByText(/Alergia informada/)).toHaveTextContent('unverified')
    expect(screen.getByText('Ana Nutricionista')).toBeInTheDocument()
    expect(screen.getByText(/Ingesta insuficiente relacionado/)).toBeInTheDocument()
    expect(document.body.textContent).not.toContain('audit_logs')
  })

  it('muestra advertencia TrakCare y deriva la minuta a su módulo operacional', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => String(input).includes('/nutrition-labs')
      ? response({ items: [{ id: 'lab-1', sampled_at: '2026-08-13T08:00:00Z', test_name: 'Glicemia', value: '110', unit: 'mg/dL', reference_range: null, source: 'trakcare_manual' }], total: 1, page: 1, page_size: 50 })
      : response(emptyList))
    const { rerender } = render(<NutritionClinicalTab tab="labs" admissionId="adm-1" historical={false} csrfToken="csrf" onChanged={vi.fn()} />)
    expect(await screen.findByText('Dato transcrito manualmente desde TrakCare')).toBeInTheDocument()
    rerender(<NutritionClinicalTab tab="intake" admissionId="adm-1" historical={false} csrfToken="csrf" onChanged={vi.fn()} />)
    expect(await screen.findByText(/La minuta diaria y el consolidado de producción se gestionan/)).toBeInTheDocument()
  })
})
