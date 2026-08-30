import {
  Alert,
  Box,
  Breadcrumbs,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  FormControl,
  InputLabel,
  Link,
  MenuItem,
  Pagination,
  Select,
  Stack,
  Tab,
  Tabs,
  Typography,
} from '@mui/material'
import Grid from '@mui/material/Grid2'
import {
  ArrowLeft,
  ArrowRightLeft,
  BedDouble,
  Clock3,
  UserRound,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  SectionCard,
} from '../../shared/components'
import {
  AdmissionStatus,
  ApiError,
  apiRequest,
  OperationalTimeline,
  OperationalTimelineEvent,
  PatientChartAdmission,
  PatientChartSummary,
  Admission,
  HospitalStructure,
} from '../../shared/services/api'
import { IdentityDialog, LocationDialog } from './PatientsDashboard'
import { MovePatientDialog } from '../transfers/Transfers'
import { NutritionClinicalTab, NutritionSummaryCard } from './NutritionClinicalTabs'
import { ClinicalContextSummaryCard, ClinicalContextTab } from './ClinicalContextTab'
import { AllergySummaryAlert } from './AllergyIntoleranceSection'
import { ActiveTreatmentsTab } from './ActiveTreatmentsTab'
import { MealPlanTab } from './MealPlanTab'

const CANONICAL_TABS = [
  'summary',
  'clinical-context',
  'treatments',
  'care',
  'assessment',
  'prescription',
  'meal-plan',
  'intake',
  'labs',
  'nitrogen-balance',
  'hourly-sheet',
  'logbook',
  'movements',
  'history',
] as const

type ChartTab = typeof CANONICAL_TABS[number]

const TAB_LABELS: Record<ChartTab, string> = {
  summary: 'Resumen',
  'clinical-context': 'Diagnósticos y antecedentes',
  treatments: 'Tratamientos activos',
  care: 'Evolución nutricional',
  assessment: 'Evaluación',
  prescription: 'Prescripción',
  'meal-plan': 'Minuta diaria',
  intake: 'Ingesta',
  labs: 'Exámenes',
  'nitrogen-balance': 'Balance nitrogenado',
  'hourly-sheet': 'Hoja horaria',
  logbook: 'Bitácora',
  movements: 'Movimientos',
  history: 'Historial',
}

const CLINICAL_TABS = new Set<ChartTab>([
  'clinical-context', 'treatments', 'care', 'assessment', 'prescription', 'meal-plan', 'intake', 'labs',
  'nitrogen-balance', 'hourly-sheet', 'logbook',
])

const PLACEHOLDERS: Record<Exclude<ChartTab, 'summary' | 'clinical-context' | 'treatments' | 'movements' | 'history'>, { title: string; description: string }> = {
  care: {
    title: 'Evolución nutricional',
    description: 'Una atención será una instancia temporal de trabajo nutricional vinculada al episodio. Podrá agrupar evaluaciones, cambios de prescripción, revisiones de ingesta o notas relacionadas. No implica presencia física y no registra modalidad presencial o remota.',
  },
  assessment: {
    title: 'Evaluación nutricional',
    description: 'Aquí se implementará la evaluación clínica estructurada, sus cálculos, tamizajes, diagnósticos PES, firma y versiones, siempre vinculada al episodio seleccionado.',
  },
  prescription: {
    title: 'Prescripción nutricional',
    description: 'Este módulo concentrará la prescripción vigente y será la futura fuente de verdad operacional para regímenes y raciones.',
  },
  'meal-plan': {
    title: 'Minuta diaria',
    description: 'Selección combinable de bandejas y preparaciones modulares para Alimentación.',
  },
  intake: {
    title: 'Control de ingesta',
    description: 'Registro de lo efectivamente consumido por el paciente.',
  },
  labs: {
    title: 'Exámenes',
    description: 'Este módulo presentará resultados relevantes fechados y trazables, sin mezclar datos clínicos en observaciones libres.',
  },
  'nitrogen-balance': {
    title: 'Balance nitrogenado',
    description: 'Aquí se calculará y conservará el balance nitrogenado cuando estén disponibles los datos requeridos.',
  },
  'hourly-sheet': {
    title: 'Hoja horaria',
    description: 'Este módulo permitirá revisar información nutricional organizada por hora dentro del episodio.',
  },
  logbook: {
    title: 'Bitácora de continuidad profesional',
    description: 'Servirá para coordinación del equipo, pendientes e incidencias operacionales. No reemplazará evaluaciones, diagnósticos, prescripciones, ingesta ni movimientos, y será independiente de la auditoría técnica.',
  },
}

