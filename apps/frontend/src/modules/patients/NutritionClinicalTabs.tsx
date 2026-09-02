import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormHelperText,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  Stack,
  Step,
  StepButton,
  Stepper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import Grid from '@mui/material/Grid2'
import { AlertTriangle, ClipboardPlus, ExternalLink, Pencil, RotateCcw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { EmptyState, ErrorState, LoadingState, SectionCard, StatusBadge } from '../../shared/components'
import {
  ApiError,
  apiRequest,
  LaboratoryTestCatalogItem,
  LabTrendPoint,
  LabTrendResponse,
  LabTrendSeries,
  NutritionAdvancedMeasurementSession,
  NutritionEncounterList,
  NutritionEncounterRead,
  NutritionLatest,
  NutritionProjectionList,
} from '../../shared/services/api'

type ClinicalTab = 'assessment' | 'anthropometry' | 'screening' | 'prescription' | 'intake' | 'labs'
type EvolutionMode = 'initial' | 'follow_up' | 'specific'

export interface ParsedLabRow {
  test_name: string
  value: string
  unit: string
  reference_range: string
  flag: string | null
}

const LAB_HEADER_ALIASES: Record<keyof Omit<ParsedLabRow, 'flag'> | 'flag', string[]> = {
  test_name: ['examen', 'prueba', 'analito', 'determinacion', 'test', 'nombre'],
  value: ['resultado', 'valor', 'result'],
  unit: ['unidad', 'unidades', 'unit'],
  reference_range: ['rango', 'referencia', 'rango referencia', 'rango de referencia', 'valores referencia', 'valores de referencia', 'valor referencia', 'valor de referencia'],
  flag: ['flag', 'indicador', 'estado', 'bandera'],
}

export function normalizeLabLabel(value: string) {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
}

function labFlag(value: string | undefined): string | null {
  const normalized = normalizeLabLabel(value ?? '')
  if (['h', 'alto', 'high'].includes(normalized)) return 'high'
  if (['l', 'bajo', 'low'].includes(normalized)) return 'low'
  if (['c', 'critico', 'critical'].includes(normalized)) return 'critical'
  if (['n', 'normal'].includes(normalized)) return 'normal'
  return null
}

export function parseLabPaste(input: string): ParsedLabRow[] {
  const lines = input.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  if (!lines.length) return []
  const delimiter = lines[0].includes('\t') ? '\t' : ';'
  const cells = lines.map((line) => line.split(delimiter).map((cell) => cell.trim()))
  const headers = cells[0].map(normalizeLabLabel)
  const indexFor = (key: keyof typeof LAB_HEADER_ALIASES) => headers.findIndex((header) => LAB_HEADER_ALIASES[key].includes(header))
  const detected = { test_name: indexFor('test_name'), value: indexFor('value'), unit: indexFor('unit'), reference_range: indexFor('reference_range'), flag: indexFor('flag') }
  const hasHeader = detected.test_name >= 0 && detected.value >= 0
  const indexes = hasHeader ? detected : { test_name: 0, value: 1, unit: 2, reference_range: 3, flag: 4 }
  return cells.slice(hasHeader ? 1 : 0).map((row) => ({
    test_name: row[indexes.test_name]?.trim() ?? '',
    value: row[indexes.value]?.trim() ?? '',
    unit: row[indexes.unit]?.trim() ?? '',
    reference_range: row[indexes.reference_range]?.trim() ?? '',
    flag: labFlag(row[indexes.flag]),
  })).filter((row) => row.test_name && row.value)
}

const SECTIONS = [
  'Contexto de la atención',
  'Antecedentes y anamnesis',
  'Antropometría',
  'Tamizaje nutricional',
  'Evaluación clínica y digestiva',
  'Ingesta y exámenes',
  'Cálculo de requerimientos',
  'Diagnóstico nutricional PES',
  'Prescripción nutricional',
  'Objetivos, seguimiento y observaciones',
]

const ALL_SECTION_INDEXES = SECTIONS.map((_, index) => index)
const MODE_SECTIONS: Record<EvolutionMode, number[]> = {
  initial: ALL_SECTION_INDEXES,
  follow_up: [0, 4, 5, 9],
  specific: [0, 9],
}
const MODE_LABELS: Record<EvolutionMode, string> = {
  initial: 'Evaluación nutricional inicial',
  follow_up: 'Seguimiento rápido',
  specific: 'Acción específica',
}
const SECTION_SUMMARY_LABELS: Record<string, string> = {
  context: 'Contexto', assessment: 'Evaluación', anthropometry: 'Antropometría',
  screening: 'Tamizaje', requirements: 'Requerimientos', diagnoses: 'PES',
  prescription: 'Prescripción', monitoring: 'Monitoreo', intake: 'Ingesta',
  labs: 'Exámenes', alerts: 'Alertas',
}

const STATUS_LABELS: Record<string, string> = {
  draft: 'Borrador', finalized: 'Finalizada', corrected: 'Corrección', cancelled: 'Cancelada',
}
const TYPE_LABELS: Record<string, string> = {
  initial_assessment: 'Evaluación inicial', follow_up: 'Seguimiento', reassessment: 'Reevaluación',
  discharge_planning: 'Planificación de alta', other: 'Otra',
}
const POPULATION_LABELS: Record<string, string> = {
  adult: 'Adulto', pediatric: 'Pediatría', neonatal: 'Neonatología', pregnancy: 'Embarazo',
}
const SOURCE_LABELS: Record<string, string> = {
  patient_interview: 'Entrevista con paciente', family_or_caregiver: 'Familiar o cuidador',
  clinical_record: 'Ficha clínica', trakcare_manual: 'Transcripción manual desde TrakCare',
  care_team_observation: 'Observación del equipo', combined: 'Combinación de fuentes', other: 'Otro',
}
const SCREENING_DEFAULTS: Record<string, string> = {
  adult: 'nrs_2002', pediatric: 'strongkids', neonatal: 'none', pregnancy: 'none',
}
const MEASUREMENT_LABELS: Record<string, string> = {
  current_weight_measured: 'Peso actual medido', current_weight_reported: 'Peso actual informado',
  usual_weight: 'Peso habitual', dry_weight: 'Peso seco', ideal_weight: 'Peso ideal',
  adjusted_weight: 'Peso ajustado', target_weight: 'Peso objetivo', prepregnancy_weight: 'Peso pregestacional',
  birth_weight: 'Peso al nacer', neonatal_minimum_weight: 'Peso neonatal mínimo',
  calculation_weight: 'Peso de cálculo', standing_height: 'Talla de pie',
  recumbent_length: 'Longitud acostado', estimated_height: 'Talla estimada',
  mid_upper_arm_circumference: 'Perímetro braquial', head_circumference: 'Perímetro cefálico',
  waist_circumference: 'Perímetro de cintura', body_mass_index: 'IMC calculado',
}

const ADVANCED_MEASUREMENT_LABELS: Record<string, string> = {
  calf_circumference: 'Circunferencia de pantorrilla',
  mid_upper_arm_circumference: 'Circunferencia braquial',
  waist_circumference: 'Circunferencia de cintura',
  handgrip_strength: 'Fuerza de agarre',
  handgrip_max_left: 'Máximo izquierdo', handgrip_max_right: 'Máximo derecho',
  handgrip_max: 'Máximo bilateral',
  skinfold_biceps: 'Pliegue bicipital',
  skinfold_triceps: 'Pliegue tricipital',
  skinfold_subscapular: 'Pliegue subescapular',
  skinfold_suprailiac: 'Pliegue suprailiaco',
  skinfold_biceps_mean: 'Media bicipital', skinfold_triceps_mean: 'Media tricipital',
  skinfold_subscapular_mean: 'Media subescapular', skinfold_suprailiac_mean: 'Media suprailiaca',
  skinfold_sum_4: 'Sumatoria de 4 pliegues',
  resistance: 'Resistencia', reactance: 'Reactancia', phase_angle: 'Ángulo de fase',
  total_body_water: 'Agua corporal total', extracellular_water: 'Agua extracelular',
  intracellular_water: 'Agua intracelular', fat_mass: 'Masa grasa',
  body_fat_percentage: 'Grasa corporal', fat_free_mass: 'Masa libre de grasa',
  skeletal_muscle_mass: 'Masa muscular esquelética',
  skeletal_muscle_mass_index: 'Índice de masa muscular esquelética',
}

type AdvancedSessionType = NutritionAdvancedMeasurementSession['session_type']
type AdvancedDraftState = Record<string, string>

const ADVANCED_PROTOCOLS: Record<AdvancedSessionType, [string, string]> = {
  circumference: ['institutional-circumferences', 'v1'],
  handgrip: ['hospital-handgrip', 'v1'],
  skinfold_4: ['durnin-womersley-4', 'v1'],
  bioimpedance: ['device-reported-bia', 'v1'],
}
const CIRCUMFERENCE_FIELDS = [
  ['calf_circumference', 'left', 'Pantorrilla izquierda'],
  ['calf_circumference', 'right', 'Pantorrilla derecha'],
  ['mid_upper_arm_circumference', 'left', 'Braquial izquierda'],
  ['mid_upper_arm_circumference', 'right', 'Braquial derecha'],
  ['waist_circumference', 'none', 'Cintura'],
] as const
const SKINFOLD_FIELDS = [
  ['skinfold_biceps', 'Bicipital'], ['skinfold_triceps', 'Tricipital'],
  ['skinfold_subscapular', 'Subescapular'], ['skinfold_suprailiac', 'Suprailiaco'],
] as const
const BIA_FIELDS = [
  ['resistance', 'Resistencia', 'ohm'], ['reactance', 'Reactancia', 'ohm'],
  ['phase_angle', 'Ángulo de fase', 'degree'], ['total_body_water', 'Agua corporal total', 'L'],
  ['extracellular_water', 'Agua extracelular', 'L'], ['intracellular_water', 'Agua intracelular', 'L'],
  ['fat_mass', 'Masa grasa', 'kg'], ['body_fat_percentage', 'Grasa corporal', '%'],
  ['fat_free_mass', 'Masa libre de grasa', 'kg'], ['skeletal_muscle_mass', 'Masa muscular esquelética', 'kg'],
  ['skeletal_muscle_mass_index', 'Índice de masa muscular', 'kg/m2'],
] as const

function advancedValueKey(type: AdvancedSessionType, code: string, laterality = 'none', attempt = 0) {
  return `${type}.value.${code}.${laterality}.${attempt}`
}
function advancedMetaKey(type: AdvancedSessionType, field: string) { return `${type}.meta.${field}` }
function advancedValue(state: AdvancedDraftState, key: string) { return state[key] ?? '' }

function advancedFromEncounter(record: NutritionEncounterRead): AdvancedDraftState {
  const result: AdvancedDraftState = {}
  for (const session of record.advanced_measurements ?? []) {
    const type = session.session_type
    const metadata: Record<string, unknown> = {
      measured_at: session.measured_at?.slice(0, 16), device_manufacturer: session.device_manufacturer,
      device_model: session.device_model, device_serial: session.device_serial, technology: session.technology,
      frequencies_khz: session.frequencies_khz, position: session.position, source: session.source,
      reliability: session.reliability, preparation_status: session.preparation_status,
      fasting_hours: session.fasting_hours, recent_exercise: session.recent_exercise,
      bladder_emptied: session.bladder_emptied, hydration_status: session.hydration_status,
      edema_present: session.edema_present, observations: session.observations,
    }
    for (const [field, value] of Object.entries(metadata)) {
      if (value !== null && value !== undefined) result[advancedMetaKey(type, field)] = String(value)
    }
    for (const row of session.values) {
      if (row.value_nature === 'calculated') continue
      result[advancedValueKey(type, row.measurement_code, row.laterality, row.attempt_number ?? 0)] = String(row.value)
    }
  }
  return result
}

function formatDate(value: unknown, time = true) {
  if (!value || typeof value !== 'string') return '—'
  return new Intl.DateTimeFormat(undefined, time
    ? { dateStyle: 'medium', timeStyle: 'short' }
    : { dateStyle: 'medium' }).format(new Date(value))
}

function text(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}

function clinicalError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 409) return 'Conflicto de concurrencia o estado. Recargue la atención antes de continuar.'
    if (error.status === 403) return 'No tiene permiso para acceder a esta ficha clínica.'
    if (error.status === 404) return 'El registro clínico solicitado no existe.'
    return error.message
  }
  return 'No fue posible cargar la información nutricional.'
}

function FieldValue({ label, value }: { label: string, value: unknown }) {
  return <Box><Typography variant="caption" color="text.secondary">{label}</Typography><Typography>{text(value)}</Typography></Box>
}

interface EditorState {
  encounter_type: string
  reason_for_assessment: string
  information_source: string
  population_group: string
  clinical_summary: string
  hospitalization_reason: string
  current_feeding_route: string
  appetite: string
  clinical_findings: string
  digestive_findings: string
  nutritional_status: string
  objectives: string
  monitoring_plan: string
  pending_actions: string
  suggested_reassessment_at: string
  weight_value: string
  weight_type: string
  height_value: string
  screening_tool: string
  nrs_nutrition: string
  nrs_initial_bmi: string
  nrs_initial_weight_loss: string
  nrs_initial_intake: string
  nrs_initial_severe_illness: string
  nrs_weight_loss_category: string
  nrs_intake_category: string
  nrs_bmi: string
  nrs_general_deterioration: string
  nrs_disease: string
  nrs_age: string
  nrs_age_source: string
  nrs_age_confirmed: string
  strong_subjective: string
  strong_disease: string
  strong_intake: string
  strong_weight: string
  no_tool_reason: string
  requirement_method: string
  basal_result: string
  activity_factor: string
  stress_factor: string
  energy_result: string
  pes_problem: string
  pes_etiology: string
  pes_signs: string
  prescription_route: string
  regimen_type: string
  energy_target: string
  protein_target: string
  fluid_target: string
  restrictions: string
  intake_percentage: string
  intake_reason: string
  lab_name: string
  lab_value: string
  lab_unit: string
}

const EMPTY_EDITOR: EditorState = {
  encounter_type: 'initial_assessment', reason_for_assessment: '', information_source: 'combined',
  population_group: 'adult', clinical_summary: '', hospitalization_reason: '', current_feeding_route: '',
  appetite: '', clinical_findings: '', digestive_findings: '', nutritional_status: '', objectives: '',
  monitoring_plan: '', pending_actions: '', suggested_reassessment_at: '', weight_value: '',
  weight_type: 'current_weight_measured', height_value: '', screening_tool: 'nrs_2002',
  nrs_nutrition: '0', nrs_initial_bmi: '', nrs_initial_weight_loss: '', nrs_initial_intake: '',
  nrs_initial_severe_illness: '', nrs_weight_loss_category: '', nrs_intake_category: '',
  nrs_bmi: '', nrs_general_deterioration: '', nrs_disease: '', nrs_age: '', nrs_age_source: 'manual',
  nrs_age_confirmed: 'false',
  strong_subjective: 'false',
  strong_disease: 'false', strong_intake: 'false', strong_weight: 'false',
  no_tool_reason: 'Protocolo institucional aún no confirmado.', requirement_method: 'factorial',
  basal_result: '', activity_factor: '1', stress_factor: '1', energy_result: '', pes_problem: '',
  pes_etiology: '', pes_signs: '', prescription_route: 'oral', regimen_type: '', energy_target: '',
  protein_target: '', fluid_target: '', restrictions: '', intake_percentage: '', intake_reason: '',
  lab_name: '', lab_value: '', lab_unit: '',
}

