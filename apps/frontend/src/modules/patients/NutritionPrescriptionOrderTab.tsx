import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Stack,
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
import { ChevronDown, Clipboard, Pencil, Plus, Printer, ShieldCheck, StopCircle, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { EmptyState, ErrorState, LoadingState, SectionCard } from '../../shared/components'
import {
  ApiError,
  apiRequest,
  EnteralFormulaCatalogItem,
  NutritionPrescriptionCoverage,
  NutritionPrescriptionOrder,
  NutritionPrescriptionWorkspace,
} from '../../shared/services/api'

const STATUS_LABELS: Record<string, string> = {
  draft: 'Borrador', validated: 'Validada', active: 'Activa', suspended: 'Suspendida',
  superseded: 'Reemplazada', cancelled: 'Cancelada',
}
const MEAL_LABELS: Record<string, string> = {
  breakfast: 'Desayuno', morning_snack: 'Colación AM', lunch: 'Almuerzo',
  afternoon_snack: 'Once', dinner: 'Cena', night_snack: 'Colación nocturna',
}

type RowDraft = Record<string, string>
interface PrescriptionForm {
  change_reason: string
  oral_enabled: boolean
  enteral_enabled: boolean
  fasting_enabled: boolean
  energy_goal_kcal: string
  protein_goal_g: string
  carbohydrate_goal_g: string
  lipid_goal_g: string
  fluid_goal_ml: string
  fluid_goal_kind: 'target' | 'minimum' | 'maximum' | 'range'
  regimen_type: string
  food_iddsi: string
  liquid_iddsi: string
  restrictions: string
  allergies_snapshot: string
  feeding_assistance: string
  kitchen_instructions: string
  nursing_instructions: string
  oral_energy_kcal: string
  oral_protein_g: string
  oral_carbohydrate_g: string
  oral_lipid_g: string
  oral_fluid_ml: string
  enteral_formula_id: string
  enteral_access_route: string
  enteral_tube_location: string
  enteral_modality: string
  enteral_rate_ml_h: string
  enteral_effective_hours: string
  water_flush_ml: string
  water_flush_every_hours: string
  medication_pause_hours: string
  enteral_starts_at: string
  suggested_reassessment_at: string
  general_observations: string
  meals: RowDraft[]
  supplements: RowDraft[]
  progressions: RowDraft[]
  monitoring: RowDraft[]
}

function requestError(error: unknown) {
  if (error instanceof ApiError) return error.message
  return 'No fue posible completar la operación.'
}
function number(value: string) { return value.trim() ? Number(value) : null }
function number0(value: string) { return value.trim() ? Number(value) : 0 }
function localDate(value: string | null) { return value ? value.slice(0, 16) : '' }
function iso(value: string) { return value ? new Date(value).toISOString() : null }
function fmt(value: string | number | null | undefined, digits = 0) {
  if (value === null || value === undefined || value === '') return '—'
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: digits }).format(Number(value))
}
function formatDate(value: string | null) {
  return value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—'
}
function requirement(workspace: NutritionPrescriptionWorkspace, aliases: string[]) {
  return workspace.requirements.find((row) => aliases.includes(row.nutrient_code))?.adopted_result ?? ''
}

function emptyForm(workspace: NutritionPrescriptionWorkspace): PrescriptionForm {
  return {
    change_reason: 'Prescripción nutricional inicial.', oral_enabled: true, enteral_enabled: false,
    fasting_enabled: false, energy_goal_kcal: requirement(workspace, ['energy']),
    protein_goal_g: requirement(workspace, ['protein']), carbohydrate_goal_g: requirement(workspace, ['carbohydrate', 'carbohydrates']),
    lipid_goal_g: requirement(workspace, ['lipid', 'fat']), fluid_goal_ml: requirement(workspace, ['fluid', 'volume']),
    fluid_goal_kind: 'target', regimen_type: '', food_iddsi: '', liquid_iddsi: '', restrictions: '',
    allergies_snapshot: '', feeding_assistance: '', kitchen_instructions: '', nursing_instructions: '',
    oral_energy_kcal: '', oral_protein_g: '', oral_carbohydrate_g: '', oral_lipid_g: '', oral_fluid_ml: '',
    enteral_formula_id: '', enteral_access_route: '', enteral_tube_location: '', enteral_modality: 'continuous',
    enteral_rate_ml_h: '', enteral_effective_hours: '', water_flush_ml: '', water_flush_every_hours: '',
    medication_pause_hours: '0', enteral_starts_at: '', suggested_reassessment_at: '', general_observations: '',
    meals: Object.keys(MEAL_LABELS).map((meal_time) => ({ meal_time, instruction: '' })),
    supplements: [], progressions: [], monitoring: [],
  }
}

