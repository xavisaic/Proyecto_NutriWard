import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import Grid from '@mui/material/Grid2'
import { ChevronDown, ClipboardCheck, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { EmptyState, ErrorState, LoadingState, SectionCard, StatCard } from '../../shared/components'
import {
  AdmissionTreatment,
  ApiError,
  MedicationCatalogItem,
  MedicationCatalogList,
  MedicationCatalogMatchResponse,
  TreatmentContext,
  TreatmentImpactSummary,
  TreatmentVersion,
  apiRequest,
} from '../../shared/services/api'

const CATEGORY_LABELS: Record<string, string> = {
  nutritional_support: 'Soporte nutricional',
  vasoactive: 'Vasoactivos',
  sedative_analgesic: 'Sedación y analgesia',
  antimicrobial: 'Antimicrobianos',
  corticosteroid: 'Corticoides',
  diuretic: 'Diuréticos',
  insulin_glycemic: 'Insulina y control glicémico',
  gastrointestinal: 'Gastrointestinales',
  anticoagulant: 'Anticoagulantes',
  other: 'Otros',
}

const STATUS_LABELS: Record<string, string> = {
  draft: 'Indicado, aún no iniciado',
  active: 'Activo',
  on_hold: 'Suspendido temporalmente',
  ended: 'Finalizado',
  stopped: 'Suspendido',
  completed: 'Completado',
  cancelled: 'Cancelado',
  entered_in_error: 'Ingresado por error',
  unknown: 'Pendiente de verificar',
}

const SOURCE_LABELS: Record<string, string> = {
  medical_order: 'Receta médica',
  trakcare_manual: 'TrakCare (transcripción manual)',
  nursing_record: 'Hoja de enfermería',
  clinical_record: 'Ficha clínica',
  care_team: 'Equipo tratante',
  other: 'Otra fuente',
}

const CURRENT_STATUSES = new Set(['draft', 'active', 'on_hold', 'unknown'])

type TreatmentForm = {
  kind: 'medication' | 'nutritional_support'
  name: string
  category: string
  prescription_text: string
  medication_catalog_code: string
  raw_medication_text: string
  concentration_value: string
  concentration_unit: string
  diluent_volume_ml: string
  dose_value: string
  dose_unit: string
  route: string
  modality: string
  frequency: string
  rate_value: string
  rate_unit: string
  infusion_duration_hours: string
  administered_volume_ml: string
  prescribed_energy_kcal_day: string
  starts_at: string
  planned_ends_at: string
  indication: string
  order_status: string
  source_type: string
  source_reference: string
  observed_at: string
  verification_status: string
  nutritional_note: string
  change_reason: string
}

function nowLocal(): string {
  const date = new Date()
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 16)
}

const EMPTY_FORM: TreatmentForm = {
  kind: 'medication',
  name: '',
  category: 'other',
  prescription_text: '',
  medication_catalog_code: '',
  raw_medication_text: '',
  concentration_value: '',
  concentration_unit: '',
  diluent_volume_ml: '',
  dose_value: '',
  dose_unit: '',
  route: '',
  modality: '',
  frequency: '',
  rate_value: '',
  rate_unit: '',
  infusion_duration_hours: '',
  administered_volume_ml: '',
  prescribed_energy_kcal_day: '',
  starts_at: '',
  planned_ends_at: '',
  indication: '',
  order_status: 'active',
  source_type: 'medical_order',
  source_reference: '',
  observed_at: nowLocal(),
  verification_status: 'verified',
  nutritional_note: '',
  change_reason: '',
}

function formatDate(value: string | null, time = true): string {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, time
    ? { dateStyle: 'medium', timeStyle: 'short' }
    : { dateStyle: 'medium' }).format(new Date(value))
}

function asLocal(value: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 16)
}

function nullableNumber(value: string): number | null {
  return value.trim() === '' ? null : Number(value)
}

function nullableDate(value: string): string | null {
  return value ? new Date(value).toISOString() : null
}

function nullableText(value: string): string | null {
  return value.trim() || null
}

function requestError(error: unknown): string {
  return error instanceof ApiError ? error.message : 'No fue posible completar la solicitud.'
}

function versionToForm(item: AdmissionTreatment): TreatmentForm {
  const row = item.current
  return {
    kind: item.kind,
    name: row.name,
    category: row.category,
    prescription_text: row.prescription_text,
    medication_catalog_code: row.medication_catalog_code ?? '',
    raw_medication_text: row.raw_medication_text ?? '',
    concentration_value: row.concentration_value === null ? '' : String(row.concentration_value),
    concentration_unit: row.concentration_unit ?? '',
    diluent_volume_ml: row.diluent_volume_ml === null ? '' : String(row.diluent_volume_ml),
    dose_value: row.dose_value === null ? '' : String(row.dose_value),
    dose_unit: row.dose_unit ?? '',
    route: row.route ?? '',
    modality: row.modality ?? '',
    frequency: row.frequency ?? '',
    rate_value: row.rate_value === null ? '' : String(row.rate_value),
    rate_unit: row.rate_unit ?? '',
    infusion_duration_hours: row.infusion_duration_hours === null ? '' : String(row.infusion_duration_hours),
    administered_volume_ml: row.administered_volume_ml === null ? '' : String(row.administered_volume_ml),
    prescribed_energy_kcal_day: row.prescribed_energy_kcal_day === null ? '' : String(row.prescribed_energy_kcal_day),
    starts_at: asLocal(row.starts_at),
    planned_ends_at: asLocal(row.planned_ends_at),
    indication: row.indication ?? '',
    order_status: row.order_status,
    source_type: row.source_type,
    source_reference: row.source_reference ?? '',
    observed_at: asLocal(row.observed_at),
    verification_status: row.verification_status,
    nutritional_note: row.nutritional_note ?? '',
    change_reason: '',
  }
}

