import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { PatientChartPage } from './PatientChartPage'

const activeAdmission = {
  id: 'admission-active', admission_identifier: 'ADM-ACTIVA', status: 'active',
  admitted_at: '2026-08-01T12:00:00Z', ended_at: null, end_reason: null,
  duration_days: 12, is_historical: false, bed_status: 'occupied',
  age_at_admission: { value: 40, unit: 'years', is_estimated: false, reference_date: '2026-08-01', display: '40 años' },
  location: {
    id: 'location-1', care_unit_id: 'bed-1', care_unit_code: '01', care_unit_label: 'Cama 01',
    room_id: 'room-1', room_code: 'A', room_name: 'Sala A', service_id: 'service-1',
    service_code: 'MED', service_name: 'Medicina', started_at: '2026-08-01T12:00:00Z',
    ended_at: null, reason: 'Ingreso', is_current: true,
  },
  open_transfer: null,
}

const historicalAdmission = {
  ...activeAdmission,
  id: 'admission-old', admission_identifier: 'ADM-HIST', status: 'discharged',
  admitted_at: '2025-01-01T12:00:00Z', ended_at: '2025-01-10T12:00:00Z',
  end_reason: 'Alta', duration_days: 9, is_historical: true, bed_status: 'released',
  location: { ...activeAdmission.location, ended_at: '2025-01-10T12:00:00Z', is_current: false },
}

const summary = {
  patient: {
    id: 'patient-1', identity_status: 'identified', display_name: 'Ana Pérez',
    temporary_identifier: null, rut: '12345678-5', hospital_identifier: 'FICHA-1',
    date_of_birth: '1986-01-01', date_of_birth_is_estimated: false, sex: 'female',
    phone: '123', provisional_description: null, merged_into_patient_id: null, is_active: true,
    current_age: { value: 40, unit: 'years', is_estimated: false, reference_date: '2026-08-13', display: '40 años' },
  },
  selected_admission: activeAdmission,
  admissions: [activeAdmission, historicalAdmission],
  total_admissions: 2,
  recent_operational_events: [{
    id: 'event-1', event_type: 'admission_started', occurred_at: '2026-08-01T12:00:00Z',
    title: 'Inicio de hospitalización', description: 'Se inició el episodio.', reason: null,
    status: 'active', origin: null, destination: null,
  }],
}

function response(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), { status, headers: { 'Content-Type': 'application/json' } })
}

function renderChart(tab = 'summary', search = '?admission_id=admission-active', roles = ['nutricionista']) {
  const onNavigate = vi.fn()
  render(
    <PatientChartPage
      patientId="patient-1"
      requestedTab={tab}
      search={search}
      roles={roles}
      csrfToken="csrf"
      onNavigate={onNavigate}
    />,
  )
  return onNavigate
}

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('Ficha del paciente', () => {
  it('muestra resumen, cabecera, episodios y movimientos recientes', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url.includes('/nutrition-latest')) return response({ admission_id: 'admission-active', latest_encounter: null, latest_screening: null, nutritional_status: null, active_diagnoses: [], current_prescription: null, adopted_requirements: [], active_alerts: [], suggested_reassessment_at: null })
      if (url.includes('/nutrition-care-encounters')) return response({ items: [], total: 0, page: 1, page_size: 20 })
      return response(summary)
    })
    renderChart()
    expect(await screen.findByRole('heading', { name: 'Ana Pérez' })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Episodio' })).toHaveTextContent('ADM-ACTIVA')
    expect(screen.getByText('Inicio de hospitalización')).toBeInTheDocument()
    expect(await screen.findByText('Sin evolución finalizada')).toBeInTheDocument()
  })

  it('normaliza una pestaña desconocida sin cargar placeholders', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(response(summary))
    const navigate = renderChart('desconocida')
    await waitFor(() => expect(navigate).toHaveBeenCalledWith(
      expect.stringContaining('/patients/patient-1/summary'), true,
    ))
  })

  it('carga timeline sólo al entrar en Movimientos', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url.includes('/operational-timeline')) {
        return response({ admission_id: 'admission-active', items: summary.recent_operational_events, total: 1, page: 1, page_size: 20 })
      }
      if (url.includes('/nutrition-assessments')) return response({ items: [], total: 0, page: 1, page_size: 20 })
      return response(summary)
    })
    renderChart('assessment')
    expect(await screen.findByText('Sin evaluación finalizada')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes('/operational-timeline'))).toBe(false)
    cleanup()
    renderChart('movements')
    expect(await screen.findByText('Línea temporal de solo lectura derivada de hospitalización, ubicaciones y traslados.')).toBeInTheDocument()
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => String(input).includes('/operational-timeline'))).toBe(true))
  })

  it('redirige la antigua pestaña de evolución a Resumen y diferencia Bitácora', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(response(summary))
    const navigate = renderChart('care')
    await waitFor(() => expect(navigate).toHaveBeenCalledWith(
      expect.stringContaining('/patients/patient-1/summary'), true,
    ))
    cleanup()
    renderChart('logbook')
    expect(await screen.findByText(/independiente de la auditoría técnica/)).toBeInTheDocument()
  })

  it('oculta pestañas clínicas al administrador y dirige Ver episodio a Resumen', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(response(summary))
    const navigate = renderChart('history', '?admission_id=admission-active', ['administrador'])
    expect((await screen.findAllByRole('button', { name: 'Ver episodio' })).length).toBe(2)
    expect(screen.queryByRole('tab', { name: 'Evaluación' })).not.toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: 'Diagnósticos y antecedentes' })).not.toBeInTheDocument()
    await userEvent.click(screen.getAllByRole('button', { name: 'Ver episodio' })[1])
    expect(navigate).toHaveBeenCalledWith(expect.stringContaining('/summary?admission_id=admission-old'))
  })

  it('muestra episodio histórico como solo lectura y maneja 404', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(response({
      ...summary, selected_admission: historicalAdmission,
    }))
    renderChart('summary', '?admission_id=admission-old')
    expect(await screen.findByText('Episodio histórico · Solo lectura')).toBeInTheDocument()
    cleanup()
    vi.restoreAllMocks()
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(response({ detail: 'Paciente no encontrado.' }, 404))
    renderChart()
    expect(await screen.findByRole('alert')).toHaveTextContent('Paciente no encontrado.')
  })
})
