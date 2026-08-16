import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { NutritionClinicalTab, NutritionSummaryCard } from './NutritionClinicalTabs'

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
    render(<NutritionClinicalTab tab="care" admissionId="adm-1" historical={false} csrfToken="csrf" onChanged={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Registrar evolución' }))
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
    render(<NutritionClinicalTab tab="care" admissionId="adm-old" historical csrfToken="csrf" onChanged={vi.fn()} />)
    expect(await screen.findByText('Episodio histórico · Solo lectura. Las evoluciones finalizadas permanecen disponibles.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Registrar evolución' })).not.toBeInTheDocument()
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
    render(<NutritionClinicalTab tab="care" admissionId="adm-1" historical={false} csrfToken="csrf" onChanged={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Registrar evolución' }))
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

  it('registra circunferencias y la serie bilateral de dinamometría en una evolución', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      if (init?.method === 'POST') return response({
        encounter: { id: 'enc-anthro', status: 'draft', version: 1 }, assessment: null,
        context_items: [], anthropometry: [], advanced_measurements: [], screenings: [], requirements: [],
        diagnoses: [], prescription: null, monitoring: [], intake: [], labs: [], alerts: [],
      }, 201)
      return response(emptyList)
    })
    render(<NutritionClinicalTab tab="care" admissionId="adm-1" historical={false} csrfToken="csrf" onChanged={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Registrar evolución' }))
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
  }, 15_000)

  it('permite iniciar una modificación de prescripción desde su propio módulo', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(response(emptyList))
    render(<NutritionClinicalTab tab="prescription" admissionId="adm-1" historical={false} csrfToken="csrf" onChanged={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Modificar prescripción' }))
    expect(screen.getByRole('heading', { name: 'Acción específica' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '9' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '3' })).not.toBeInTheDocument()
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

  it('muestra advertencia TrakCare y alcance limitado de Minutas', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => String(input).includes('/nutrition-labs')
      ? response({ items: [{ id: 'lab-1', sampled_at: '2026-08-13T08:00:00Z', test_name: 'Glicemia', value: '110', unit: 'mg/dL', reference_range: null, source: 'trakcare_manual' }], total: 1, page: 1, page_size: 50 })
      : response(emptyList))
    const { rerender } = render(<NutritionClinicalTab tab="labs" admissionId="adm-1" historical={false} csrfToken="csrf" onChanged={vi.fn()} />)
    expect(await screen.findByText('Dato transcrito manualmente desde TrakCare')).toBeInTheDocument()
    rerender(<NutritionClinicalTab tab="intake" admissionId="adm-1" historical={false} csrfToken="csrf" onChanged={vi.fn()} />)
    expect(await screen.findByText(/Minutas, raciones y producción de cocina están pendientes/)).toBeInTheDocument()
  })
})