function statusColor(status: string): 'success' | 'warning' | 'default' | 'error' {
  if (status === 'active') return 'success'
  if (status === 'on_hold' || status === 'unknown' || status === 'draft') return 'warning'
  if (status === 'entered_in_error') return 'error'
  return 'default'
}

type TreatmentDraft = {
  id: string
  sourceText: string
  catalog: MedicationCatalogItem | null
  suggestions: MedicationCatalogItem[]
  prescriptionText: string
  rateValue: string
  infusionDurationHours: string
  administeredVolumeMl: string
}

function CatalogBadges({ item }: { item: MedicationCatalogItem }) {
  return (
    <Stack direction="row" gap={0.75} useFlexGap flexWrap="wrap">
      {item.available_inpatient && <Chip size="small" color="primary" variant="outlined" label="Farmacia hospitalizado" />}
      {item.available_outpatient && <Chip size="small" color="secondary" variant="outlined" label="Farmacia ambulatorio" />}
      {item.route && <Chip size="small" variant="outlined" label={item.route} />}
      {item.restriction && <Chip size="small" color="warning" label="Con restricción" />}
    </Stack>
  )
}

function AddTreatmentsDialog({
  open, csrfToken, admissionId, onClose, onSaved,
}: {
  open: boolean
  csrfToken: string
  admissionId: string
  onClose: () => void
  onSaved: () => void
}) {
  const [query, setQuery] = useState('')
  const [options, setOptions] = useState<MedicationCatalogItem[]>([])
  const [pasted, setPasted] = useState('')
  const [drafts, setDrafts] = useState<TreatmentDraft[]>([])
  const [busy, setBusy] = useState<'search' | 'match' | 'save' | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setQuery(''); setOptions([]); setPasted(''); setDrafts([]); setError(null)
  }, [open])

  useEffect(() => {
    if (!open || query.trim().length < 2) {
      setOptions([])
      return
    }
    let active = true
    const timeout = window.setTimeout(async () => {
      setBusy('search')
      try {
        const result = await apiRequest<MedicationCatalogList>(
          `/medication-catalog?q=${encodeURIComponent(query.trim())}&availability=inpatient&limit=25`,
        )
        if (active) setOptions(result.items)
      } catch (caught) {
        if (active) setError(requestError(caught))
      } finally {
        if (active) setBusy(null)
      }
    }, 250)
    return () => { active = false; window.clearTimeout(timeout) }
  }, [open, query])

  function draft(catalog: MedicationCatalogItem | null, sourceText: string, suggestions: MedicationCatalogItem[] = []): TreatmentDraft {
    return {
      id: `${Date.now()}-${Math.random()}`, sourceText, catalog, suggestions,
      prescriptionText: sourceText || catalog?.display_name || '',
      rateValue: '', infusionDurationHours: '', administeredVolumeMl: '',
    }
  }

  function update(id: string, values: Partial<TreatmentDraft>) {
    setDrafts((rows) => rows.map((row) => row.id === id ? { ...row, ...values } : row))
  }

  function add(item: MedicationCatalogItem | null) {
    if (!item) return
    if (drafts.some((row) => row.catalog?.code === item.code)) {
      setError('Ese medicamento ya está incluido en la revisión.')
      return
    }
    setDrafts((rows) => [...rows, draft(item, item.display_name)])
    setQuery(''); setOptions([]); setError(null)
  }

  async function separateList() {
    const lines = pasted.split(/\r?\n|;/)
      .map((line) => line.replace(/^\s*(?:[-•*]|\d+[.)])\s*/, '').trim()).filter(Boolean)
    const unique = [...new Map(lines.map((line) => [line.toLocaleLowerCase(), line])).values()]
    if (!unique.length || unique.length > 50) {
      setError(unique.length > 50 ? 'Puede revisar hasta 50 medicamentos a la vez.' : 'Pegue al menos un medicamento.')
      return
    }
    setBusy('match'); setError(null)
    try {
      const result = await apiRequest<MedicationCatalogMatchResponse>(
        '/medication-catalog/match', { method: 'POST', body: JSON.stringify({ lines: unique }) },
      )
      setDrafts(result.items.map((row) => draft(row.match, row.source_text, row.suggestions)))
    } catch (caught) {
      setError(requestError(caught))
    } finally {
      setBusy(null)
    }
  }

  function attemptClose() {
    if ((pasted.trim() || drafts.length) && !window.confirm('Hay cambios sin guardar. ¿Desea cerrar el formulario?')) return
    onClose()
  }

  const resolved = drafts.length > 0 && drafts.every((row) => row.catalog && row.prescriptionText.trim())
  const infusionValid = drafts.every((row) => !row.infusionDurationHours || Boolean(row.rateValue))

  async function submit() {
    if (!resolved || !infusionValid) return
    setBusy('save'); setError(null)
    try {
      await apiRequest(
        `/admissions/${admissionId}/treatments/bulk`,
        {
          method: 'POST',
          body: JSON.stringify({ items: drafts.map((row) => ({
            kind: 'medication',
            medication_catalog_code: row.catalog!.code,
            raw_medication_text: row.sourceText,
            name: row.catalog!.display_name,
            category: row.catalog!.default_category,
            prescription_text: row.prescriptionText,
            route: row.catalog!.route,
            modality: row.catalog!.clinical_profile === 'continuous_infusion' ? 'Infusión continua' : null,
            rate_value: nullableNumber(row.rateValue),
            rate_unit: row.rateValue ? 'mL/h' : null,
            infusion_duration_hours: nullableNumber(row.infusionDurationHours),
            administered_volume_ml: nullableNumber(row.administeredVolumeMl),
            order_status: 'active',
            source_type: 'medical_order',
            observed_at: new Date().toISOString(),
            verification_status: 'verified',
          })) }),
        },
        csrfToken,
      )
      onSaved(); onClose()
    } catch (caught) {
      setError(requestError(caught))
    } finally {
      setBusy(null)
    }
  }

  const optionProps = {
    options,
    filterOptions: (values: MedicationCatalogItem[]) => values,
    getOptionLabel: (item: MedicationCatalogItem) => `${item.display_name} · ${item.code}`,
    isOptionEqualToValue: (option: MedicationCatalogItem, value: MedicationCatalogItem) => option.code === value.code,
  }

  return (
    <Dialog open={open} onClose={busy === 'save' ? undefined : attemptClose} fullWidth maxWidth="md">
      <DialogTitle>Agregar medicamentos activos</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2.25}>
          <Alert severity="info">Busque en el arsenal o pegue una lista. Revisará las coincidencias antes de guardar y los datos de infusión sólo aparecerán cuando correspondan.</Alert>
          {error && <Alert severity="error">{error}</Alert>}
          <Autocomplete
            {...optionProps}
            loading={busy === 'search'}
            inputValue={query}
            onInputChange={(_, value, reason) => { if (reason !== 'reset') setQuery(value) }}
            onChange={(_, value) => add(value)}
            renderInput={(params) => <TextField {...params} label="Buscar medicamento del arsenal" placeholder="Nombre o código, por ejemplo propofol" helperText="Resultados disponibles para farmacia de hospitalizados." />}
          />
          <Divider>o pegue la receta</Divider>
          <TextField fullWidth multiline minRows={4} label="Listado de medicamentos" value={pasted}
            onChange={(event) => setPasted(event.target.value)}
            placeholder={'PROPOFOL FA 2% SOL INY 50 ML\nOMEPRAZOL FA 40 MG'}
            helperText="Una línea por medicamento; también acepta viñetas, numeración o punto y coma." />
          <Box><Button variant="outlined" onClick={() => void separateList()} disabled={busy === 'match' || !pasted.trim()}>{busy === 'match' ? 'Comparando…' : 'Separar y revisar'}</Button></Box>
          {drafts.length > 0 && <Stack spacing={1.5}>
            <Typography variant="subtitle1" fontWeight={800}>Revisión ({drafts.length})</Typography>
            {drafts.map((row) => {
              const infusion = row.catalog?.clinical_profile === 'intravenous' || row.catalog?.clinical_profile === 'continuous_infusion'
              const rowOptions = [...new Map([...row.suggestions, ...options].map((item) => [item.code, item])).values()]
              const estimated = row.rateValue && row.infusionDurationHours ? Number(row.rateValue) * Number(row.infusionDurationHours) : null
              return <Box key={row.id} sx={{ border: 1, borderColor: 'divider', borderRadius: 2, p: 2 }}>
                <Stack spacing={1.5}>
                  <Stack direction="row" justifyContent="space-between" gap={1}>
                    <Box><Typography variant="caption" color="text.secondary">Texto original</Typography><Typography variant="body2">{row.sourceText}</Typography></Box>
                    <Button color="inherit" size="small" aria-label="Quitar medicamento" onClick={() => setDrafts((rows) => rows.filter((item) => item.id !== row.id))}><Trash2 size={17} /></Button>
                  </Stack>
                  {row.catalog ? <Stack spacing={0.75}>
                    <Typography fontWeight={800}>{row.catalog.display_name}</Typography>
                    <CatalogBadges item={row.catalog} />
                    {row.catalog.restriction && <Alert severity="warning">Restricción farmacia: {row.catalog.restriction}</Alert>}
                    <Button size="small" sx={{ alignSelf: 'flex-start' }} onClick={() => update(row.id, { catalog: null })}>Cambiar coincidencia</Button>
                  </Stack> : <Autocomplete
                    {...optionProps} options={rowOptions}
                    onInputChange={(_, value, reason) => { if (reason === 'input') setQuery(value) }}
                    onChange={(_, value) => update(row.id, { catalog: value, prescriptionText: row.prescriptionText || value?.display_name || '' })}
                    renderInput={(params) => <TextField {...params} required error label={row.suggestions.length ? 'Seleccione la coincidencia correcta' : 'Busque el medicamento'} helperText={row.suggestions.length ? 'Hay más de una posibilidad; no se eligió automáticamente.' : 'No hubo una coincidencia segura.'} />}
                  />}
                  <TextField required fullWidth multiline minRows={2} label="Indicación transcrita" value={row.prescriptionText}
                    onChange={(event) => update(row.id, { prescriptionText: event.target.value })}
                    helperText="Complete dosis y frecuencia tal como aparecen en la receta." />
                  {infusion && <Grid container spacing={1.5}>
                    <Grid size={{ xs: 12, sm: 4 }}><TextField fullWidth type="number" label="Velocidad (mL/h)" value={row.rateValue} onChange={(event) => update(row.id, { rateValue: event.target.value })} inputProps={{ min: 0, step: 'any' }} /></Grid>
                    <Grid size={{ xs: 12, sm: 4 }}><TextField fullWidth type="number" label="Duración (horas)" value={row.infusionDurationHours} onChange={(event) => update(row.id, { infusionDurationHours: event.target.value })} inputProps={{ min: 0, step: 'any' }} /></Grid>
                    <Grid size={{ xs: 12, sm: 4 }}><TextField fullWidth type="number" label="Volumen informado (mL)" value={row.administeredVolumeMl} onChange={(event) => update(row.id, { administeredVolumeMl: event.target.value })} inputProps={{ min: 0, step: 'any' }} /></Grid>
                    {estimated !== null && Number.isFinite(estimated) && <Grid size={12}><Alert severity="info">Volumen estimado por velocidad × duración: <strong>{estimated.toLocaleString()} mL</strong>. El volumen informado se mantiene separado y no sustituye el registro de enfermería.</Alert></Grid>}
                  </Grid>}
                </Stack>
              </Box>
            })}
            {!resolved && <Alert severity="warning">Revise los medicamentos sin coincidencia antes de guardar.</Alert>}
            {!infusionValid && <Alert severity="warning">La duración requiere una velocidad en mL/h.</Alert>}
          </Stack>}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={attemptClose} disabled={busy === 'save'}>Cancelar</Button>
        <Button variant="contained" onClick={() => void submit()} disabled={busy === 'save' || !resolved || !infusionValid}>{busy === 'save' ? 'Guardando…' : `Guardar ${drafts.length || ''} medicamento${drafts.length === 1 ? '' : 's'}`}</Button>
      </DialogActions>
    </Dialog>
  )
}