const ADMISSION_LABELS: Record<AdmissionStatus, string> = {
  active: 'Activo',
  discharged: 'Alta',
  deceased: 'Fallecido',
  closed: 'Cerrado',
}

function requestError(error: unknown): string {
  return error instanceof ApiError ? error.message : 'No fue posible cargar la ficha del paciente.'
}

function formatDate(value: string | null, includeTime = false): string {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, includeTime
    ? { dateStyle: 'medium', timeStyle: 'short' }
    : { dateStyle: 'medium' }).format(new Date(value))
}

function formatRut(rut: string | null): string {
  if (!rut) return 'Sin RUT confirmado'
  const [body, digit] = rut.split('-')
  return `${body.replace(/\B(?=(\d{3})+(?!\d))/g, '.')}-${digit}`
}

function locationLabel(location: PatientChartAdmission['location']): string {
  if (!location) return 'Sin cama asignada'
  return [location.service_name, location.room_name, location.care_unit_label || location.care_unit_code]
    .filter(Boolean).join(' · ')
}

function timelineLocation(location: OperationalTimelineEvent['origin']): string {
  if (!location) return ''
  return [location.service_name, location.room_name, location.care_unit_label || location.care_unit_code]
    .filter(Boolean).join(' · ')
}

function chartPath(
  patientId: string,
  tab: ChartTab,
  admissionId: string | null,
  returnTo: string,
): string {
  const params = new URLSearchParams()
  if (admissionId) params.set('admission_id', admissionId)
  if (returnTo !== '/patients') params.set('return_to', returnTo)
  const query = params.toString()
  return `/patients/${patientId}/${tab}${query ? `?${query}` : ''}`
}

function Detail({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      <Typography>{value === null || value === undefined || value === '' ? '—' : value}</Typography>
    </Box>
  )
}

function TimelineList({ events }: { events: OperationalTimelineEvent[] }) {
  return (
    <Stack divider={<Divider flexItem />}>
      {events.map((event) => (
        <Stack key={event.id} direction="row" spacing={1.5} sx={{ py: 1.5 }}>
          <Box sx={{ color: 'primary.main', pt: 0.25 }}><Clock3 size={18} aria-hidden="true" /></Box>
          <Box sx={{ minWidth: 0 }}>
            <Typography fontWeight={780}>{event.title}</Typography>
            <Typography variant="body2">{event.description}</Typography>
            {event.reason && <Typography variant="body2" color="text.secondary">Motivo: {event.reason}</Typography>}
            {event.origin && <Typography variant="caption" display="block">Origen: {timelineLocation(event.origin)}</Typography>}
            {event.destination && <Typography variant="caption" display="block">Destino: {timelineLocation(event.destination)}</Typography>}
            <Typography variant="caption" color="text.secondary">{formatDate(event.occurred_at, true)}</Typography>
          </Box>
        </Stack>
      ))}
    </Stack>
  )
}

