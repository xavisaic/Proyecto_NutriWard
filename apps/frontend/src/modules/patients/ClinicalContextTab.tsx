import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { ChevronDown, ClipboardPaste, Pencil, Plus, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { EmptyState, ErrorState, LoadingState, SectionCard } from '../../shared/components'
import {
  AdmissionDiagnosis,
  ApiError,
  ClinicalContext,
  PatientCondition,
  apiRequest,
} from '../../shared/services/api'
import { AllergyIntoleranceSection } from './AllergyIntoleranceSection'

type RecordKind = 'diagnosis' | 'condition'
type ClinicalRecord = AdmissionDiagnosis | PatientCondition

const SOURCES: Record<string, string> = {
  trakcare_manual: 'TrakCare (transcripción manual)',
  clinical_record: 'Ficha clínica',
  care_team: 'Equipo tratante',
  patient: 'Paciente',
  family_or_caregiver: 'Familiar o cuidador',
  other: 'Otra fuente',
}

const CLINICAL_STATUS: Record<string, string> = {
  active: 'Activo', inactive: 'Inactivo', remission: 'En remisión', resolved: 'Resuelto',
  entered_in_error: 'Ingresado por error',
}
const VERIFICATION_STATUS: Record<string, string> = {
  provisional: 'Provisional', confirmed: 'Confirmado', ruled_out: 'Descartado',
  unconfirmed: 'No confirmado', refuted: 'Refutado',
}
const DIAGNOSIS_TYPE: Record<string, string> = {
  principal: 'Principal', secondary: 'Secundario', complication: 'Complicación',
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 409) return `${error.message} Recargue y revise los registros antes de reintentar.`
    if (error.status === 403) return 'No tiene permiso para acceder a antecedentes clínicos.'
    return error.message
  }
  return 'No fue posible cargar los diagnósticos y antecedentes.'
}

function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  const parsed = value.includes('T')
    ? new Date(value)
    : (() => { const [year, month, day] = value.split('-').map(Number); return new Date(year, month - 1, day) })()
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: value.includes('T') ? 'short' : undefined }).format(parsed)
}