function TreatmentDialog({
  open,
  item,
  csrfToken,
  admissionId,
  onClose,
  onSaved,
}: {
  open: boolean
  item: AdmissionTreatment | null
  csrfToken: string
  admissionId: string
  onClose: () => void
  onSaved: () => void
}) {
  const [form, setForm] = useState<TreatmentForm>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    if (open) {
      setForm(item ? versionToForm(item) : { ...EMPTY_FORM, observed_at: nowLocal() })
      setError(null)
      setDirty(false)
    }
  }, [item, open])

  useEffect(() => {
    if (!open || !dirty) return
    const warn = (event: BeforeUnloadEvent) => event.preventDefault()
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty, open])

  function set<K extends keyof TreatmentForm>(key: K, value: TreatmentForm[K]) {
    setForm((current) => ({ ...current, [key]: value }))
    setDirty(true)
  }

  function attemptClose() {
    if (dirty && !window.confirm('Hay cambios sin guardar. ¿Desea cerrar el formulario?')) return
    onClose()
  }

  async function submit() {
    setSaving(true)
    setError(null)
    const payload = {
      medication_catalog_code: nullableText(form.medication_catalog_code),
      raw_medication_text: nullableText(form.raw_medication_text),
      name: form.name,
      category: form.category,
      prescription_text: form.prescription_text,
      concentration_value: nullableNumber(form.concentration_value),
      concentration_unit: nullableText(form.concentration_unit),
      diluent_volume_ml: nullableNumber(form.diluent_volume_ml),
      dose_value: nullableNumber(form.dose_value),
      dose_unit: nullableText(form.dose_unit),
      route: nullableText(form.route),
      modality: nullableText(form.modality),
      frequency: nullableText(form.frequency),
      rate_value: nullableNumber(form.rate_value),
      rate_unit: nullableText(form.rate_unit),
      infusion_duration_hours: nullableNumber(form.infusion_duration_hours),
      administered_volume_ml: nullableNumber(form.administered_volume_ml),
      prescribed_energy_kcal_day: nullableNumber(form.prescribed_energy_kcal_day),
      starts_at: nullableDate(form.starts_at),
      planned_ends_at: nullableDate(form.planned_ends_at),
      indication: nullableText(form.indication),
      order_status: form.order_status,
      source_type: form.source_type,
      source_reference: nullableText(form.source_reference),
      observed_at: new Date(form.observed_at).toISOString(),
      verification_status: form.verification_status,
      nutritional_note: nullableText(form.nutritional_note),
      ...(item
        ? { expected_version: item.current.version, change_reason: form.change_reason }
        : { kind: form.kind }),
    }
    try {
      await apiRequest(
        item ? `/admission-treatments/${item.id}` : `/admissions/${admissionId}/treatments`,
        { method: item ? 'PATCH' : 'POST', body: JSON.stringify(payload) },
        csrfToken,
      )
      setDirty(false)
      onSaved()
      onClose()
    } catch (caught) {
      setError(requestError(caught))
    } finally {
      setSaving(false)
    }
  }

  const validPairs = [
    [form.concentration_value, form.concentration_unit],
    [form.dose_value, form.dose_unit],
    [form.rate_value, form.rate_unit],
  ].every(([value, unit]) => Boolean(value) === Boolean(unit))
  const canSubmit = form.name.trim() && form.prescription_text.trim() && form.source_type
    && form.observed_at && validPairs && (!item || form.change_reason.trim().length >= 3)

  return (
    <Dialog open={open} onClose={saving ? undefined : attemptClose} fullWidth maxWidth="md">
      <DialogTitle>{item ? `Actualizar ${item.current.name}` : 'Agregar tratamiento'}</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2.25}>
          <Alert severity="info">Transcriba la indicación desde una fuente clínica. NutriWard no emite ni modifica la receta médica.</Alert>
          {error && <Alert severity="error">{error}</Alert>}
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 4 }}>
              <FormControl fullWidth><InputLabel id="kind-label">Tipo</InputLabel><Select labelId="kind-label" label="Tipo" value={form.kind} disabled={Boolean(item)} onChange={(event) => set('kind', event.target.value as TreatmentForm['kind'])}><MenuItem value="medication">Medicamento</MenuItem><MenuItem value="nutritional_support">Soporte nutricional</MenuItem></Select></FormControl>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <FormControl fullWidth><InputLabel id="category-label">Categoría</InputLabel><Select labelId="category-label" label="Categoría" value={form.category} onChange={(event) => set('category', event.target.value)}>{Object.entries(CATEGORY_LABELS).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <FormControl fullWidth><InputLabel id="status-label">Estado</InputLabel><Select labelId="status-label" label="Estado" value={form.order_status} onChange={(event) => set('order_status', event.target.value)}>{Object.entries(STATUS_LABELS).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
            </Grid>
            <Grid size={12}><TextField required fullWidth label="Nombre" value={form.name} onChange={(event) => set('name', event.target.value)} /></Grid>
            <Grid size={12}><TextField required fullWidth multiline minRows={2} label="Prescripción o esquema indicado" value={form.prescription_text} onChange={(event) => set('prescription_text', event.target.value)} /></Grid>
            <Grid size={{ xs: 6, md: 3 }}><TextField fullWidth type="number" label="Concentración" value={form.concentration_value} onChange={(event) => set('concentration_value', event.target.value)} inputProps={{ min: 0, step: 'any' }} /></Grid>
            <Grid size={{ xs: 6, md: 3 }}><TextField fullWidth label="Unidad concentración" value={form.concentration_unit} onChange={(event) => set('concentration_unit', event.target.value)} placeholder="mg/mL" /></Grid>
            <Grid size={{ xs: 6, md: 3 }}><TextField fullWidth type="number" label="Dosis actual" value={form.dose_value} onChange={(event) => set('dose_value', event.target.value)} inputProps={{ min: 0, step: 'any' }} /></Grid>
            <Grid size={{ xs: 6, md: 3 }}><TextField fullWidth label="Unidad dosis" value={form.dose_unit} onChange={(event) => set('dose_unit', event.target.value)} placeholder="µg/kg/min" /></Grid>
            <Grid size={{ xs: 6, md: 3 }}><TextField fullWidth type="number" label="Diluyente (mL)" value={form.diluent_volume_ml} onChange={(event) => set('diluent_volume_ml', event.target.value)} inputProps={{ min: 0, step: 'any' }} /></Grid>
            <Grid size={{ xs: 6, md: 3 }}><TextField fullWidth type="number" label="Velocidad" value={form.rate_value} onChange={(event) => set('rate_value', event.target.value)} inputProps={{ min: 0, step: 'any' }} /></Grid>
            <Grid size={{ xs: 6, md: 3 }}><TextField fullWidth label="Unidad velocidad" value={form.rate_unit} onChange={(event) => set('rate_unit', event.target.value)} placeholder="mL/h" /></Grid>
            <Grid size={{ xs: 6, md: 3 }}><TextField fullWidth type="number" label="Duración infusión (horas)" value={form.infusion_duration_hours} onChange={(event) => set('infusion_duration_hours', event.target.value)} inputProps={{ min: 0, step: 'any' }} /></Grid>
            <Grid size={{ xs: 6, md: 3 }}><TextField fullWidth type="number" label="Volumen informado (mL)" value={form.administered_volume_ml} onChange={(event) => set('administered_volume_ml', event.target.value)} inputProps={{ min: 0, step: 'any' }} /></Grid>
            <Grid size={{ xs: 6, md: 3 }}><TextField fullWidth type="number" label="Energía potencial (kcal/día)" value={form.prescribed_energy_kcal_day} onChange={(event) => set('prescribed_energy_kcal_day', event.target.value)} inputProps={{ min: 0, step: 'any' }} /></Grid>
            <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth label="Vía" value={form.route} onChange={(event) => set('route', event.target.value)} placeholder="EV, oral, enteral" /></Grid>
            <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth label="Modalidad" value={form.modality} onChange={(event) => set('modality', event.target.value)} placeholder="Infusión continua" /></Grid>
            <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth label="Frecuencia" value={form.frequency} onChange={(event) => set('frequency', event.target.value)} placeholder="Cada 8 horas" /></Grid>
            <Grid size={{ xs: 12, md: 6 }}><TextField fullWidth type="datetime-local" label="Inicio" value={form.starts_at} onChange={(event) => set('starts_at', event.target.value)} InputLabelProps={{ shrink: true }} /></Grid>
            <Grid size={{ xs: 12, md: 6 }}><TextField fullWidth type="datetime-local" label="Término previsto" value={form.planned_ends_at} onChange={(event) => set('planned_ends_at', event.target.value)} InputLabelProps={{ shrink: true }} /></Grid>
            <Grid size={12}><TextField fullWidth label="Indicación clínica" value={form.indication} onChange={(event) => set('indication', event.target.value)} /></Grid>
            <Grid size={{ xs: 12, md: 4 }}><FormControl fullWidth><InputLabel id="source-label">Fuente</InputLabel><Select labelId="source-label" label="Fuente" value={form.source_type} onChange={(event) => set('source_type', event.target.value)}>{Object.entries(SOURCE_LABELS).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl></Grid>
            <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth label="Referencia de fuente" value={form.source_reference} onChange={(event) => set('source_reference', event.target.value)} placeholder="Receta 08:00" /></Grid>
            <Grid size={{ xs: 12, md: 4 }}><TextField required fullWidth type="datetime-local" label="Fecha y hora observada" value={form.observed_at} onChange={(event) => set('observed_at', event.target.value)} InputLabelProps={{ shrink: true }} /></Grid>
            <Grid size={{ xs: 12, md: 4 }}><FormControl fullWidth><InputLabel id="verification-label">Verificación</InputLabel><Select labelId="verification-label" label="Verificación" value={form.verification_status} onChange={(event) => set('verification_status', event.target.value)}><MenuItem value="verified">Verificado</MenuItem><MenuItem value="pending">Pendiente</MenuItem><MenuItem value="stale">Desactualizado</MenuItem></Select></FormControl></Grid>
            <Grid size={{ xs: 12, md: 8 }}><TextField fullWidth label="Observación nutricional" value={form.nutritional_note} onChange={(event) => set('nutritional_note', event.target.value)} /></Grid>
            {item && <Grid size={12}><TextField required fullWidth label="Motivo del cambio" value={form.change_reason} onChange={(event) => set('change_reason', event.target.value)} helperText="La versión anterior se conservará íntegramente." /></Grid>}
          </Grid>
          {!validPairs && <Alert severity="warning">Concentración, dosis y velocidad requieren valor y unidad en conjunto.</Alert>}
        </Stack>
      </DialogContent>
      <DialogActions><Button onClick={attemptClose} disabled={saving}>Cancelar</Button><Button variant="contained" onClick={() => void submit()} disabled={saving || !canSubmit}>{saving ? 'Guardando…' : item ? 'Guardar nueva versión' : 'Agregar tratamiento'}</Button></DialogActions>
    </Dialog>
  )
}

function VersionDetails({ row }: { row: TreatmentVersion }) {
  const dose = row.dose_value === null ? '—' : `${row.dose_value} ${row.dose_unit}`
  const rate = row.rate_value === null ? '—' : `${row.rate_value} ${row.rate_unit}`
  return (
    <Grid container spacing={1.5}>
      {row.medication_catalog && <Grid size={12}><CatalogBadges item={row.medication_catalog} /></Grid>}
      <Grid size={{ xs: 12, sm: 6 }}><Typography variant="caption" color="text.secondary">Esquema</Typography><Typography variant="body2">{row.prescription_text}</Typography></Grid>
      <Grid size={{ xs: 6, sm: 3 }}><Typography variant="caption" color="text.secondary">Dosis</Typography><Typography variant="body2">{dose}</Typography></Grid>
      <Grid size={{ xs: 6, sm: 3 }}><Typography variant="caption" color="text.secondary">Velocidad</Typography><Typography variant="body2">{rate}</Typography></Grid>
      {row.estimated_volume_ml != null && <Grid size={{ xs: 6, sm: 3 }}><Typography variant="caption" color="text.secondary">Volumen estimado</Typography><Typography variant="body2">{row.estimated_volume_ml} mL</Typography></Grid>}
      {row.administered_volume_ml != null && <Grid size={{ xs: 6, sm: 3 }}><Typography variant="caption" color="text.secondary">Volumen informado</Typography><Typography variant="body2">{row.administered_volume_ml} mL</Typography></Grid>}
      <Grid size={{ xs: 6, sm: 3 }}><Typography variant="caption" color="text.secondary">Vía</Typography><Typography variant="body2">{row.route || '—'}</Typography></Grid>
      <Grid size={{ xs: 6, sm: 3 }}><Typography variant="caption" color="text.secondary">Frecuencia</Typography><Typography variant="body2">{row.frequency || '—'}</Typography></Grid>
      <Grid size={{ xs: 6, sm: 3 }}><Typography variant="caption" color="text.secondary">Inicio</Typography><Typography variant="body2">{formatDate(row.starts_at)}</Typography></Grid>
      <Grid size={{ xs: 6, sm: 3 }}><Typography variant="caption" color="text.secondary">Término previsto</Typography><Typography variant="body2">{formatDate(row.planned_ends_at)}</Typography></Grid>
      <Grid size={{ xs: 12, sm: 6 }}><Typography variant="caption" color="text.secondary">Fuente</Typography><Typography variant="body2">{SOURCE_LABELS[row.source_type] || row.source_type}{row.source_reference ? ` · ${row.source_reference}` : ''}</Typography></Grid>
      <Grid size={{ xs: 12, sm: 6 }}><Typography variant="caption" color="text.secondary">Verificación</Typography><Typography variant="body2">{row.verification_status === 'verified' ? `Verificado por ${row.verifier_name || 'usuario clínico'} · ${formatDate(row.verified_at)}` : STATUS_LABELS.unknown}</Typography></Grid>
      {row.nutritional_note && <Grid size={12}><Typography variant="caption" color="text.secondary">Observación nutricional</Typography><Typography variant="body2">{row.nutritional_note}</Typography></Grid>}
    </Grid>
  )
}

export function ActiveTreatmentsTab({
  admissionId,
  historical,
  csrfToken,
}: {
  admissionId: string
  historical: boolean
  csrfToken: string
}) {
  const [context, setContext] = useState<TreatmentContext | null>(null)
  const [impact, setImpact] = useState<TreatmentImpactSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [category, setCategory] = useState('all')
  const [scope, setScope] = useState<'current' | 'history' | 'all'>('current')
  const [editing, setEditing] = useState<AdmissionTreatment | null>(null)
  const [addOpen, setAddOpen] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const sequence = useRef(0)

  const load = useCallback(async () => {
    const current = ++sequence.current
    setLoading(true)
    setError(null)
    try {
      const [nextContext, nextImpact] = await Promise.all([
        apiRequest<TreatmentContext>(`/admissions/${admissionId}/treatments`),
        apiRequest<TreatmentImpactSummary>(`/admissions/${admissionId}/treatment-impact-summary`),
      ])
      if (current !== sequence.current) return
      setContext(nextContext)
      setImpact(nextImpact)
    } catch (caught) {
      if (current === sequence.current) setError(requestError(caught))
    } finally {
      if (current === sequence.current) setLoading(false)
    }
  }, [admissionId])

  useEffect(() => {
    void load()
    return () => { sequence.current += 1 }
  }, [load])

  const filtered = useMemo(() => (context?.items ?? []).filter((item) => {
    const current = CURRENT_STATUSES.has(item.current.order_status)
    if (scope === 'current' && !current) return false
    if (scope === 'history' && current) return false
    return category === 'all' || item.current.category === category
  }), [category, context, scope])

  async function review(assertion: 'no_known' | 'information_unavailable') {
    const label = assertion === 'no_known' ? 'sin tratamientos relevantes' : 'información no disponible'
    if (!window.confirm(`¿Confirma registrar ${label} para este episodio?`)) return
    try {
      await apiRequest(
        `/admissions/${admissionId}/treatments/review`,
        { method: 'POST', body: JSON.stringify({ assertion, source_type: 'clinical_record', note: null }) },
        csrfToken,
      )
      await load()
    } catch (caught) {
      setError(requestError(caught))
    }
  }

  if (loading && !context) return <LoadingState label="Cargando tratamientos activos" rows={5} />
  if (error && !context) return <ErrorState message={error} onRetry={() => void load()} />
  if (!context) return null

  return (
    <Stack spacing={2.5}>
      {historical && <Alert severity="info">Episodio histórico · los tratamientos se muestran en modo de sólo lectura.</Alert>}
      {context.review_status === 'not_reviewed' && <Alert severity="warning">La receta todavía no ha sido conciliada en NutriWard. Una lista vacía no confirma ausencia de tratamientos.</Alert>}
      {context.review_status === 'information_unavailable' && <Alert severity="warning">La información terapéutica fue registrada como no disponible. Última revisión: {formatDate(context.latest_review?.recorded_at ?? null)}.</Alert>}
      {context.review_status === 'no_known' && <Alert severity="success">Conciliación revisada sin tratamientos nutricionalmente relevantes · {formatDate(context.latest_review?.recorded_at ?? null)}.</Alert>}
      {error && <ErrorState message={error} onRetry={() => void load()} />}
      <Grid container spacing={2}>
        <Grid size={{ xs: 6, md: 3 }}><StatCard label="Activos" value={context.counts.active} icon={<ClipboardCheck size={18} />} tone="success" /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><StatCard label="En pausa" value={context.counts.on_hold} icon={<ClipboardCheck size={18} />} tone="warning" /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><StatCard label="Por verificar" value={context.counts.pending_verification} icon={<ClipboardCheck size={18} />} tone="warning" /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><StatCard label="Históricos" value={context.counts.historical} icon={<ClipboardCheck size={18} />} tone="secondary" /></Grid>
      </Grid>
      <Grid container spacing={2.5} alignItems="flex-start">
        <Grid size={{ xs: 12, lg: 8 }}>
          <SectionCard
            title="Tratamientos del episodio"
            description="Conciliación manual de indicaciones relevantes para la atención nutricional."
            actions={!historical ? <Stack direction="row" useFlexGap flexWrap="wrap" gap={1}><Button size="small" startIcon={<RefreshCw size={16} />} onClick={() => void load()}>Actualizar</Button><Button size="small" variant="contained" startIcon={<Plus size={16} />} onClick={() => setAddOpen(true)}>Agregar medicamentos</Button></Stack> : undefined}
          >
            <Stack spacing={2}>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
                <FormControl size="small" sx={{ minWidth: 220 }}><InputLabel id="scope-filter-label">Vista</InputLabel><Select labelId="scope-filter-label" label="Vista" value={scope} onChange={(event) => setScope(event.target.value as typeof scope)}><MenuItem value="current">Vigentes</MenuItem><MenuItem value="history">Finalizados</MenuItem><MenuItem value="all">Todos</MenuItem></Select></FormControl>
                <FormControl size="small" sx={{ minWidth: 240 }}><InputLabel id="category-filter-label">Categoría</InputLabel><Select labelId="category-filter-label" label="Categoría" value={category} onChange={(event) => setCategory(event.target.value)}><MenuItem value="all">Todas las categorías</MenuItem>{Object.entries(CATEGORY_LABELS).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              </Stack>
              {!filtered.length ? <EmptyState title="Sin tratamientos para esta vista" description="Ajuste los filtros o registre una conciliación desde una fuente clínica." /> : filtered.map((item) => (
                <Accordion key={item.id} variant="outlined" disableGutters>
                  <AccordionSummary expandIcon={<ChevronDown size={18} />}>
                    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} gap={1} width="100%" pr={1}>
                      <Box><Typography fontWeight={800}>{item.current.name}</Typography><Typography variant="body2" color="text.secondary">{CATEGORY_LABELS[item.current.category] || item.current.category} · {item.current.prescription_text}</Typography></Box>
                      <Stack direction="row" gap={0.75} flexWrap="wrap"><Chip size="small" color={statusColor(item.current.order_status)} label={STATUS_LABELS[item.current.order_status] || item.current.order_status} /><Chip size="small" variant="outlined" label={item.current.verification_status === 'verified' ? 'Verificado' : 'Por verificar'} /></Stack>
                    </Stack>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Stack spacing={2}>
                      <VersionDetails row={item.current} />
                      {!historical && <Box><Button size="small" variant="outlined" onClick={() => { setEditing(item); setDialogOpen(true) }}>Actualizar tratamiento</Button></Box>}
                      <Divider />
                      <Typography variant="subtitle2">Historial de versiones ({item.history.length})</Typography>
                      <Stack divider={<Divider flexItem />}>
                        {item.history.map((version) => <Box key={version.id} py={1}><Typography variant="body2" fontWeight={700}>Versión {version.version} · {STATUS_LABELS[version.order_status] || version.order_status} · {formatDate(version.created_at)}</Typography><Typography variant="caption" color="text.secondary">{version.change_reason} · {version.author_name}</Typography></Box>)}
                      </Stack>
                    </Stack>
                  </AccordionDetails>
                </Accordion>
              ))}
            </Stack>
          </SectionCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <Stack spacing={2.5}>
            <SectionCard title="Impacto nutricional actual" description="Reglas informativas y explicables.">
              <Stack spacing={1.5}>
                <Box><Typography variant="caption" color="text.secondary">Aporte prescrito/potencial identificado</Typography><Typography variant="h5" fontWeight={850}>{Number(impact?.potential_energy_kcal_day ?? 0).toLocaleString()} kcal/día</Typography><Typography variant="caption" color="text.secondary">{impact?.energy_source_count ?? 0} fuentes con energía declarada</Typography></Box>
                <Divider />
                {!impact?.items.length ? <Typography variant="body2" color="text.secondary">Sin impactos automáticos para los tratamientos activos.</Typography> : impact.items.map((item) => <Alert key={`${item.treatment_id}-${item.rule_code}`} severity={item.severity}><Typography variant="body2" fontWeight={750}>{item.treatment_name}</Typography><Typography variant="body2">{item.message}</Typography></Alert>)}
                <Typography variant="caption" color="text.secondary">{impact?.disclaimer}</Typography>
              </Stack>
            </SectionCard>
            {!historical && <SectionCard title="Conciliación sin hallazgos" description="Use estas acciones sólo después de revisar una fuente clínica."><Stack spacing={1}><Button variant="outlined" startIcon={<ClipboardCheck size={16} />} onClick={() => void review('no_known')}>Confirmar sin tratamientos relevantes</Button><Button variant="text" onClick={() => void review('information_unavailable')}>Registrar información no disponible</Button></Stack></SectionCard>}
          </Stack>
        </Grid>
      </Grid>
      <AddTreatmentsDialog open={addOpen} csrfToken={csrfToken} admissionId={admissionId} onClose={() => setAddOpen(false)} onSaved={() => void load()} />
      <TreatmentDialog open={dialogOpen} item={editing} csrfToken={csrfToken} admissionId={admissionId} onClose={() => setDialogOpen(false)} onSaved={() => void load()} />
    </Stack>
  )
}