function formFromOrder(row: NutritionPrescriptionOrder): PrescriptionForm {
  return {
    change_reason: row.change_reason, oral_enabled: row.oral_enabled, enteral_enabled: row.enteral_enabled,
    fasting_enabled: row.fasting_enabled, energy_goal_kcal: row.energy_goal_kcal ?? '', protein_goal_g: row.protein_goal_g ?? '',
    carbohydrate_goal_g: row.carbohydrate_goal_g ?? '', lipid_goal_g: row.lipid_goal_g ?? '', fluid_goal_ml: row.fluid_goal_ml ?? '',
    fluid_goal_kind: row.fluid_goal_kind, regimen_type: row.regimen_type ?? '', food_iddsi: row.food_iddsi?.toString() ?? '',
    liquid_iddsi: row.liquid_iddsi?.toString() ?? '', restrictions: row.restrictions ?? '', allergies_snapshot: row.allergies_snapshot ?? '',
    feeding_assistance: row.feeding_assistance ?? '', kitchen_instructions: row.kitchen_instructions ?? '', nursing_instructions: row.nursing_instructions ?? '',
    oral_energy_kcal: row.oral_energy_kcal, oral_protein_g: row.oral_protein_g, oral_carbohydrate_g: row.oral_carbohydrate_g,
    oral_lipid_g: row.oral_lipid_g, oral_fluid_ml: row.oral_fluid_ml, enteral_formula_id: row.enteral_formula_id ?? '',
    enteral_access_route: row.enteral_access_route ?? '', enteral_tube_location: row.enteral_tube_location ?? '',
    enteral_modality: row.enteral_modality ?? 'continuous', enteral_rate_ml_h: row.enteral_rate_ml_h ?? '',
    enteral_effective_hours: row.enteral_effective_hours ?? '', water_flush_ml: row.water_flush_ml,
    water_flush_every_hours: row.water_flush_every_hours ?? '', medication_pause_hours: row.medication_pause_hours,
    enteral_starts_at: localDate(row.enteral_starts_at), suggested_reassessment_at: localDate(row.suggested_reassessment_at),
    general_observations: row.general_observations ?? '',
    meals: Object.keys(MEAL_LABELS).map((meal_time) => ({ meal_time, instruction: row.meals.find((item) => item.meal_time === meal_time)?.instruction ?? '' })),
    supplements: row.supplements.map((item) => ({ ...item })), progressions: row.progressions.map((item) => ({ ...item })),
    monitoring: row.monitoring.map((item) => ({ ...item })),
  }
}

function payload(form: PrescriptionForm, expected?: number) {
  return {
    change_reason: form.change_reason, oral_enabled: form.oral_enabled, enteral_enabled: form.enteral_enabled,
    fasting_enabled: form.fasting_enabled, energy_goal_kcal: number(form.energy_goal_kcal), protein_goal_g: number(form.protein_goal_g),
    carbohydrate_goal_g: number(form.carbohydrate_goal_g), lipid_goal_g: number(form.lipid_goal_g), fluid_goal_ml: number(form.fluid_goal_ml),
    fluid_goal_kind: form.fluid_goal_kind, regimen_type: form.regimen_type || null, food_iddsi: number(form.food_iddsi),
    liquid_iddsi: number(form.liquid_iddsi), restrictions: form.restrictions || null, allergies_snapshot: form.allergies_snapshot || null,
    feeding_assistance: form.feeding_assistance || null, kitchen_instructions: form.kitchen_instructions || null,
    nursing_instructions: form.nursing_instructions || null, oral_energy_kcal: number0(form.oral_energy_kcal),
    oral_protein_g: number0(form.oral_protein_g), oral_carbohydrate_g: number0(form.oral_carbohydrate_g),
    oral_lipid_g: number0(form.oral_lipid_g), oral_fluid_ml: number0(form.oral_fluid_ml),
    enteral_formula_id: form.enteral_formula_id || null, enteral_access_route: form.enteral_access_route || null,
    enteral_tube_location: form.enteral_tube_location || null, enteral_modality: form.enteral_enabled ? form.enteral_modality : null,
    enteral_rate_ml_h: number(form.enteral_rate_ml_h), enteral_effective_hours: number(form.enteral_effective_hours),
    water_flush_ml: number0(form.water_flush_ml), water_flush_every_hours: number(form.water_flush_every_hours),
    medication_pause_hours: number0(form.medication_pause_hours), enteral_starts_at: iso(form.enteral_starts_at),
    suggested_reassessment_at: iso(form.suggested_reassessment_at), general_observations: form.general_observations || null,
    meals: form.meals.filter((item) => item.instruction.trim()).map(({ meal_time, instruction }) => ({ meal_time, instruction })),
    supplements: form.supplements.map((item) => ({
      product_type: item.product_type, product_name: item.product_name, dose: number(item.dose), dose_unit: item.dose_unit || null,
      schedule: item.schedule || null, route: item.route || null, duration: item.duration || null,
      energy_kcal: number0(item.energy_kcal), protein_g: number0(item.protein_g), carbohydrate_g: number0(item.carbohydrate_g),
      lipid_g: number0(item.lipid_g), fluid_ml: number0(item.fluid_ml),
    })),
    progressions: form.progressions.map((item, index) => ({ sequence: index + 1, stage: item.stage, rate_ml_h: number0(item.rate_ml_h), duration_hours: number0(item.duration_hours), condition: item.condition || null })),
    monitoring: form.monitoring.map((item) => ({ parameter: item.parameter, frequency: item.frequency, responsible: item.responsible || null, instruction: item.instruction || null })),
    ...(expected ? { expected_lock_version: expected } : {}),
  }
}