function SummaryTab({ summary, showNutrition }: { summary: PatientChartSummary, showNutrition: boolean }) {
  const admission = summary.selected_admission
  return (
    <Stack spacing={2.5}>
      {!admission ? (
        <Alert severity="info">El paciente no tiene hospitalizaciones. La identidad longitudinal permanece disponible.</Alert>
      ) : admission.status === 'active' && !admission.location ? (
        <Alert severity="warning">Hospitalización activa sin cama asignada.</Alert>
      ) : null}
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <SectionCard title="Identificación">
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6 }}><Detail label="Nombre" value={summary.patient.display_name} /></Grid>
              <Grid size={{ xs: 12, sm: 6 }}><Detail label="Estado de identidad" value={summary.patient.identity_status} /></Grid>
              <Grid size={{ xs: 12, sm: 6 }}><Detail label="RUT" value={formatRut(summary.patient.rut)} /></Grid>
              <Grid size={{ xs: 12, sm: 6 }}><Detail label="Identificador temporal" value={summary.patient.temporary_identifier} /></Grid>
              <Grid size={{ xs: 12, sm: 6 }}><Detail label="N.º de ficha" value={summary.patient.hospital_identifier} /></Grid>
              <Grid size={{ xs: 12, sm: 6 }}><Detail label="Edad actual" value={summary.patient.current_age.display} /></Grid>
              <Grid size={{ xs: 12, sm: 6 }}><Detail label="Sexo" value={summary.patient.sex} /></Grid>
              <Grid size={{ xs: 12, sm: 6 }}><Detail label="Teléfono" value={summary.patient.phone} /></Grid>
            </Grid>
          </SectionCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <SectionCard title="Episodio seleccionado">
            {admission ? (
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6 }}><Detail label="Ingreso" value={admission.admission_identifier} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><Detail label="Estado" value={ADMISSION_LABELS[admission.status]} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><Detail label="Fecha de ingreso" value={formatDate(admission.admitted_at, true)} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><Detail label="Edad al ingreso" value={admission.age_at_admission.display} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><Detail label="Término" value={formatDate(admission.ended_at, true)} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><Detail label="Duración" value={`${admission.duration_days} días`} /></Grid>
                <Grid size={{ xs: 12 }}><Detail label="Motivo de término" value={admission.end_reason} /></Grid>
                <Grid size={{ xs: 12 }}><Detail label={admission.is_historical ? 'Última ubicación' : 'Ubicación actual'} value={locationLabel(admission.location)} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><Detail label="Estado de cama" value={admission.bed_status} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><Detail label="Hospitalizaciones totales" value={summary.total_admissions} /></Grid>
              </Grid>
            ) : <Typography color="text.secondary">Sin episodios registrados.</Typography>}
          </SectionCard>
        </Grid>
      </Grid>
      {admission?.open_transfer && (
        <Alert severity="info" icon={<ArrowRightLeft aria-hidden="true" />}>
          Traslado pendiente hacia {admission.open_transfer.destination_service_name} · estado {admission.open_transfer.status}.
          El paciente permanece en su ubicación de origen hasta la asignación efectiva.
        </Alert>
      )}
      {showNutrition && admission ? <AllergySummaryAlert admissionId={admission.id} /> : null}
      <SectionCard title="Últimos movimientos" description="Vista breve del episodio seleccionado.">
        {summary.recent_operational_events.length
          ? <TimelineList events={summary.recent_operational_events} />
          : <EmptyState title="Sin movimientos" description="El episodio no tiene movimientos operacionales registrados." />}
      </SectionCard>
      {showNutrition && admission ? <ClinicalContextSummaryCard admissionId={admission.id} /> : null}
      {showNutrition && admission ? <NutritionSummaryCard admissionId={admission.id} /> : null}
    </Stack>
  )
}