export function parseClinicalPaste(value: string): string[] {
  const seen = new Set<string>()
  return value
    .split(/[\n;]+/)
    .map((line) => line.replace(/^\s*(?:(?:[-•*])|(?:\d+[.)]))\s*/, '').trim())
    .filter((line) => {
      if (!line) return false
      const key = line.toLocaleLowerCase().replace(/\s+/g, ' ')
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
    .slice(0, 100)
}

interface PreviewRow { name: string; code: string; diagnosisType: string; presentOnAdmission: boolean }

function BulkEntryDialog({ kind, open, admissionId, patientId, csrfToken, onClose, onSaved }: {
  kind: RecordKind
  open: boolean
  admissionId: string
  patientId: string
  csrfToken: string
  onClose: () => void
  onSaved: () => void
}) {
  const diagnosis = kind === 'diagnosis'
  const [pasted, setPasted] = useState('')
  const [rows, setRows] = useState<PreviewRow[]>([])
  const [source, setSource] = useState('clinical_record')
  const [verification, setVerification] = useState(diagnosis ? 'provisional' : 'confirmed')
  const [diagnosisType, setDiagnosisType] = useState('secondary')
  const [presentOnAdmission, setPresentOnAdmission] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setPasted('')
    setRows([])
    setError(null)
    setVerification(diagnosis ? 'provisional' : 'confirmed')
  }, [diagnosis, open])

  function prepare() {
    const parsed = parseClinicalPaste(pasted)
    if (!parsed.length) {
      setError('Pegue o escriba al menos un registro.')
      return
    }
    setRows(parsed.map((name) => ({ name, code: '', diagnosisType, presentOnAdmission })))
    setError(null)
  }

  async function save() {
    const valid = rows.filter((row) => row.name.trim())
    if (!valid.length) return
    setSaving(true)
    setError(null)
    try {
      const items = valid.map((row) => diagnosis ? {
        diagnosis_name: row.name.trim(), code_system: row.code.trim() ? 'CIE-10' : null,
        code: row.code.trim() || null, diagnosis_type: row.diagnosisType, clinical_status: 'active',
        verification_status: verification, present_on_admission: row.presentOnAdmission, source,
      } : {
        condition_name: row.name.trim(), code_system: row.code.trim() ? 'CIE-10' : null,
        code: row.code.trim() || null, clinical_status: 'active', verification_status: verification, source,
      })
      await apiRequest(
        diagnosis ? `/admissions/${admissionId}/diagnoses` : `/patients/${patientId}/conditions`,
        { method: 'POST', body: JSON.stringify({ items }) },
        csrfToken,
      )
      onSaved()
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onClose={saving ? undefined : onClose} fullWidth maxWidth="md">
      <DialogTitle>{diagnosis ? 'Agregar diagnósticos de la hospitalización' : 'Agregar antecedentes mórbidos'}</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2.5}>
          <Alert severity="info">
            Pegue una lista con un registro por línea o separado por punto y coma. Antes de guardar podrá revisar cada fila; el texto pegado no se conserva como bloque libre.
          </Alert>
          {!rows.length ? (
            <>
              <TextField
                autoFocus label={diagnosis ? 'Diagnósticos' : 'Antecedentes'} value={pasted}
                onChange={(event) => setPasted(event.target.value)} multiline minRows={8}
                placeholder={'Hipertensión arterial\nDiabetes mellitus tipo 2\nEnfermedad renal crónica etapa 3'}
                helperText="Reconoce saltos de línea, viñetas, numeración y punto y coma. Máximo 100 registros."
              />
              <Button startIcon={<ClipboardPaste size={17} />} variant="contained" onClick={prepare} sx={{ alignSelf: 'flex-start' }}>
                Preparar registros
              </Button>
            </>
          ) : (
            <>
              <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
                <FormControl fullWidth><InputLabel id="bulk-source-label">Fuente para todos</InputLabel><Select labelId="bulk-source-label" label="Fuente para todos" value={source} onChange={(e) => setSource(e.target.value)}>{Object.entries(SOURCES).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
                <FormControl fullWidth><InputLabel id="bulk-verification-label">Verificación</InputLabel><Select labelId="bulk-verification-label" label="Verificación" value={verification} onChange={(e) => setVerification(e.target.value)}>{(diagnosis ? ['provisional', 'confirmed', 'ruled_out'] : ['unconfirmed', 'confirmed', 'refuted']).map((value) => <MenuItem key={value} value={value}>{VERIFICATION_STATUS[value]}</MenuItem>)}</Select></FormControl>
                {diagnosis && <FormControl fullWidth><InputLabel id="bulk-type-label">Tipo para todos</InputLabel><Select labelId="bulk-type-label" label="Tipo para todos" value={diagnosisType} onChange={(e) => { setDiagnosisType(e.target.value); setRows((current) => current.map((row) => ({ ...row, diagnosisType: e.target.value }))) }}>{Object.entries(DIAGNOSIS_TYPE).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>}
              </Stack>
              {diagnosis && <FormControlLabel control={<Switch checked={presentOnAdmission} onChange={(e) => { setPresentOnAdmission(e.target.checked); setRows((current) => current.map((row) => ({ ...row, presentOnAdmission: e.target.checked }))) }} />} label="Aplicar a todos: presente al ingreso" />}
              <Typography fontWeight={800}>{rows.length} registros detectados</Typography>
              <Stack spacing={1.25}>
                {rows.map((row, index) => (
                  <Stack key={`${index}-${row.name}`} direction="row" spacing={1} alignItems="center">
                    <TextField fullWidth label={`Registro ${index + 1}`} value={row.name} onChange={(e) => setRows((current) => current.map((item, rowIndex) => rowIndex === index ? { ...item, name: e.target.value } : item))} />
                    <TextField label="CIE-10 opcional" value={row.code} sx={{ width: 170 }} onChange={(e) => setRows((current) => current.map((item, rowIndex) => rowIndex === index ? { ...item, code: e.target.value } : item))} />
                    {diagnosis && <FormControl sx={{ minWidth: 150 }}><InputLabel id={`row-type-label-${index}`}>Tipo</InputLabel><Select labelId={`row-type-label-${index}`} label="Tipo" value={row.diagnosisType} onChange={(e) => setRows((current) => current.map((item, rowIndex) => rowIndex === index ? { ...item, diagnosisType: e.target.value } : item))}>{Object.entries(DIAGNOSIS_TYPE).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>}
                    {diagnosis && <FormControlLabel control={<Switch checked={row.presentOnAdmission} onChange={(e) => setRows((current) => current.map((item, rowIndex) => rowIndex === index ? { ...item, presentOnAdmission: e.target.checked } : item))} />} label="Al ingreso" />}
                    <IconButton aria-label={`Quitar ${row.name}`} onClick={() => setRows((current) => current.filter((_, rowIndex) => rowIndex !== index))}><Trash2 size={18} /></IconButton>
                  </Stack>
                ))}
              </Stack>
              <Button onClick={() => setRows([])} sx={{ alignSelf: 'flex-start' }}>Volver al texto pegado</Button>
            </>
          )}
          {error && <Alert severity="error">{error}</Alert>}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving}>Cancelar</Button>
        {rows.length > 0 && <Button variant="contained" onClick={() => void save()} disabled={saving || !rows.some((row) => row.name.trim())}>{saving ? 'Guardando…' : `Guardar ${rows.length} registros`}</Button>}
      </DialogActions>
    </Dialog>
  )
}

function StatusDialog({ kind, record, csrfToken, onClose, onSaved }: {
  kind: RecordKind
  record: ClinicalRecord | null
  csrfToken: string
  onClose: () => void
  onSaved: () => void
}) {
  const diagnosis = kind === 'diagnosis'
  const [clinicalStatus, setClinicalStatus] = useState('active')
  const [verification, setVerification] = useState('confirmed')
  const [source, setSource] = useState('clinical_record')
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!record) return
    setClinicalStatus(record.clinical_status)
    setVerification(record.verification_status)
    setSource(record.source)
    setReason('')
    setError(null)
  }, [record])

  async function save() {
    if (!record || reason.trim().length < 3) return
    setSaving(true)
    setError(null)
    try {
      await apiRequest(
        diagnosis ? `/admission-diagnoses/${record.id}/status` : `/patient-conditions/${record.id}/status`,
        { method: 'PATCH', body: JSON.stringify({ version: record.version, clinical_status: clinicalStatus, verification_status: verification, source, reason: reason.trim() }) },
        csrfToken,
      )
      onSaved()
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setSaving(false)
    }
  }

  const name = record && ('diagnosis_name' in record ? record.diagnosis_name : record.condition_name)
  return (
    <Dialog open={Boolean(record)} onClose={saving ? undefined : onClose} fullWidth maxWidth="sm">
      <DialogTitle>Actualizar estado</DialogTitle>
      <DialogContent dividers><Stack spacing={2}>
        <Typography fontWeight={800}>{name}</Typography>
        <FormControl fullWidth><InputLabel id="clinical-status-label">Estado clínico</InputLabel><Select labelId="clinical-status-label" label="Estado clínico" value={clinicalStatus} onChange={(e) => setClinicalStatus(e.target.value)}>{(diagnosis ? ['active', 'resolved', 'entered_in_error'] : ['active', 'inactive', 'remission', 'resolved', 'entered_in_error']).map((value) => <MenuItem key={value} value={value}>{CLINICAL_STATUS[value]}</MenuItem>)}</Select></FormControl>
        <FormControl fullWidth><InputLabel id="verification-status-label">Verificación</InputLabel><Select labelId="verification-status-label" label="Verificación" value={verification} onChange={(e) => setVerification(e.target.value)}>{(diagnosis ? ['provisional', 'confirmed', 'ruled_out'] : ['unconfirmed', 'confirmed', 'refuted']).map((value) => <MenuItem key={value} value={value}>{VERIFICATION_STATUS[value]}</MenuItem>)}</Select></FormControl>
        <FormControl fullWidth><InputLabel id="clinical-source-label">Fuente</InputLabel><Select labelId="clinical-source-label" label="Fuente" value={source} onChange={(e) => setSource(e.target.value)}>{Object.entries(SOURCES).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
        <TextField required label="Motivo del cambio" value={reason} onChange={(e) => setReason(e.target.value)} multiline minRows={3} helperText="El cambio conservará estado anterior, usuario, fecha, fuente y motivo." />
        {error && <Alert severity="error">{error}</Alert>}
      </Stack></DialogContent>
      <DialogActions><Button onClick={onClose} disabled={saving}>Cancelar</Button><Button variant="contained" onClick={() => void save()} disabled={saving || reason.trim().length < 3}>{saving ? 'Guardando…' : 'Actualizar'}</Button></DialogActions>
    </Dialog>
  )
}