function fromEncounter(record: NutritionEncounterRead): EditorState {
  const assessment = record.assessment ?? {}
  const firstWeight = record.anthropometry.find((row) => String(row.measurement_type).includes('weight'))
  const height = record.anthropometry.find((row) => row.measurement_type === 'standing_height')
  const screening = record.screenings[0]
  const answers = Object.fromEntries(((screening?.answers as Array<Record<string, unknown>> | undefined) ?? []).map((row) => [row.answer_code, row.answer_value]))
  const requirement = record.requirements[0]
  const inputs = (requirement?.inputs_snapshot ?? {}) as Record<string, unknown>
  const diagnosis = record.diagnoses[0]
  const prescription = record.prescription
  const intake = record.intake[0]
  const lab = record.labs[0]
  return {
    ...EMPTY_EDITOR,
    encounter_type: record.encounter.encounter_type,
    reason_for_assessment: record.encounter.reason_for_assessment ?? '',
    information_source: record.encounter.information_source ?? 'combined',
    clinical_summary: record.encounter.clinical_summary ?? '',
    population_group: text(assessment.population_group) === '—' ? 'adult' : text(assessment.population_group),
    hospitalization_reason: text(assessment.hospitalization_reason) === '—' ? '' : text(assessment.hospitalization_reason),
    current_feeding_route: text(assessment.current_feeding_route) === '—' ? '' : text(assessment.current_feeding_route),
    appetite: text(assessment.appetite) === '—' ? '' : text(assessment.appetite),
    clinical_findings: text(assessment.clinical_findings) === '—' ? '' : text(assessment.clinical_findings),
    digestive_findings: text(assessment.digestive_findings) === '—' ? '' : text(assessment.digestive_findings),
    nutritional_status: text(assessment.nutritional_status) === '—' ? '' : text(assessment.nutritional_status),
    objectives: text(assessment.objectives) === '—' ? '' : text(assessment.objectives),
    monitoring_plan: text(assessment.monitoring_plan) === '—' ? '' : text(assessment.monitoring_plan),
    pending_actions: text(assessment.pending_actions) === '—' ? '' : text(assessment.pending_actions),
    suggested_reassessment_at: typeof assessment.suggested_reassessment_at === 'string' ? assessment.suggested_reassessment_at.slice(0, 16) : '',
    weight_value: firstWeight ? text(firstWeight.value) : '', weight_type: firstWeight ? text(firstWeight.measurement_type) : 'current_weight_measured',
    height_value: height ? text(height.value) : '', screening_tool: screening ? text(screening.tool_code) : SCREENING_DEFAULTS[text(assessment.population_group)] ?? 'nrs_2002',
    nrs_nutrition: text(answers.nutritional_status_score) === '—' ? '0' : text(answers.nutritional_status_score),
    nrs_initial_bmi: text(answers.initial_bmi_below_20_5) === '—' ? '' : text(answers.initial_bmi_below_20_5),
    nrs_initial_weight_loss: text(answers.initial_weight_loss_3_months) === '—' ? '' : text(answers.initial_weight_loss_3_months),
    nrs_initial_intake: text(answers.initial_reduced_intake_last_week) === '—' ? '' : text(answers.initial_reduced_intake_last_week),
    nrs_initial_severe_illness: text(answers.initial_severely_ill) === '—' ? '' : text(answers.initial_severely_ill),
    nrs_weight_loss_category: text(answers.weight_loss_category) === '—' ? '' : text(answers.weight_loss_category),
    nrs_intake_category: text(answers.intake_category) === '—' ? '' : text(answers.intake_category),
    nrs_bmi: text(answers.current_bmi) === '—' ? '' : text(answers.current_bmi),
    nrs_general_deterioration: text(answers.impaired_general_condition) === '—' ? '' : text(answers.impaired_general_condition),
    nrs_disease: text(answers.disease_severity_score) === '—' ? '' : text(answers.disease_severity_score),
    nrs_age: text(answers.age_70_or_more) === '—' ? '' : text(answers.age_70_or_more),
    nrs_age_source: text(answers.age_source) === '—' ? 'manual' : text(answers.age_source),
    nrs_age_confirmed: text(answers.age_70_or_more) === '—' ? 'false' : 'true',
    strong_subjective: text(answers.subjective_clinical_assessment) === '—' ? 'false' : text(answers.subjective_clinical_assessment),
    strong_disease: text(answers.high_risk_disease) === '—' ? 'false' : text(answers.high_risk_disease),
    strong_intake: text(answers.nutritional_intake_or_losses) === '—' ? 'false' : text(answers.nutritional_intake_or_losses),
    strong_weight: text(answers.weight_loss_or_poor_gain) === '—' ? 'false' : text(answers.weight_loss_or_poor_gain),
    no_tool_reason: screening && screening.no_tool_reason ? text(screening.no_tool_reason) : EMPTY_EDITOR.no_tool_reason,
    requirement_method: requirement ? text(requirement.method) : 'factorial',
    basal_result: text(inputs.basal_result) === '—' ? '' : text(inputs.basal_result),
    activity_factor: text(inputs.activity_factor) === '—' ? '1' : text(inputs.activity_factor),
    stress_factor: text(inputs.stress_factor) === '—' ? '1' : text(inputs.stress_factor),
    energy_result: requirement ? text(requirement.adopted_result) : '',
    pes_problem: diagnosis ? text(diagnosis.problem) : '', pes_etiology: diagnosis ? text(diagnosis.etiology) : '',
    pes_signs: diagnosis ? text(diagnosis.signs_and_symptoms) : '', prescription_route: prescription ? text(prescription.primary_route) : 'oral',
    regimen_type: prescription ? text(prescription.regimen_type) === '—' ? '' : text(prescription.regimen_type) : '',
    energy_target: prescription ? text(prescription.energy_target) === '—' ? '' : text(prescription.energy_target) : '',
    protein_target: prescription ? text(prescription.protein_target) === '—' ? '' : text(prescription.protein_target) : '',
    fluid_target: prescription ? text(prescription.fluid_target) === '—' ? '' : text(prescription.fluid_target) : '',
    restrictions: prescription ? text(prescription.restrictions) === '—' ? '' : text(prescription.restrictions) : '',
    intake_percentage: intake ? text(intake.consumed_percentage) : '', intake_reason: intake ? text(intake.incomplete_reason) === '—' ? '' : text(intake.incomplete_reason) : '',
    lab_name: lab ? text(lab.test_name) : '', lab_value: lab ? text(lab.value) : '', lab_unit: lab ? text(lab.unit) === '—' ? '' : text(lab.unit) : '',
  }
}

function sectionsFromEncounter(record: NutritionEncounterRead): number[] {
  const sections = new Set<number>([0, 9])
  if (record.assessment) { sections.add(1); sections.add(4) }
  if (record.anthropometry.length || (record.advanced_measurements ?? []).length) sections.add(2)
  if (record.screenings.length) sections.add(3)
  if (record.intake.length || record.labs.length) sections.add(5)
  if (record.requirements.length) sections.add(6)
  if (record.diagnoses.length) sections.add(7)
  if (record.prescription) sections.add(8)
  return [...sections].sort((a, b) => a - b)
}

function numberOrUndefined(value: string) { return value.trim() ? Number(value) : undefined }
function localIso(value: string) { return value ? new Date(value).toISOString() : undefined }

const NRS_WEIGHT_SCORES: Record<string, number> = {
  none_or_below_threshold: 0, over_5_3_months: 1, over_5_2_months: 2,
  over_5_1_month_or_over_15_3_months: 3,
}
const NRS_INTAKE_SCORES: Record<string, number> = {
  over_75: 0, '50_75': 1, '25_50': 2, below_25: 3,
}

function calculatedBmi(editor: EditorState): number | null {
  const weight = Number(editor.weight_value)
  const height = Number(editor.height_value) / 100
  if (!weight || !height) return null
  return Math.round((weight / (height * height)) * 10) / 10
}

function nrsBmi(editor: EditorState): string {
  const calculated = calculatedBmi(editor)
  return calculated === null ? editor.nrs_bmi : String(calculated)
}

function nrsInitialAnswers(editor: EditorState) {
  const bmi = nrsBmi(editor)
  return {
    initial_bmi_below_20_5: bmi ? String(Number(bmi) < 20.5) : editor.nrs_initial_bmi,
    initial_weight_loss_3_months: editor.nrs_initial_weight_loss,
    initial_reduced_intake_last_week: editor.nrs_initial_intake,
    initial_severely_ill: editor.nrs_initial_severe_illness,
  }
}

function nrsPreview(editor: EditorState) {
  const initial = nrsInitialAnswers(editor)
  const initialComplete = Object.values(initial).every((value) => value !== '')
  const needsFinal = initialComplete && Object.values(initial).some((value) => value === 'true')
  const bmi = nrsBmi(editor)
  let bmiScore = 0
  if (bmi && editor.nrs_general_deterioration === 'true') {
    if (Number(bmi) < 18.5) bmiScore = 3
    else if (Number(bmi) < 20.5) bmiScore = 2
  }
  const weightScore = NRS_WEIGHT_SCORES[editor.nrs_weight_loss_category]
  const intakeScore = NRS_INTAKE_SCORES[editor.nrs_intake_category]
  const nutritionalScore = Math.max(weightScore ?? 0, intakeScore ?? 0, bmiScore)
  const finalComplete = Boolean(
    editor.nrs_weight_loss_category && editor.nrs_intake_category
    && editor.nrs_general_deterioration !== '' && editor.nrs_disease !== ''
    && editor.nrs_age !== '' && editor.nrs_age_confirmed === 'true'
    && (initial.initial_bmi_below_20_5 !== 'true' || bmi),
  )
  const total = needsFinal && finalComplete
    ? nutritionalScore + Number(editor.nrs_disease) + (editor.nrs_age === 'true' ? 1 : 0)
    : initialComplete && !needsFinal ? 0 : null
  return { initial, initialComplete, needsFinal, bmi, bmiScore, weightScore, intakeScore, nutritionalScore, finalComplete, total }
}

function buildNrsAnswers(editor: EditorState) {
  const preview = nrsPreview(editor)
  const answers = [{ answer_code: 'screening_flow_version', answer_value: 'v2' }]
  for (const [answer_code, answer_value] of Object.entries(preview.initial)) {
    if (answer_value !== '') answers.push({ answer_code, answer_value })
  }
  if (preview.needsFinal) {
    const finalAnswers = [
      ['weight_loss_category', editor.nrs_weight_loss_category],
      ['intake_category', editor.nrs_intake_category],
      ['current_bmi', preview.bmi],
      ['impaired_general_condition', editor.nrs_general_deterioration],
      ['disease_severity_score', editor.nrs_disease],
      ['age_70_or_more', editor.nrs_age],
      ['age_source', editor.nrs_age_source],
    ]
    for (const [answer_code, answer_value] of finalAnswers) {
      if (answer_value !== '') answers.push({ answer_code, answer_value })
    }
  }
  return answers
}

function optionalBoolean(value: string) {
  if (value === '') return undefined
  return value === 'true'
}

function buildAdvancedMeasurements(state: AdvancedDraftState, now: string) {
  const meta = (type: AdvancedSessionType, field: string) => advancedValue(state, advancedMetaKey(type, field))
  const base = (type: AdvancedSessionType) => ({
    session_type: type,
    measured_at: localIso(meta(type, 'measured_at')) ?? now,
    protocol_code: ADVANCED_PROTOCOLS[type][0], protocol_version: ADVANCED_PROTOCOLS[type][1],
    device_manufacturer: meta(type, 'device_manufacturer') || undefined,
    device_model: meta(type, 'device_model') || undefined,
    device_serial: meta(type, 'device_serial') || undefined,
    technology: meta(type, 'technology') || undefined,
    frequencies_khz: meta(type, 'frequencies_khz') || undefined,
    position: meta(type, 'position') || undefined,
    source: 'clinical_measurement', reliability: meta(type, 'reliability') || 'unknown',
    observations: meta(type, 'observations') || undefined,
  })
  const sessions: Array<Record<string, unknown>> = []

  const circumferenceValues = CIRCUMFERENCE_FIELDS.flatMap(([code, laterality]) => {
    const value = advancedValue(state, advancedValueKey('circumference', code, laterality))
    return value ? [{ measurement_code: code, body_site: code, laterality, value: Number(value), unit: 'cm' }] : []
  })
  if (circumferenceValues.length) sessions.push({ ...base('circumference'), values: circumferenceValues })

  const handgripValues = (['left', 'right'] as const).flatMap((laterality) => [1, 2, 3].flatMap((attempt) => {
    const value = advancedValue(state, advancedValueKey('handgrip', 'handgrip_strength', laterality, attempt))
    return value ? [{ measurement_code: 'handgrip_strength', body_site: 'hand', laterality, attempt_number: attempt, value: Number(value), unit: 'kgf' }] : []
  }))
  if (handgripValues.length) sessions.push({ ...base('handgrip'), values: handgripValues })

  const skinfoldValues = SKINFOLD_FIELDS.flatMap(([code]) => [1, 2, 3].flatMap((attempt) => {
    const value = advancedValue(state, advancedValueKey('skinfold_4', code, 'right', attempt))
    return value ? [{ measurement_code: code, body_site: code, laterality: 'right', attempt_number: attempt, value: Number(value), unit: 'mm' }] : []
  }))
  if (skinfoldValues.length) sessions.push({ ...base('skinfold_4'), values: skinfoldValues })

  const bioimpedanceValues = BIA_FIELDS.flatMap(([code, , unit]) => {
    const value = advancedValue(state, advancedValueKey('bioimpedance', code))
    return value ? [{ measurement_code: code, laterality: 'none', value: Number(value), unit }] : []
  })
  if (bioimpedanceValues.length) sessions.push({
    ...base('bioimpedance'),
    preparation_status: meta('bioimpedance', 'preparation_status') || undefined,
    fasting_hours: numberOrUndefined(meta('bioimpedance', 'fasting_hours')),
    recent_exercise: optionalBoolean(meta('bioimpedance', 'recent_exercise')),
    bladder_emptied: optionalBoolean(meta('bioimpedance', 'bladder_emptied')),
    hydration_status: meta('bioimpedance', 'hydration_status') || undefined,
    edema_present: optionalBoolean(meta('bioimpedance', 'edema_present')),
    values: bioimpedanceValues,
  })
  return sessions
}

function validateAdvancedMeasurements(state: AdvancedDraftState): string[] {
  const errors: string[] = []
  const meta = (type: AdvancedSessionType, field: string) => advancedValue(state, advancedMetaKey(type, field))
  const grip = (['left', 'right'] as const).flatMap((side) => [1, 2, 3].map((attempt) => advancedValue(state, advancedValueKey('handgrip', 'handgrip_strength', side, attempt))))
  if (grip.some(Boolean) && (!grip.every(Boolean) || !meta('handgrip', 'device_manufacturer') || !meta('handgrip', 'device_model') || !meta('handgrip', 'position'))) {
    errors.push('Dinamometría: complete tres intentos por mano, fabricante, modelo y posición.')
  }
  const skinfolds = SKINFOLD_FIELDS.flatMap(([code]) => [1, 2, 3].map((attempt) => advancedValue(state, advancedValueKey('skinfold_4', code, 'right', attempt))))
  if (skinfolds.some(Boolean) && (!skinfolds.every(Boolean) || !meta('skinfold_4', 'device_manufacturer') || !meta('skinfold_4', 'device_model'))) {
    errors.push('Pliegues: complete los tres intentos de los cuatro sitios e identifique el plicómetro.')
  }
  const bia = BIA_FIELDS.map(([code]) => advancedValue(state, advancedValueKey('bioimpedance', code)))
  if (bia.some(Boolean) && (!meta('bioimpedance', 'device_manufacturer') || !meta('bioimpedance', 'device_model') || !meta('bioimpedance', 'technology'))) {
    errors.push('Bioimpedancia: identifique fabricante, modelo y tecnología del equipo.')
  }
  return errors
}

