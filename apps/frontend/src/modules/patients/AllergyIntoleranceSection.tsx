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
  IconButton,
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
import { ChevronDown, ClipboardPaste, Pencil, Plus, ShieldAlert, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { EmptyState, ErrorState, LoadingState, SectionCard } from '../../shared/components'
import {
  AllergyContext,
  AllergyIntolerance,
  ApiError,
  FoodSafetyAllergyProjection,
  apiRequest,
} from '../../shared/services/api'

const CATEGORY: Record<string, string> = {
  all: 'Todas', food: 'Alimento', medication: 'Medicamento', environment: 'Ambiental',
  biologic: 'Biológico', other: 'Otro',
}
const TYPE: Record<string, string> = { allergy: 'Alergia', intolerance: 'Intolerancia' }
const CLINICAL: Record<string, string> = { active: 'Activa', inactive: 'Inactiva', resolved: 'Resuelta' }
const VERIFICATION: Record<string, string> = {
  unconfirmed: 'No confirmada', presumed: 'Presunta', confirmed: 'Confirmada',
  refuted: 'Refutada', entered_in_error: 'Ingresada por error',
}
const CRITICALITY: Record<string, string> = {
  low: 'Baja', high: 'Alta', unable_to_assess: 'No evaluada',
}
const SEVERITY: Record<string, string> = { mild: 'Leve', moderate: 'Moderada', severe: 'Grave' }
const SOURCE: Record<string, string> = {
  trakcare_manual: 'TrakCare (transcripción manual)', clinical_record: 'Ficha clínica',
  care_team: 'Equipo tratante', patient: 'Paciente', family_or_caregiver: 'Familiar o cuidador',
  other: 'Otra fuente',
}
const REVIEW: Record<string, string> = {
  not_asked: 'No consultado', information_unavailable: 'Información no disponible',
  no_known: 'Sin alergias o intolerancias conocidas', reviewed_with_findings: 'Revisado con hallazgos',
}

function message(error: unknown) {
  if (error instanceof ApiError) return error.message
  return 'No fue posible completar la operación.'
}

function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

export function parseAllergyPaste(value: string): string[] {
  const seen = new Set<string>()
  return value.split(/[\n;]+/)
    .map((line) => line.replace(/^\s*(?:(?:[-•*])|(?:\d+[.)]))\s*/, '').trim())
    .filter((line) => {
      const key = line.toLocaleLowerCase().replace(/\s+/g, ' ')
      if (!key || seen.has(key)) return false
      seen.add(key)
      return true
    })
    .slice(0, 100)
}

interface EntryRow {
  name: string
  category: string
  allergyType: string
  criticality: string
  manifestation: string
  severity: string
}