function RecordTable({ kind, rows, historical, onEdit }: {
  kind: RecordKind
  rows: ClinicalRecord[]
  historical: boolean
  onEdit: (row: ClinicalRecord) => void
}) {
  const diagnosis = kind === 'diagnosis'
  if (!rows.length) return <EmptyState title={diagnosis ? 'Sin diagnósticos registrados' : 'Sin antecedentes registrados'} description={diagnosis ? 'Puede pegar o escribir varios diagnósticos en una sola operación.' : 'Confirme antecedentes conocidos o registre varios mediante pegado rápido.'} />
  return <TableContainer><Table size="small"><TableHead><TableRow><TableCell>Registro</TableCell>{diagnosis && <TableCell>Tipo</TableCell>}<TableCell>Estado</TableCell><TableCell>Verificación</TableCell><TableCell>Fuente</TableCell><TableCell>Fecha</TableCell><TableCell align="right">Acciones</TableCell></TableRow></TableHead><TableBody>{rows.map((row) => {
    const name = 'diagnosis_name' in row ? row.diagnosis_name : row.condition_name
    const dateValue = 'diagnosed_at' in row ? row.diagnosed_at : row.onset_date
    return <TableRow key={row.id} sx={row.clinical_status === 'entered_in_error' ? { opacity: 0.62 } : undefined}>
      <TableCell><Stack spacing={0.5}><Typography fontWeight={750}>{name}</Typography>{row.code && <Typography variant="caption" color="text.secondary">{row.code_system} {row.code}</Typography>}</Stack></TableCell>
      {diagnosis && <TableCell>{DIAGNOSIS_TYPE[(row as AdmissionDiagnosis).diagnosis_type]}</TableCell>}
      <TableCell><Chip size="small" label={CLINICAL_STATUS[row.clinical_status] || row.clinical_status} variant="outlined" /></TableCell>
      <TableCell>{VERIFICATION_STATUS[row.verification_status] || row.verification_status}</TableCell>
      <TableCell>{SOURCES[row.source] || row.source}</TableCell>
      <TableCell>{formatDate(dateValue)}</TableCell>
      <TableCell align="right"><IconButton aria-label={`Actualizar ${name}`} disabled={historical} onClick={() => onEdit(row)}><Pencil size={17} /></IconButton></TableCell>
    </TableRow>
  })}</TableBody></Table></TableContainer>
}