function buildPayload(editor: EditorState, selectedSections = ALL_SECTION_INDEXES, advanced: AdvancedDraftState = {}) {
  const now = new Date().toISOString()
  const includes = (section: number) => selectedSections.includes(section)
  const hasFollowUpDetails = Boolean(
    editor.objectives || editor.monitoring_plan || editor.pending_actions
    || editor.suggested_reassessment_at,
  )
  const anthropometry = []
  if (includes(2) && editor.weight_value) anthropometry.push({ measurement_type: editor.weight_type, value: Number(editor.weight_value), unit: 'kg', measured_at: now, reliability: 'unknown', value_nature: editor.weight_type === 'current_weight_reported' ? 'reported' : 'measured' })
  if (includes(2) && editor.height_value) anthropometry.push({ measurement_type: 'standing_height', value: Number(editor.height_value), unit: 'cm', measured_at: now, reliability: 'unknown', value_nature: 'measured' })
  const answers = includes(3) && editor.screening_tool === 'nrs_2002' ? buildNrsAnswers(editor) : includes(3) && editor.screening_tool === 'strongkids' ? [
    { answer_code: 'subjective_clinical_assessment', answer_value: editor.strong_subjective },
    { answer_code: 'high_risk_disease', answer_value: editor.strong_disease },
    { answer_code: 'nutritional_intake_or_losses', answer_value: editor.strong_intake },
    { answer_code: 'weight_loss_or_poor_gain', answer_value: editor.strong_weight },
  ] : []
  const requirements = includes(6) && editor.requirement_method === 'factorial' && editor.basal_result ? [{
    nutrient_code: 'energy', method: 'factorial', unit: 'kcal/day',
    inputs: { basal_result: Number(editor.basal_result), activity_factor: Number(editor.activity_factor), stress_factor: Number(editor.stress_factor), thermal_factor: 1 },
  }] : includes(6) && editor.requirement_method === 'manual' && editor.energy_result ? [{
    nutrient_code: 'energy', method: 'manual', unit: 'kcal/day', inputs: { measured_or_manual_value: Number(editor.energy_result) },
  }] : []
  return {
    encounter_type: editor.encounter_type,
    reason_for_assessment: editor.reason_for_assessment || null,
    information_source: editor.information_source || null,
    clinical_summary: editor.clinical_summary || null,
    assessment: includes(1) || includes(4) || (includes(9) && hasFollowUpDetails) ? {
      population_group: editor.population_group, hospitalization_reason: editor.hospitalization_reason || null,
      current_feeding_route: editor.current_feeding_route || null, appetite: editor.appetite || null,
      clinical_findings: editor.clinical_findings || null, digestive_findings: editor.digestive_findings || null,
      nutritional_status: editor.nutritional_status || null, objectives: editor.objectives || null,
      monitoring_plan: editor.monitoring_plan || null, pending_actions: editor.pending_actions || null,
      suggested_reassessment_at: localIso(editor.suggested_reassessment_at), observed_at: now,
    } : null,
    anthropometry,
    advanced_measurements: includes(2) ? buildAdvancedMeasurements(advanced, now) : [],
    screenings: includes(3) ? [{ tool_code: editor.screening_tool, tool_version: editor.screening_tool === 'nrs_2002' ? 'ESPEN 2002' : editor.screening_tool === 'strongkids' ? 'original' : 'institutional-policy-pending', applied_at: now, no_tool_reason: editor.screening_tool === 'none' ? editor.no_tool_reason : null, answers }] : [],
    requirements,
    diagnoses: includes(7) && editor.pes_problem && editor.pes_etiology && editor.pes_signs ? [{ problem: editor.pes_problem, etiology: editor.pes_etiology, signs_and_symptoms: editor.pes_signs, priority: 1, status: 'active' }] : [],
    prescription: includes(8) && editor.regimen_type ? {
      effective_from: now, primary_route: editor.prescription_route, regimen_type: editor.regimen_type,
      energy_target: numberOrUndefined(editor.energy_target), protein_target: numberOrUndefined(editor.protein_target),
      fluid_target: numberOrUndefined(editor.fluid_target), restrictions: editor.restrictions || null, meal_times: [],
    } : null,
    intake: includes(5) && editor.intake_percentage ? [{ intake_date: now.slice(0, 10), meal_time: 'other', consumed_percentage: Number(editor.intake_percentage), incomplete_reason: editor.intake_reason || null, source: editor.information_source }] : [],
    labs: includes(5) && editor.lab_name && editor.lab_value ? [{ test_name: editor.lab_name, value: editor.lab_value, unit: editor.lab_unit || null, sampled_at: now, source: 'trakcare_manual' }] : [],
  }
}

function AdvancedNumberField({ label, unit, value, onChange }: {
  label: string; unit: string; value: string; onChange: (value: string) => void
}) {
  return <TextField
    fullWidth type="number" label={label} value={value} onChange={(event) => onChange(event.target.value)}
    inputProps={{ min: 0, step: '0.1' }} helperText={unit}
  />
}

function AdvancedAnthropometryEditor({ state, setValue }: {
  state: AdvancedDraftState; setValue: (key: string, value: string) => void
}) {
  const value = (type: AdvancedSessionType, code: string, laterality = 'none', attempt = 0) =>
    advancedValue(state, advancedValueKey(type, code, laterality, attempt))
  const setMeasurement = (type: AdvancedSessionType, code: string, next: string, laterality = 'none', attempt = 0) =>
    setValue(advancedValueKey(type, code, laterality, attempt), next)
  const meta = (type: AdvancedSessionType, field: string) => advancedValue(state, advancedMetaKey(type, field))
  const setMeta = (type: AdvancedSessionType, field: string, next: string) => setValue(advancedMetaKey(type, field), next)
  const panel = { border: 1, borderColor: 'divider', borderRadius: 2, p: 2 }
  const deviceFields = (type: AdvancedSessionType, noun: string) => <Grid container spacing={2}>
    <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth label={`Fabricante del ${noun}`} value={meta(type, 'device_manufacturer')} onChange={(e) => setMeta(type, 'device_manufacturer', e.target.value)} /></Grid>
    <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth label={`Modelo del ${noun}`} value={meta(type, 'device_model')} onChange={(e) => setMeta(type, 'device_model', e.target.value)} /></Grid>
    <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth label="N.º de serie (opcional)" value={meta(type, 'device_serial')} onChange={(e) => setMeta(type, 'device_serial', e.target.value)} /></Grid>
  </Grid>
  const booleanSelect = (type: AdvancedSessionType, field: string, label: string) => <FormControl fullWidth>
    <InputLabel>{label}</InputLabel><Select label={label} value={meta(type, field)} onChange={(e) => setMeta(type, field, e.target.value)}>
      <MenuItem value=""><em>Sin registrar</em></MenuItem><MenuItem value="false">No</MenuItem><MenuItem value="true">Sí</MenuItem>
    </Select>
  </FormControl>

  return <Stack spacing={2}>
    <Box sx={panel}><Stack spacing={2}>
      <Box><Typography fontWeight={800}>Circunferencias</Typography><Typography variant="body2" color="text.secondary">Registre sólo las mediciones realizadas, en centímetros.</Typography></Box>
      <Grid container spacing={2}>{CIRCUMFERENCE_FIELDS.map(([code, laterality, label]) => <Grid key={`${code}-${laterality}`} size={{ xs: 12, sm: 6, md: 4 }}><AdvancedNumberField label={label} unit="cm" value={value('circumference', code, laterality)} onChange={(next) => setMeasurement('circumference', code, next, laterality)} /></Grid>)}
        <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth label="Posición del paciente" placeholder="De pie, sentado o decúbito" value={meta('circumference', 'position')} onChange={(e) => setMeta('circumference', 'position', e.target.value)} /></Grid>
      </Grid>
    </Stack></Box>

    <Box sx={panel}><Stack spacing={2}>
      <Box><Typography fontWeight={800}>Fuerza de agarre con dinamómetro</Typography><Typography variant="body2" color="text.secondary">Tres intentos por mano en kgf. NutriWard conserva los seis valores y calcula los máximos por lado y bilateral.</Typography></Box>
      {deviceFields('handgrip', 'dinamómetro')}
      <TextField fullWidth label="Posición y protocolo aplicado" placeholder="Sentado, hombro aducido, codo a 90°" value={meta('handgrip', 'position')} onChange={(e) => setMeta('handgrip', 'position', e.target.value)} />
      <Grid container spacing={2}>{(['left', 'right'] as const).flatMap((side) => [1, 2, 3].map((attempt) => <Grid key={`${side}-${attempt}`} size={{ xs: 12, sm: 6, md: 4 }}><AdvancedNumberField label={`${side === 'left' ? 'Izquierda' : 'Derecha'} · intento ${attempt}`} unit="kgf" value={value('handgrip', 'handgrip_strength', side, attempt)} onChange={(next) => setMeasurement('handgrip', 'handgrip_strength', next, side, attempt)} /></Grid>))}</Grid>
    </Stack></Box>

    <Box sx={panel}><Stack spacing={2}>
      <Box><Typography fontWeight={800}>Cuatro pliegues · Durnin–Womersley</Typography><Typography variant="body2" color="text.secondary">Tres lecturas derechas en cada sitio. El backend calcula la media por sitio y su sumatoria; no estima porcentaje de grasa.</Typography></Box>
      {deviceFields('skinfold_4', 'plicómetro')}
      {SKINFOLD_FIELDS.map(([code, label]) => <Box key={code}><Typography variant="subtitle2" mb={1}>{label}</Typography><Grid container spacing={2}>{[1, 2, 3].map((attempt) => <Grid key={attempt} size={{ xs: 12, sm: 4 }}><AdvancedNumberField label={`Intento ${attempt}`} unit="mm" value={value('skinfold_4', code, 'right', attempt)} onChange={(next) => setMeasurement('skinfold_4', code, next, 'right', attempt)} /></Grid>)}</Grid></Box>)}
    </Stack></Box>

    <Box sx={panel}><Stack spacing={2}>
      <Box><Typography fontWeight={800}>Bioimpedancia clínica</Typography><Typography variant="body2" color="text.secondary">Se conservan las salidas informadas por el equipo y las condiciones de medición. NutriWard no genera interpretación automática.</Typography></Box>
      {deviceFields('bioimpedance', 'bioimpedanciómetro')}
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth label="Tecnología" placeholder="Monofrecuencia, multifrecuencia…" value={meta('bioimpedance', 'technology')} onChange={(e) => setMeta('bioimpedance', 'technology', e.target.value)} /></Grid>
        <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth label="Frecuencias (kHz)" value={meta('bioimpedance', 'frequencies_khz')} onChange={(e) => setMeta('bioimpedance', 'frequencies_khz', e.target.value)} /></Grid>
        <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth label="Posición" value={meta('bioimpedance', 'position')} onChange={(e) => setMeta('bioimpedance', 'position', e.target.value)} /></Grid>
        <Grid size={{ xs: 12, md: 4 }}><FormControl fullWidth><InputLabel>Preparación</InputLabel><Select label="Preparación" value={meta('bioimpedance', 'preparation_status')} onChange={(e) => setMeta('bioimpedance', 'preparation_status', e.target.value)}><MenuItem value=""><em>Sin registrar</em></MenuItem><MenuItem value="standard">Estándar</MenuItem><MenuItem value="nonstandard">No estándar</MenuItem><MenuItem value="unknown">Desconocida</MenuItem></Select></FormControl></Grid>
        <Grid size={{ xs: 12, md: 4 }}><AdvancedNumberField label="Horas de ayuno" unit="h" value={meta('bioimpedance', 'fasting_hours')} onChange={(next) => setMeta('bioimpedance', 'fasting_hours', next)} /></Grid>
        <Grid size={{ xs: 12, md: 4 }}><FormControl fullWidth><InputLabel>Hidratación</InputLabel><Select label="Hidratación" value={meta('bioimpedance', 'hydration_status')} onChange={(e) => setMeta('bioimpedance', 'hydration_status', e.target.value)}><MenuItem value=""><em>Sin registrar</em></MenuItem><MenuItem value="usual">Habitual</MenuItem><MenuItem value="altered">Alterada</MenuItem><MenuItem value="unknown">Desconocida</MenuItem></Select></FormControl></Grid>
        <Grid size={{ xs: 12, md: 4 }}>{booleanSelect('bioimpedance', 'recent_exercise', 'Ejercicio reciente')}</Grid>
        <Grid size={{ xs: 12, md: 4 }}>{booleanSelect('bioimpedance', 'bladder_emptied', 'Vejiga vaciada')}</Grid>
        <Grid size={{ xs: 12, md: 4 }}>{booleanSelect('bioimpedance', 'edema_present', 'Edema presente')}</Grid>
      </Grid>
      <Divider /><Typography variant="subtitle2">Resultados informados por el equipo</Typography>
      <Grid container spacing={2}>{BIA_FIELDS.map(([code, label, unit]) => <Grid key={code} size={{ xs: 12, sm: 6, md: 4 }}><AdvancedNumberField label={label} unit={unit} value={value('bioimpedance', code)} onChange={(next) => setMeasurement('bioimpedance', code, next)} /></Grid>)}</Grid>
      <TextField fullWidth multiline minRows={2} label="Observaciones de la medición" value={meta('bioimpedance', 'observations')} onChange={(e) => setMeta('bioimpedance', 'observations', e.target.value)} />
    </Stack></Box>
  </Stack>
}

function ageFromBirthDate(dateOfBirth: string, reference = new Date()): number {
  const [year, month, day] = dateOfBirth.split('-').map(Number)
  const birthdayPassed = (reference.getUTCMonth() + 1) > month
    || ((reference.getUTCMonth() + 1) === month && reference.getUTCDate() >= day)
  return reference.getUTCFullYear() - year - (birthdayPassed ? 0 : 1)
}

function YesNoQuestion({ label, value, onChange }: {
  label: string; value: string; onChange: (value: string) => void
}) {
  return <Box sx={{ border: 1, borderColor: value === '' ? 'divider' : 'primary.light', borderRadius: 2, p: 1.5 }}>
    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} gap={1}>
      <Typography fontWeight={650}>{label}</Typography>
      <Stack direction="row" gap={1}>
        <Button aria-label={`No · ${label}`} size="small" variant={value === 'false' ? 'contained' : 'outlined'} color={value === 'false' ? 'success' : 'inherit'} onClick={() => onChange('false')}>No</Button>
        <Button aria-label={`Sí · ${label}`} size="small" variant={value === 'true' ? 'contained' : 'outlined'} color={value === 'true' ? 'warning' : 'inherit'} onClick={() => onChange('true')}>Sí</Button>
      </Stack>
    </Stack>
  </Box>
}

