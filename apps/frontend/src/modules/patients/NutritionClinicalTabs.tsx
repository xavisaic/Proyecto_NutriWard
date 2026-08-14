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
  NutritionEncounterList,
  NutritionEncounterRead,
  NutritionLatest,
  NutritionProjectionList,
} from '../../shared/services/api'

type ClinicalTab = 'care' | 'assessment' | 'prescription' | 'intake' | 'labs'

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
  nrs_disease: string
  nrs_age: string
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
  nrs_nutrition: '0', nrs_disease: '0', nrs_age: 'false', strong_subjective: 'false',
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
    nrs_disease: text(answers.disease_severity_score) === '—' ? '0' : text(answers.disease_severity_score),
    nrs_age: text(answers.age_70_or_more) === '—' ? 'false' : text(answers.age_70_or_more),
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

function numberOrUndefined(value: string) { return value.trim() ? Number(value) : undefined }
function localIso(value: string) { return value ? new Date(value).toISOString() : undefined }

function buildPayload(editor: EditorState) {
  const now = new Date().toISOString()
  const anthropometry = []
  if (editor.weight_value) anthropometry.push({ measurement_type: editor.weight_type, value: Number(editor.weight_value), unit: 'kg', measured_at: now, reliability: 'unknown', value_nature: editor.weight_type === 'current_weight_reported' ? 'reported' : 'measured' })
  if (editor.height_value) anthropometry.push({ measurement_type: 'standing_height', value: Number(editor.height_value), unit: 'cm', measured_at: now, reliability: 'unknown', value_nature: 'measured' })
  const answers = editor.screening_tool === 'nrs_2002' ? [
    { answer_code: 'nutritional_status_score', answer_value: editor.nrs_nutrition },
    { answer_code: 'disease_severity_score', answer_value: editor.nrs_disease },
    { answer_code: 'age_70_or_more', answer_value: editor.nrs_age },
  ] : editor.screening_tool === 'strongkids' ? [
    { answer_code: 'subjective_clinical_assessment', answer_value: editor.strong_subjective },
    { answer_code: 'high_risk_disease', answer_value: editor.strong_disease },
    { answer_code: 'nutritional_intake_or_losses', answer_value: editor.strong_intake },
    { answer_code: 'weight_loss_or_poor_gain', answer_value: editor.strong_weight },
  ] : []
  const requirements = editor.requirement_method === 'factorial' && editor.basal_result ? [{
    nutrient_code: 'energy', method: 'factorial', unit: 'kcal/day',
    inputs: { basal_result: Number(editor.basal_result), activity_factor: Number(editor.activity_factor), stress_factor: Number(editor.stress_factor), thermal_factor: 1 },
  }] : editor.requirement_method === 'manual' && editor.energy_result ? [{
    nutrient_code: 'energy', method: 'manual', unit: 'kcal/day', inputs: { measured_or_manual_value: Number(editor.energy_result) },
  }] : []
  return {
    encounter_type: editor.encounter_type,
    reason_for_assessment: editor.reason_for_assessment || null,
    information_source: editor.information_source || null,
    clinical_summary: editor.clinical_summary || null,
    assessment: {
      population_group: editor.population_group, hospitalization_reason: editor.hospitalization_reason || null,
      current_feeding_route: editor.current_feeding_route || null, appetite: editor.appetite || null,
      clinical_findings: editor.clinical_findings || null, digestive_findings: editor.digestive_findings || null,
      nutritional_status: editor.nutritional_status || null, objectives: editor.objectives || null,
      monitoring_plan: editor.monitoring_plan || null, pending_actions: editor.pending_actions || null,
      suggested_reassessment_at: localIso(editor.suggested_reassessment_at), observed_at: now,
    },
    anthropometry,
    screenings: [{ tool_code: editor.screening_tool, tool_version: editor.screening_tool === 'nrs_2002' ? 'ESPEN 2002' : editor.screening_tool === 'strongkids' ? 'original' : 'institutional-policy-pending', applied_at: now, no_tool_reason: editor.screening_tool === 'none' ? editor.no_tool_reason : null, answers }],
    requirements,
    diagnoses: editor.pes_problem && editor.pes_etiology && editor.pes_signs ? [{ problem: editor.pes_problem, etiology: editor.pes_etiology, signs_and_symptoms: editor.pes_signs, priority: 1, status: 'active' }] : [],
    prescription: editor.regimen_type ? {
      effective_from: now, primary_route: editor.prescription_route, regimen_type: editor.regimen_type,
      energy_target: numberOrUndefined(editor.energy_target), protein_target: numberOrUndefined(editor.protein_target),
      fluid_target: numberOrUndefined(editor.fluid_target), restrictions: editor.restrictions || null, meal_times: [],
    } : null,
    intake: editor.intake_percentage ? [{ intake_date: now.slice(0, 10), meal_time: 'other', consumed_percentage: Number(editor.intake_percentage), incomplete_reason: editor.intake_reason || null, source: editor.information_source }] : [],
    labs: editor.lab_name && editor.lab_value ? [{ test_name: editor.lab_name, value: editor.lab_value, unit: editor.lab_unit || null, sampled_at: now, source: 'trakcare_manual' }] : [],
  }
}