function calculate(form: PrescriptionForm, formulas: EnteralFormulaCatalogItem[]) {
  let energy = form.oral_enabled ? number0(form.oral_energy_kcal) : 0
  let protein = form.oral_enabled ? number0(form.oral_protein_g) : 0
  let carbohydrate = form.oral_enabled ? number0(form.oral_carbohydrate_g) : 0
  let lipid = form.oral_enabled ? number0(form.oral_lipid_g) : 0
  let fluid = form.oral_enabled ? number0(form.oral_fluid_ml) : 0
  const volume = form.enteral_enabled ? number0(form.enteral_rate_ml_h) * number0(form.enteral_effective_hours) : 0
  const formula = formulas.find((item) => item.id === form.enteral_formula_id)
  if (formula && volume) {
    const liters = volume / 1000
    energy += volume * Number(formula.kcal_per_ml)
    protein += liters * Number(formula.protein_g_per_l)
    carbohydrate += liters * Number(formula.carbohydrate_g_per_l)
    lipid += liters * Number(formula.lipid_g_per_l)
    fluid += liters * Number(formula.free_water_ml_per_l)
  }
  if (number0(form.water_flush_every_hours)) fluid += number0(form.water_flush_ml) * 24 / number0(form.water_flush_every_hours)
  for (const item of form.supplements) {
    energy += number0(item.energy_kcal); protein += number0(item.protein_g); carbohydrate += number0(item.carbohydrate_g)
    lipid += number0(item.lipid_g); fluid += number0(item.fluid_ml)
  }
  return { energy, protein, carbohydrate, lipid, fluid, volume }
}

function coverageColor(percent: number | null, goalKind: string, prescribed: number, goal: number, workspace: NutritionPrescriptionWorkspace) {
  if (percent === null) return 'neutral'
  if (goalKind === 'maximum' && prescribed <= goal) return 'green'
  const s = workspace.settings
  if (percent >= Number(s.green_min_percent) && percent <= Number(s.green_max_percent)) return 'green'
  if (percent >= Number(s.yellow_min_percent) && percent <= Number(s.yellow_max_percent)) return 'yellow'
  return 'red'
}

function liveCoverage(form: PrescriptionForm, workspace: NutritionPrescriptionWorkspace): NutritionPrescriptionCoverage[] {
  const totals = calculate(form, workspace.formulas)
  const rows: Array<[string, string, string, number, string, string]> = [
    ['energy', 'Energía', form.energy_goal_kcal, totals.energy, 'kcal', 'target'],
    ['protein', 'Proteínas', form.protein_goal_g, totals.protein, 'g', 'target'],
    ['carbohydrate', 'Carbohidratos', form.carbohydrate_goal_g, totals.carbohydrate, 'g', 'target'],
    ['lipid', 'Lípidos', form.lipid_goal_g, totals.lipid, 'g', 'target'],
    ['fluid', 'Volumen', form.fluid_goal_ml, totals.fluid, 'mL', form.fluid_goal_kind],
  ]
  return rows.map(([code, label, goalText, prescribed, unit, goalKind]) => {
    const goal = number0(goalText); const percent = goal ? prescribed / goal * 100 : null
    return { code, label, goal: goalText || null, prescribed: String(prescribed), unit, percent: percent === null ? null : String(percent), color: coverageColor(percent, goalKind, prescribed, goal, workspace), goal_kind: goalKind }
  })
}