function HistoryPanels({ data }: { data: ClinicalContext }) {
  const rows = [...data.diagnoses.map((record) => ({ name: record.diagnosis_name, history: record.history })), ...data.conditions.map((record) => ({ name: record.condition_name, history: record.history }))]
    .filter((row) => row.history.length > 1)
  if (!rows.length) return null
  return <SectionCard title="Historial de cambios" description="La ficha conserva cada transición; no elimina registros clínicos."><Stack>{rows.map((row) => <Accordion key={row.name} disableGutters elevation={0}><AccordionSummary expandIcon={<ChevronDown size={17} />}><Typography fontWeight={750}>{row.name} · {row.history.length} versiones</Typography></AccordionSummary><AccordionDetails><Stack spacing={1}>{[...row.history].reverse().map((event) => <Box key={event.id}><Typography variant="body2" fontWeight={700}>{CLINICAL_STATUS[event.to_clinical_status] || event.to_clinical_status} · {VERIFICATION_STATUS[event.to_verification_status] || event.to_verification_status}</Typography><Typography variant="caption" color="text.secondary">{formatDate(event.changed_at)} · {SOURCES[event.source] || event.source} · {event.reason}</Typography></Box>)}</Stack></AccordionDetails></Accordion>)}</Stack></SectionCard>
}