function NrsScreeningForm({ editor, set, legacy }: {
  editor: EditorState; set: (name: keyof EditorState, value: string) => void; legacy: boolean
}) {
  const preview = nrsPreview(editor)
  const calculated = calculatedBmi(editor)
  const diseaseLevels = [
    ['0', 'Requerimientos normales', 'Sin aumento relevante de requerimientos.'],
    ['1', 'Gravedad leve', 'Enfermedad crónica reagudizada, fractura de cadera o diabetes con complicaciones.'],
    ['2', 'Gravedad moderada', 'Cirugía abdominal mayor, neumonía grave, ACV o neoplasia hematológica.'],
    ['3', 'Gravedad grave', 'Trauma craneoencefálico, trasplante de médula o paciente crítico de alta gravedad.'],
  ]
  return <Stack spacing={2.5}>
    <Alert severity="info">Responda el flujo en orden. El puntaje mostrado es provisional; el backend lo recalcula y conserva la versión del algoritmo al guardar.</Alert>
    {legacy && <Alert severity="warning">Este borrador proviene del formulario NRS-2002 anterior. Complete los criterios guiados para actualizarlo sin inventar antecedentes.</Alert>}

    <Box><Typography variant="subtitle1" fontWeight={800}>Paso 1 · Tamizaje inicial</Typography><Typography variant="body2" color="text.secondary">Si todas las respuestas son negativas, finaliza aquí y se recomienda repetir semanalmente.</Typography></Box>
    <Grid container spacing={2}>
      <Grid size={{ xs: 12, md: 5 }}><TextField
        fullWidth type="number" label="IMC utilizado" value={preview.bmi}
        disabled={calculated !== null}
        onChange={(e) => set('nrs_bmi', e.target.value)}
        inputProps={{ min: 1, step: '0.1' }}
        helperText={calculated !== null ? 'Calculado desde el peso y la talla de esta evolución.' : 'Ingrese el IMC si no hay peso y talla disponibles.'}
      /></Grid>
      <Grid size={{ xs: 12, md: 7 }}>{preview.bmi ? <Box sx={{ border: 1, borderColor: 'primary.light', borderRadius: 2, p: 1.5 }}><Stack direction="row" justifyContent="space-between" alignItems="center" gap={1}><Typography fontWeight={650}>¿IMC menor de 20,5 kg/m²?</Typography><Chip color={preview.initial.initial_bmi_below_20_5 === 'true' ? 'warning' : 'success'} label={`${preview.initial.initial_bmi_below_20_5 === 'true' ? 'Sí' : 'No'} · calculado`} /></Stack></Box> : <YesNoQuestion label="¿IMC menor de 20,5 kg/m²?" value={editor.nrs_initial_bmi} onChange={(next) => set('nrs_initial_bmi', next)} />}</Grid>
    </Grid>
    <YesNoQuestion label="¿Ha perdido peso durante los últimos 3 meses?" value={editor.nrs_initial_weight_loss} onChange={(next) => set('nrs_initial_weight_loss', next)} />
    <YesNoQuestion label="¿Redujo la ingesta durante la última semana?" value={editor.nrs_initial_intake} onChange={(next) => set('nrs_initial_intake', next)} />
    <YesNoQuestion label="¿Está gravemente enfermo o en tratamiento intensivo?" value={editor.nrs_initial_severe_illness} onChange={(next) => set('nrs_initial_severe_illness', next)} />

    {!preview.initialComplete && <Alert severity="warning">Complete las cuatro respuestas iniciales. Puede guardar el avance como borrador.</Alert>}
    {preview.initialComplete && !preview.needsFinal && <Alert severity="success"><strong>Tamizaje inicial negativo · NRS-2002: 0.</strong> Repetir semanalmente durante la hospitalización.</Alert>}

    {preview.needsFinal && <>
      <Divider /><Box><Typography variant="subtitle1" fontWeight={800}>Paso 2 · Deterioro nutricional</Typography><Typography variant="body2" color="text.secondary">NutriWard compara los criterios y utiliza el puntaje mayor; no los suma entre sí.</Typography></Box>
      <FormControl fullWidth><InputLabel id="nrs-weight-loss-label">Pérdida de peso</InputLabel><Select id="nrs-weight-loss" labelId="nrs-weight-loss-label" label="Pérdida de peso" value={editor.nrs_weight_loss_category} onChange={(e) => set('nrs_weight_loss_category', e.target.value)}>
        <MenuItem value="none_or_below_threshold">0 · Sin pérdida o bajo los umbrales</MenuItem>
        <MenuItem value="over_5_3_months">1 · Más de 5% en 3 meses</MenuItem>
        <MenuItem value="over_5_2_months">2 · Más de 5% en 2 meses</MenuItem>
        <MenuItem value="over_5_1_month_or_over_15_3_months">3 · Más de 5% en 1 mes o más de 15% en 3 meses</MenuItem>
      </Select></FormControl>
      <FormControl fullWidth><InputLabel id="nrs-intake-label">Ingesta respecto del requerimiento</InputLabel><Select id="nrs-intake" labelId="nrs-intake-label" label="Ingesta respecto del requerimiento" value={editor.nrs_intake_category} onChange={(e) => set('nrs_intake_category', e.target.value)}>
        <MenuItem value="over_75">0 · Más de 75%</MenuItem><MenuItem value="50_75">1 · 50–75%</MenuItem><MenuItem value="25_50">2 · 25–50%</MenuItem><MenuItem value="below_25">3 · Menos de 25%</MenuItem>
      </Select></FormControl>
      <YesNoQuestion label="¿Existe deterioro del estado general asociado al IMC?" value={editor.nrs_general_deterioration} onChange={(next) => set('nrs_general_deterioration', next)} />
      {preview.initial.initial_bmi_below_20_5 === 'true' && !preview.bmi && <Alert severity="warning">Ingrese el IMC utilizado para distinguir el criterio 18,5–20,5 del criterio menor de 18,5.</Alert>}
      <Stack direction="row" useFlexGap flexWrap="wrap" gap={1}><Chip label={`Pérdida: ${preview.weightScore ?? '—'}`} /><Chip label={`Ingesta: ${preview.intakeScore ?? '—'}`} /><Chip label={`IMC: ${preview.bmiScore}`} /><Chip color="primary" label={`Componente nutricional: ${preview.nutritionalScore}`} /></Stack>

      <Divider /><Box><Typography variant="subtitle1" fontWeight={800}>Paso 3 · Gravedad de la enfermedad</Typography><Typography variant="body2" color="text.secondary">Seleccione según el estrés metabólico y aumento de requerimientos. No se infiere automáticamente desde el diagnóstico.</Typography></Box>
      <Grid container spacing={1.5}>{diseaseLevels.map(([score, title, description]) => <Grid key={score} size={{ xs: 12, md: 6 }}><Button
        fullWidth variant={editor.nrs_disease === score ? 'contained' : 'outlined'}
        onClick={() => set('nrs_disease', score)}
        sx={{ height: '100%', alignItems: 'flex-start', flexDirection: 'column', textAlign: 'left', py: 1.5 }}
      ><Typography fontWeight={800}>{score} · {title}</Typography><Typography variant="body2" sx={{ textTransform: 'none' }}>{description}</Typography></Button></Grid>)}</Grid>
      <Alert severity="warning">No asigne 3 puntos sólo por estar hospitalizado. La categoría representa el aumento de requerimientos y la gravedad metabólica actual.</Alert>

      <Divider /><Typography variant="subtitle1" fontWeight={800}>Paso 4 · Edad</Typography>
      {editor.nrs_age_source === 'patient_record_exact' ? <Alert severity="info">Edad calculada automáticamente desde la fecha de nacimiento: <strong>{editor.nrs_age === 'true' ? '70 años o más · +1 punto' : 'menor de 70 años · 0 puntos'}</strong>.</Alert> : <FormControl fullWidth><InputLabel id="nrs-age-label">Confirmación de edad</InputLabel><Select id="nrs-age" labelId="nrs-age-label" label="Confirmación de edad" value={editor.nrs_age_confirmed === 'true' ? editor.nrs_age : ''} onChange={(e) => { set('nrs_age', e.target.value); set('nrs_age_confirmed', 'true'); set('nrs_age_source', editor.nrs_age_source === 'patient_record_estimated' ? 'patient_record_estimated_confirmed' : 'manual') }}>
        <MenuItem value="false">Menor de 70 años · 0 puntos</MenuItem><MenuItem value="true">70 años o más · +1 punto</MenuItem>
      </Select><FormHelperText>{editor.nrs_age_source.startsWith('patient_record_estimated') ? 'La edad del registro es estimada y requiere confirmación profesional.' : 'No hay una fecha de nacimiento exacta disponible.'}</FormHelperText></FormControl>}

      <Box sx={{ border: 2, borderColor: preview.total !== null && preview.total >= 3 ? 'warning.main' : 'success.main', borderRadius: 2, p: 2 }}><Grid container spacing={1}>
        <Grid size={{ xs: 6, md: 3 }}><FieldValue label="Deterioro nutricional" value={preview.finalComplete ? preview.nutritionalScore : '—'} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><FieldValue label="Gravedad" value={editor.nrs_disease || '—'} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><FieldValue label="Edad" value={editor.nrs_age_confirmed === 'true' ? (editor.nrs_age === 'true' ? 1 : 0) : '—'} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><FieldValue label="Total NRS-2002" value={preview.total ?? 'Incompleto'} /></Grid>
        <Grid size={12}><Alert severity={preview.total !== null && preview.total >= 3 ? 'warning' : preview.total === null ? 'info' : 'success'}>{preview.total === null ? 'Complete los pasos para obtener el resultado.' : preview.total >= 3 ? 'Con riesgo nutricional: efectuar valoración completa y definir un plan según estabilidad clínica.' : 'Sin riesgo nutricional según NRS-2002: repetir semanalmente.'}</Alert></Grid>
      </Grid></Box>
    </>}
  </Stack>
}