function CoverageTable({ rows }: { rows: NutritionPrescriptionCoverage[] }) {
  return <TableContainer><Table size="small"><TableHead><TableRow><TableCell>Variable</TableCell><TableCell align="right">Meta</TableCell><TableCell align="right">Prescrito</TableCell><TableCell align="right">Cobertura</TableCell></TableRow></TableHead><TableBody>
    {rows.map((row) => <TableRow key={row.code}><TableCell>{row.label}</TableCell><TableCell align="right">{row.goal_kind === 'maximum' && row.goal ? 'Máx. ' : ''}{fmt(row.goal, 1)} {row.unit}</TableCell><TableCell align="right">{fmt(row.prescribed, 1)} {row.unit}</TableCell><TableCell align="right"><Chip size="small" color={row.color === 'green' ? 'success' : row.color === 'yellow' ? 'warning' : row.color === 'red' ? 'error' : 'default'} label={row.percent ? `${fmt(row.percent)}%` : 'Sin meta'} /></TableCell></TableRow>)}
  </TableBody></Table></TableContainer>
}

function ArrayRow({ item, fields, onChange, onDelete }: { item: RowDraft; fields: Array<[string, string, string?]>; onChange: (next: RowDraft) => void; onDelete: () => void }) {
  return <Grid container spacing={1} alignItems="center">{fields.map(([key, label, type]) => <Grid key={key} size={{ xs: 12, sm: fields.length > 4 ? 4 : 6, md: fields.length > 4 ? 2 : 3 }}><TextField fullWidth size="small" type={type ?? 'text'} label={label} value={item[key] ?? ''} onChange={(event) => onChange({ ...item, [key]: event.target.value })} /></Grid>)}<Grid size="auto"><Button color="error" aria-label="Eliminar fila" onClick={onDelete}><Trash2 size={18} /></Button></Grid></Grid>
}