function MovementsTab({ admissionId }: { admissionId: string | null }) {
  const [timeline, setTimeline] = useState<OperationalTimeline | null>(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(Boolean(admissionId))
  const [error, setError] = useState<string | null>(null)
  const sequence = useRef(0)
  const cache = useRef(new Map<string, OperationalTimeline>())

  const load = useCallback(async (nextPage: number, force = false) => {
    if (!admissionId) return
    const key = `${admissionId}:${nextPage}`
    const current = ++sequence.current
    setLoading(true)
    setError(null)
    try {
      const next = !force && cache.current.get(key)
        ? cache.current.get(key)!
        : await apiRequest<OperationalTimeline>(`/admissions/${admissionId}/operational-timeline?page=${nextPage}&page_size=20`)
      if (current !== sequence.current) return
      cache.current.set(key, next)
      setTimeline(next)
    } catch (caught) {
      if (current === sequence.current) setError(requestError(caught))
    } finally {
      if (current === sequence.current) setLoading(false)
    }
  }, [admissionId])

  useEffect(() => {
    setPage(1)
    setTimeline(null)
    if (admissionId) void load(1)
    return () => { sequence.current += 1 }
  }, [admissionId, load])

  if (!admissionId) return <EmptyState title="Sin episodio" description="Seleccione una hospitalización para consultar sus movimientos." />
  return (
    <SectionCard title="Movimientos operacionales" description="Línea temporal de solo lectura derivada de hospitalización, ubicaciones y traslados.">
      {error && <ErrorState message={error} onRetry={() => void load(page, true)} />}
      {loading && !timeline ? <LoadingState label="Cargando movimientos" rows={3} /> : !timeline?.items.length ? (
        <EmptyState title="Sin movimientos" description="No existen eventos para el episodio seleccionado." />
      ) : (
        <Stack spacing={2}>
          <TimelineList events={timeline.items} />
          {timeline.total > timeline.page_size && (
            <Pagination
              page={page}
              count={Math.ceil(timeline.total / timeline.page_size)}
              onChange={(_, next) => { setPage(next); void load(next) }}
            />
          )}
        </Stack>
      )}
    </SectionCard>
  )
}

function HistoryTab({
  admissions,
  onSelect,
}: {
  admissions: PatientChartAdmission[]
  onSelect: (admissionId: string) => void
}) {
  if (!admissions.length) return <EmptyState title="Sin hospitalizaciones" description="La identidad del paciente existe, pero todavía no tiene episodios." />
  return (
    <Stack spacing={1.5}>
      {admissions.map((admission) => (
        <Card key={admission.id} variant="outlined">
          <CardContent>
              <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={2}>
                <Box>
                  <Typography fontWeight={820}>{admission.admission_identifier}</Typography>
                  <Typography variant="body2">{formatDate(admission.admitted_at)} — {formatDate(admission.ended_at)}</Typography>
                  <Typography variant="body2" color="text.secondary">{locationLabel(admission.location)}</Typography>
                  {admission.end_reason && <Typography variant="body2">Motivo de término: {admission.end_reason}</Typography>}
                </Box>
                <Stack alignItems={{ xs: 'flex-start', sm: 'flex-end' }} spacing={1}>
                  <Chip label={admission.is_historical ? 'Histórico' : 'Activo'} size="small" variant="outlined" />
                  <Typography variant="caption">{admission.duration_days} días</Typography>
                  <Button size="small" onClick={() => onSelect(admission.id)}>Ver episodio</Button>
                </Stack>
              </Stack>
          </CardContent>
        </Card>
      ))}
    </Stack>
  )
}

export function PatientChartPage({
  patientId,
  requestedTab,
  search,
  roles,
  csrfToken,
  onNavigate,
}: {
  patientId: string
  requestedTab: string
  search: string
  roles: string[]
  csrfToken: string
  onNavigate: (path: string, replace?: boolean) => void
}) {
  const params = useMemo(() => new URLSearchParams(search), [search])
  const requestedAdmissionId = params.get('admission_id')
  const returnTo = params.get('return_to') || '/patients'
  const isAdminOnly = roles.includes('administrador') && !roles.some((role) => role === 'jefatura' || role === 'nutricionista')
  const allowedTabs = useMemo(() => CANONICAL_TABS.filter((tab) => !(isAdminOnly && CLINICAL_TABS.has(tab))), [isAdminOnly])
  const tab = allowedTabs.includes(requestedTab as ChartTab) ? requestedTab as ChartTab : 'summary'
  const [summary, setSummary] = useState<PatientChartSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [detail, setDetail] = useState<import('../../shared/services/api').Patient | null>(null)
  const [structure, setStructure] = useState<HospitalStructure | null>(null)
  const [activeAdmissions, setActiveAdmissions] = useState<Admission[]>([])
  const [identityOpen, setIdentityOpen] = useState(false)
  const [locationOpen, setLocationOpen] = useState(false)
  const [moveOpen, setMoveOpen] = useState(false)
  const sequence = useRef(0)
  const canMutate = roles.some((role) => role === 'jefatura' || role === 'nutricionista')
  const canReadClinical = canMutate

  const load = useCallback(async () => {
    const current = ++sequence.current
    setLoading(true)
    setError(null)
    try {
      const query = requestedAdmissionId ? `?admission_id=${encodeURIComponent(requestedAdmissionId)}` : ''
      const next = await apiRequest<PatientChartSummary>(`/patients/${patientId}/chart-summary${query}`)
      if (current !== sequence.current) return
      setSummary(next)
      if (canMutate && !next.patient.merged_into_patient_id && !next.selected_admission?.is_historical) {
        const [patientDetail, hospital, admissions] = await Promise.all([
          apiRequest<import('../../shared/services/api').Patient>(`/patients/${patientId}`),
          apiRequest<HospitalStructure>('/hospital/structure'),
          apiRequest<{ items: Admission[] }>('/admissions/active'),
        ])
        if (current !== sequence.current) return
        setDetail(patientDetail)
        setStructure(hospital)
        setActiveAdmissions(admissions.items ?? [])
      } else {
        setDetail(null)
        setStructure(null)
        setActiveAdmissions([])
      }
      if (!requestedAdmissionId && next.selected_admission) {
        onNavigate(chartPath(patientId, tab, next.selected_admission.id, returnTo), true)
      }
    } catch (caught) {
      if (current === sequence.current) setError(requestError(caught))
    } finally {
      if (current === sequence.current) setLoading(false)
    }
  }, [canMutate, onNavigate, patientId, requestedAdmissionId, returnTo, tab])

  useEffect(() => {
    if (requestedTab !== tab) {
      onNavigate(chartPath(patientId, 'summary', requestedAdmissionId, returnTo), true)
      return
    }
    void load()
    return () => { sequence.current += 1 }
  }, [load, onNavigate, patientId, requestedAdmissionId, requestedTab, returnTo, tab])

  if (loading && !summary) return <LoadingState label="Cargando ficha del paciente" rows={5} />
  if (error && !summary) return <ErrorState message={error} onRetry={() => void load()} />
  if (!summary) return null

  const admission = summary.selected_admission
  const merged = Boolean(summary.patient.merged_into_patient_id)
  const selectedDetailAdmission = detail?.admissions?.find((item) => item.id === admission?.id)
    ?? (detail && detail.active_admission?.id === admission?.id ? detail.active_admission : null)
  const beds = structure?.items?.flatMap((service) => service.rooms.flatMap((room) =>
    room.care_units.filter((unit) => unit.unit_type === 'bed' && unit.is_active).map((unit) => ({
      ...unit,
      roomName: room.name,
      serviceName: service.name,
    })),
  )) ?? []
  const occupied = new Map(activeAdmissions
    .filter((item) => item.current_location)
    .map((item) => [item.current_location!.care_unit_id, item.admission_identifier]))
  const canAct = canMutate && !merged && Boolean(detail) && (!admission || !admission.is_historical)

  async function createAdmission() {
    await apiRequest('/admissions', { method: 'POST', body: JSON.stringify({ patient_id: patientId }) }, csrfToken)
    await load()
  }

  async function endAdmission() {
    if (!admission || !window.confirm('¿Confirma el término de esta hospitalización? La cama vigente será liberada.')) return
    await apiRequest(
      `/admissions/${admission.id}/status`,
      { method: 'PATCH', body: JSON.stringify({ status: 'discharged', reason: 'Alta registrada desde ficha de paciente.' }) },
      csrfToken,
    )
    await load()
  }
  const selectedPlaceholder = tab === 'nitrogen-balance' || tab === 'hourly-sheet' || tab === 'logbook'
    ? PLACEHOLDERS[tab]
    : null

  return (
    <Stack spacing={2.5}>
      <Breadcrumbs aria-label="Ruta de navegación">
        <Link component="button" underline="hover" onClick={() => onNavigate(returnTo)}>Pacientes</Link>
        <Typography color="text.primary">{summary.patient.display_name}</Typography>
        <Typography color="text.primary">{TAB_LABELS[tab]}</Typography>
      </Breadcrumbs>
      <PageHeader
        eyebrow="Ficha longitudinal"
        title={summary.patient.display_name}
        description={`${formatRut(summary.patient.rut)} · ${summary.patient.current_age.display}`}
        actions={(
          <Stack direction="row" useFlexGap flexWrap="wrap" gap={1}>
            <Button startIcon={<ArrowLeft size={17} />} onClick={() => onNavigate(returnTo)}>Volver al listado</Button>
            {canAct && detail && detail.identity_status !== 'identified' && (
              <Button variant="outlined" onClick={() => setIdentityOpen(true)}>Identificar paciente</Button>
            )}
            {canAct && !admission && (
              <Button variant="contained" onClick={() => void createAdmission()}>Crear hospitalización</Button>
            )}
            {canAct && admission?.status === 'active' && selectedDetailAdmission && (
              <>
                <Button variant="outlined" onClick={() => admission.location ? setMoveOpen(true) : setLocationOpen(true)}>
                  {admission.location ? 'Mover paciente' : 'Asignar cama inicial'}
                </Button>
                <Button color="error" onClick={() => void endAdmission()}>Terminar hospitalización</Button>
              </>
            )}
          </Stack>
        )}
      />
      {merged && (
        <Alert severity="warning" action={(
          <Button
            color="inherit"
            onClick={() => onNavigate(chartPath(summary.patient.merged_into_patient_id!, tab, null, returnTo))}
          >
            Abrir ficha canónica
          </Button>
        )}>
          Esta ficha fue conciliada con otra ficha canónica y permanece disponible sólo para trazabilidad.
        </Alert>
      )}
      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2}>
            <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" gap={2}>
              <Stack direction="row" spacing={1.25} alignItems="center">
                <Box sx={{ color: 'primary.main' }}><UserRound aria-hidden="true" /></Box>
                <Box>
                  <Typography fontWeight={850}>{summary.patient.display_name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Ficha {summary.patient.hospital_identifier || 'sin número'} · {summary.patient.identity_status}
                  </Typography>
                </Box>
              </Stack>
              <FormControl size="small" sx={{ minWidth: { xs: '100%', sm: 330 } }}>
                <InputLabel id="episode-selector-label">Episodio</InputLabel>
                <Select
                  labelId="episode-selector-label"
                  label="Episodio"
                  value={admission?.id ?? ''}
                  disabled={!summary.admissions.length}
                  onChange={(event) => onNavigate(chartPath(patientId, tab, event.target.value, returnTo))}
                >
                  {summary.admissions.map((item) => (
                    <MenuItem key={item.id} value={item.id}>
                      {item.admission_identifier} · {formatDate(item.admitted_at)} · {ADMISSION_LABELS[item.status]} · {locationLabel(item.location)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Stack>
            <Divider />
            <Stack direction="row" useFlexGap flexWrap="wrap" gap={1.5} alignItems="center">
              <Chip label={summary.patient.current_age.display} variant="outlined" />
              <Chip label={admission ? ADMISSION_LABELS[admission.status] : 'Sin episodio'} variant="outlined" />
              <Chip icon={<BedDouble size={15} />} label={admission ? locationLabel(admission.location) : 'Sin ubicación'} variant="outlined" />
              {admission?.open_transfer && <Chip icon={<ArrowRightLeft size={15} />} label={`Traslado · ${admission.open_transfer.destination_service_code}`} variant="outlined" />}
              {admission?.is_historical && <Chip label="Episodio histórico · Solo lectura" size="small" variant="outlined" />}
            </Stack>
          </Stack>
        </CardContent>
      </Card>
      {error && <ErrorState message={error} onRetry={() => void load()} />}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', maxWidth: '100%', overflowX: 'auto' }}>
        <Tabs
          value={tab}
          variant="scrollable"
          scrollButtons="auto"
          aria-label="Secciones de la ficha"
          onChange={(_, next: ChartTab) => onNavigate(chartPath(patientId, next, admission?.id ?? null, returnTo))}
        >
          {allowedTabs.map((item) => <Tab key={item} value={item} label={TAB_LABELS[item]} />)}
        </Tabs>
      </Box>
      {tab === 'summary' ? <SummaryTab summary={summary} showNutrition={canReadClinical} /> : null}
      {canReadClinical && admission && tab === 'clinical-context' ? (
        <ClinicalContextTab
          admissionId={admission.id}
          patientId={summary.patient.id}
          historical={admission.is_historical}
          csrfToken={csrfToken}
          onChanged={() => void load()}
        />
      ) : null}
      {canReadClinical && admission && tab === 'treatments' ? (
        <ActiveTreatmentsTab
          admissionId={admission.id}
          historical={admission.is_historical}
          csrfToken={csrfToken}
        />
      ) : null}
      {canReadClinical && admission && ['care', 'assessment', 'prescription', 'intake', 'labs'].includes(tab) ? (
        <NutritionClinicalTab
          tab={tab as 'care' | 'assessment' | 'prescription' | 'intake' | 'labs'}
          admissionId={admission.id}
          historical={admission.is_historical}
          csrfToken={csrfToken}
          patientDateOfBirth={summary.patient.date_of_birth}
          patientAgeIsEstimated={summary.patient.date_of_birth_is_estimated}
          onChanged={() => void load()}
        />
      ) : null}
      {canReadClinical && admission && tab === 'meal-plan' ? (
        <MealPlanTab admissionId={admission.id} historical={admission.is_historical} csrfToken={csrfToken} />
      ) : null}
      {tab === 'movements' ? <MovementsTab admissionId={admission?.id ?? null} /> : null}
      {tab === 'history' ? (
        <HistoryTab
          admissions={summary.admissions}
          onSelect={(admissionId) => onNavigate(chartPath(patientId, 'summary', admissionId, returnTo))}
        />
      ) : null}
      {selectedPlaceholder ? (
        <SectionCard title={selectedPlaceholder.title} description={admission ? `Episodio ${admission.admission_identifier}` : undefined}>
          {!admission ? (
            <EmptyState title="Seleccione un episodio" description="Este módulo estará contextualizado por hospitalización." />
          ) : (
            <Stack spacing={2}>
              {admission.is_historical && <Alert severity="info">Episodio histórico · Solo lectura</Alert>}
              <Typography>{selectedPlaceholder.description}</Typography>
              <Alert severity="info">No disponible en NutriWard en esta fase</Alert>
            </Stack>
          )}
        </SectionCard>
      ) : null}
      {identityOpen && detail && (
        <IdentityDialog
          csrfToken={csrfToken}
          patient={detail}
          canResolveActiveConflicts={roles.includes('jefatura')}
          onClose={() => setIdentityOpen(false)}
          onUpdated={() => { setIdentityOpen(false); void load() }}
        />
      )}
      {locationOpen && selectedDetailAdmission && (
        <LocationDialog
          admission={selectedDetailAdmission}
          beds={beds}
          occupied={occupied}
          csrfToken={csrfToken}
          onClose={() => setLocationOpen(false)}
          onUpdated={() => { setLocationOpen(false); void load() }}
        />
      )}
      {moveOpen && selectedDetailAdmission && structure && (
        <MovePatientDialog
          open
          admission={selectedDetailAdmission}
          services={structure.items}
          csrfToken={csrfToken}
          onClose={() => setMoveOpen(false)}
          onCompleted={() => { setMoveOpen(false); void load() }}
        />
      )}
    </Stack>
  )
}