function NutritionEditor({ open, record, admissionId, csrfToken, mode, presetSections, patientDateOfBirth, patientAgeIsEstimated = false, onClose, onSaved }: {
  open: boolean, record: NutritionEncounterRead | null, admissionId: string, csrfToken: string,
  mode: EvolutionMode, presetSections?: number[],
  patientDateOfBirth?: string | null, patientAgeIsEstimated?: boolean,
  onClose: () => void, onSaved: () => void,
}) {
  const [editor, setEditor] = useState<EditorState>(EMPTY_EDITOR)
  const [advanced, setAdvanced] = useState<AdvancedDraftState>({})
  const [activeSection, setActiveSection] = useState(0)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sectionErrors, setSectionErrors] = useState<string[]>([])
  const [selectedSections, setSelectedSections] = useState<number[]>(MODE_SECTIONS[mode])

  useEffect(() => {
    if (open) {
      const sections = record
        ? sectionsFromEncounter(record)
        : [...(presetSections ?? MODE_SECTIONS[mode])]
      const encounterType = mode === 'initial' ? 'initial_assessment'
        : mode === 'follow_up' ? 'follow_up' : 'other'
      const nextEditor = record ? fromEncounter(record) : { ...EMPTY_EDITOR, encounter_type: encounterType }
      if (!record && patientDateOfBirth) {
        nextEditor.nrs_age = String(ageFromBirthDate(patientDateOfBirth) >= 70)
        nextEditor.nrs_age_source = patientAgeIsEstimated ? 'patient_record_estimated' : 'patient_record_exact'
        nextEditor.nrs_age_confirmed = patientAgeIsEstimated ? 'false' : 'true'
      }
      setEditor(nextEditor)
      setAdvanced(record ? advancedFromEncounter(record) : {})
      setSelectedSections(sections)
      setDirty(false); setActiveSection(sections[0] ?? 0); setError(null); setSectionErrors([])
    }
  }, [mode, open, patientAgeIsEstimated, patientDateOfBirth, presetSections, record])
  useEffect(() => {
    if (!dirty) return
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])

  function set(name: keyof EditorState, value: string) {
    setEditor((current) => ({ ...current, [name]: value })); setDirty(true)
  }
  function setAdvancedValue(key: string, value: string) {
    setAdvanced((current) => ({ ...current, [key]: value })); setDirty(true)
  }
  function close() {
    if (dirty && !window.confirm('Hay cambios sin guardar. ¿Desea cerrar el editor?')) return
    onClose()
  }
  async function save(finalize = false) {
    if (finalize && selectedSections.includes(3) && editor.screening_tool === 'nrs_2002' && nrsPreview(editor).total === null) {
      setSectionErrors(['Tamizaje NRS-2002: complete todas las respuestas antes de finalizar.'])
      setActiveSection(3)
      return
    }
    const advancedErrors = selectedSections.includes(2) ? validateAdvancedMeasurements(advanced) : []
    if (advancedErrors.length) { setSectionErrors(advancedErrors); setActiveSection(2); return }
    if (finalize && !window.confirm('¿Confirma registrar y finalizar esta evolución? Luego será inmutable y cualquier cambio requerirá una corrección.')) return
    setSaving(true); setError(null); setSectionErrors([])
    try {
      let saved: NutritionEncounterRead
      if (record) {
        saved = await apiRequest(`/nutrition-care-encounters/${record.encounter.id}`, {
          method: 'PATCH', body: JSON.stringify({ ...buildPayload(editor, selectedSections, advanced), version: record.encounter.version }),
        }, csrfToken)
      } else {
        saved = await apiRequest(`/admissions/${admissionId}/nutrition-care-encounters`, {
          method: 'POST', body: JSON.stringify(buildPayload(editor, selectedSections, advanced)),
        }, csrfToken)
      }
      if (finalize) {
        saved = await apiRequest(`/nutrition-care-encounters/${saved.encounter.id}/finalize`, {
          method: 'POST', body: JSON.stringify({ version: saved.encounter.version }),
        }, csrfToken)
      }
      setDirty(false); onSaved()
    } catch (caught) {
      const message = clinicalError(caught)
      setError(message)
      if (caught instanceof ApiError && caught.status === 422) setSectionErrors([
        editor.encounter_type === 'initial_assessment'
          ? 'Revise Contexto, Tamizaje, Diagnóstico PES y Seguimiento antes de finalizar.'
          : 'Revise el motivo, la fuente y la síntesis de la evolución.',
      ])
    } finally { setSaving(false) }
  }

  const progressFields = [
    editor.reason_for_assessment, editor.hospitalization_reason, editor.weight_value,
    editor.screening_tool, editor.clinical_findings, editor.intake_percentage || editor.lab_name,
    editor.basal_result || editor.energy_result, editor.pes_problem, editor.regimen_type,
    editor.clinical_summary,
  ]
  const progress = Math.round((selectedSections.filter((section) => progressFields[section]).length
    / Math.max(selectedSections.length, 1)) * 100)

  function toggleSection(section: number) {
    if (section === 0 || section === 9 || mode === 'initial') return
    setSelectedSections((current) => {
      const next = current.includes(section)
        ? current.filter((value) => value !== section)
        : [...current, section].sort((a, b) => a - b)
      if (!next.includes(activeSection)) setActiveSection(next[0])
      return next
    })
    setDirty(true)
  }

  return <Dialog open={open} onClose={close} fullWidth maxWidth="lg" fullScreen={false} aria-labelledby="nutrition-editor-title">
    <DialogTitle id="nutrition-editor-title">{record ? 'Continuar evolución nutricional' : MODE_LABELS[mode]}</DialogTitle>
    <DialogContent dividers>
      <Stack spacing={2.5}>
        <Box><Stack direction="row" justifyContent="space-between"><Typography variant="body2">Progreso por secciones</Typography><Typography variant="body2">{progress}%</Typography></Stack><LinearProgress variant="determinate" value={progress} /></Box>
        {mode !== 'initial' && !record && <Box>
          <Typography variant="subtitle2" mb={1}>¿Qué información cambió en esta evolución?</Typography>
          <Stack direction="row" useFlexGap flexWrap="wrap" gap={1}>
            {SECTIONS.map((label, index) => <Chip
              key={label}
              label={label}
              clickable={index !== 0 && index !== 9}
              color={selectedSections.includes(index) ? 'primary' : 'default'}
              variant={selectedSections.includes(index) ? 'filled' : 'outlined'}
              onClick={() => toggleSection(index)}
            />)}
          </Stack>
          <Typography variant="caption" color="text.secondary" display="block" mt={1}>
            Contexto y síntesis se incluyen siempre. Los demás módulos son opcionales.
          </Typography>
        </Box>}
        <Stepper nonLinear activeStep={selectedSections.indexOf(activeSection)} sx={{ overflowX: 'auto', pb: 1 }}>
          {selectedSections.map((index) => <Step key={SECTIONS[index]}><StepButton onClick={() => setActiveSection(index)}>{index + 1}</StepButton></Step>)}
        </Stepper>
        <Typography variant="h6">{SECTIONS[activeSection]}</Typography>
        {error && <Alert severity="error">{error}</Alert>}
        {sectionErrors.map((message) => <Alert severity="warning" key={message}>{message}</Alert>)}
        {activeSection === 0 && <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 6 }}><FormControl fullWidth><InputLabel>Tipo de atención</InputLabel><Select label="Tipo de atención" value={editor.encounter_type} onChange={(e) => set('encounter_type', e.target.value)}>{Object.entries(TYPE_LABELS).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl></Grid>
          <Grid size={{ xs: 12, md: 6 }}><FormControl fullWidth><InputLabel>Fuente de información</InputLabel><Select label="Fuente de información" value={editor.information_source} onChange={(e) => set('information_source', e.target.value)}>{Object.entries(SOURCE_LABELS).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl></Grid>
          <Grid size={12}><TextField fullWidth label="Motivo de evaluación" value={editor.reason_for_assessment} onChange={(e) => set('reason_for_assessment', e.target.value)} required /></Grid>
          <Grid size={12}><FormControl fullWidth><InputLabel>Población clínica</InputLabel><Select label="Población clínica" value={editor.population_group} onChange={(e) => { const population = e.target.value; setEditor((current) => ({ ...current, population_group: population, screening_tool: SCREENING_DEFAULTS[population] })); setDirty(true) }}>{Object.entries(POPULATION_LABELS).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select><FormHelperText>Cambiar población adapta el formulario y no borra los demás datos.</FormHelperText></FormControl></Grid>
        </Grid>}
        {activeSection === 1 && <Stack spacing={2}><TextField label="Motivo de hospitalización" value={editor.hospitalization_reason} onChange={(e) => set('hospitalization_reason', e.target.value)} multiline minRows={2} /><TextField label="Vía de alimentación actual" value={editor.current_feeding_route} onChange={(e) => set('current_feeding_route', e.target.value)} /><TextField label="Apetito y cambios recientes" value={editor.appetite} onChange={(e) => set('appetite', e.target.value)} multiline minRows={2} /></Stack>}
        {activeSection === 2 && <Stack spacing={2.5}>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 5 }}><FormControl fullWidth><InputLabel>Tipo de peso</InputLabel><Select label="Tipo de peso" value={editor.weight_type} onChange={(e) => set('weight_type', e.target.value)}>{Object.entries(MEASUREMENT_LABELS).filter(([value]) => value.includes('weight')).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl></Grid>
            <Grid size={{ xs: 8, md: 5 }}><TextField fullWidth type="number" label="Peso" value={editor.weight_value} onChange={(e) => set('weight_value', e.target.value)} inputProps={{ min: 0, step: '0.01' }} /></Grid><Grid size={{ xs: 4, md: 2 }}><TextField fullWidth label="Unidad" value="kg" disabled /></Grid>
            <Grid size={{ xs: 8, md: 10 }}><TextField fullWidth type="number" label="Talla de pie" value={editor.height_value} onChange={(e) => set('height_value', e.target.value)} inputProps={{ min: 0, step: '0.1' }} /></Grid><Grid size={{ xs: 4, md: 2 }}><TextField fullWidth label="Unidad" value="cm" disabled /></Grid>
            <Grid size={12}><Alert severity="info">El IMC se calcula en backend. Ningún tipo de peso se reemplaza automáticamente por peso ideal o ajustado.</Alert></Grid>
          </Grid>
          <Divider><Chip label="Mediciones avanzadas opcionales" /></Divider>
          <AdvancedAnthropometryEditor state={advanced} setValue={setAdvancedValue} />
        </Stack>}
        {activeSection === 3 && <Stack spacing={2}>
          <FormControl fullWidth><InputLabel>Herramienta de tamizaje</InputLabel><Select label="Herramienta de tamizaje" value={editor.screening_tool} onChange={(e) => set('screening_tool', e.target.value)}><MenuItem value="nrs_2002">NRS-2002 · ESPEN</MenuItem><MenuItem value="strongkids">STRONGkids</MenuItem><MenuItem value="none">Sin herramienta definida</MenuItem></Select><FormHelperText>Predeterminada para {POPULATION_LABELS[editor.population_group]}: {SCREENING_DEFAULTS[editor.population_group]}</FormHelperText></FormControl>
          {editor.screening_tool === 'nrs_2002' && <NrsScreeningForm editor={editor} set={set} legacy={Boolean(record?.screenings[0] && text(record.screenings[0].algorithm_version) !== 'espen-nrs2002-v2')} />}
          {editor.screening_tool === 'strongkids' && <Grid container spacing={2}>{[['strong_subjective', 'Evaluación clínica subjetiva'], ['strong_disease', 'Enfermedad de alto riesgo'], ['strong_intake', 'Ingesta reducida o pérdidas'], ['strong_weight', 'Pérdida o mala ganancia de peso']].map(([name, label]) => <Grid key={name} size={{ xs: 12, md: 6 }}><FormControl fullWidth><InputLabel>{label}</InputLabel><Select label={label} value={editor[name as keyof EditorState]} onChange={(e) => set(name as keyof EditorState, e.target.value)}><MenuItem value="false">No</MenuItem><MenuItem value="true">Sí</MenuItem></Select></FormControl></Grid>)}</Grid>}
          {editor.screening_tool === 'none' && <TextField label="Motivo documentado" value={editor.no_tool_reason} onChange={(e) => set('no_tool_reason', e.target.value)} required multiline minRows={2} />}
          <Alert severity="info">El puntaje y la clasificación se calculan exclusivamente en backend y quedan congelados con su versión.</Alert>
        </Stack>}
        {activeSection === 4 && <Stack spacing={2}><TextField label="Hallazgos clínicos" value={editor.clinical_findings} onChange={(e) => set('clinical_findings', e.target.value)} multiline minRows={3} /><TextField label="Hallazgos digestivos y tolerancia" value={editor.digestive_findings} onChange={(e) => set('digestive_findings', e.target.value)} multiline minRows={3} /><TextField label="Estado nutricional" value={editor.nutritional_status} onChange={(e) => set('nutritional_status', e.target.value)} /></Stack>}
        {activeSection === 5 && <Grid container spacing={2}><Grid size={{ xs: 12, md: 6 }}><TextField fullWidth type="number" label="Ingesta consumida" value={editor.intake_percentage} onChange={(e) => set('intake_percentage', e.target.value)} helperText="Porcentaje entre 0 y 100" inputProps={{ min: 0, max: 100 }} /></Grid><Grid size={{ xs: 12, md: 6 }}><TextField fullWidth label="Motivo de ingesta incompleta" value={editor.intake_reason} onChange={(e) => set('intake_reason', e.target.value)} /></Grid><Grid size={{ xs: 12, md: 5 }}><TextField fullWidth label="Examen transcrito" value={editor.lab_name} onChange={(e) => set('lab_name', e.target.value)} /></Grid><Grid size={{ xs: 7, md: 5 }}><TextField fullWidth label="Valor" value={editor.lab_value} onChange={(e) => set('lab_value', e.target.value)} /></Grid><Grid size={{ xs: 5, md: 2 }}><TextField fullWidth label="Unidad" value={editor.lab_unit} onChange={(e) => set('lab_unit', e.target.value)} /></Grid><Grid size={12}><Alert severity="warning">Dato transcrito manualmente desde TrakCare. NutriWard no interpreta ni reemplaza al sistema de laboratorio.</Alert></Grid></Grid>}
        {activeSection === 6 && <Stack spacing={2}><FormControl fullWidth><InputLabel>Método</InputLabel><Select label="Método" value={editor.requirement_method} onChange={(e) => set('requirement_method', e.target.value)}><MenuItem value="factorial">Factorial (predeterminado)</MenuItem><MenuItem value="manual">Cálculo manual razonado</MenuItem></Select></FormControl>{editor.requirement_method === 'factorial' ? <Grid container spacing={2}><Grid size={{ xs: 12, md: 4 }}><TextField fullWidth type="number" label="Resultado basal" value={editor.basal_result} onChange={(e) => set('basal_result', e.target.value)} /></Grid><Grid size={{ xs: 12, md: 4 }}><TextField fullWidth type="number" label="Factor de actividad" value={editor.activity_factor} onChange={(e) => set('activity_factor', e.target.value)} /></Grid><Grid size={{ xs: 12, md: 4 }}><TextField fullWidth type="number" label="Factor de estrés" value={editor.stress_factor} onChange={(e) => set('stress_factor', e.target.value)} /></Grid></Grid> : <TextField type="number" label="Resultado manual (kcal/día)" value={editor.energy_result} onChange={(e) => set('energy_result', e.target.value)} />}<Alert severity="info">Los factores no se seleccionan por diagnóstico. Deben confirmarse profesionalmente.</Alert></Stack>}
        {activeSection === 7 && <Stack spacing={2}><TextField required label="Problema" value={editor.pes_problem} onChange={(e) => set('pes_problem', e.target.value)} /><TextField required label="Etiología" value={editor.pes_etiology} onChange={(e) => set('pes_etiology', e.target.value)} /><TextField required label="Signos y síntomas" value={editor.pes_signs} onChange={(e) => set('pes_signs', e.target.value)} multiline minRows={2} />{editor.pes_problem && editor.pes_etiology && editor.pes_signs && <Alert severity="info">{editor.pes_problem} relacionado con {editor.pes_etiology}, evidenciado por {editor.pes_signs}</Alert>}</Stack>}
        {activeSection === 8 && <Grid container spacing={2}><Grid size={{ xs: 12, md: 4 }}><FormControl fullWidth><InputLabel>Vía principal</InputLabel><Select label="Vía principal" value={editor.prescription_route} onChange={(e) => set('prescription_route', e.target.value)}>{['oral', 'enteral', 'parenteral', 'mixed', 'fasting', 'other'].map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}</Select></FormControl></Grid><Grid size={{ xs: 12, md: 8 }}><TextField fullWidth label="Régimen general" value={editor.regimen_type} onChange={(e) => set('regimen_type', e.target.value)} /></Grid><Grid size={{ xs: 12, md: 4 }}><TextField fullWidth type="number" label="Objetivo energético" value={editor.energy_target} onChange={(e) => set('energy_target', e.target.value)} helperText="kcal/día" /></Grid><Grid size={{ xs: 12, md: 4 }}><TextField fullWidth type="number" label="Objetivo proteico" value={editor.protein_target} onChange={(e) => set('protein_target', e.target.value)} helperText="g/día" /></Grid><Grid size={{ xs: 12, md: 4 }}><TextField fullWidth type="number" label="Objetivo hídrico" value={editor.fluid_target} onChange={(e) => set('fluid_target', e.target.value)} helperText="mL/día" /></Grid><Grid size={12}><TextField fullWidth label="Restricciones" value={editor.restrictions} onChange={(e) => set('restrictions', e.target.value)} multiline minRows={2} /></Grid></Grid>}
        {activeSection === 9 && <Stack spacing={2}><TextField required label="Síntesis clínica" value={editor.clinical_summary} onChange={(e) => set('clinical_summary', e.target.value)} multiline minRows={3} /><TextField label="Objetivos" value={editor.objectives} onChange={(e) => set('objectives', e.target.value)} multiline minRows={2} /><TextField label="Plan de monitoreo" value={editor.monitoring_plan} onChange={(e) => set('monitoring_plan', e.target.value)} multiline minRows={2} /><TextField label="Pendientes" value={editor.pending_actions} onChange={(e) => set('pending_actions', e.target.value)} multiline minRows={2} /><TextField type="datetime-local" label="Fecha sugerida de reevaluación" value={editor.suggested_reassessment_at} onChange={(e) => set('suggested_reassessment_at', e.target.value)} InputLabelProps={{ shrink: true }} /></Stack>}
      </Stack>
    </DialogContent>
    <DialogActions sx={{ flexWrap: 'wrap', gap: 1 }}><Button onClick={close}>Cerrar</Button><Button variant="outlined" disabled={saving} onClick={() => void save(false)}>Guardar borrador</Button><Button variant="contained" disabled={saving} onClick={() => void save(true)}>Registrar y finalizar</Button></DialogActions>
  </Dialog>
}

function useClinicalData<T>(path: string | null, refreshKey: number) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(Boolean(path))
  const [error, setError] = useState<string | null>(null)
  const sequence = useRef(0)
  const load = useCallback(async () => {
    if (!path) { setData(null); setLoading(false); return }
    const current = ++sequence.current; setLoading(true); setError(null)
    try { const next = await apiRequest<T>(path); if (current === sequence.current) setData(next) }
    catch (caught) { if (current === sequence.current) setError(clinicalError(caught)) }
    finally { if (current === sequence.current) setLoading(false) }
  }, [path])
  useEffect(() => { setData(null); void load(); return () => { sequence.current += 1 } }, [load, refreshKey])
  return { data, loading, error, reload: load }
}

function modeForEncounter(type: string): EvolutionMode {
  if (type === 'initial_assessment') return 'initial'
  if (type === 'follow_up' || type === 'reassessment' || type === 'discharge_planning') return 'follow_up'
  return 'specific'
}

function EvolutionStartDialog({ open, onClose, onSelect }: {
  open: boolean; onClose: () => void; onSelect: (mode: EvolutionMode) => void
}) {
  const choices: Array<{ mode: EvolutionMode; description: string }> = [
    { mode: 'follow_up', description: 'Documente sólo los cambios del control diario: clínica, ingesta y seguimiento.' },
    { mode: 'specific', description: 'Registre peso, tamizaje, requerimientos, PES, prescripción o exámenes sin completar todo el formulario.' },
    { mode: 'initial', description: 'Evaluación estructurada completa para el ingreso nutricional del paciente.' },
  ]
  return <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
    <DialogTitle>Registrar evolución nutricional</DialogTitle>
    <DialogContent dividers><Stack spacing={1.5}>
      <Typography color="text.secondary">Seleccione el flujo que mejor representa el trabajo realizado.</Typography>
      {choices.map((choice) => <Button
        key={choice.mode}
        variant={choice.mode === 'follow_up' ? 'contained' : 'outlined'}
        onClick={() => onSelect(choice.mode)}
        sx={{ alignItems: 'flex-start', flexDirection: 'column', textAlign: 'left', py: 1.5 }}
      >
        <Typography fontWeight={800}>{MODE_LABELS[choice.mode]}</Typography>
        <Typography variant="body2" sx={{ textTransform: 'none' }}>{choice.description}</Typography>
      </Button>)}
    </Stack></DialogContent>
    <DialogActions><Button onClick={onClose}>Cancelar</Button></DialogActions>
  </Dialog>
}

export function NutritionRegisterAction({ admissionId, csrfToken, patientDateOfBirth, patientAgeIsEstimated, onSaved }: { admissionId: string; csrfToken: string; patientDateOfBirth?: string | null; patientAgeIsEstimated?: boolean; onSaved: () => void }) {
  const [startOpen, setStartOpen] = useState(false)
  const [editorOpen, setEditorOpen] = useState(false)
  const [mode, setMode] = useState<EvolutionMode>('follow_up')
  function start(modeChoice: EvolutionMode) {
    setMode(modeChoice)
    setStartOpen(false)
    setEditorOpen(true)
  }
  return <>
    <Button variant="contained" startIcon={<ClipboardPlus size={17} />} onClick={() => setStartOpen(true)}>Registrar</Button>
    <EvolutionStartDialog open={startOpen} onClose={() => setStartOpen(false)} onSelect={start} />
    <NutritionEditor
      open={editorOpen}
      record={null}
      admissionId={admissionId}
      csrfToken={csrfToken}
      mode={mode}
      patientDateOfBirth={patientDateOfBirth}
      patientAgeIsEstimated={patientAgeIsEstimated}
      onClose={() => setEditorOpen(false)}
      onSaved={() => { setEditorOpen(false); onSaved() }}
    />
  </>
}