export function ClinicalContextTab({ admissionId, patientId, historical, csrfToken, onChanged }: {
  admissionId: string
  patientId: string
  historical: boolean
  csrfToken: string
  onChanged: () => void
}) {
  const [data, setData] = useState<ClinicalContext | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [bulkKind, setBulkKind] = useState<RecordKind | null>(null)
  const [editing, setEditing] = useState<{ kind: RecordKind; record: ClinicalRecord } | null>(null)
  const sequence = useRef(0)
  const load = useCallback(async () => {
    const current = ++sequence.current
    setLoading(true)
    setError(null)
    try {
      const next = await apiRequest<ClinicalContext>(`/admissions/${admissionId}/clinical-context`)
      if (current === sequence.current) setData(next)
    } catch (caught) {
      if (current === sequence.current) setError(errorMessage(caught))
    } finally {
      if (current === sequence.current) setLoading(false)
    }
  }, [admissionId])
  useEffect(() => { void load(); return () => { sequence.current += 1 } }, [load])

  if (loading && !data) return <LoadingState label="Cargando diagnósticos y antecedentes" rows={5} />
  if (error && !data) return <ErrorState message={error} onRetry={() => void load()} />
  if (!data) return null
  const afterSaved = () => { setBulkKind(null); setEditing(null); void load(); onChanged() }
  return <Stack spacing={2}>
    {historical && <Alert severity="info">Episodio histórico · Diagnósticos de solo lectura. Los antecedentes mostrados son longitudinales y reflejan su estado actual.</Alert>}
    {error && <Alert severity="error">{error}</Alert>}
    <SectionCard title="Diagnósticos de la hospitalización" description="Múltiples diagnósticos vinculados exclusivamente al episodio seleccionado.">
      <Stack spacing={2}>
        {!historical && <Button startIcon={<Plus size={17} />} variant="contained" onClick={() => setBulkKind('diagnosis')} sx={{ alignSelf: 'flex-start' }}>Agregar diagnósticos</Button>}
        <RecordTable kind="diagnosis" rows={data.diagnoses} historical={historical} onEdit={(record) => setEditing({ kind: 'diagnosis', record })} />
      </Stack>
    </SectionCard>
    <SectionCard title="Antecedentes mórbidos longitudinales" description="Se conservan para futuras hospitalizaciones; no es necesario volver a escribirlos en cada ingreso.">
      <Stack spacing={2}>
        {!historical && <Button startIcon={<Plus size={17} />} variant="outlined" onClick={() => setBulkKind('condition')} sx={{ alignSelf: 'flex-start' }}>Agregar antecedentes</Button>}
        <RecordTable kind="condition" rows={data.conditions} historical={historical} onEdit={(record) => setEditing({ kind: 'condition', record })} />
      </Stack>
    </SectionCard>
    <AllergyIntoleranceSection
      admissionId={admissionId}
      historical={historical}
      csrfToken={csrfToken}
      onChanged={onChanged}
    />
    <HistoryPanels data={data} />
    {bulkKind && <BulkEntryDialog kind={bulkKind} open admissionId={admissionId} patientId={patientId} csrfToken={csrfToken} onClose={() => setBulkKind(null)} onSaved={afterSaved} />}
    {editing && <StatusDialog kind={editing.kind} record={editing.record} csrfToken={csrfToken} onClose={() => setEditing(null)} onSaved={afterSaved} />}
  </Stack>
}

export function ClinicalContextSummaryCard({ admissionId }: { admissionId: string }) {
  const [data, setData] = useState<ClinicalContext | null>(null)
  const [loaded, setLoaded] = useState(false)
  const activeDiagnoses = useMemo(() => (data?.diagnoses ?? []).filter((row) => row.clinical_status === 'active' && row.verification_status !== 'ruled_out'), [data])
  const activeConditions = useMemo(() => (data?.conditions ?? []).filter((row) => row.clinical_status === 'active' && row.verification_status !== 'refuted'), [data])
  useEffect(() => {
    let active = true
    setLoaded(false)
    setData(null)
    apiRequest<ClinicalContext>(`/admissions/${admissionId}/clinical-context`)
      .then((next) => { if (active) setData(next) })
      .catch(() => { if (active) setData(null) })
      .finally(() => { if (active) setLoaded(true) })
    return () => { active = false }
  }, [admissionId])
  return <SectionCard title="Diagnósticos y antecedentes clínicos">
    {!loaded ? <Typography color="text.secondary">Cargando contexto clínico…</Typography> : !data ? <Alert severity="error">No fue posible cargar el contexto clínico.</Alert> : !(data.diagnoses ?? []).length && !(data.conditions ?? []).length ? <Alert severity="warning">Antecedentes clínicos pendientes de registrar o conciliar.</Alert> : <Stack spacing={1.5}>
      <Box><Typography variant="caption" color="text.secondary">Diagnósticos activos</Typography><Stack direction="row" useFlexGap flexWrap="wrap" gap={0.75}>{activeDiagnoses.length ? activeDiagnoses.map((row) => <Chip key={row.id} size="small" label={row.diagnosis_name} />) : <Typography>Sin diagnósticos activos</Typography>}</Stack></Box>
      <Box><Typography variant="caption" color="text.secondary">Antecedentes activos</Typography><Stack direction="row" useFlexGap flexWrap="wrap" gap={0.75}>{activeConditions.length ? activeConditions.map((row) => <Chip key={row.id} size="small" label={row.condition_name} variant="outlined" />) : <Typography>Sin antecedentes activos registrados</Typography>}</Stack></Box>
    </Stack>}
  </SectionCard>
}