function BulkDialog({ admissionId, csrfToken, open, onClose, onSaved }: {
  admissionId: string; csrfToken: string; open: boolean; onClose: () => void; onSaved: () => void
}) {
  const [pasted, setPasted] = useState('')
  const [rows, setRows] = useState<EntryRow[]>([])
  const [source, setSource] = useState('patient')
  const [verification, setVerification] = useState('unconfirmed')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    if (open) { setPasted(''); setRows([]); setError(null) }
  }, [open])

  function prepare() {
    const names = parseAllergyPaste(pasted)
    if (!names.length) { setError('Pegue o escriba al menos una sustancia.'); return }
    setRows(names.map((name) => ({
      name, category: 'food', allergyType: '', criticality: 'unable_to_assess',
      manifestation: '', severity: '',
    })))
    setError(null)
  }

  function update(index: number, change: Partial<EntryRow>) {
    setRows((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, ...change } : row))
  }

  async function save() {
    setSaving(true)
    setError(null)
    try {
      await apiRequest(`/admissions/${admissionId}/allergy-intolerances`, {
        method: 'POST',
        body: JSON.stringify({ items: rows.filter((row) => row.name.trim()).map((row) => ({
          substance_name: row.name.trim(), category: row.category,
          allergy_type: row.allergyType || null, clinical_status: 'active',
          verification_status: verification, criticality: row.criticality, source,
          reactions: row.manifestation.trim() ? [{
            manifestation: row.manifestation.trim(), severity: row.severity || null,
          }] : [],
        })) }),
      }, csrfToken)
      onSaved()
    } catch (caught) { setError(message(caught)) } finally { setSaving(false) }
  }

  return <Dialog open={open} onClose={saving ? undefined : onClose} fullWidth maxWidth="lg">
    <DialogTitle>Agregar alergias o intolerancias</DialogTitle>
    <DialogContent dividers><Stack spacing={2.5}>
      <Alert severity="info">Pegue una lista completa. Cada fila se transforma en un registro estructurado y puede revisarse antes de guardar.</Alert>
      {!rows.length ? <>
        <TextField autoFocus label="Sustancias o alimentos" value={pasted} onChange={(e) => setPasted(e.target.value)} multiline minRows={7} placeholder={'Maní\nPenicilina\nLactosa'} helperText="Una por línea o separadas por punto y coma. Máximo 100 registros." />
        <Button variant="contained" startIcon={<ClipboardPaste size={17} />} onClick={prepare} sx={{ alignSelf: 'flex-start' }}>Preparar registros</Button>
      </> : <>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
          <FormControl fullWidth><InputLabel id="allergy-source">Fuente para todos</InputLabel><Select labelId="allergy-source" label="Fuente para todos" value={source} onChange={(e) => setSource(e.target.value)}>{Object.entries(SOURCE).map(([value, label]) => <MenuItem value={value} key={value}>{label}</MenuItem>)}</Select></FormControl>
          <FormControl fullWidth><InputLabel id="allergy-verification">Verificación</InputLabel><Select labelId="allergy-verification" label="Verificación" value={verification} onChange={(e) => setVerification(e.target.value)}>{['unconfirmed', 'presumed', 'confirmed'].map((value) => <MenuItem value={value} key={value}>{VERIFICATION[value]}</MenuItem>)}</Select></FormControl>
        </Stack>
        <Typography fontWeight={800}>{rows.length} registros detectados</Typography>
        <Stack spacing={1.5}>{rows.map((row, index) => <Box key={`${index}-${row.name}`} sx={{ border: 1, borderColor: 'divider', borderRadius: 2, p: 2 }}>
          <Stack direction={{ xs: 'column', lg: 'row' }} spacing={1.25} alignItems={{ lg: 'center' }}>
            <TextField label={`Sustancia ${index + 1}`} value={row.name} onChange={(e) => update(index, { name: e.target.value })} sx={{ flex: 1 }} />
            <FormControl sx={{ minWidth: 150 }}><InputLabel id={`category-${index}`}>Categoría</InputLabel><Select labelId={`category-${index}`} label="Categoría" value={row.category} onChange={(e) => update(index, { category: e.target.value })}>{['food', 'medication', 'environment', 'biologic', 'other'].map((value) => <MenuItem key={value} value={value}>{CATEGORY[value]}</MenuItem>)}</Select></FormControl>
            <FormControl sx={{ minWidth: 150 }}><InputLabel id={`type-${index}`}>Tipo</InputLabel><Select labelId={`type-${index}`} label="Tipo" value={row.allergyType} onChange={(e) => update(index, { allergyType: e.target.value })}><MenuItem value="">No determinado</MenuItem><MenuItem value="allergy">Alergia</MenuItem><MenuItem value="intolerance">Intolerancia</MenuItem></Select></FormControl>
            <FormControl sx={{ minWidth: 150 }}><InputLabel id={`criticality-${index}`}>Criticidad</InputLabel><Select labelId={`criticality-${index}`} label="Criticidad" value={row.criticality} onChange={(e) => update(index, { criticality: e.target.value })}>{Object.entries(CRITICALITY).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
            <IconButton aria-label={`Quitar ${row.name}`} onClick={() => setRows((current) => current.filter((_, i) => i !== index))}><Trash2 size={18} /></IconButton>
          </Stack>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.25} mt={1.25}>
            <TextField fullWidth label="Reacción o manifestación inicial (opcional)" value={row.manifestation} onChange={(e) => update(index, { manifestation: e.target.value })} />
            <FormControl sx={{ minWidth: 180 }}><InputLabel id={`severity-${index}`}>Gravedad</InputLabel><Select labelId={`severity-${index}`} label="Gravedad" value={row.severity} onChange={(e) => update(index, { severity: e.target.value })}><MenuItem value="">No registrada</MenuItem>{Object.entries(SEVERITY).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
          </Stack>
        </Box>)}</Stack>
        <Button onClick={() => setRows([])} sx={{ alignSelf: 'flex-start' }}>Volver al texto pegado</Button>
      </>}
      {error && <Alert severity="error">{error}</Alert>}
    </Stack></DialogContent>
    <DialogActions><Button onClick={onClose} disabled={saving}>Cancelar</Button>{rows.length > 0 && <Button variant="contained" disabled={saving || !rows.some((row) => row.name.trim())} onClick={() => void save()}>{saving ? 'Guardando…' : `Guardar ${rows.length} registros`}</Button>}</DialogActions>
  </Dialog>
}