export function NutritionActivityCard({ admissionId, historical, csrfToken, patientDateOfBirth, patientAgeIsEstimated, refreshKey = 0, onChanged }: { admissionId: string, historical: boolean, csrfToken: string, patientDateOfBirth?: string | null, patientAgeIsEstimated?: boolean, refreshKey?: number, onChanged: () => void }) {
  const [refresh, setRefresh] = useState(0)
  const { data, loading, error, reload } = useClinicalData<NutritionEncounterList>(`/admissions/${admissionId}/nutrition-care-encounters`, refresh + refreshKey)
  const [editorOpen, setEditorOpen] = useState(false)
  const [mode, setMode] = useState<EvolutionMode>('follow_up')
  const [selected, setSelected] = useState<NutritionEncounterRead | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  async function openRecord(id: string, edit = false) {
    try {
      const record = await apiRequest<NutritionEncounterRead>(`/nutrition-care-encounters/${id}`)
      setMode(modeForEncounter(record.encounter.encounter_type))
      setSelected(record); setEditorOpen(edit)
    }
    catch (caught) { setActionError(clinicalError(caught)) }
  }
  async function correct(id: string, version: number) {
    const reason = window.prompt('Motivo de corrección (obligatorio):')
    if (!reason || reason.trim().length < 10) return
    if (!window.confirm('Se creará un borrador correctivo enlazado. El original no será sobrescrito.')) return
    try {
      const record = await apiRequest<NutritionEncounterRead>(`/nutrition-care-encounters/${id}/correct`, { method: 'POST', body: JSON.stringify({ version, reason }) }, csrfToken)
      setMode(modeForEncounter(record.encounter.encounter_type))
      setSelected(record); setEditorOpen(true); setRefresh((value) => value + 1)
    } catch (caught) { setActionError(clinicalError(caught)) }
  }
  async function cancelDraft(id: string, version: number) {
    const reason = window.prompt('Motivo de cancelación (obligatorio):')
    if (!reason || reason.trim().length < 5) return
    if (!window.confirm('El borrador quedará cancelado y se conservará para trazabilidad.')) return
    try {
      await apiRequest(`/nutrition-care-encounters/${id}/cancel`, {
        method: 'POST', body: JSON.stringify({ version, reason }),
      }, csrfToken)
      setRefresh((value) => value + 1); onChanged()
    } catch (caught) { setActionError(clinicalError(caught)) }
  }
  return <Stack spacing={2}>
    {historical && <Alert severity="info">Episodio histórico · Solo lectura. Las evoluciones finalizadas permanecen disponibles.</Alert>}
    {actionError && <Alert severity="error">{actionError}</Alert>}
    <SectionCard title="Actividad nutricional" description="Cronología auditable de registros, borradores y correcciones. Las pestañas clínicas muestran la información vigente de cada módulo.">
      {error ? <ErrorState message={error} onRetry={() => void reload()} /> : loading ? <LoadingState label="Cargando actividad nutricional" rows={3} /> : !data?.items?.length ? <EmptyState title="Sin actividad nutricional" description="No hay documentación nutricional para esta hospitalización." /> : <Stack spacing={0}>{data.items.map((item, index) => <Box key={item.id} sx={{ position: 'relative', pl: 3, pb: index === data.items.length - 1 ? 0 : 2.5, '&::before': index === data.items.length - 1 ? undefined : { content: '""', position: 'absolute', left: 7, top: 16, bottom: 0, borderLeft: 2, borderColor: 'divider' } }}><Box sx={{ position: 'absolute', left: 0, top: 8, width: 16, height: 16, borderRadius: '50%', bgcolor: item.status === 'draft' ? 'warning.main' : item.status === 'cancelled' ? 'text.disabled' : 'success.main', border: 3, borderColor: 'background.paper' }} /><Box sx={{ border: 1, borderColor: 'divider', borderRadius: 2, p: 2 }}><Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" gap={2}><Box sx={{ minWidth: 0 }}><Stack direction="row" gap={1} alignItems="center" flexWrap="wrap"><Typography fontWeight={800}>{TYPE_LABELS[item.encounter_type]}</Typography><StatusBadge label={STATUS_LABELS[item.status]} tone={item.status === 'draft' ? 'warning' : item.status === 'cancelled' ? 'neutral' : 'success'} /></Stack><Typography variant="body2">{formatDate(item.encounter_datetime)} · {item.author_name}</Typography><Typography variant="body2" color="text.secondary">{item.clinical_summary || 'Borrador sin síntesis clínica'}</Typography><Stack direction="row" useFlexGap flexWrap="wrap" gap={0.5} mt={1}>{(item.documented_sections ?? []).map((section) => <Chip key={section} size="small" variant="outlined" label={SECTION_SUMMARY_LABELS[section] || section} />)}</Stack></Box><Stack direction="row" gap={1} flexWrap="wrap" alignItems="flex-start"><Button size="small" startIcon={<ExternalLink size={15} />} onClick={() => void openRecord(item.id)}>Ver</Button>{item.status === 'draft' && !historical && <><Button size="small" startIcon={<Pencil size={15} />} onClick={() => void openRecord(item.id, true)}>Continuar</Button><Button size="small" color="error" onClick={() => void cancelDraft(item.id, item.version)}>Cancelar</Button></>}{(item.status === 'finalized' || item.status === 'corrected') && !historical && <Button size="small" startIcon={<RotateCcw size={15} />} onClick={() => void correct(item.id, item.version)}>Corregir</Button>}</Stack></Stack></Box></Box>)}</Stack>}
    </SectionCard>
    {selected && !editorOpen && <EncounterViewer record={selected} onClose={() => setSelected(null)} />}
    <NutritionEditor open={editorOpen} record={selected?.encounter.status === 'draft' ? selected : null} admissionId={admissionId} csrfToken={csrfToken} mode={mode} patientDateOfBirth={patientDateOfBirth} patientAgeIsEstimated={patientAgeIsEstimated} onClose={() => { setEditorOpen(false); setSelected(null) }} onSaved={() => { setEditorOpen(false); setSelected(null); setRefresh((value) => value + 1); onChanged() }} />
  </Stack>
}

function ScreeningResult({ row }: { row: Record<string, unknown> }) {
  const answers = (row.answers as Array<Record<string, unknown>> | undefined) ?? []
  const byCode = Object.fromEntries(answers.map((answer) => [text(answer.answer_code), answer]))
  const classification = text(row.classification)
  if (row.tool_code === 'none') return <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 2, p: 1.5 }}><Stack spacing={1}>
    <Typography fontWeight={800}>Tamizaje no aplicado</Typography>
    <Typography variant="caption" color="text.secondary">Documentado {formatDate(row.applied_at)}</Typography>
    <FieldValue label="Motivo" value={row.no_tool_reason} />
  </Stack></Box>
  if (row.tool_code === 'strongkids') {
    const resultLabel = classification === 'high' ? 'Riesgo alto' : classification === 'medium' ? 'Riesgo moderado' : classification === 'low' ? 'Riesgo bajo' : classification
    const answerLabels: Record<string, string> = {
      subjective_clinical_assessment: 'Evaluación clínica subjetiva',
      high_risk_disease: 'Enfermedad de alto riesgo',
      nutritional_intake_or_losses: 'Ingesta reducida o pérdidas',
      weight_loss_or_poor_gain: 'Pérdida o mala ganancia de peso',
    }
    return <Box sx={{ border: 1, borderColor: classification === 'high' ? 'warning.main' : 'divider', borderRadius: 2, p: 1.5 }}><Stack spacing={1}>
      <Stack direction="row" justifyContent="space-between" gap={1} flexWrap="wrap"><Typography fontWeight={800}>STRONGkids · {resultLabel}</Typography><Chip color={classification === 'high' ? 'warning' : 'success'} label={`Puntaje ${text(row.total_score)}`} /></Stack>
      <Typography variant="caption" color="text.secondary">Aplicado {formatDate(row.applied_at)}</Typography>
      <Grid container spacing={1}>{answers.filter((answer) => answerLabels[text(answer.answer_code)]).map((answer) => <Grid key={text(answer.id) + text(answer.answer_code)} size={{ xs: 12, sm: 6 }}><FieldValue label={answerLabels[text(answer.answer_code)]} value={text(answer.answer_value) === 'true' ? 'Sí' : 'No'} /></Grid>)}</Grid>
    </Stack></Box>
  }
  const resultLabel = classification === 'nutritional_risk' ? 'Con riesgo nutricional'
    : classification === 'initial_screen_negative' ? 'Tamizaje inicial negativo'
      : classification === 'no_nutritional_risk' ? 'Sin riesgo nutricional' : 'Tamizaje incompleto'
  return <Box sx={{ border: 1, borderColor: classification === 'nutritional_risk' ? 'warning.main' : 'divider', borderRadius: 2, p: 1.5 }}><Stack spacing={1}>
    <Stack direction="row" justifyContent="space-between" gap={1} flexWrap="wrap"><Typography fontWeight={800}>NRS-2002 · {resultLabel}</Typography><Chip color={classification === 'nutritional_risk' ? 'warning' : classification === 'incomplete' ? 'default' : 'success'} label={`Puntaje ${text(row.total_score)}`} /></Stack>
    <Typography variant="caption" color="text.secondary">Algoritmo {text(row.algorithm_version)} · aplicado {formatDate(row.applied_at)}</Typography>
    {classification !== 'initial_screen_negative' && classification !== 'incomplete' && <Grid container spacing={1}><Grid size={{ xs: 4 }}><FieldValue label="Deterioro nutricional" value={byCode.nutritional_status_score?.component_score ?? byCode.nutritional_status_score?.answer_value} /></Grid><Grid size={{ xs: 4 }}><FieldValue label="Gravedad" value={byCode.disease_severity_score?.component_score ?? byCode.disease_severity_score?.answer_value} /></Grid><Grid size={{ xs: 4 }}><FieldValue label="Edad" value={byCode.age_70_or_more?.component_score ?? (byCode.age_70_or_more?.answer_value === 'true' ? 1 : 0)} /></Grid></Grid>}
    {(classification === 'initial_screen_negative' || classification === 'no_nutritional_risk') && <Typography variant="body2">Repetir el tamizaje semanalmente durante la hospitalización.</Typography>}
  </Stack></Box>
}

function EncounterViewer({ record, onClose }: { record: NutritionEncounterRead, onClose: () => void }) {
  return <Dialog open onClose={onClose} fullWidth maxWidth="md"><DialogTitle>Evolución nutricional · {STATUS_LABELS[record.encounter.status]}</DialogTitle><DialogContent dividers><Stack spacing={2.5}>
    <Grid container spacing={2}><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Fecha" value={formatDate(record.encounter.encounter_datetime)} /></Grid><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Profesional" value={record.author_name} /></Grid><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Tipo" value={TYPE_LABELS[record.encounter.encounter_type]} /></Grid><Grid size={12}><FieldValue label="Motivo" value={record.encounter.reason_for_assessment} /></Grid><Grid size={12}><FieldValue label="Síntesis" value={record.encounter.clinical_summary} /></Grid></Grid>
    {record.assessment && <><Divider /><Typography variant="subtitle1" fontWeight={800}>Evaluación</Typography><Grid container spacing={2}><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Población" value={POPULATION_LABELS[text(record.assessment.population_group)]} /></Grid><Grid size={{ xs: 12, md: 8 }}><FieldValue label="Estado nutricional" value={record.assessment.nutritional_status} /></Grid><Grid size={12}><FieldValue label="Hallazgos clínicos" value={record.assessment.clinical_findings} /></Grid><Grid size={12}><FieldValue label="Hallazgos digestivos" value={record.assessment.digestive_findings} /></Grid></Grid></>}
    {record.anthropometry.length > 0 && <><Divider /><Typography variant="subtitle1" fontWeight={800}>Antropometría</Typography>{record.anthropometry.map((row) => <Typography key={text(row.id)}>{MEASUREMENT_LABELS[text(row.measurement_type)] || text(row.measurement_type)}: {text(row.value)} {text(row.unit)}</Typography>)}</>}
    {(record.advanced_measurements ?? []).length > 0 && <><Divider /><Typography variant="subtitle1" fontWeight={800}>Mediciones antropométricas avanzadas</Typography><Stack spacing={2}>{(record.advanced_measurements ?? []).map((session) => <Box key={session.id} sx={{ border: 1, borderColor: 'divider', borderRadius: 2, p: 1.5 }}><Stack spacing={1}>
      <Stack direction="row" justifyContent="space-between" gap={1} flexWrap="wrap"><Typography fontWeight={800}>{session.session_type === 'circumference' ? 'Circunferencias' : session.session_type === 'handgrip' ? 'Dinamometría' : session.session_type === 'skinfold_4' ? 'Cuatro pliegues Durnin–Womersley' : 'Bioimpedancia clínica'}</Typography><Chip size="small" variant="outlined" label={`${session.protocol_code} ${session.protocol_version}`} /></Stack>
      <Typography variant="caption" color="text.secondary">{formatDate(session.measured_at)}{session.device_manufacturer ? ` · ${session.device_manufacturer} ${session.device_model ?? ''}` : ''}{session.position ? ` · ${session.position}` : ''}</Typography>
      <Grid container spacing={1}>{session.values.map((row) => <Grid key={row.id} size={{ xs: 12, sm: 6 }}><Typography variant="body2"><strong>{ADVANCED_MEASUREMENT_LABELS[row.measurement_code] || row.measurement_code}</strong>{row.laterality !== 'none' ? ` · ${row.laterality === 'left' ? 'izquierda' : row.laterality === 'right' ? 'derecha' : 'bilateral'}` : ''}{row.attempt_number ? ` · intento ${row.attempt_number}` : ''}: {text(row.value)} {row.unit} {row.value_nature === 'calculated' && <Chip component="span" size="small" color="primary" label="calculado" sx={{ ml: 0.5 }} />}</Typography></Grid>)}</Grid>
      {session.session_type === 'bioimpedance' && <Typography variant="caption" color="text.secondary">Preparación: {session.preparation_status ?? 'no registrada'} · Hidratación: {session.hydration_status ?? 'no registrada'} · Edema: {session.edema_present === null ? 'no registrado' : session.edema_present ? 'sí' : 'no'}</Typography>}
    </Stack></Box>)}</Stack></>}
    {record.screenings.length > 0 && <><Divider /><Typography variant="subtitle1" fontWeight={800}>Tamizaje</Typography><Stack spacing={1.5}>{record.screenings.map((row) => <ScreeningResult key={text(row.id)} row={row} />)}</Stack></>}
    {record.requirements.length > 0 && <><Divider /><Typography variant="subtitle1" fontWeight={800}>Requerimientos</Typography>{record.requirements.map((row) => <Typography key={text(row.id)}>{text(row.nutrient_code)}: {text(row.adopted_result)} {text(row.unit)} · {text(row.method)}</Typography>)}</>}
    {record.diagnoses.length > 0 && <><Divider /><Typography variant="subtitle1" fontWeight={800}>Diagnósticos PES</Typography>{record.diagnoses.map((row) => <Typography key={text(row.id)}>{text(row.generated_statement)}</Typography>)}</>}
    {record.prescription && <><Divider /><Typography variant="subtitle1" fontWeight={800}>Prescripción</Typography><FieldValue label="Régimen" value={record.prescription.regimen_type} /><FieldValue label="Vía" value={record.prescription.primary_route} /><FieldValue label="Restricciones" value={record.prescription.restrictions} /></>}
    {record.intake.length > 0 && <><Divider /><Typography variant="subtitle1" fontWeight={800}>Ingesta</Typography>{record.intake.map((row) => <Typography key={text(row.id)}>{formatDate(text(row.intake_date), false)} · {text(row.consumed_percentage)}% · {text(row.incomplete_reason)}</Typography>)}</>}
    {record.labs.length > 0 && <><Divider /><Typography variant="subtitle1" fontWeight={800}>Exámenes</Typography>{record.labs.map((row) => <Typography key={text(row.id)}>{text(row.test_name)}: {text(row.value)} {text(row.unit)}</Typography>)}</>}
    {record.encounter.correction_reason && <Alert severity="info">Corrección: {record.encounter.correction_reason}</Alert>}{record.encounter.cancellation_reason && <Alert severity="warning">Cancelación: {record.encounter.cancellation_reason}</Alert>}
  </Stack></DialogContent><DialogActions><Button onClick={onClose}>Cerrar</Button></DialogActions></Dialog>
}

function ModularEvolutionAction({ admissionId, csrfToken, historical, label, sections, patientDateOfBirth, patientAgeIsEstimated, onSaved }: {
  admissionId: string; csrfToken: string; historical: boolean; label: string;
  sections: number[]; patientDateOfBirth?: string | null; patientAgeIsEstimated?: boolean;
  onSaved: () => void
}) {
  const [open, setOpen] = useState(false)
  if (historical) return null
  return <>
    <Button variant="outlined" startIcon={<ClipboardPlus size={16} />} onClick={() => setOpen(true)}>{label}</Button>
    <NutritionEditor
      open={open}
      record={null}
      admissionId={admissionId}
      csrfToken={csrfToken}
      mode="specific"
      presetSections={[0, ...sections, 9].filter((value, index, values) => values.indexOf(value) === index).sort((a, b) => a - b)}
      patientDateOfBirth={patientDateOfBirth}
      patientAgeIsEstimated={patientAgeIsEstimated}
      onClose={() => setOpen(false)}
      onSaved={() => { setOpen(false); onSaved() }}
    />
  </>
}

function AdvancedMeasurementCard({ session }: { session: NutritionAdvancedMeasurementSession }) {
  const title = session.session_type === 'circumference' ? 'Circunferencias'
    : session.session_type === 'handgrip' ? 'Dinamometría'
      : session.session_type === 'skinfold_4' ? 'Cuatro pliegues Durnin–Womersley'
        : 'Bioimpedancia clínica'
  return <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 2, p: 1.5 }}><Stack spacing={1}>
    <Stack direction="row" justifyContent="space-between" gap={1} flexWrap="wrap"><Typography fontWeight={800}>{title}</Typography><Chip size="small" variant="outlined" label={`${session.protocol_code} ${session.protocol_version}`} /></Stack>
    <Typography variant="caption" color="text.secondary">{formatDate(session.measured_at)}{session.device_manufacturer ? ` · ${session.device_manufacturer} ${session.device_model ?? ''}` : ''}{session.position ? ` · ${session.position}` : ''}</Typography>
    <Grid container spacing={1}>{session.values.map((row) => <Grid key={row.id} size={{ xs: 12, sm: 6 }}><Typography variant="body2"><strong>{ADVANCED_MEASUREMENT_LABELS[row.measurement_code] || row.measurement_code}</strong>{row.laterality !== 'none' ? ` · ${row.laterality === 'left' ? 'izquierda' : row.laterality === 'right' ? 'derecha' : 'bilateral'}` : ''}{row.attempt_number ? ` · intento ${row.attempt_number}` : ''}: {text(row.value)} {row.unit} {row.value_nature === 'calculated' && <Chip component="span" size="small" color="primary" label="calculado" sx={{ ml: 0.5 }} />}</Typography></Grid>)}</Grid>
    {session.session_type === 'bioimpedance' && <Typography variant="caption" color="text.secondary">Preparación: {session.preparation_status ?? 'no registrada'} · Hidratación: {session.hydration_status ?? 'no registrada'} · Edema: {session.edema_present === null ? 'no registrado' : session.edema_present ? 'sí' : 'no'}</Typography>}
  </Stack></Box>
}

