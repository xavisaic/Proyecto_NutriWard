import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  AllergyIntoleranceSection,
  FoodSafetyAllergyPanel,
  parseAllergyPaste,
} from './AllergyIntoleranceSection'

const empty = { admission_id: 'adm-1', patient_id: 'patient-1', items: [], review_assertions: [] }

function response(payload: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(payload), {
    status, headers: { 'Content-Type': 'application/json' },
  }))
}

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('Alergias e intolerancias', () => {
  it('normaliza el pegado masivo y permite revisar cada sustancia', async () => {
    expect(parseAllergyPaste('• Maní\n2. Penicilina; Lactosa\nmaní')).toEqual(['Maní', 'Penicilina', 'Lactosa'])
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((_input, init) =>
      init?.method === 'POST' ? response([], 201) : response(empty),
    )
    render(<AllergyIntoleranceSection admissionId="adm-1" historical={false} csrfToken="csrf-demo" onChanged={vi.fn()} />)
    await screen.findByText('Sin registros estructurados')
    await userEvent.click(screen.getByRole('button', { name: 'Agregar alergias o intolerancias' }))
    await userEvent.type(screen.getByRole('textbox', { name: 'Sustancias o alimentos' }), 'Maní{enter}Penicilina')
    await userEvent.click(screen.getByRole('button', { name: 'Preparar registros' }))
    expect(screen.getByText('2 registros detectados')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Maní')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Guardar 2 registros' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(true))
    const request = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    const body = JSON.parse(String(request?.[1]?.body))
    expect(body.items.map((item: { substance_name: string }) => item.substance_name)).toEqual(['Maní', 'Penicilina'])
    expect(new Headers(request?.[1]?.headers).get('X-CSRF-Token')).toBe('csrf-demo')
  })

  it('registra explícitamente que no hay alergias conocidas', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((_input, init) =>
      init?.method === 'POST' ? response({}, 201) : response(empty),
    )
    render(<AllergyIntoleranceSection admissionId="adm-1" historical={false} csrfToken="csrf" onChanged={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Registrar revisión sin hallazgos' }))
    await userEvent.click(screen.getByRole('button', { name: 'Registrar revisión' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([input, init]) =>
      String(input).includes('/allergy-review-assertions') && init?.method === 'POST',
    )).toBe(true))
    const request = fetchMock.mock.calls.find(([input]) => String(input).includes('/allergy-review-assertions'))
    expect(JSON.parse(String(request?.[1]?.body))).toMatchObject({ category: 'all', assertion: 'no_known' })
  })

  it('anula un registro erróneo sin borrarlo y sin estado clínico', async () => {
    const item = {
      id: 'allergy-1', patient_id: 'patient-1', asserted_admission_id: 'adm-1', substance_name: 'Maní',
      code_system: null, code: null, allergy_type: 'allergy', category: 'food', clinical_status: 'active',
      verification_status: 'confirmed', criticality: 'high', onset_date: null, source: 'patient', note: null,
      version: 3, reactions: [], history: [],
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((_input, init) =>
      init?.method === 'PATCH' ? response({ ...item, clinical_status: null, verification_status: 'entered_in_error' }) : response({ ...empty, items: [item] }),
    )
    render(<AllergyIntoleranceSection admissionId="adm-1" historical={false} csrfToken="csrf" onChanged={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Actualizar Maní' }))
    await userEvent.click(screen.getByRole('combobox', { name: 'Verificación' }))
    await userEvent.click(screen.getByRole('option', { name: 'Ingresada por error' }))
    await userEvent.type(screen.getByRole('textbox', { name: 'Motivo del cambio' }), 'Registro asociado por error.')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambio' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH')).toBe(true))
    const request = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')
    expect(JSON.parse(String(request?.[1]?.body))).toMatchObject({
      version: 3, clinical_status: null, verification_status: 'entered_in_error',
    })
  })

  it('entrega a Alimentación sólo la proyección de seguridad alimentaria', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => response({
      admission_id: 'adm-1', review_status: 'active_food_risks', items: [{
        id: 'food-1', substance_name: 'Maní', allergy_type: 'allergy', criticality: 'high',
        reactions: [{ manifestation: 'Anafilaxia', severity: 'severe' }],
      }],
    }))
    render(<FoodSafetyAllergyPanel admissionId="adm-1" />)
    expect(await screen.findByText('Riesgo alimentario activo')).toBeInTheDocument()
    expect(screen.getByText(/Maní · Alergia · criticidad alta/)).toBeInTheDocument()
    expect(screen.getByText(/Anafilaxia/)).toBeInTheDocument()
    expect(screen.queryByText(/fuente/i)).not.toBeInTheDocument()
  })

  it('mantiene los episodios históricos sin controles de edición', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => response(empty))
    render(<AllergyIntoleranceSection admissionId="adm-old" historical csrfToken="csrf" onChanged={vi.fn()} />)
    expect(await screen.findByText(/Se muestra el estado longitudinal actual/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Agregar alergias o intolerancias' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Registrar revisión sin hallazgos' })).not.toBeInTheDocument()
  })
})