function StatusDialog({ record, csrfToken, onClose, onSaved }: {
  record: AllergyIntolerance | null; csrfToken: string; onClose: () => void; onSaved: () => void
}) {
  const [clinical, setClinical] = useState('active')
  const [verification, setVerification] = useState('confirmed')
  const [criticality, setCriticality] = useState('unable_to_assess')
  const [source, setSource] = useState('clinical_record')
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    if (!record) return
    setClinical(record.clinical_status || 'active'); setVerification(record.verification_status)
    setCriticality(record.criticality); setSource(record.source); setReason(''); setError(null)
  }, [record])
  async function save() {
    if (!record) return
    setSaving(true); setError(null)
    try {
      await apiRequest(`/allergy-intolerances/${record.id}/status`, {
        method: 'PATCH', body: JSON.stringify({
          version: record.version,
          clinical_status: verification === 'entered_in_error' ? null : clinical,
          verification_status: verification, criticality, source, reason,
        }),
      }, csrfToken)
      onSaved()
    } catch (caught) { setError(message(caught)) } finally { setSaving(false) }
  }
  return <Dialog open={Boolean(record)} onClose={saving ? undefined : onClose} fullWidth maxWidth="sm">
    <DialogTitle>Actualizar {record?.substance_name}</DialogTitle>
    <DialogContent dividers><Stack spacing={2}>
      <FormControl fullWidth disabled={verification === 'entered_in_error'}><InputLabel id="allergy-clinical">Estado clínico</InputLabel><Select labelId="allergy-clinical" label="Estado clínico" value={clinical} onChange={(e) => setClinical(e.target.value)}>{Object.entries(CLINICAL).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
      <FormControl fullWidth><InputLabel id="allergy-status-verification">Verificación</InputLabel><Select labelId="allergy-status-verification" label="Verificación" value={verification} onChange={(e) => setVerification(e.target.value)}>{Object.entries(VERIFICATION).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
      {verification === 'entered_in_error' && <Alert severity="warning">El registro permanecerá visible para trazabilidad, sin estado clínico y fuera de las alertas operacionales.</Alert>}
      <FormControl fullWidth><InputLabel id="allergy-status-criticality">Criticidad</InputLabel><Select labelId="allergy-status-criticality" label="Criticidad" value={criticality} onChange={(e) => setCriticality(e.target.value)}>{Object.entries(CRITICALITY).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
      <FormControl fullWidth><InputLabel id="allergy-status-source">Fuente</InputLabel><Select labelId="allergy-status-source" label="Fuente" value={source} onChange={(e) => setSource(e.target.value)}>{Object.entries(SOURCE).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
      <TextField label="Motivo del cambio" value={reason} onChange={(e) => setReason(e.target.value)} multiline minRows={3} required />
      {error && <Alert severity="error">{error}</Alert>}
    </Stack></DialogContent>
    <DialogActions><Button onClick={onClose} disabled={saving}>Cancelar</Button><Button variant="contained" disabled={saving || reason.trim().length < 3} onClick={() => void save()}>Guardar cambio</Button></DialogActions>
  </Dialog>
}

function ReactionDialog({ record, csrfToken, onClose, onSaved }: {
  record: AllergyIntolerance | null; csrfToken: string; onClose: () => void; onSaved: () => void
}) {
  const [manifestation, setManifestation] = useState('')
  const [severity, setSeverity] = useState('')
  const [route, setRoute] = useState('')
  const [note, setNote] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  useEffect(() => { if (record) { setManifestation(''); setSeverity(''); setRoute(''); setNote(''); setError(null) } }, [record])
  async function save() {
    if (!record) return
    setSaving(true); setError(null)
    try {
      await apiRequest(`/allergy-intolerances/${record.id}/reactions`, {
        method: 'POST', body: JSON.stringify({ manifestation, severity: severity || null, exposure_route: route || null, note: note || null }),
      }, csrfToken)
      onSaved()
    } catch (caught) { setError(message(caught)) } finally { setSaving(false) }
  }
  return <Dialog open={Boolean(record)} onClose={saving ? undefined : onClose} fullWidth maxWidth="sm">
    <DialogTitle>Agregar reacción a {record?.substance_name}</DialogTitle>
    <DialogContent dividers><Stack spacing={2}>
      <TextField autoFocus label="Manifestación" value={manifestation} onChange={(e) => setManifestation(e.target.value)} required />
      <FormControl fullWidth><InputLabel id="reaction-severity">Gravedad</InputLabel><Select labelId="reaction-severity" label="Gravedad" value={severity} onChange={(e) => setSeverity(e.target.value)}><MenuItem value="">No evaluada</MenuItem>{Object.entries(SEVERITY).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
      <TextField label="Vía de exposición (opcional)" value={route} onChange={(e) => setRoute(e.target.value)} />
      <TextField label="Nota clínica (opcional)" value={note} onChange={(e) => setNote(e.target.value)} multiline minRows={2} />
      {error && <Alert severity="error">{error}</Alert>}
    </Stack></DialogContent>
    <DialogActions><Button onClick={onClose} disabled={saving}>Cancelar</Button><Button variant="contained" disabled={saving || !manifestation.trim()} onClick={() => void save()}>Agregar reacción</Button></DialogActions>
  </Dialog>
}

function ReviewDialog({ admissionId, csrfToken, open, onClose, onSaved }: {
  admissionId: string; csrfToken: string; open: boolean; onClose: () => void; onSaved: () => void
}) {
  const [category, setCategory] = useState('all')
  const [assertion, setAssertion] = useState('no_known')
  const [source, setSource] = useState('patient')
  const [note, setNote] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  useEffect(() => { if (open) { setCategory('all'); setAssertion('no_known'); setSource('patient'); setNote(''); setError(null) } }, [open])
  async function save() {
    setSaving(true); setError(null)
    try {
      await apiRequest(`/admissions/${admissionId}/allergy-review-assertions`, {
        method: 'POST', body: JSON.stringify({ category, assertion, source, note: note || null }),
      }, csrfToken)
      onSaved()
    } catch (caught) { setError(message(caught)) } finally { setSaving(false) }
  }
  return <Dialog open={open} onClose={saving ? undefined : onClose} fullWidth maxWidth="sm">
    <DialogTitle>Registrar revisión de alergias</DialogTitle>
    <DialogContent dividers><Stack spacing={2}>
      <Alert severity="info">Una revisión explícita permite distinguir “sin antecedentes conocidos” de información aún no consultada.</Alert>
      <FormControl fullWidth><InputLabel id="review-category">Categoría revisada</InputLabel><Select labelId="review-category" label="Categoría revisada" value={category} onChange={(e) => setCategory(e.target.value)}>{Object.entries(CATEGORY).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
      <FormControl fullWidth><InputLabel id="review-result">Resultado</InputLabel><Select labelId="review-result" label="Resultado" value={assertion} onChange={(e) => setAssertion(e.target.value)}>{['no_known', 'information_unavailable', 'not_asked'].map((value) => <MenuItem key={value} value={value}>{REVIEW[value]}</MenuItem>)}</Select></FormControl>
      <FormControl fullWidth><InputLabel id="review-source">Fuente</InputLabel><Select labelId="review-source" label="Fuente" value={source} onChange={(e) => setSource(e.target.value)}>{Object.entries(SOURCE).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
      <TextField label="Observación (opcional)" value={note} onChange={(e) => setNote(e.target.value)} multiline minRows={2} />
      {error && <Alert severity="error">{error}</Alert>}
    </Stack></DialogContent>
    <DialogActions><Button onClick={onClose} disabled={saving}>Cancelar</Button><Button variant="contained" disabled={saving} onClick={() => void save()}>Registrar revisión</Button></DialogActions>
  </Dialog>
}

function AllergyHistory({ items }: { items: AllergyIntolerance[] }) {
  const changed = items.filter((item) => item.history.length > 1)
  if (!changed.length) return null
  return <Accordion disableGutters elevation={0} sx={{ border: 1, borderColor: 'divider', borderRadius: 2 }}>
    <AccordionSummary expandIcon={<ChevronDown size={17} />}><Typography fontWeight={750}>Historial de alergias e intolerancias</Typography></AccordionSummary>
    <AccordionDetails><Stack spacing={1.5}>{changed.map((item) => <Box key={item.id}>
      <Typography fontWeight={750}>{item.substance_name}</Typography>
      {[...item.history].reverse().map((event) => <Typography key={event.id} variant="caption" display="block" color="text.secondary">{formatDate(event.changed_at)} · {event.to_clinical_status ? CLINICAL[event.to_clinical_status] : 'Sin estado clínico'} · {VERIFICATION[event.to_verification_status]} · {event.reason}</Typography>)}
    </Box>)}</Stack></AccordionDetails>
  </Accordion>
}

export function AllergyIntoleranceSection({ admissionId, historical, csrfToken, onChanged }: {
  admissionId: string; historical: boolean; csrfToken: string; onChanged: () => void
}) {
  const [data, setData] = useState<AllergyContext | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [bulkOpen, setBulkOpen] = useState(false)
  const [reviewOpen, setReviewOpen] = useState(false)
  const [editing, setEditing] = useState<AllergyIntolerance | null>(null)
  const [reactionFor, setReactionFor] = useState<AllergyIntolerance | null>(null)
  const sequence = useRef(0)
  const load = useCallback(async () => {
    const current = ++sequence.current; setLoading(true); setError(null)
    try {
      const next = await apiRequest<AllergyContext>(`/admissions/${admissionId}/allergy-intolerances`)
      if (current === sequence.current) setData(next)
    } catch (caught) { if (current === sequence.current) setError(message(caught)) }
    finally { if (current === sequence.current) setLoading(false) }
  }, [admissionId])
  useEffect(() => { void load(); return () => { sequence.current += 1 } }, [load])
  const currentAssertions = useMemo(() => (data?.review_assertions ?? []).filter((item) => item.admission_id === admissionId), [admissionId, data])
  const latestReview = currentAssertions[0]
  const items = data?.items ?? []
  const afterSaved = () => {
    setBulkOpen(false); setReviewOpen(false); setEditing(null); setReactionFor(null)
    void load(); onChanged()
  }

  return <SectionCard title="Alergias e intolerancias" description="Registro longitudinal separado de diagnósticos, con reacciones múltiples, estado y trazabilidad.">
    {loading && !data ? <LoadingState label="Cargando alergias e intolerancias" rows={3} /> : error && !data ? <ErrorState message={error} onRetry={() => void load()} /> : data ? <Stack spacing={2}>
      {historical && <Alert severity="info">Episodio histórico · Solo lectura. Se muestra el estado longitudinal actual del paciente.</Alert>}
      {error && <Alert severity="error">{error}</Alert>}
      {latestReview ? <Alert severity={latestReview.assertion === 'no_known' ? 'success' : latestReview.assertion === 'information_unavailable' ? 'warning' : 'info'}>
        Última revisión de este ingreso: {CATEGORY[latestReview.category]} · {REVIEW[latestReview.assertion]} · {formatDate(latestReview.recorded_at)}
      </Alert> : <Alert severity="warning">Alergias e intolerancias aún no revisadas en este ingreso.</Alert>}
      {!historical && <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
        <Button variant="contained" startIcon={<Plus size={17} />} onClick={() => setBulkOpen(true)}>Agregar alergias o intolerancias</Button>
        <Button variant="outlined" onClick={() => setReviewOpen(true)}>Registrar revisión sin hallazgos</Button>
      </Stack>}
      {!items.length ? <EmptyState title="Sin registros estructurados" description="Registre una revisión explícita aunque el paciente no refiera alergias conocidas." /> : <TableContainer><Table size="small">
        <TableHead><TableRow><TableCell>Sustancia</TableCell><TableCell>Tipo</TableCell><TableCell>Estado</TableCell><TableCell>Criticidad</TableCell><TableCell>Reacciones</TableCell><TableCell align="right">Acciones</TableCell></TableRow></TableHead>
        <TableBody>{items.map((item) => <TableRow key={item.id} sx={item.verification_status === 'entered_in_error' ? { opacity: 0.6 } : undefined}>
          <TableCell><Typography fontWeight={750}>{item.substance_name}</Typography><Typography variant="caption" color="text.secondary">{CATEGORY[item.category]} · {SOURCE[item.source] || item.source}</Typography></TableCell>
          <TableCell>{item.allergy_type ? TYPE[item.allergy_type] : 'No determinado'}</TableCell>
          <TableCell><Chip size="small" variant="outlined" label={item.clinical_status ? CLINICAL[item.clinical_status] : VERIFICATION[item.verification_status]} /><Typography variant="caption" display="block" mt={0.5}>{VERIFICATION[item.verification_status]}</Typography></TableCell>
          <TableCell><Chip size="small" color={item.criticality === 'high' ? 'error' : 'default'} label={CRITICALITY[item.criticality]} /></TableCell>
          <TableCell>{item.reactions.length ? <Stack spacing={0.5}>{item.reactions.map((reaction) => <Typography variant="body2" key={reaction.id}>{reaction.manifestation}{reaction.severity ? ` · ${SEVERITY[reaction.severity]}` : ''}</Typography>)}</Stack> : 'Sin reacciones registradas'}</TableCell>
          <TableCell align="right"><Stack direction="row" justifyContent="flex-end"><IconButton aria-label={`Agregar reacción a ${item.substance_name}`} disabled={historical || item.verification_status === 'entered_in_error'} onClick={() => setReactionFor(item)}><Plus size={17} /></IconButton><IconButton aria-label={`Actualizar ${item.substance_name}`} disabled={historical} onClick={() => setEditing(item)}><Pencil size={17} /></IconButton></Stack></TableCell>
        </TableRow>)}</TableBody>
      </Table></TableContainer>}
      <AllergyHistory items={items} />
      <BulkDialog admissionId={admissionId} csrfToken={csrfToken} open={bulkOpen} onClose={() => setBulkOpen(false)} onSaved={afterSaved} />
      <ReviewDialog admissionId={admissionId} csrfToken={csrfToken} open={reviewOpen} onClose={() => setReviewOpen(false)} onSaved={afterSaved} />
      <StatusDialog record={editing} csrfToken={csrfToken} onClose={() => setEditing(null)} onSaved={afterSaved} />
      <ReactionDialog record={reactionFor} csrfToken={csrfToken} onClose={() => setReactionFor(null)} onSaved={afterSaved} />
    </Stack> : null}
  </SectionCard>
}

export function AllergySummaryAlert({ admissionId }: { admissionId: string }) {
  const [data, setData] = useState<AllergyContext | null>(null)
  const [loaded, setLoaded] = useState(false)
  useEffect(() => {
    let active = true; setLoaded(false)
    apiRequest<AllergyContext>(`/admissions/${admissionId}/allergy-intolerances`)
      .then((next) => { if (active) setData(next) }).catch(() => { if (active) setData(null) })
      .finally(() => { if (active) setLoaded(true) })
    return () => { active = false }
  }, [admissionId])
  if (!loaded) return <Alert severity="info">Cargando alertas de alergias…</Alert>
  if (!data) return <Alert severity="error">No fue posible verificar alergias e intolerancias.</Alert>
  const activeItems = (data.items ?? []).filter((item) => item.clinical_status === 'active' && !['refuted', 'entered_in_error'].includes(item.verification_status))
  if (!activeItems.length) {
    const latestOverallReview = (data.review_assertions ?? []).find((item) =>
      item.admission_id === admissionId && item.category === 'all')
    const reviewed = latestOverallReview?.assertion === 'no_known'
    return <Alert severity={reviewed ? 'success' : 'warning'}>{reviewed ? 'Sin alergias o intolerancias conocidas (revisión registrada).' : 'Alergias e intolerancias pendientes de revisar en este ingreso.'}</Alert>
  }
  return <Alert severity={activeItems.some((item) => item.criticality === 'high') ? 'error' : 'warning'} icon={<ShieldAlert aria-hidden="true" />}>
    <Typography fontWeight={800}>Alergias/intolerancias activas</Typography>
    <Stack direction="row" useFlexGap flexWrap="wrap" gap={0.75} mt={0.75}>{activeItems.map((item) => <Chip key={item.id} size="small" label={`${item.substance_name} · ${CRITICALITY[item.criticality]}`} />)}</Stack>
  </Alert>
}

export function FoodSafetyAllergyPanel({ admissionId }: { admissionId: string }) {
  const [data, setData] = useState<FoodSafetyAllergyProjection | null>(null)
  const [loaded, setLoaded] = useState(false)
  useEffect(() => {
    let active = true; setLoaded(false)
    apiRequest<FoodSafetyAllergyProjection>(`/admissions/${admissionId}/food-safety-allergies`)
      .then((next) => { if (active) setData(next) }).catch(() => { if (active) setData(null) })
      .finally(() => { if (active) setLoaded(true) })
    return () => { active = false }
  }, [admissionId])
  if (!loaded) return <Alert severity="info">Verificando riesgos alimentarios…</Alert>
  if (!data) return <Alert severity="error">No fue posible verificar riesgos alimentarios. No liberar preparación hasta confirmar.</Alert>
  if (data.review_status === 'active_food_risks') return <Alert severity={data.items.some((item) => item.criticality === 'high') ? 'error' : 'warning'}>
    <Typography fontWeight={850}>Riesgo alimentario activo</Typography>
    {data.items.map((item) => <Box key={item.id} mt={0.75}><Typography fontWeight={750}>{item.substance_name} · {item.allergy_type ? TYPE[item.allergy_type] : 'Tipo no determinado'} · criticidad {CRITICALITY[item.criticality].toLocaleLowerCase()}</Typography>{item.reactions.map((reaction, index) => <Typography variant="caption" display="block" key={`${item.id}-${index}`}>Reacción: {reaction.manifestation}{reaction.severity ? ` (${SEVERITY[reaction.severity].toLocaleLowerCase()})` : ''}</Typography>)}</Box>)}
  </Alert>
  const states = {
    no_known: ['success', 'Sin alergias alimentarias conocidas (revisión registrada).'],
    not_reviewed: ['warning', 'Alergias alimentarias no revisadas. Confirmar antes de liberar la alimentación.'],
    information_unavailable: ['warning', 'Información de alergias alimentarias no disponible. Confirmar antes de liberar la alimentación.'],
    no_active_food_risks: ['info', 'Sin riesgos alimentarios activos; existen hallazgos históricos o resueltos.'],
  } as const
  const [severity, label] = states[data.review_status]
  return <Alert severity={severity}>{label}</Alert>
}