function AnthropometryTab({ admissionId, historical, csrfToken, onChanged }: { admissionId: string; historical: boolean; csrfToken: string; onChanged: () => void }) {
  const { data, loading, error, reload } = useClinicalData<NutritionProjectionList>(`/admissions/${admissionId}/nutrition-anthropometry`, 0)
  return <SectionCard title="Antropometría y composición corporal" description="Mediciones simples, composición corporal y función muscular ordenadas longitudinalmente." actions={<ModularEvolutionAction admissionId={admissionId} csrfToken={csrfToken} historical={historical} label="Registrar mediciones" sections={[2]} onSaved={() => { void reload(); onChanged() }} />}>
    {error ? <ErrorState message={error} onRetry={() => void reload()} /> : loading ? <LoadingState label="Cargando antropometría" rows={4} /> : !data?.items.length ? <EmptyState title="Sin mediciones finalizadas" description="Registre peso, talla, circunferencias, dinamometría, pliegues o bioimpedancia." /> : <Stack spacing={2}>
      <Alert severity="info">Los resultados del equipo se muestran como informados por el dispositivo; NutriWard no los interpreta automáticamente.</Alert>
      {data.items.map((row) => row.record_type === 'advanced_session'
        ? <AdvancedMeasurementCard key={text(row.id)} session={row as unknown as NutritionAdvancedMeasurementSession} />
        : <Box key={text(row.id)} sx={{ borderBottom: 1, borderColor: 'divider', pb: 1.5 }}><Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={1}><Typography fontWeight={700}>{MEASUREMENT_LABELS[text(row.measurement_type)] || text(row.measurement_type)}</Typography><Typography>{text(row.value)} {text(row.unit)}</Typography></Stack><Typography variant="caption" color="text.secondary">{formatDate(row.measured_at)} · {text(row.value_nature)} · confiabilidad {text(row.reliability)}</Typography></Box>)}
    </Stack>}
  </SectionCard>
}

function ScreeningTab({ admissionId, historical, csrfToken, patientDateOfBirth, patientAgeIsEstimated, onChanged }: { admissionId: string; historical: boolean; csrfToken: string; patientDateOfBirth?: string | null; patientAgeIsEstimated?: boolean; onChanged: () => void }) {
  const { data, loading, error, reload } = useClinicalData<NutritionProjectionList>(`/admissions/${admissionId}/nutrition-screenings`, 0)
  return <SectionCard title="Tamizaje nutricional" description="Resultado vigente e historial de herramientas aplicadas durante la hospitalización." actions={<ModularEvolutionAction admissionId={admissionId} csrfToken={csrfToken} historical={historical} label="Registrar tamizaje" sections={[3]} patientDateOfBirth={patientDateOfBirth} patientAgeIsEstimated={patientAgeIsEstimated} onSaved={() => { void reload(); onChanged() }} />}>
    {error ? <ErrorState message={error} onRetry={() => void reload()} /> : loading ? <LoadingState label="Cargando tamizajes" rows={3} /> : !data?.items.length ? <EmptyState title="Sin tamizajes finalizados" description="Aplique la herramienta correspondiente a la población o documente por qué no corresponde." /> : <Stack spacing={2}>
      <Alert severity="success">Último tamizaje aplicado · {formatDate(data.items[0].applied_at)}</Alert>
      {data.items.map((row) => <ScreeningResult key={text(row.id)} row={row} />)}
    </Stack>}
  </SectionCard>
}

function AssessmentTab({ admissionId, historical, csrfToken, onChanged }: { admissionId: string; historical: boolean; csrfToken: string; onChanged: () => void }) {
  const { data, loading, error, reload } = useClinicalData<NutritionProjectionList>(`/admissions/${admissionId}/nutrition-assessments`, 0)
  const current = useClinicalData<NutritionLatest>(`/admissions/${admissionId}/nutrition-latest`, 0)
  const latest = data?.items?.[0]
  function reloadAll() { void reload(); void current.reload(); onChanged() }
  return <SectionCard title="Evaluación clínica" description="Valoración clínica, requerimientos, diagnósticos PES, objetivos y seguimiento vigentes." actions={<ModularEvolutionAction admissionId={admissionId} csrfToken={csrfToken} historical={historical} label="Actualizar evaluación" sections={[1, 4, 6, 7]} onSaved={reloadAll} />}>{error || current.error ? <ErrorState message={error || current.error || ''} onRetry={() => { void reload(); void current.reload() }} /> : loading || current.loading ? <LoadingState label="Cargando evaluación clínica" rows={4} /> : !latest && !current.data?.latest_encounter ? <EmptyState title="Sin evaluación finalizada" description="Registre y finalice una evaluación para publicar esta proyección." /> : <Stack spacing={2}>
    {latest && <><Alert severity="success">Última evaluación finalizada · {formatDate(latest.observed_at)}</Alert><Grid container spacing={2}><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Población" value={POPULATION_LABELS[text(latest.population_group)]} /></Grid><Grid size={{ xs: 12, md: 8 }}><FieldValue label="Estado nutricional" value={latest.nutritional_status} /></Grid><Grid size={12}><FieldValue label="Hallazgos clínicos" value={latest.clinical_findings} /></Grid><Grid size={12}><FieldValue label="Hallazgos digestivos" value={latest.digestive_findings} /></Grid><Grid size={12}><FieldValue label="Objetivos" value={latest.objectives} /></Grid><Grid size={12}><FieldValue label="Plan de monitoreo" value={latest.monitoring_plan} /></Grid><Grid size={12}><FieldValue label="Pendientes" value={latest.pending_actions} /></Grid></Grid></>}
    <Divider /><Typography variant="subtitle1" fontWeight={800}>Requerimientos adoptados</Typography>
    {!current.data?.adopted_requirements.length ? <Typography color="text.secondary">Sin requerimientos finalizados.</Typography> : current.data.adopted_requirements.map((row) => <Typography key={text(row.id)} variant="body2">{text(row.nutrient_code)}: {text(row.adopted_result)} {text(row.unit)} · {text(row.method)}</Typography>)}
    <Divider /><Typography variant="subtitle1" fontWeight={800}>Diagnósticos PES activos</Typography>
    {!current.data?.active_diagnoses.length ? <Typography color="text.secondary">Sin diagnósticos PES activos.</Typography> : current.data.active_diagnoses.map((row) => <Typography key={text(row.id)} variant="body2">{text(row.generated_statement)}</Typography>)}
    {data?.items.length ? <><Divider /><Typography variant="subtitle1" fontWeight={800}>Historial de evaluaciones ({data.total})</Typography>{data.items.map((row) => <Typography key={text(row.id)} variant="body2">{formatDate(row.observed_at)} · {POPULATION_LABELS[text(row.population_group)]} · Evolución {text(row.encounter_id)}</Typography>)}</> : null}
  </Stack>}</SectionCard>
}

function PrescriptionTab({ admissionId, historical, csrfToken, onChanged }: { admissionId: string; historical: boolean; csrfToken: string; onChanged: () => void }) {
  const { data, loading, error, reload } = useClinicalData<NutritionProjectionList>(`/admissions/${admissionId}/nutrition-prescriptions`, 0)
  const latest = data?.items?.[0]
  return <SectionCard title="Prescripción nutricional" description="La prescripción vigente procede de la última evolución finalizada que modificó este módulo." actions={<ModularEvolutionAction admissionId={admissionId} csrfToken={csrfToken} historical={historical} label="Modificar prescripción" sections={[8]} onSaved={() => { void reload(); onChanged() }} />}>{error ? <ErrorState message={error} onRetry={() => void reload()} /> : loading ? <LoadingState label="Cargando prescripciones" rows={3} /> : !latest ? <EmptyState title="Sin prescripción vigente" description="No hay una prescripción finalizada en este episodio." /> : <Stack spacing={2}><Grid container spacing={2}><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Fecha efectiva" value={formatDate(latest.effective_from)} /></Grid><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Vía" value={latest.primary_route} /></Grid><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Estado" value={latest.status} /></Grid><Grid size={12}><FieldValue label="Régimen general" value={latest.regimen_type} /></Grid><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Energía" value={latest.energy_target ? `${latest.energy_target} kcal/día` : null} /></Grid><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Proteínas" value={latest.protein_target ? `${latest.protein_target} g/día` : null} /></Grid><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Líquidos" value={latest.fluid_target ? `${latest.fluid_target} mL/día` : null} /></Grid><Grid size={12}><FieldValue label="Restricciones" value={latest.restrictions} /></Grid></Grid><Alert severity="info">Los borradores nunca alimentan raciones. Alimentación recibe sólo la proyección operacional de la minuta finalizada, no esta ficha clínica.</Alert></Stack>}</SectionCard>
}

function IntakeTab({ admissionId, historical, csrfToken, onChanged }: { admissionId: string; historical: boolean; csrfToken: string; onChanged: () => void }) {
  const { data, loading, error, reload } = useClinicalData<NutritionProjectionList>(`/admissions/${admissionId}/nutrition-intake`, 0)
  return <Stack spacing={2}><Alert severity="info">Esta pestaña conserva el control clínico de ingesta. La minuta diaria y el consolidado de producción se gestionan en sus módulos operacionales específicos.</Alert><SectionCard title="Control de ingesta" actions={<ModularEvolutionAction admissionId={admissionId} csrfToken={csrfToken} historical={historical} label="Registrar ingesta" sections={[5]} onSaved={() => { void reload(); onChanged() }} />}>{error ? <ErrorState message={error} onRetry={() => void reload()} /> : loading ? <LoadingState label="Cargando ingesta" rows={3} /> : !data?.items.length ? <EmptyState title="Sin controles de ingesta" description="Registre ingesta mediante una evolución específica." /> : <TableContainer><Table size="small"><TableHead><TableRow><TableCell>Fecha</TableCell><TableCell>Tiempo</TableCell><TableCell>Consumido</TableCell><TableCell>Motivo incompleto</TableCell><TableCell>Fuente</TableCell></TableRow></TableHead><TableBody>{data.items.map((row) => <TableRow key={text(row.id)}><TableCell>{formatDate(text(row.intake_date), false)}</TableCell><TableCell>{text(row.meal_time)}</TableCell><TableCell>{text(row.consumed_percentage)}%</TableCell><TableCell>{text(row.incomplete_reason)}</TableCell><TableCell>{SOURCE_LABELS[text(row.source)] || text(row.source)}</TableCell></TableRow>)}</TableBody></Table></TableContainer>}</SectionCard></Stack>
}

type ReviewLabRow = ParsedLabRow & { catalog_test_id: string | null; resolution: 'match' | 'create' | 'pending' }

function localDateTimeValue() {
  const now = new Date()
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 16)
}

function exactCatalogMatch(name: string, catalog: LaboratoryTestCatalogItem[]) {
  const normalized = normalizeLabLabel(name)
  return catalog.find((item) => item.normalized_name === normalized || item.normalized_aliases.includes(normalized)) ?? null
}