function NutritionEditor({ open, record, admissionId, csrfToken, onClose, onSaved }: {
  open: boolean, record: NutritionEncounterRead | null, admissionId: string, csrfToken: string,
  onClose: () => void, onSaved: () => void,
}) {
  const [editor, setEditor] = useState<EditorState>(EMPTY_EDITOR)
  const [activeSection, setActiveSection] = useState(0)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sectionErrors, setSectionErrors] = useState<string[]>([])

  useEffect(() => {
    if (open) { setEditor(record ? fromEncounter(record) : EMPTY_EDITOR); setDirty(false); setActiveSection(0); setError(null); setSectionErrors([]) }
  }, [open, record])
  useEffect(() => {
    if (!dirty) return
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])

  function set(name: keyof EditorState, value: string) {
    setEditor((current) => ({ ...current, [name]: value })); setDirty(true)
  }
  function close() {
    if (dirty && !window.confirm('Hay cambios sin guardar. ¿Desea cerrar el editor?')) return
    onClose()
  }
  async function save(finalize = false) {
    setSaving(true); setError(null); setSectionErrors([])
    try {
      let saved: NutritionEncounterRead
      if (record) {
        saved = await apiRequest(`/nutrition-care-encounters/${record.encounter.id}`, {
          method: 'PATCH', body: JSON.stringify({ ...buildPayload(editor), version: record.encounter.version }),
        }, csrfToken)
      } else {
        saved = await apiRequest(`/admissions/${admissionId}/nutrition-care-encounters`, {
          method: 'POST', body: JSON.stringify(buildPayload(editor)),
        }, csrfToken)
      }
      if (finalize) {
        if (!window.confirm('¿Confirma finalizar esta atención? Luego será inmutable y cualquier cambio requerirá una corrección.')) { setSaving(false); return }
        saved = await apiRequest(`/nutrition-care-encounters/${saved.encounter.id}/finalize`, {
          method: 'POST', body: JSON.stringify({ version: saved.encounter.version }),
        }, csrfToken)
      }
      setDirty(false); onSaved()
    } catch (caught) {
      const message = clinicalError(caught)
      setError(message)
      if (caught instanceof ApiError && caught.status === 422) setSectionErrors(['Revise Contexto, Tamizaje, Diagnóstico PES y Seguimiento antes de finalizar.'])
    } finally { setSaving(false) }
  }

  const progress = Math.round(([
    editor.reason_for_assessment, editor.hospitalization_reason, editor.weight_value,
    editor.screening_tool, editor.clinical_findings, editor.intake_percentage || editor.lab_name,
    editor.basal_result || editor.energy_result, editor.pes_problem, editor.regimen_type,
    editor.clinical_summary,
  ].filter(Boolean).length / SECTIONS.length) * 100)

  return <Dialog open={open} onClose={close} fullWidth maxWidth="lg" fullScreen={false} aria-labelledby="nutrition-editor-title">
    <DialogTitle id="nutrition-editor-title">{record ? 'Continuar atención nutricional' : 'Nueva atención nutricional'}</DialogTitle>
    <DialogContent dividers>
      <Stack spacing={2.5}>
        <Box><Stack direction="row" justifyContent="space-between"><Typography variant="body2">Progreso por secciones</Typography><Typography variant="body2">{progress}%</Typography></Stack><LinearProgress variant="determinate" value={progress} /></Box>
        <Stepper nonLinear activeStep={activeSection} sx={{ overflowX: 'auto', pb: 1 }}>
          {SECTIONS.map((label, index) => <Step key={label}><StepButton onClick={() => setActiveSection(index)}>{index + 1}</StepButton></Step>)}
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
        {activeSection === 2 && <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 5 }}><FormControl fullWidth><InputLabel>Tipo de peso</InputLabel><Select label="Tipo de peso" value={editor.weight_type} onChange={(e) => set('weight_type', e.target.value)}>{Object.entries(MEASUREMENT_LABELS).filter(([value]) => value.includes('weight')).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl></Grid>
          <Grid size={{ xs: 8, md: 5 }}><TextField fullWidth type="number" label="Peso" value={editor.weight_value} onChange={(e) => set('weight_value', e.target.value)} inputProps={{ min: 0, step: '0.01' }} /></Grid><Grid size={{ xs: 4, md: 2 }}><TextField fullWidth label="Unidad" value="kg" disabled /></Grid>
          <Grid size={{ xs: 8, md: 10 }}><TextField fullWidth type="number" label="Talla de pie" value={editor.height_value} onChange={(e) => set('height_value', e.target.value)} inputProps={{ min: 0, step: '0.1' }} /></Grid><Grid size={{ xs: 4, md: 2 }}><TextField fullWidth label="Unidad" value="cm" disabled /></Grid>
          <Grid size={12}><Alert severity="info">El IMC se calcula en backend. Ningún tipo de peso se reemplaza automáticamente por peso ideal o ajustado.</Alert></Grid>
        </Grid>}
        {activeSection === 3 && <Stack spacing={2}>
          <FormControl fullWidth><InputLabel>Herramienta de tamizaje</InputLabel><Select label="Herramienta de tamizaje" value={editor.screening_tool} onChange={(e) => set('screening_tool', e.target.value)}><MenuItem value="nrs_2002">NRS-2002 · ESPEN</MenuItem><MenuItem value="strongkids">STRONGkids</MenuItem><MenuItem value="none">Sin herramienta definida</MenuItem></Select><FormHelperText>Predeterminada para {POPULATION_LABELS[editor.population_group]}: {SCREENING_DEFAULTS[editor.population_group]}</FormHelperText></FormControl>
          {editor.screening_tool === 'nrs_2002' && <Grid container spacing={2}>{[['nrs_nutrition', 'Puntaje nutricional'], ['nrs_disease', 'Gravedad de enfermedad']].map(([name, label]) => <Grid key={name} size={{ xs: 12, md: 4 }}><TextField fullWidth type="number" label={label} value={editor[name as keyof EditorState]} onChange={(e) => set(name as keyof EditorState, e.target.value)} inputProps={{ min: 0, max: 3 }} /></Grid>)}<Grid size={{ xs: 12, md: 4 }}><FormControl fullWidth><InputLabel>Edad ≥ 70 años</InputLabel><Select label="Edad ≥ 70 años" value={editor.nrs_age} onChange={(e) => set('nrs_age', e.target.value)}><MenuItem value="false">No</MenuItem><MenuItem value="true">Sí</MenuItem></Select></FormControl></Grid></Grid>}
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
    <DialogActions sx={{ flexWrap: 'wrap', gap: 1 }}><Button onClick={close}>Cerrar</Button><Button variant="outlined" disabled={saving} onClick={() => void save(false)}>Guardar borrador</Button><Button variant="contained" disabled={saving} onClick={() => void save(true)}>Guardar y finalizar</Button></DialogActions>
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

function CareTab({ admissionId, historical, csrfToken, onChanged }: { admissionId: string, historical: boolean, csrfToken: string, onChanged: () => void }) {
  const [refresh, setRefresh] = useState(0)
  const { data, loading, error, reload } = useClinicalData<NutritionEncounterList>(`/admissions/${admissionId}/nutrition-care-encounters`, refresh)
  const [editorOpen, setEditorOpen] = useState(false)
  const [selected, setSelected] = useState<NutritionEncounterRead | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  async function openRecord(id: string, edit = false) {
    try { const record = await apiRequest<NutritionEncounterRead>(`/nutrition-care-encounters/${id}`); setSelected(record); setEditorOpen(edit) }
    catch (caught) { setActionError(clinicalError(caught)) }
  }
  async function correct(id: string, version: number) {
    const reason = window.prompt('Motivo de corrección (obligatorio):')
    if (!reason || reason.trim().length < 10) return
    if (!window.confirm('Se creará un borrador correctivo enlazado. El original no será sobrescrito.')) return
    try {
      const record = await apiRequest<NutritionEncounterRead>(`/nutrition-care-encounters/${id}/correct`, { method: 'POST', body: JSON.stringify({ version, reason }) }, csrfToken)
      setSelected(record); setEditorOpen(true); setRefresh((value) => value + 1)
    } catch (caught) { setActionError(clinicalError(caught)) }
  }
  return <Stack spacing={2}>
    {historical && <Alert severity="info">Episodio histórico · Solo lectura. Las atenciones finalizadas permanecen disponibles.</Alert>}
    {actionError && <Alert severity="error">{actionError}</Alert>}
    <SectionCard title="Atenciones nutricionales" description="Instancias temporales de trabajo clínico; no registran ubicación física ni modalidad presencial/remota." actions={!historical ? <Button variant="contained" startIcon={<ClipboardPlus size={17} />} onClick={() => { setSelected(null); setEditorOpen(true) }}>Nueva atención nutricional</Button> : undefined}>
      {error ? <ErrorState message={error} onRetry={() => void reload()} /> : loading ? <LoadingState label="Cargando atenciones" rows={3} /> : !data?.items.length ? <EmptyState title="Sin atenciones" description="No hay documentación nutricional para esta hospitalización." action={!historical ? <Button onClick={() => setEditorOpen(true)}>Crear primer borrador</Button> : undefined} /> : <Stack spacing={1.5}>{data.items.map((item) => <Box key={item.id} sx={{ border: 1, borderColor: 'divider', borderRadius: 2, p: 2 }}><Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" gap={2}><Box><Stack direction="row" gap={1} alignItems="center" flexWrap="wrap"><Typography fontWeight={800}>{TYPE_LABELS[item.encounter_type]}</Typography><StatusBadge label={STATUS_LABELS[item.status]} tone={item.status === 'draft' ? 'warning' : item.status === 'cancelled' ? 'neutral' : 'success'} /></Stack><Typography variant="body2">{formatDate(item.encounter_datetime)} · {item.author_name}</Typography><Typography variant="body2" color="text.secondary">{item.clinical_summary || 'Borrador sin síntesis clínica'}</Typography></Box><Stack direction="row" gap={1} flexWrap="wrap"><Button size="small" startIcon={<ExternalLink size={15} />} onClick={() => void openRecord(item.id)}>Ver</Button>{item.status === 'draft' && !historical && <Button size="small" startIcon={<Pencil size={15} />} onClick={() => void openRecord(item.id, true)}>Continuar borrador</Button>}{(item.status === 'finalized' || item.status === 'corrected') && !historical && <Button size="small" startIcon={<RotateCcw size={15} />} onClick={() => void correct(item.id, item.version)}>Corregir</Button>}</Stack></Stack></Box>)}</Stack>}
    </SectionCard>
    {selected && !editorOpen && <EncounterViewer record={selected} onClose={() => setSelected(null)} />}
    <NutritionEditor open={editorOpen} record={selected?.encounter.status === 'draft' ? selected : null} admissionId={admissionId} csrfToken={csrfToken} onClose={() => { setEditorOpen(false); setSelected(null) }} onSaved={() => { setEditorOpen(false); setSelected(null); setRefresh((value) => value + 1); onChanged() }} />
  </Stack>
}

function EncounterViewer({ record, onClose }: { record: NutritionEncounterRead, onClose: () => void }) {
  return <Dialog open onClose={onClose} fullWidth maxWidth="md"><DialogTitle>Atención nutricional · {STATUS_LABELS[record.encounter.status]}</DialogTitle><DialogContent dividers><Stack spacing={2}><FieldValue label="Fecha" value={formatDate(record.encounter.encounter_datetime)} /><FieldValue label="Profesional" value={record.author_name} /><FieldValue label="Tipo" value={TYPE_LABELS[record.encounter.encounter_type]} /><FieldValue label="Síntesis" value={record.encounter.clinical_summary} /><FieldValue label="Población" value={record.assessment ? POPULATION_LABELS[text(record.assessment.population_group)] : null} /><Divider /><Typography variant="subtitle1" fontWeight={800}>Diagnósticos PES</Typography>{record.diagnoses.map((row) => <Typography key={text(row.id)}>{text(row.generated_statement)}</Typography>)}{record.encounter.correction_reason && <Alert severity="info">Corrección: {record.encounter.correction_reason}</Alert>}{record.encounter.cancellation_reason && <Alert severity="warning">Cancelación: {record.encounter.cancellation_reason}</Alert>}</Stack></DialogContent><DialogActions><Button onClick={onClose}>Cerrar</Button></DialogActions></Dialog>
}

function AssessmentTab({ admissionId }: { admissionId: string }) {
  const { data, loading, error, reload } = useClinicalData<NutritionProjectionList>(`/admissions/${admissionId}/nutrition-assessments`, 0)
  const latest = data?.items?.[0]
  return <SectionCard title="Evaluación nutricional" description="Última evaluación finalizada e historial, proyectados desde sus atenciones de origen.">{error ? <ErrorState message={error} onRetry={() => void reload()} /> : loading ? <LoadingState label="Cargando evaluaciones" rows={3} /> : !latest ? <EmptyState title="Sin evaluación finalizada" description="Finalice una atención nutricional para publicar esta proyección." /> : <Stack spacing={2}><Alert severity="success">Última evaluación finalizada · {formatDate(latest.observed_at)}</Alert><Grid container spacing={2}><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Población" value={POPULATION_LABELS[text(latest.population_group)]} /></Grid><Grid size={{ xs: 12, md: 8 }}><FieldValue label="Estado nutricional" value={latest.nutritional_status} /></Grid><Grid size={12}><FieldValue label="Hallazgos clínicos" value={latest.clinical_findings} /></Grid><Grid size={12}><FieldValue label="Hallazgos digestivos" value={latest.digestive_findings} /></Grid><Grid size={12}><FieldValue label="Objetivos" value={latest.objectives} /></Grid></Grid><Divider /><Typography variant="subtitle1" fontWeight={800}>Historial de evaluaciones ({data?.total})</Typography>{data?.items.map((row) => <Typography key={text(row.id)} variant="body2">{formatDate(row.observed_at)} · {POPULATION_LABELS[text(row.population_group)]} · Atención {text(row.encounter_id)}</Typography>)}</Stack>}</SectionCard>
}

function PrescriptionTab({ admissionId }: { admissionId: string }) {
  const { data, loading, error, reload } = useClinicalData<NutritionProjectionList>(`/admissions/${admissionId}/nutrition-prescriptions`, 0)
  const latest = data?.items?.[0]
  return <SectionCard title="Prescripción nutricional" description="La prescripción vigente procede de la última atención finalizada y será la fuente clínica futura para raciones.">{error ? <ErrorState message={error} onRetry={() => void reload()} /> : loading ? <LoadingState label="Cargando prescripciones" rows={3} /> : !latest ? <EmptyState title="Sin prescripción vigente" description="No hay una prescripción finalizada en este episodio." /> : <Stack spacing={2}><Grid container spacing={2}><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Fecha efectiva" value={formatDate(latest.effective_from)} /></Grid><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Vía" value={latest.primary_route} /></Grid><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Estado" value={latest.status} /></Grid><Grid size={12}><FieldValue label="Régimen general" value={latest.regimen_type} /></Grid><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Energía" value={latest.energy_target ? `${latest.energy_target} kcal/día` : null} /></Grid><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Proteínas" value={latest.protein_target ? `${latest.protein_target} g/día` : null} /></Grid><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Líquidos" value={latest.fluid_target ? `${latest.fluid_target} mL/día` : null} /></Grid><Grid size={12}><FieldValue label="Restricciones" value={latest.restrictions} /></Grid></Grid><Alert severity="info">Los borradores nunca alimentan raciones y Alimentación no accede a esta ficha.</Alert></Stack>}</SectionCard>
}

function IntakeTab({ admissionId }: { admissionId: string }) {
  const { data, loading, error, reload } = useClinicalData<NutritionProjectionList>(`/admissions/${admissionId}/nutrition-intake`, 0)
  return <Stack spacing={2}><Alert severity="info">En esta fase sólo está disponible el control clínico de ingesta. Minutas, raciones y producción de cocina están pendientes.</Alert><SectionCard title="Control de ingesta">{error ? <ErrorState message={error} onRetry={() => void reload()} /> : loading ? <LoadingState label="Cargando ingesta" rows={3} /> : !data?.items.length ? <EmptyState title="Sin controles de ingesta" description="Registre ingesta dentro de una atención nutricional." /> : <TableContainer><Table size="small"><TableHead><TableRow><TableCell>Fecha</TableCell><TableCell>Tiempo</TableCell><TableCell>Consumido</TableCell><TableCell>Motivo incompleto</TableCell><TableCell>Fuente</TableCell></TableRow></TableHead><TableBody>{data.items.map((row) => <TableRow key={text(row.id)}><TableCell>{formatDate(text(row.intake_date), false)}</TableCell><TableCell>{text(row.meal_time)}</TableCell><TableCell>{text(row.consumed_percentage)}%</TableCell><TableCell>{text(row.incomplete_reason)}</TableCell><TableCell>{SOURCE_LABELS[text(row.source)] || text(row.source)}</TableCell></TableRow>)}</TableBody></Table></TableContainer>}</SectionCard></Stack>
}

function LabsTab({ admissionId }: { admissionId: string }) {
  const { data, loading, error, reload } = useClinicalData<NutritionProjectionList>(`/admissions/${admissionId}/nutrition-labs`, 0)
  return <SectionCard title="Exámenes relevantes" description="Resultados transcritos manualmente; NutriWard no interpreta valores críticos ni reemplaza al laboratorio.">{error ? <ErrorState message={error} onRetry={() => void reload()} /> : loading ? <LoadingState label="Cargando exámenes" rows={3} /> : !data?.items.length ? <EmptyState title="Sin exámenes transcritos" description="Registre exámenes relevantes dentro de una atención nutricional." /> : <TableContainer><Table size="small"><TableHead><TableRow><TableCell>Muestra</TableCell><TableCell>Examen</TableCell><TableCell>Resultado</TableCell><TableCell>Referencia</TableCell><TableCell>Fuente</TableCell></TableRow></TableHead><TableBody>{data.items.map((row) => <TableRow key={text(row.id)}><TableCell>{formatDate(row.sampled_at)}</TableCell><TableCell>{text(row.test_name)}</TableCell><TableCell>{text(row.value)} {text(row.unit) === '—' ? '' : text(row.unit)}</TableCell><TableCell>{text(row.reference_range)}</TableCell><TableCell>{row.source === 'trakcare_manual' ? <Chip icon={<AlertTriangle size={14} />} size="small" label="Dato transcrito manualmente desde TrakCare" /> : text(row.source)}</TableCell></TableRow>)}</TableBody></Table></TableContainer>}</SectionCard>
}

export function NutritionSummaryCard({ admissionId }: { admissionId: string }) {
  const { data, loading, error, reload } = useClinicalData<NutritionLatest>(`/admissions/${admissionId}/nutrition-latest`, 0)
  return <SectionCard title="Resumen nutricional clínico" description="Visible sólo para nutricionista y jefatura.">{loading ? <LoadingState label="Cargando resumen nutricional" rows={2} /> : error ? <ErrorState message={error} onRetry={() => void reload()} /> : !data?.latest_encounter ? <EmptyState title="Sin atención finalizada" description="Los borradores no se publican como información clínica vigente." /> : <Stack spacing={2}>{data.active_alerts.map((alert) => <Alert severity={alert.severity === 'critical' ? 'error' : 'warning'} key={text(alert.id)}>{text(alert.description)} · Fuente: {text(alert.source)} · Verificación: {text(alert.verification_status)}</Alert>)}<Grid container spacing={2}><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Última atención" value={formatDate(data.latest_encounter.finalized_at)} /></Grid><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Profesional" value={data.latest_encounter.professional_name} /></Grid><Grid size={{ xs: 12, md: 4 }}><FieldValue label="Estado nutricional" value={data.nutritional_status} /></Grid><Grid size={12}><FieldValue label="Diagnósticos PES activos" value={data.active_diagnoses.map((row) => text(row.generated_statement)).join(' · ')} /></Grid><Grid size={12}><FieldValue label="Reevaluación sugerida" value={formatDate(data.suggested_reassessment_at)} /></Grid></Grid></Stack>}</SectionCard>
}

export function NutritionClinicalTab({ tab, admissionId, historical, csrfToken, onChanged }: { tab: ClinicalTab, admissionId: string, historical: boolean, csrfToken: string, onChanged: () => void }) {
  if (tab === 'care') return <CareTab admissionId={admissionId} historical={historical} csrfToken={csrfToken} onChanged={onChanged} />
  if (tab === 'assessment') return <AssessmentTab admissionId={admissionId} />
  if (tab === 'prescription') return <PrescriptionTab admissionId={admissionId} />
  if (tab === 'intake') return <IntakeTab admissionId={admissionId} />
  return <LabsTab admissionId={admissionId} />
}