function PrescriptionEditor({ open, workspace, order, csrfToken, onClose, onSaved }: { open: boolean; workspace: NutritionPrescriptionWorkspace; order: NutritionPrescriptionOrder | null; csrfToken: string; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState<PrescriptionForm>(() => order ? formFromOrder(order) : emptyForm(workspace))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)
  useEffect(() => { if (open) { setForm(order ? formFromOrder(order) : emptyForm(workspace)); setError(null); setDirty(false) } }, [open, order, workspace])
  useEffect(() => { if (!open || !dirty) return; const warn = (event: BeforeUnloadEvent) => event.preventDefault(); window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn) }, [open, dirty])
  function set<K extends keyof PrescriptionForm>(key: K, value: PrescriptionForm[K]) { setForm((current) => ({ ...current, [key]: value })); setDirty(true) }
  function rowSet(key: 'supplements' | 'progressions' | 'monitoring', index: number, value?: RowDraft) { set(key, value ? form[key].map((item, i) => i === index ? value : item) : form[key].filter((_, i) => i !== index)) }
  function close() { if (dirty && !window.confirm('Hay cambios sin guardar. ¿Desea cerrar?')) return; onClose() }
  async function save() {
    setSaving(true); setError(null)
    try {
      await apiRequest(
        order ? `/nutrition-prescription-orders/${order.id}` : `/admissions/${workspace.admission_id}/nutrition-prescription-orders`,
        { method: order ? 'PATCH' : 'POST', body: JSON.stringify(payload(form, order?.lock_version)) }, csrfToken,
      )
      setDirty(false); onSaved(); onClose()
    } catch (caught) { setError(requestError(caught)) } finally { setSaving(false) }
  }
  const live = liveCoverage(form, workspace)
  const totals = calculate(form, workspace.formulas)
  const canSave = form.change_reason.trim().length >= 3 && !(form.fasting_enabled && (form.oral_enabled || form.enteral_enabled || form.supplements.length > 0))
  return <Dialog open={open} onClose={saving ? undefined : close} fullScreen><DialogTitle>Prescripción nutricional {order ? `· versión ${order.version_number}` : 'nueva'}</DialogTitle><DialogContent dividers>
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    <Grid container spacing={2}>
      <Grid size={{ xs: 12, lg: 3 }}><Stack spacing={2}><SectionCard title="Contexto y metas" description="Se importan desde la última evaluación finalizada y quedan congeladas en esta versión."><Stack spacing={1.5}>
        <TextField required label="Motivo de la prescripción o cambio" value={form.change_reason} onChange={(e) => set('change_reason', e.target.value)} multiline minRows={2} />
        {[['energy_goal_kcal', 'Energía', 'kcal/día'], ['protein_goal_g', 'Proteínas', 'g/día'], ['carbohydrate_goal_g', 'Carbohidratos', 'g/día'], ['lipid_goal_g', 'Lípidos', 'g/día']].map(([key, label, unit]) => <TextField key={key} type="number" label={label} value={form[key as keyof PrescriptionForm] as string} onChange={(e) => set(key as keyof PrescriptionForm, e.target.value as never)} helperText={unit} />)}
        <Grid container spacing={1}><Grid size={7}><TextField fullWidth type="number" label="Volumen" value={form.fluid_goal_ml} onChange={(e) => set('fluid_goal_ml', e.target.value)} helperText="mL/día" /></Grid><Grid size={5}><FormControl fullWidth><InputLabel>Tipo</InputLabel><Select label="Tipo" value={form.fluid_goal_kind} onChange={(e) => set('fluid_goal_kind', e.target.value as PrescriptionForm['fluid_goal_kind'])}><MenuItem value="target">Meta</MenuItem><MenuItem value="maximum">Máximo</MenuItem><MenuItem value="minimum">Mínimo</MenuItem><MenuItem value="range">Rango</MenuItem></Select></FormControl></Grid></Grid>
        <TextField type="datetime-local" label="Próxima reevaluación" value={form.suggested_reassessment_at} onChange={(e) => set('suggested_reassessment_at', e.target.value)} InputLabelProps={{ shrink: true }} />
      </Stack></SectionCard></Stack></Grid>
      <Grid size={{ xs: 12, lg: 6 }}><Stack spacing={2}><SectionCard title="Estrategia nutricional" description="Puede combinar vías; régimen cero es exclusivo."><Stack direction={{ xs: 'column', sm: 'row' }}><FormControlLabel control={<Checkbox checked={form.oral_enabled} onChange={(e) => set('oral_enabled', e.target.checked)} />} label="Alimentación oral" /><FormControlLabel control={<Checkbox checked={form.enteral_enabled} onChange={(e) => set('enteral_enabled', e.target.checked)} />} label="Nutrición enteral" /><FormControlLabel control={<Checkbox checked={form.fasting_enabled} onChange={(e) => set('fasting_enabled', e.target.checked)} />} label="Régimen cero" /></Stack>{form.fasting_enabled && (form.oral_enabled || form.enteral_enabled || form.supplements.length > 0) && <Alert severity="error">Régimen cero no puede combinarse con aportes nutricionales.</Alert>}</SectionCard>
        {form.oral_enabled && <SectionCard title="Prescripción oral"><Grid container spacing={1.5}><Grid size={{ xs: 12, md: 6 }}><TextField fullWidth required label="Tipo de régimen" value={form.regimen_type} onChange={(e) => set('regimen_type', e.target.value)} /></Grid><Grid size={{ xs: 6, md: 3 }}><FormControl fullWidth><InputLabel>Alimentos IDDSI</InputLabel><Select label="Alimentos IDDSI" value={form.food_iddsi} onChange={(e) => set('food_iddsi', e.target.value)}><MenuItem value="">Sin indicar</MenuItem>{[3,4,5,6,7].map((v) => <MenuItem key={v} value={v}>{v}</MenuItem>)}</Select></FormControl></Grid><Grid size={{ xs: 6, md: 3 }}><FormControl fullWidth><InputLabel>Líquidos IDDSI</InputLabel><Select label="Líquidos IDDSI" value={form.liquid_iddsi} onChange={(e) => set('liquid_iddsi', e.target.value)}><MenuItem value="">Sin indicar</MenuItem>{[0,1,2,3,4].map((v) => <MenuItem key={v} value={v}>{v}</MenuItem>)}</Select></FormControl></Grid>
          <Grid size={12}><TextField fullWidth label="Restricciones" value={form.restrictions} onChange={(e) => set('restrictions', e.target.value)} multiline /></Grid><Grid size={{ xs: 12, md: 6 }}><TextField fullWidth label="Alergias e intolerancias consideradas" value={form.allergies_snapshot} onChange={(e) => set('allergies_snapshot', e.target.value)} /></Grid><Grid size={{ xs: 12, md: 6 }}><TextField fullWidth label="Asistencia para alimentación" value={form.feeding_assistance} onChange={(e) => set('feeding_assistance', e.target.value)} /></Grid>
          {([['oral_energy_kcal','Energía kcal'],['oral_protein_g','Proteína g'],['oral_carbohydrate_g','CHO g'],['oral_lipid_g','Lípidos g'],['oral_fluid_ml','Volumen mL']] as const).map(([key,label]) => <Grid key={key} size={{ xs: 6, md: 2.4 }}><TextField fullWidth type="number" label={label} value={form[key]} onChange={(e) => set(key, e.target.value)} /></Grid>)}
          <Grid size={{ xs: 12, md: 6 }}><TextField fullWidth label="Indicaciones para cocina" value={form.kitchen_instructions} onChange={(e) => set('kitchen_instructions', e.target.value)} multiline /></Grid><Grid size={{ xs: 12, md: 6 }}><TextField fullWidth label="Indicaciones para enfermería" value={form.nursing_instructions} onChange={(e) => set('nursing_instructions', e.target.value)} multiline /></Grid>
          {form.meals.map((item, index) => <Grid key={item.meal_time} size={{ xs: 12, md: 6 }}><TextField fullWidth size="small" label={MEAL_LABELS[item.meal_time]} value={item.instruction} onChange={(e) => set('meals', form.meals.map((row, i) => i === index ? { ...row, instruction: e.target.value } : row))} /></Grid>)}
        </Grid></SectionCard>}
        {form.enteral_enabled && <SectionCard title="Nutrición enteral"><Grid container spacing={1.5}><Grid size={12}><FormControl fullWidth><InputLabel>Fórmula</InputLabel><Select label="Fórmula" value={form.enteral_formula_id} onChange={(e) => set('enteral_formula_id', e.target.value)}><MenuItem value="">Seleccionar</MenuItem>{workspace.formulas.map((formula) => <MenuItem key={formula.id} value={formula.id}>{formula.display_name} · {formula.kcal_per_ml} kcal/mL · v{formula.catalog_version}</MenuItem>)}</Select></FormControl>{workspace.formulas.length === 0 && <Alert severity="info" sx={{ mt: 1 }}>El catálogo institucional aún no tiene fórmulas activas.</Alert>}</Grid>
          <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth label="Vía/acceso" value={form.enteral_access_route} onChange={(e) => set('enteral_access_route', e.target.value)} placeholder="SNG, gastrostomía" /></Grid><Grid size={{ xs: 12, md: 4 }}><TextField fullWidth label="Ubicación de sonda" value={form.enteral_tube_location} onChange={(e) => set('enteral_tube_location', e.target.value)} /></Grid><Grid size={{ xs: 12, md: 4 }}><FormControl fullWidth><InputLabel>Modalidad</InputLabel><Select label="Modalidad" value={form.enteral_modality} onChange={(e) => set('enteral_modality', e.target.value)}>{[['continuous','Continua'],['cyclic','Cíclica'],['intermittent','Intermitente'],['bolus','Bolos']].map(([v,l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}</Select></FormControl></Grid>
          <Grid size={{ xs: 6, md: 3 }}><TextField fullWidth type="number" label="Velocidad mL/h" value={form.enteral_rate_ml_h} onChange={(e) => set('enteral_rate_ml_h', e.target.value)} /></Grid><Grid size={{ xs: 6, md: 3 }}><TextField fullWidth type="number" label="Horas efectivas" value={form.enteral_effective_hours} onChange={(e) => set('enteral_effective_hours', e.target.value)} /></Grid><Grid size={{ xs: 6, md: 3 }}><TextField fullWidth type="number" label="Lavado mL" value={form.water_flush_ml} onChange={(e) => set('water_flush_ml', e.target.value)} /></Grid><Grid size={{ xs: 6, md: 3 }}><TextField fullWidth type="number" label="Cada horas" value={form.water_flush_every_hours} onChange={(e) => set('water_flush_every_hours', e.target.value)} /></Grid>
          <Grid size={{ xs: 12, md: 6 }}><TextField fullWidth type="number" label="Pausas por medicamentos/procedimientos (h)" value={form.medication_pause_hours} onChange={(e) => set('medication_pause_hours', e.target.value)} /></Grid><Grid size={{ xs: 12, md: 6 }}><TextField fullWidth type="datetime-local" label="Inicio" value={form.enteral_starts_at} onChange={(e) => set('enteral_starts_at', e.target.value)} InputLabelProps={{ shrink: true }} /></Grid><Grid size={12}><Alert severity="info">Volumen diario calculado: {fmt(totals.volume, 1)} mL.</Alert></Grid>
          <Grid size={12}><Stack spacing={1}><Stack direction="row" justifyContent="space-between"><Typography fontWeight={700}>Progresión</Typography><Button size="small" startIcon={<Plus size={16} />} onClick={() => set('progressions', [...form.progressions, { stage: '', rate_ml_h: '', duration_hours: '', condition: '' }])}>Etapa</Button></Stack>{form.progressions.map((item,index) => <ArrayRow key={index} item={item} fields={[["stage","Etapa"],["rate_ml_h","mL/h","number"],["duration_hours","Duración h","number"],["condition","Condición"]]} onChange={(next) => rowSet('progressions',index,next)} onDelete={() => rowSet('progressions',index)} />)}</Stack></Grid>
        </Grid></SectionCard>}
        {!form.fasting_enabled && <SectionCard title="Suplementos y módulos" actions={<Button size="small" startIcon={<Plus size={16} />} onClick={() => set('supplements', [...form.supplements, { product_type: 'oral_supplement', product_name: '', dose: '', dose_unit: '', schedule: '', route: 'oral', duration: '', energy_kcal: '', protein_g: '', carbohydrate_g: '', lipid_g: '', fluid_ml: '' }])}>Producto</Button>}><Stack spacing={1.5}>{form.supplements.length === 0 ? <Typography color="text.secondary">Sin productos adicionales.</Typography> : form.supplements.map((item,index) => <ArrayRow key={index} item={item} fields={[["product_name","Producto"],["dose","Dosis","number"],["dose_unit","Unidad"],["schedule","Horario"],["energy_kcal","kcal","number"],["protein_g","Proteína g","number"],["fluid_ml","Volumen mL","number"]]} onChange={(next) => rowSet('supplements',index,next)} onDelete={() => rowSet('supplements',index)} />)}</Stack></SectionCard>}
        <SectionCard title="Monitoreo" actions={<Button size="small" startIcon={<Plus size={16} />} onClick={() => set('monitoring', [...form.monitoring, { parameter: '', frequency: '', responsible: '', instruction: '' }])}>Indicación</Button>}><Stack spacing={1.5}>{form.monitoring.map((item,index) => <ArrayRow key={index} item={item} fields={[["parameter","Parámetro"],["frequency","Frecuencia"],["responsible","Responsable"],["instruction","Instrucción"]]} onChange={(next) => rowSet('monitoring',index,next)} onDelete={() => rowSet('monitoring',index)} />)}{form.monitoring.length === 0 && <Typography color="text.secondary">Sin indicaciones de monitoreo.</Typography>}</Stack></SectionCard>
      </Stack></Grid>
      <Grid size={{ xs: 12, lg: 3 }}><Box sx={{ position: { lg: 'sticky' }, top: 8 }}><SectionCard title="Aportes en tiempo real" description="La API recalculará y congelará estos valores al guardar."><CoverageTable rows={live} /><Alert severity="info" sx={{ mt: 2 }}>Los colores apoyan la revisión y no impiden guardar ni validar.</Alert></SectionCard></Box></Grid>
    </Grid>
  </DialogContent><DialogActions><Button onClick={close}>Cerrar</Button><Button variant="contained" disabled={saving || !canSave} onClick={() => void save()}>Guardar borrador</Button></DialogActions></Dialog>
}

function Recipe({ order, active = false }: { order: NutritionPrescriptionOrder; active?: boolean }) {
  return <Box className={active ? 'nutrition-prescription-print-active' : undefined}><Typography variant="h6" fontWeight={800}>Prescripción nutricional vigente</Typography><Typography sx={{ mt: 1 }}>{order.recipe_text}</Typography><Typography variant="caption" color="text.secondary">Versión {order.version_number} · {order.author_name} · {formatDate(order.activated_at ?? order.validated_at)}</Typography></Box>
}

export function NutritionPrescriptionOrderTab({ admissionId, historical, csrfToken, onChanged }: { admissionId: string; historical: boolean; csrfToken: string; onChanged: () => void }) {
  const [workspace, setWorkspace] = useState<NutritionPrescriptionWorkspace | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editor, setEditor] = useState<{ open: boolean; order: NutritionPrescriptionOrder | null }>({ open: false, order: null })
  const [busy, setBusy] = useState(false)
  const load = useCallback(async () => { setLoading(true); setError(null); try { setWorkspace(await apiRequest(`/admissions/${admissionId}/nutrition-prescription-workspace`)) } catch (caught) { setError(requestError(caught)) } finally { setLoading(false) } }, [admissionId])
  useEffect(() => { void load() }, [load])
  async function action(path: string, body: object) { setBusy(true); setError(null); try { await apiRequest(path, { method: 'POST', body: JSON.stringify(body) }, csrfToken); await load(); onChanged() } catch (caught) { setError(requestError(caught)) } finally { setBusy(false) } }
  async function modify(order: NutritionPrescriptionOrder) { setBusy(true); try { const draft = await apiRequest<NutritionPrescriptionOrder>(`/nutrition-prescription-orders/${order.id}/clone`, { method: 'POST', body: JSON.stringify({ reason: 'Modificación de prescripción vigente.' }) }, csrfToken); await load(); setEditor({ open: true, order: draft }) } catch (caught) { setError(requestError(caught)) } finally { setBusy(false) } }
  if (error && !workspace) return <ErrorState message={error} onRetry={() => void load()} />
  if (loading || !workspace) return <LoadingState label="Cargando prescripción nutricional" rows={5} />
  const active = workspace.active
  const validated = workspace.history.find((row) => row.status === 'validated')
  return <Stack spacing={2}>
    <style>{'@media print { body * { visibility: hidden !important; } .nutrition-prescription-print-active, .nutrition-prescription-print-active * { visibility: visible !important; } .nutrition-prescription-print-active { position: absolute; left: 0; top: 0; width: 100%; padding: 24px; } }'}</style>
    {error && <Alert severity="error">{error}</Alert>}
    <SectionCard title="Prescripción nutricional" description="Define cómo se entregarán las metas calculadas y conserva cada versión clínica." actions={!historical ? <Button variant="contained" startIcon={<Plus size={18} />} onClick={() => setEditor({ open: true, order: null })}>Nueva prescripción</Button> : undefined}>
      {active ? <Stack spacing={2}><Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" gap={2}><Box><Stack direction="row" gap={1} alignItems="center"><Typography variant="h6" fontWeight={800}>Versión {active.version_number}</Typography><Chip color="success" label="Activa" size="small" /></Stack><Typography color="text.secondary">Vigente desde {formatDate(active.effective_from)} · {active.author_name}</Typography></Box>{!historical && <Stack direction="row" gap={1} flexWrap="wrap"><Button startIcon={<Pencil size={17} />} disabled={busy} onClick={() => void modify(active)}>Modificar</Button><Button startIcon={<Clipboard size={17} />} onClick={() => void navigator.clipboard.writeText(active.recipe_text ?? '')}>Copiar indicación</Button><Button startIcon={<Printer size={17} />} onClick={() => window.print()}>Imprimir</Button><Button color="warning" startIcon={<StopCircle size={17} />} disabled={busy} onClick={() => { const reason = window.prompt('Motivo de suspensión'); if (reason?.trim()) void action(`/nutrition-prescription-orders/${active.id}/suspend`, { expected_lock_version: active.lock_version, reason }) }}>Suspender</Button></Stack>}</Stack><Divider /><Recipe order={active} active /><CoverageTable rows={active.coverage} />{active.alerts.map((item) => <Alert key={item.code} severity={item.severity}>{item.message}</Alert>)}</Stack> : <EmptyState title="Sin prescripción activa" description="Cree un borrador, valídelo y actívelo para publicar una indicación vigente." />}
    </SectionCard>
    {workspace.drafts.length > 0 && <SectionCard title={`Borradores (${workspace.drafts.length})`} description="Sólo el autor o jefatura puede editarlos."><Stack spacing={1.5}>{workspace.drafts.map((draft) => <Box key={draft.id} p={2} border={1} borderColor="divider" borderRadius={2}><Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={1}><Box><Typography fontWeight={800}>Versión {draft.version_number} · {draft.change_reason}</Typography><Typography variant="body2" color="text.secondary">Actualizada {formatDate(draft.updated_at)} · {draft.author_name}</Typography></Box><Stack direction="row" gap={1}><Button onClick={() => setEditor({ open: true, order: draft })}>Continuar</Button><Button variant="contained" startIcon={<ShieldCheck size={17} />} disabled={busy} onClick={() => void action(`/nutrition-prescription-orders/${draft.id}/validate`, { expected_lock_version: draft.lock_version })}>Validar</Button></Stack></Stack>{draft.alerts.length > 0 && <Alert severity="warning" sx={{ mt: 1 }}>{draft.alerts.map((item) => item.message).join(' ')}</Alert>}</Box>)}</Stack></SectionCard>}
    {validated && !historical && <Alert severity="info" action={<Button disabled={busy} onClick={() => void action(`/nutrition-prescription-orders/${validated.id}/activate`, { expected_lock_version: validated.lock_version })}>Activar versión {validated.version_number}</Button>}>Existe una prescripción validada pendiente de activación. Activarla reemplazará atómicamente cualquier versión vigente.</Alert>}
    <SectionCard title={`Historial de versiones (${workspace.history.length})`}><Stack>{workspace.history.length === 0 ? <Typography color="text.secondary">Aún no hay versiones validadas.</Typography> : workspace.history.map((row) => <Accordion key={row.id} disableGutters><AccordionSummary expandIcon={<ChevronDown size={18} />}><Stack direction="row" gap={1} alignItems="center"><Typography fontWeight={700}>Versión {row.version_number}</Typography><Chip size="small" label={STATUS_LABELS[row.status] ?? row.status} /><Typography variant="body2" color="text.secondary">{formatDate(row.validated_at)}</Typography></Stack></AccordionSummary><AccordionDetails><Stack spacing={2}><Recipe order={row} />{row.changes.length > 0 && <Box><Typography fontWeight={700}>Cambios respecto de la versión anterior</Typography>{row.changes.map((change) => <Typography key={change.field} variant="body2">{change.label}: {String(change.before ?? '—')} → {String(change.after ?? '—')}</Typography>)}</Box>}<CoverageTable rows={row.coverage} />{row.suspension_reason && <Alert severity="warning">Suspensión: {row.suspension_reason}</Alert>}</Stack></AccordionDetails></Accordion>)}</Stack></SectionCard>
    <PrescriptionEditor open={editor.open} workspace={workspace} order={editor.order} csrfToken={csrfToken} onClose={() => setEditor({ open: false, order: null })} onSaved={() => { void load(); onChanged() }} />
  </Stack>
}