function LabPasteDialog({ open, admissionId, csrfToken, catalog, onClose, onSaved }: {
  open: boolean; admissionId: string; csrfToken: string; catalog: LaboratoryTestCatalogItem[];
  onClose: () => void; onSaved: () => void
}) {
  const [raw, setRaw] = useState('')
  const [sampledAt, setSampledAt] = useState(localDateTimeValue)
  const [rows, setRows] = useState<ReviewLabRow[]>([])
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setRaw(''); setRows([]); setError(null); setSampledAt(localDateTimeValue())
  }, [open])

  function review(value: string) {
    setRaw(value); setError(null)
    const parsed = parseLabPaste(value)
    setRows(parsed.map((row) => {
      const match = exactCatalogMatch(row.test_name, catalog)
      return { ...row, catalog_test_id: match?.id ?? null, resolution: match ? 'match' : 'create' }
    }))
  }

  function resolutionValue(row: ReviewLabRow) {
    return row.catalog_test_id ? `catalog:${row.catalog_test_id}` : row.resolution
  }

  function setResolution(index: number, value: string) {
    setRows((current) => current.map((row, rowIndex) => rowIndex !== index ? row : value.startsWith('catalog:')
      ? { ...row, catalog_test_id: value.slice(8), resolution: 'match' }
      : { ...row, catalog_test_id: null, resolution: value as 'create' | 'pending' }))
  }

  async function save() {
    if (!rows.length) { setError('Pegue al menos una fila con examen y resultado.'); return }
    setSaving(true); setError(null)
    try {
      await apiRequest(`/admissions/${admissionId}/nutrition-lab-imports`, {
        method: 'POST',
        body: JSON.stringify({
          sampled_at: new Date(sampledAt).toISOString(), source: 'trakcare_manual',
          rows: rows.map((row) => ({
            test_name: row.test_name, value: row.value, unit: row.unit || null,
            reference_range: row.reference_range || null, flag: row.flag,
            catalog_test_id: row.catalog_test_id, resolution: row.resolution,
          })),
        }),
      }, csrfToken)
      onSaved(); onClose()
    } catch (caught) { setError(clinicalError(caught)) }
    finally { setSaving(false) }
  }

  const newCount = rows.filter((row) => row.resolution === 'create' && !row.catalog_test_id).length
  const pendingCount = rows.filter((row) => row.resolution === 'pending').length
  return <Dialog open={open} onClose={saving ? undefined : onClose} fullWidth maxWidth="lg">
    <DialogTitle>Pegar resultados de exámenes</DialogTitle>
    <DialogContent dividers><Stack spacing={2}>
      <Alert severity="info">Copie desde TrakCare o Excel. Se aceptan columnas en cualquier orden si incluyen encabezados como Examen, Resultado, Unidad y Rango.</Alert>
      <TextField label="Fecha y hora de la muestra" type="datetime-local" value={sampledAt} onChange={(event) => setSampledAt(event.target.value)} InputLabelProps={{ shrink: true }} sx={{ maxWidth: 320 }} />
      <TextField multiline minRows={5} label="Tabla de resultados" placeholder={'Examen\tResultado\tUnidad\tRango\nAlbúmina\t3,2\tg/dL\t3,5 - 5,2'} value={raw} onChange={(event) => review(event.target.value)} />
      {raw && !rows.length && <Alert severity="warning">No se detectaron filas válidas. Use tabulaciones o punto y coma entre las columnas.</Alert>}
      {rows.length > 0 && <>
        <Stack direction="row" gap={1} flexWrap="wrap"><Chip color="success" label={`${rows.length} filas listas`} />{newCount > 0 && <Chip color="warning" label={`${newCount} exámenes nuevos`} />}{pendingCount > 0 && <Chip label={`${pendingCount} pendientes`} />}</Stack>
        <TableContainer sx={{ maxHeight: 390 }}><Table size="small" stickyHeader><TableHead><TableRow><TableCell>Examen original</TableCell><TableCell>Resultado</TableCell><TableCell>Unidad</TableCell><TableCell>Referencia</TableCell><TableCell sx={{ minWidth: 240 }}>Clasificación</TableCell></TableRow></TableHead><TableBody>{rows.map((row, index) => <TableRow key={`${row.test_name}:${index}`}><TableCell>{row.test_name}</TableCell><TableCell>{row.value}</TableCell><TableCell>{row.unit || '—'}</TableCell><TableCell>{row.reference_range || '—'}</TableCell><TableCell><TextField select size="small" fullWidth value={resolutionValue(row)} onChange={(event) => setResolution(index, event.target.value)}>
          {!row.catalog_test_id && <MenuItem value="create">Crear “{row.test_name}”</MenuItem>}
          <MenuItem value="pending">Guardar pendiente</MenuItem>
          {catalog.map((item) => <MenuItem key={item.id} value={`catalog:${item.id}`}>{item.canonical_name}</MenuItem>)}
        </TextField></TableCell></TableRow>)}</TableBody></Table></TableContainer>
      </>}
      {error && <Alert severity="error">{error}</Alert>}{saving && <LinearProgress />}
    </Stack></DialogContent>
    <DialogActions><Button onClick={onClose} disabled={saving}>Cancelar</Button><Button variant="contained" onClick={() => void save()} disabled={saving || !rows.length}>Guardar {rows.length || ''} resultados</Button></DialogActions>
  </Dialog>
}

function LabTrendChart({ series, compact = false }: { series: LabTrendSeries; compact?: boolean }) {
  const points = series.points
  if (!points.length) return null
  const numeric = points.map((point) => Number(point.numeric_value))
  const bounds = points.flatMap((point) => [point.reference_low, point.reference_high].filter((value): value is number => value !== null).map(Number))
  const minimum = Math.min(...numeric, ...bounds)
  const maximum = Math.max(...numeric, ...bounds)
  const padding = Math.max((maximum - minimum) * 0.12, Math.abs(maximum) * 0.05, 1)
  const low = minimum - padding; const high = maximum + padding
  const width = 640; const height = compact ? 95 : 230; const left = compact ? 8 : 48; const right = 14; const top = 14; const bottom = compact ? 12 : 38
  const x = (index: number) => points.length === 1 ? (left + width - right) / 2 : left + index * (width - left - right) / (points.length - 1)
  const y = (value: number) => top + (high - value) * (height - top - bottom) / (high - low)
  const latest = points[points.length - 1]
  const referenceTop = latest.reference_high === null ? null : y(Number(latest.reference_high))
  const referenceBottom = latest.reference_low === null ? null : y(Number(latest.reference_low))
  const outOfRange = (point: LabTrendPoint) => point.flag === 'high' || point.flag === 'low' || point.flag === 'critical' || (point.reference_low !== null && Number(point.numeric_value) < Number(point.reference_low)) || (point.reference_high !== null && Number(point.numeric_value) > Number(point.reference_high))
  return <Box>
    <Box component="svg" role="img" aria-label={`Tendencia de ${series.display_name}`} viewBox={`0 0 ${width} ${height}`} sx={{ width: '100%', height: compact ? 95 : { xs: 180, md: 230 }, display: 'block', color: 'text.secondary' }}>
      {!compact && referenceTop !== null && referenceBottom !== null && <rect x={left} y={Math.min(referenceTop, referenceBottom)} width={width - left - right} height={Math.abs(referenceBottom - referenceTop)} fill="#2e7d32" opacity="0.1" />}
      {!compact && <><line x1={left} y1={top} x2={left} y2={height - bottom} stroke="currentColor" opacity="0.35" /><line x1={left} y1={height - bottom} x2={width - right} y2={height - bottom} stroke="currentColor" opacity="0.35" /><text x={left - 6} y={top + 5} textAnchor="end" fontSize="11" fill="currentColor">{maximum.toLocaleString('es-CL')}</text><text x={left - 6} y={height - bottom} textAnchor="end" fontSize="11" fill="currentColor">{minimum.toLocaleString('es-CL')}</text></>}
      {points.length > 1 && <polyline fill="none" stroke="#1976d2" strokeWidth={compact ? 3 : 2.5} points={points.map((point, index) => `${x(index)},${y(Number(point.numeric_value))}`).join(' ')} />}
      {points.map((point, index) => <circle key={point.id} cx={x(index)} cy={y(Number(point.numeric_value))} r={compact ? 4 : 5} fill={outOfRange(point) ? '#ed6c02' : '#1976d2'}><title>{`${formatDate(point.sampled_at)}: ${point.value} ${point.unit ?? ''}`}</title></circle>)}
      {!compact && <><text x={left} y={height - 9} fontSize="11" fill="currentColor">{formatDate(points[0].sampled_at, false)}</text><text x={width - right} y={height - 9} textAnchor="end" fontSize="11" fill="currentColor">{formatDate(latest.sampled_at, false)}</text></>}
    </Box>
  </Box>
}

function LabsTab({ admissionId, historical, csrfToken, onChanged }: { admissionId: string; historical: boolean; csrfToken: string; onChanged: () => void }) {
  const [refresh, setRefresh] = useState(0)
  const [pasteOpen, setPasteOpen] = useState(false)
  const [selectedKey, setSelectedKey] = useState('')
  const [classifyingId, setClassifyingId] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const results = useClinicalData<NutritionProjectionList>(`/admissions/${admissionId}/nutrition-labs?page_size=100`, refresh)
  const trends = useClinicalData<LabTrendResponse>(`/admissions/${admissionId}/nutrition-lab-trends`, refresh)
  const catalog = useClinicalData<LaboratoryTestCatalogItem[]>('/nutrition-lab-catalog', refresh)
  const catalogItems = Array.isArray(catalog.data) ? catalog.data : []
  const selected = trends.data?.series?.find((series) => series.key === selectedKey) ?? trends.data?.series?.[0] ?? null
  function reloadAll() { setRefresh((value) => value + 1); onChanged() }
  async function classify(rowId: string, target: string) {
    setClassifyingId(rowId); setActionError(null)
    try {
      await apiRequest(`/nutrition-lab-observations/${rowId}/classification`, {
        method: 'PATCH',
        body: JSON.stringify(target === 'create' ? { create_new: true } : { catalog_test_id: target }),
      }, csrfToken)
      reloadAll()
    } catch (caught) { setActionError(clinicalError(caught)) }
    finally { setClassifyingId(null) }
  }
  return <Stack spacing={2}>
    <Alert severity="info">Los rangos se conservan como fueron transcritos. NutriWard muestra tendencias y resultados fuera del rango informado, pero no reemplaza la validación del laboratorio.</Alert>
    {actionError && <Alert severity="error">{actionError}</Alert>}
    {trends.data?.series?.length ? <SectionCard title="Tendencia histórica" description="Seleccione un examen para revisar su evolución durante esta hospitalización."><Stack spacing={1.5}><FormControl size="small" sx={{ maxWidth: 420 }}><InputLabel id="lab-series-label">Examen</InputLabel><Select labelId="lab-series-label" label="Examen" value={selected?.key ?? ''} onChange={(event) => setSelectedKey(event.target.value)}>{trends.data.series.map((series) => <MenuItem key={series.key} value={series.key}>{series.display_name}{series.pending_classification ? ' · pendiente' : ''}</MenuItem>)}</Select></FormControl>{selected && <><Stack direction="row" gap={1} alignItems="baseline" flexWrap="wrap"><Typography variant="h5" fontWeight={850}>{selected.points[selected.points.length - 1]?.value} {selected.unit}</Typography><Typography color="text.secondary">Último resultado · {formatDate(selected.points[selected.points.length - 1]?.sampled_at)}</Typography></Stack><LabTrendChart series={selected} /></>}</Stack></SectionCard> : null}
    <SectionCard title="Exámenes relevantes" description="Resultados finalizados y auditables, agrupados por nombre canónico aunque lleguen en distinto orden." actions={<Button variant="contained" startIcon={<ClipboardPlus size={17} />} disabled={historical} onClick={() => setPasteOpen(true)}>Pegar resultados</Button>}>
      {results.error ? <ErrorState message={results.error} onRetry={() => void results.reload()} /> : results.loading ? <LoadingState label="Cargando exámenes" rows={3} /> : !results.data?.items.length ? <EmptyState title="Sin exámenes transcritos" description="Pegue una tabla desde TrakCare o Excel para registrar el primer lote." /> : <TableContainer><Table size="small"><TableHead><TableRow><TableCell>Muestra</TableCell><TableCell>Examen</TableCell><TableCell>Resultado</TableCell><TableCell>Referencia</TableCell><TableCell sx={{ minWidth: 180 }}>Clasificación</TableCell><TableCell>Fuente</TableCell></TableRow></TableHead><TableBody>{results.data.items.map((row) => <TableRow key={text(row.id)}><TableCell>{formatDate(row.sampled_at)}</TableCell><TableCell><Typography fontWeight={700}>{text(row.canonical_name) === '—' ? text(row.test_name) : text(row.canonical_name)}</Typography>{text(row.canonical_name) !== '—' && text(row.canonical_name) !== text(row.test_name) && <Typography variant="caption" color="text.secondary">Original: {text(row.test_name)}</Typography>}</TableCell><TableCell>{text(row.value)} {text(row.unit) === '—' ? '' : text(row.unit)}</TableCell><TableCell>{text(row.reference_range)}</TableCell><TableCell>{row.pending_classification ? <TextField select size="small" fullWidth value="" label="Clasificar" disabled={historical || classifyingId === text(row.id)} onChange={(event) => void classify(text(row.id), event.target.value)}><MenuItem value="create">Crear este examen</MenuItem>{catalogItems.map((item) => <MenuItem key={item.id} value={item.id}>{item.canonical_name}</MenuItem>)}</TextField> : <Chip size="small" color="success" variant="outlined" label="Clasificado" />}</TableCell><TableCell>{row.source === 'trakcare_manual' ? <Chip icon={<AlertTriangle size={14} />} size="small" label="Dato transcrito manualmente desde TrakCare" /> : text(row.source)}</TableCell></TableRow>)}</TableBody></Table></TableContainer>}
    </SectionCard>
    <LabPasteDialog open={pasteOpen} admissionId={admissionId} csrfToken={csrfToken} catalog={catalogItems} onClose={() => setPasteOpen(false)} onSaved={reloadAll} />
  </Stack>
}

export function LabSummaryCard({ admissionId, refreshKey = 0 }: { admissionId: string; refreshKey?: number }) {
  const trends = useClinicalData<LabTrendResponse>(`/admissions/${admissionId}/nutrition-lab-trends`, refreshKey)
  const recent = trends.data?.series?.slice(0, 3) ?? []
  return <SectionCard title="Tendencias de exámenes" description="Últimos exámenes numéricos disponibles en esta hospitalización.">{trends.loading ? <LoadingState label="Cargando tendencias de exámenes" rows={2} /> : trends.error ? <ErrorState message={trends.error} onRetry={() => void trends.reload()} /> : !recent.length ? <EmptyState title="Sin tendencias disponibles" description="Los resultados numéricos pegados aparecerán aquí automáticamente." /> : <Grid container spacing={2}>{recent.map((series) => { const latest = series.points[series.points.length - 1]; return <Grid key={series.key} size={{ xs: 12, md: 4 }}><Box sx={{ border: 1, borderColor: 'divider', borderRadius: 2, p: 1.5, height: '100%' }}><Stack direction="row" justifyContent="space-between" gap={1}><Box><Typography fontWeight={800}>{series.display_name}</Typography><Typography variant="h6">{latest.value} {latest.unit}</Typography></Box>{series.pending_classification && <Chip size="small" color="warning" label="Pendiente" />}</Stack><LabTrendChart series={series} compact /><Typography variant="caption" color="text.secondary">{formatDate(latest.sampled_at)}</Typography></Box></Grid> })}</Grid>}</SectionCard>
}

export function NutritionSummaryCard({ admissionId, refreshKey = 0 }: { admissionId: string; refreshKey?: number }) {
  const { data, loading, error, reload } = useClinicalData<NutritionLatest>(`/admissions/${admissionId}/nutrition-latest`, refreshKey)
  return <SectionCard title="Resumen nutricional clínico" description="Visible sólo para nutricionista y jefatura.">{loading ? <LoadingState label="Cargando resumen nutricional" rows={2} /> : error ? <ErrorState message={error} onRetry={() => void reload()} /> : !data?.latest_encounter ? <EmptyState title="Sin evolución finalizada" description="Los borradores no se publican como información clínica vigente." /> : <Stack spacing={2}>{data.active_alerts.map((alert) => <Alert severity={alert.severity === 'critical' ? 'error' : 'warning'} key={text(alert.id)}>{text(alert.description)} · Fuente: {text(alert.source)} · Verificación: {text(alert.verification_status)}</Alert>)}<Grid container spacing={2}><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Última evolución" value={formatDate(data.latest_encounter.finalized_at)} /></Grid><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Profesional" value={data.latest_encounter.professional_name} /></Grid><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Estado nutricional" value={data.nutritional_status} /></Grid><Grid size={12}><FieldValue label="Diagnósticos PES activos" value={data.active_diagnoses.map((row) => text(row.generated_statement)).join(' · ')} /></Grid><Grid size={12}><FieldValue label="Reevaluación sugerida" value={formatDate(data.suggested_reassessment_at)} /></Grid></Grid></Stack>}</SectionCard>
}

export function NutritionClinicalTab({ tab, admissionId, historical, csrfToken, patientDateOfBirth, patientAgeIsEstimated, onChanged }: { tab: ClinicalTab, admissionId: string, historical: boolean, csrfToken: string, patientDateOfBirth?: string | null, patientAgeIsEstimated?: boolean, onChanged: () => void }) {
  if (tab === 'assessment') return <AssessmentTab admissionId={admissionId} historical={historical} csrfToken={csrfToken} onChanged={onChanged} />
  if (tab === 'anthropometry') return <AnthropometryTab admissionId={admissionId} historical={historical} csrfToken={csrfToken} onChanged={onChanged} />
  if (tab === 'screening') return <ScreeningTab admissionId={admissionId} historical={historical} csrfToken={csrfToken} patientDateOfBirth={patientDateOfBirth} patientAgeIsEstimated={patientAgeIsEstimated} onChanged={onChanged} />
  if (tab === 'prescription') return <PrescriptionTab admissionId={admissionId} historical={historical} csrfToken={csrfToken} onChanged={onChanged} />
  if (tab === 'intake') return <IntakeTab admissionId={admissionId} historical={historical} csrfToken={csrfToken} onChanged={onChanged} />
  return <LabsTab admissionId={admissionId} historical={historical} csrfToken={csrfToken} onChanged={onChanged} />
}
