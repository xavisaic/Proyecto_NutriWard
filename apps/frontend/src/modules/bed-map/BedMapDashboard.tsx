import {
  Alert,
  Box,
  Button,
  ButtonBase,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Drawer,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Typography,
} from '@mui/material'
import { ArrowRightLeft, BedDouble, CheckCircle2, CircleAlert, RefreshCw, UserRound, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { FeedbackSnackbar, LoadingState, PageHeader, StatCard, StatusBadge } from '../../shared/components'
import {
  ApiError,
  apiRequest,
  BedMap,
  BedMapBed,
  BedMapRoom,
  HospitalService,
  HospitalStructure,
  IdentityStatus,
  NutritionistServiceAssignmentList,
} from '../../shared/services/api'
import { MovePatientDialog, ReceptionTray } from '../transfers/Transfers'

const REFRESH_INTERVAL_MS = 45_000
const ALL_ROOMS = 'all'
const SERVICE_PREFERENCE_PREFIX = 'nutriward:bed-map:service:'

interface BedMapDashboardProps {
  userId?: string
  isNutritionist?: boolean
  canMutateTransfers?: boolean
  csrfToken?: string
  onOpenPatient?: (patientId: string, admissionId?: string) => void
}

const identityLabels: Record<IdentityStatus, string> = {
  identified: 'Identificado',
  provisional: 'Provisorio',
  unidentified: 'Paciente NN',
}

function requestError(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : 'No fue posible cargar el mapa de camas.'
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function updatedAgo(value: string, now: number): string {
  const seconds = Math.max(0, Math.floor((now - new Date(value).getTime()) / 1000))
  if (seconds < 10) return 'Actualizado hace unos segundos'
  if (seconds < 60) return `Actualizado hace ${seconds} segundos`
  const minutes = Math.floor(seconds / 60)
  return `Actualizado hace ${minutes} ${minutes === 1 ? 'minuto' : 'minutos'}`
}

function transferElapsed(value: string): string {
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60_000))
  if (minutes < 1) return 'Solicitado hace menos de un minuto'
  if (minutes < 60) return `Solicitado hace ${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `Solicitado hace ${hours} h`
  const days = Math.floor(hours / 24)
  return `Solicitado hace ${days} ${days === 1 ? 'día' : 'días'}`
}

function pendingTransferLabel(transfer: NonNullable<NonNullable<BedMapBed['occupancy']>['pending_transfer']>): string {
  return transfer.status === 'pending_reception'
    ? `Traslado solicitado · ${transfer.destination_service_code}`
    : `Aceptado · espera cama · ${transfer.destination_service_code}`
}

function bedTitle(bed: BedMapBed): string {
  return bed.label || `Cama ${bed.code}`
}

function accessibleBedLabel(bed: BedMapBed): string {
  const title = bedTitle(bed)
  const pendingTransfer = bed.occupancy?.pending_transfer
  return bed.occupancy
    ? `${title}, ocupada por ${bed.occupancy.patient.display_name}${pendingTransfer ? `, ${pendingTransferLabel(pendingTransfer)}` : ''}`
    : `${title}, libre`
}

function overlaps(first: BedMapBed, second: BedMapBed): boolean {
  const a = first.layout!
  const b = second.layout!
  return (
    a.grid_x < b.grid_x + b.width
    && a.grid_x + a.width > b.grid_x
    && a.grid_y < b.grid_y + b.height
    && a.grid_y + a.height > b.grid_y
  )
}

export function classifyRoomBeds(room: BedMapRoom) {
  const configured = room.beds.filter((bed) => bed.layout)
  const conflictingIds = new Set<string>()
  configured.forEach((bed, index) => {
    configured.slice(index + 1).forEach((candidate) => {
      if (overlaps(bed, candidate)) {
        conflictingIds.add(bed.id)
        conflictingIds.add(candidate.id)
      }
    })
  })
  return {
    positioned: configured.filter((bed) => !conflictingIds.has(bed.id)),
    unpositioned: room.beds.filter((bed) => !bed.layout),
    conflicting: configured.filter((bed) => conflictingIds.has(bed.id)),
  }
}

function BedBlock({
  bed,
  positioned = false,
  selected = false,
  onSelect,
  registerTrigger,
}: {
  bed: BedMapBed
  positioned?: boolean
  selected?: boolean
  onSelect: (bed: BedMapBed) => void
  registerTrigger: (bedId: string, element: HTMLButtonElement | null) => void
}) {
  const occupied = bed.status === 'occupied' && bed.occupancy
  const pendingTransfer = occupied ? occupied.pending_transfer : null
  const layout = bed.layout

  return (
    <ButtonBase
      ref={(element) => registerTrigger(bed.id, element)}
      aria-label={accessibleBedLabel(bed)}
      aria-pressed={occupied ? selected : undefined}
      onClick={() => occupied && onSelect(bed)}
      style={positioned && layout ? {
        gridColumn: `${layout.grid_x + 1} / span ${layout.width}`,
        gridRow: `${layout.grid_y + 1} / span ${layout.height}`,
      } : undefined}
      sx={{
        display: 'block',
        width: '100%',
        minHeight: 116,
        textAlign: 'left',
        border: '2px solid',
        borderColor: selected ? 'primary.main' : occupied ? 'warning.dark' : 'success.dark',
        borderRadius: 2,
        bgcolor: (theme) => selected
          ? theme.nutriward.colors.operational.bedSelected.background
          : occupied
            ? theme.nutriward.colors.operational.bedOccupied.background
            : theme.nutriward.colors.operational.bedFree.background,
        boxShadow: (theme) => pendingTransfer
          ? `inset 5px 0 0 ${theme.nutriward.colors.transfer.main}${selected ? `, 0 0 0 3px ${theme.nutriward.colors.primary.light}` : ''}`
          : selected
            ? `0 0 0 3px ${theme.nutriward.colors.primary.light}`
            : 'none',
        p: 1.5,
        alignSelf: 'stretch',
        ...(positioned && layout
          ? {
              gridColumn: `${layout.grid_x + 1} / span ${layout.width}`,
              gridRow: `${layout.grid_y + 1} / span ${layout.height}`,
            }
          : {}),
        '&:focus-visible': { outline: '3px solid', outlineColor: 'primary.main', outlineOffset: 2 },
        '&:hover': {
          borderColor: selected ? 'primary.dark' : occupied ? 'warning.main' : 'success.main',
          transform: 'translateY(-1px)',
        },
        transition: (theme) => theme.transitions.create(
          ['background-color', 'border-color', 'box-shadow', 'transform'],
          { duration: theme.transitions.duration.short },
        ),
      }}
    >
      <Stack height="100%" spacing={0.75}>
        <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1}>
          <Typography fontWeight={850}>{bedTitle(bed)}</Typography>
          {occupied ? <UserRound size={20} aria-hidden="true" /> : <CheckCircle2 size={20} aria-hidden="true" />}
        </Stack>
        <Chip
          size="small"
          variant="outlined"
          color={occupied ? 'warning' : 'success'}
          label={occupied ? 'Ocupada' : 'Libre'}
          sx={{ alignSelf: 'flex-start', fontWeight: 750 }}
        />
        {occupied && (
          <>
            <Typography variant="body2" fontWeight={750}>
              {occupied.patient.display_name}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {occupied.patient.age_years === null
                ? 'Edad no registrada'
                : `${occupied.patient.age_years} años${occupied.patient.age_is_estimated ? ' · estimada' : ''}`}
            </Typography>
            {pendingTransfer && (
              <Stack spacing={0.25}>
                <StatusBadge
                  icon={<ArrowRightLeft size={15} aria-hidden="true" />}
                  label={pendingTransferLabel(pendingTransfer)}
                  title={`${pendingTransferLabel(pendingTransfer)} · ${pendingTransfer.destination_service_name}`}
                  tone="transfer"
                  sx={{
                    alignSelf: 'flex-start',
                    height: 'auto',
                    maxWidth: '100%',
                    fontWeight: 800,
                    '& .MuiChip-icon': { ml: 0.75 },
                    '& .MuiChip-label': { whiteSpace: 'normal', py: 0.5 },
                  }}
                />
                <Typography variant="caption" sx={(theme) => ({ color: theme.nutriward.colors.transfer.dark, fontWeight: 650 })}>
                  {transferElapsed(pendingTransfer.requested_at)}
                </Typography>
              </Stack>
            )}
            <Typography variant="caption">Hospitalización {occupied.admission.status}</Typography>
            <Typography variant="caption" color="text.secondary">
              Régimen: No disponible en esta fase
            </Typography>
          </>
        )}
      </Stack>
    </ButtonBase>
  )
}

function BedCollection({
  beds,
  selectedBedId,
  onSelect,
  registerTrigger,
}: {
  beds: BedMapBed[]
  selectedBedId?: string
  onSelect: (bed: BedMapBed) => void
  registerTrigger: (bedId: string, element: HTMLButtonElement | null) => void
}) {
  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))', md: 'repeat(3, minmax(0, 1fr))' },
        gap: 1.5,
      }}
    >
      {beds.map((bed) => (
        <BedBlock key={bed.id} bed={bed} selected={bed.id === selectedBedId} onSelect={onSelect} registerTrigger={registerTrigger} />
      ))}
    </Box>
  )
}

function RoomMap({
  room,
  selectedBedId,
  onSelect,
  registerTrigger,
}: {
  room: BedMapRoom
  selectedBedId?: string
  onSelect: (room: BedMapRoom, bed: BedMapBed) => void
  registerTrigger: (bedId: string, element: HTMLButtonElement | null) => void
}) {
  const groups = useMemo(() => classifyRoomBeds(room), [room])
  const maxColumns = Math.max(
    1,
    ...groups.positioned.map((bed) => bed.layout!.grid_x + bed.layout!.width),
  )

  return (
    <Paper component="section" variant="outlined" sx={{ p: { xs: 2, md: 2.5 } }}>
      <Stack spacing={2}>
        <Box>
          <Typography component="h2" variant="h6" fontWeight={850}>
            {room.code} · {room.name}
          </Typography>
          {room.floor && <Typography color="text.secondary">{room.floor}</Typography>}
        </Box>

        {room.beds.length === 0 ? (
          <Alert severity="info">Esta sala no tiene camas activas.</Alert>
        ) : (
          <>
            {groups.positioned.length > 0 && (
              <Box sx={{ overflowX: 'auto', pb: 1 }} data-testid={`room-grid-${room.id}`}>
                <Box
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: `repeat(${maxColumns}, minmax(9rem, 1fr))`,
                    gridAutoRows: 'minmax(7.25rem, auto)',
                    gap: 1.5,
                    minWidth: maxColumns * 150,
                  }}
                >
                  {groups.positioned.map((bed) => (
                    <BedBlock
                      key={bed.id}
                      bed={bed}
                      positioned
                      selected={bed.id === selectedBedId}
                      onSelect={(selected) => onSelect(room, selected)}
                      registerTrigger={registerTrigger}
                    />
                  ))}
                </Box>
              </Box>
            )}

            {groups.conflicting.length > 0 && (
              <Stack spacing={1.25}>
                <Alert severity="warning" icon={<CircleAlert size={20} />}>
                  Hay posiciones superpuestas. Corrija la configuración desde Estructura hospitalaria.
                </Alert>
                <Typography component="h3" variant="subtitle1" fontWeight={800}>
                  Posición conflictiva
                </Typography>
                <BedCollection
                  beds={groups.conflicting}
                  selectedBedId={selectedBedId}
                  onSelect={(bed) => onSelect(room, bed)}
                  registerTrigger={registerTrigger}
                />
              </Stack>
            )}

            {groups.unpositioned.length > 0 && (
              <Stack spacing={1.25}>
                <Divider />
                <Typography component="h3" variant="subtitle1" fontWeight={800}>
                  Sin posición configurada
                </Typography>
                <BedCollection
                  beds={groups.unpositioned}
                  selectedBedId={selectedBedId}
                  onSelect={(bed) => onSelect(room, bed)}
                  registerTrigger={registerTrigger}
                />
              </Stack>
            )}
          </>
        )}
      </Stack>
    </Paper>
  )
}

interface Selection {
  room: BedMapRoom
  bed: BedMapBed
}

function OccupancyDrawer({
  service,
  selection,
  onClose,
  canMove,
  onMove,
  onOpenPatient,
}: {
  service: BedMap['service'] | null
  selection: Selection | null
  onClose: () => void
  canMove: boolean
  onMove: () => void
  onOpenPatient?: (patientId: string, admissionId?: string) => void
}) {
  const occupancy = selection?.bed.occupancy
  return (
    <Drawer anchor="right" open={Boolean(selection && occupancy)} onClose={onClose}>
      <Box sx={{ width: { xs: 'min(100vw, 360px)', sm: 420 }, p: 3 }} role="region" aria-label="Detalle de ocupación">
        {selection && occupancy && service && (
          <Stack spacing={2}>
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
              <Box>
                <Typography variant="overline">Detalle operacional</Typography>
                <Typography component="h2" variant="h5" fontWeight={850}>
                  {bedTitle(selection.bed)}
                </Typography>
              </Box>
              <IconButton onClick={onClose} aria-label="Cerrar panel de ocupación" autoFocus>
                <X aria-hidden="true" />
              </IconButton>
            </Stack>
            <Divider />
            <Box>
              <Typography variant="caption" color="text.secondary">Servicio</Typography>
              <Typography>{service.code} · {service.name}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">Sala</Typography>
              <Typography>{selection.room.code} · {selection.room.name}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">Paciente</Typography>
              <Typography fontWeight={800}>{occupancy.patient.display_name}</Typography>
              <Typography variant="body2">Tipo de identidad: {identityLabels[occupancy.patient.identity_status]}</Typography>
              <Typography variant="body2">
                Edad: {occupancy.patient.age_years === null ? 'No registrada' : `${occupancy.patient.age_years} años`}
                {occupancy.patient.age_is_estimated ? ' (estimada)' : ''}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">Hospitalización</Typography>
              <Typography>{occupancy.admission.admission_identifier}</Typography>
              <Typography variant="body2">Ingreso: {formatDateTime(occupancy.admission.admitted_at)}</Typography>
              <Typography variant="body2">Estado: {occupancy.admission.status}</Typography>
            </Box>
            {occupancy.pending_transfer && (
              <Alert severity="info" icon={<ArrowRightLeft aria-hidden="true" />}>
                <Typography fontWeight={800}>{pendingTransferLabel(occupancy.pending_transfer)}</Typography>
                <Typography variant="body2">
                  Destino: {occupancy.pending_transfer.destination_service_name}.{' '}
                  {transferElapsed(occupancy.pending_transfer.requested_at)}.
                </Typography>
                <Typography variant="caption">
                  El paciente continúa ocupando esta cama hasta que se asigne una cama destino.
                </Typography>
              </Alert>
            )}
            <Alert severity="info">Régimen: No disponible en esta fase</Alert>
            {onOpenPatient && (
              <Button
                variant="outlined"
                onClick={() => onOpenPatient(occupancy.patient.id, occupancy.admission.id)}
              >
                Abrir ficha completa
              </Button>
            )}
            {canMove && <Button variant="contained" onClick={onMove}>Mover paciente</Button>}
            <Button variant="outlined" onClick={onClose}>Cerrar</Button>
          </Stack>
        )}
      </Box>
    </Drawer>
  )
}

export function BedMapDashboard({
  userId,
  isNutritionist = false,
  canMutateTransfers = false,
  csrfToken = '',
  onOpenPatient,
}: BedMapDashboardProps = {}) {
  const [services, setServices] = useState<HospitalService[] | null>(null)
  const [assignedServiceIds, setAssignedServiceIds] = useState<Set<string>>(new Set())
  const [selectedServiceId, setSelectedServiceId] = useState('')
  const [selectedRoomId, setSelectedRoomId] = useState(ALL_ROOMS)
  const [bedMap, setBedMap] = useState<BedMap | null>(null)
  const [initialLoading, setInitialLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [initialError, setInitialError] = useState<string | null>(null)
  const [refreshError, setRefreshError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [selection, setSelection] = useState<Selection | null>(null)
  const [clock, setClock] = useState(Date.now())
  const [moveOpen, setMoveOpen] = useState(false)
  const [trayRefreshToken, setTrayRefreshToken] = useState(0)
  const requestSequence = useRef(0)
  const abortController = useRef<AbortController | null>(null)
  const catalogAbortController = useRef<AbortController | null>(null)
  const triggerElements = useRef(new Map<string, HTMLButtonElement>())
  const selectionRef = useRef<Selection | null>(null)
  const bedMapRef = useRef<BedMap | null>(null)
  const servicePreferenceKey = userId
    ? `${SERVICE_PREFERENCE_PREFIX}${userId}`
    : null

  useEffect(() => {
    selectionRef.current = selection
  }, [selection])

  const registerTrigger = useCallback((bedId: string, element: HTMLButtonElement | null) => {
    if (element) triggerElements.current.set(bedId, element)
    else triggerElements.current.delete(bedId)
  }, [])

  const closePanel = useCallback(() => {
    const bedId = selectionRef.current?.bed.id
    setSelection(null)
    selectionRef.current = null
    if (bedId) setTimeout(() => triggerElements.current.get(bedId)?.focus(), 0)
  }, [])

  const loadMap = useCallback(async (serviceId: string, background: boolean) => {
    const sequence = ++requestSequence.current
    abortController.current?.abort()
    const controller = new AbortController()
    abortController.current = controller
    if (background) setRefreshing(true)
    else setInitialLoading(true)
    if (!background) setInitialError(null)
    setRefreshError(null)
    try {
      const nextMap = await apiRequest<BedMap>(
        `/bed-map?service_id=${encodeURIComponent(serviceId)}`,
        { signal: controller.signal },
      )
      if (sequence !== requestSequence.current) return
      const currentSelection = selectionRef.current
      if (currentSelection) {
        const updatedBed = nextMap.rooms
          .flatMap((room) => room.beds)
          .find((bed) => bed.id === currentSelection.bed.id)
        if (!updatedBed?.occupancy) {
          closePanel()
          setNotice('La ocupación cambió y la cama ahora está libre.')
        } else {
          const updatedRoom = nextMap.rooms.find((room) => room.beds.some((bed) => bed.id === updatedBed.id))!
          setSelection({ room: updatedRoom, bed: updatedBed })
        }
      }
      setBedMap(nextMap)
      bedMapRef.current = nextMap
      setClock(Date.now())
    } catch (error) {
      if (controller.signal.aborted || sequence !== requestSequence.current) return
      if (background && bedMapRef.current) setRefreshError(requestError(error))
      else setInitialError(requestError(error))
    } finally {
      if (sequence === requestSequence.current) {
        setInitialLoading(false)
        setRefreshing(false)
      }
    }
  }, [closePanel])

  const loadServices = useCallback(async () => {
    catalogAbortController.current?.abort()
    const controller = new AbortController()
    catalogAbortController.current = controller
    setInitialLoading(true)
    setInitialError(null)
    try {
      const assignmentRequest = isNutritionist
        ? apiRequest<NutritionistServiceAssignmentList>(
          '/nutritionist-service-assignments/me',
          { signal: controller.signal },
        ).catch((error) => {
          if (controller.signal.aborted) throw error
          setNotice('No fue posible cargar sus servicios asignados; se mostrará el primer servicio activo.')
          return { items: [], total: 0 }
        })
        : Promise.resolve({ items: [], total: 0 })
      const [structure, assignments] = await Promise.all([
        apiRequest<HospitalStructure>(
          '/hospital/structure?include_inactive=false',
          { signal: controller.signal },
        ),
        assignmentRequest,
      ])
      const activeServices = structure.items
        .filter((service) => service.is_active)
        .sort((first, second) =>
          first.code.localeCompare(second.code) || first.name.localeCompare(second.name),
        )
      const activeServiceIds = new Set(activeServices.map((service) => service.id))
      const nextAssignedIds = new Set(
        assignments.items
          .filter((assignment) => assignment.is_active && activeServiceIds.has(assignment.service_id))
          .map((assignment) => assignment.service_id),
      )
      setServices(activeServices)
      setAssignedServiceIds(nextAssignedIds)
      if (activeServices.length) {
        const storedServiceId = servicePreferenceKey
          ? window.sessionStorage.getItem(servicePreferenceKey)
          : null
        const storedService = activeServices.find((service) => (
          service.id === storedServiceId
          && (!isNutritionist || nextAssignedIds.has(service.id))
        ))
        const assignedService = activeServices.find((service) => nextAssignedIds.has(service.id))
        const initialService = storedService ?? assignedService ?? activeServices[0]
        setSelectedServiceId(initialService.id)
        if (servicePreferenceKey && (!isNutritionist || nextAssignedIds.has(initialService.id))) {
          window.sessionStorage.setItem(servicePreferenceKey, initialService.id)
        }
      } else {
        setInitialLoading(false)
      }
    } catch (error) {
      if (controller.signal.aborted) return
      setServices([])
      setInitialError(requestError(error))
      setInitialLoading(false)
    }
  }, [isNutritionist, servicePreferenceKey])

  useEffect(() => {
    void loadServices()
    return () => {
      catalogAbortController.current?.abort()
      abortController.current?.abort()
    }
  }, [loadServices])

  useEffect(() => {
    if (selectedServiceId) void loadMap(selectedServiceId, false)
  }, [loadMap, selectedServiceId])

  useEffect(() => {
    if (!selectedServiceId) return
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void loadMap(selectedServiceId, true)
    }, REFRESH_INTERVAL_MS)
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') void loadMap(selectedServiceId, true)
    }
    document.addEventListener('visibilitychange', onVisibilityChange)
    return () => {
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
  }, [loadMap, selectedServiceId])

  useEffect(() => {
    const timer = window.setInterval(() => setClock(Date.now()), 15_000)
    return () => window.clearInterval(timer)
  }, [])

  const visibleRooms = useMemo(() => {
    if (!bedMap) return []
    return selectedRoomId === ALL_ROOMS
      ? bedMap.rooms
      : bedMap.rooms.filter((room) => room.id === selectedRoomId)
  }, [bedMap, selectedRoomId])

  const operationalSummary = useMemo(() => {
    const beds = bedMap?.rooms.flatMap((room) => room.beds) ?? []
    const occupied = beds.filter((bed) => bed.status === 'occupied' && bed.occupancy).length
    const transfers = beds.filter((bed) => bed.occupancy?.pending_transfer).length
    return { total: beds.length, occupied, free: beds.length - occupied, transfers }
  }, [bedMap])

  function changeService(nextServiceId: string) {
    requestSequence.current += 1
    abortController.current?.abort()
    closePanel()
    setSelectedRoomId(ALL_ROOMS)
    setBedMap(null)
    bedMapRef.current = null
    setRefreshError(null)
    setInitialError(null)
    setSelectedServiceId(nextServiceId)
    if (
      servicePreferenceKey
      && (!isNutritionist || assignedServiceIds.has(nextServiceId))
    ) {
      window.sessionStorage.setItem(servicePreferenceKey, nextServiceId)
    }
  }

  return (
    <Stack spacing={{ xs: 2.5, md: 3 }}>
      <PageHeader
        eyebrow="Operación hospitalaria"
        title="Mapa de camas"
        description="Estado actual por servicio y sala, con traslados pendientes y actualización automática."
        actions={(
          <Stack direction="row" alignItems="center" spacing={1.5} justifyContent={{ xs: 'space-between', sm: 'flex-end' }}>
            <Box sx={{ textAlign: { sm: 'right' } }} aria-live="polite">
              {refreshing && (
                <Stack direction="row" spacing={0.75} alignItems="center" justifyContent="flex-end">
                  <CircularProgress size={16} aria-label="Actualizando mapa" />
                  <Typography variant="caption" color="text.secondary">Actualizando</Typography>
                </Stack>
              )}
              {!refreshing && bedMap && <Typography variant="caption" color="text.secondary">{updatedAgo(bedMap.generated_at, clock)}</Typography>}
            </Box>
            <Button
              variant="outlined"
              startIcon={<RefreshCw size={17} aria-hidden="true" />}
              disabled={!selectedServiceId || refreshing}
              onClick={() => void loadMap(selectedServiceId, Boolean(bedMap))}
            >
              Actualizar
            </Button>
          </Stack>
        )}
      />

      {bedMap && (
        <Box
          aria-label="Resumen del mapa"
          sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2, minmax(0, 1fr))', lg: 'repeat(4, minmax(0, 1fr))' }, gap: 1.5 }}
        >
          <StatCard label="Camas activas" value={operationalSummary.total} icon={<BedDouble size={20} />} />
          <StatCard label="Libres" value={operationalSummary.free} icon={<CheckCircle2 size={20} />} tone="success" />
          <StatCard label="Ocupadas" value={operationalSummary.occupied} icon={<UserRound size={20} />} tone="warning" />
          <StatCard label="Con traslado" value={operationalSummary.transfers} icon={<ArrowRightLeft size={20} />} tone="secondary" />
        </Box>
      )}

      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2}>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
            <FormControl fullWidth>
              <InputLabel id="service-selector-label">Servicio</InputLabel>
              <Select
                labelId="service-selector-label"
                label="Servicio"
                value={selectedServiceId}
                disabled={!services?.length}
                onChange={(event) => changeService(event.target.value)}
              >
                {services?.map((service) => (
                  <MenuItem key={service.id} value={service.id}>
                    <Stack direction="row" spacing={1} alignItems="center" width="100%">
                      <span>{service.code} · {service.name}</span>
                      {assignedServiceIds.has(service.id) && (
                        <Chip label="Asignado" size="small" color="primary" variant="outlined" />
                      )}
                    </Stack>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel id="room-selector-label">Sala</InputLabel>
              <Select
                labelId="room-selector-label"
                label="Sala"
                value={selectedRoomId}
                disabled={!bedMap?.rooms.length}
                onChange={(event) => setSelectedRoomId(event.target.value)}
              >
                <MenuItem value={ALL_ROOMS}>Todas las salas</MenuItem>
                {bedMap?.rooms.map((room) => (
                  <MenuItem key={room.id} value={room.id}>{room.code} · {room.name}</MenuItem>
                ))}
              </Select>
            </FormControl>
            </Stack>
            <Stack
              component="aside"
              aria-label="Leyenda de estados de camas"
              direction="row"
              spacing={1}
              useFlexGap
              flexWrap="wrap"
              alignItems="center"
              sx={{ pt: 1.5, borderTop: '1px solid', borderColor: 'divider' }}
            >
              <Typography variant="caption" color="text.secondary" fontWeight={750}>Leyenda</Typography>
              <StatusBadge label="Libre" tone="success" icon={<CheckCircle2 size={14} aria-hidden="true" />} />
              <StatusBadge label="Ocupada" tone="warning" icon={<UserRound size={14} aria-hidden="true" />} />
              <StatusBadge label="Traslado pendiente" tone="transfer" icon={<ArrowRightLeft size={14} aria-hidden="true" />} />
              <StatusBadge label="Seleccionada" tone="info" icon={<CircleAlert size={14} aria-hidden="true" />} />
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {selectedServiceId && csrfToken && (
        <ReceptionTray
          serviceId={selectedServiceId}
          canMutate={canMutateTransfers}
          csrfToken={csrfToken}
          refreshToken={trayRefreshToken}
          onMutation={() => void loadMap(selectedServiceId, true)}
          onOpenPatient={onOpenPatient}
        />
      )}

      {refreshError && (
        <Alert
          severity="warning"
          action={<Button color="inherit" size="small" onClick={() => void loadMap(selectedServiceId, true)}>Reintentar</Button>}
        >
          No fue posible actualizar el mapa. Se conserva la última información válida. {refreshError}
        </Alert>
      )}

      {initialLoading && !bedMap ? (
        <LoadingState label="Cargando mapa de camas" rows={3} />
      ) : initialError && !bedMap ? (
        <Alert
          severity="error"
          action={<Button color="inherit" onClick={() => selectedServiceId ? void loadMap(selectedServiceId, false) : void loadServices()}>Reintentar</Button>}
        >
          {initialError}
        </Alert>
      ) : services?.length === 0 ? (
        <Alert severity="info">No hay servicios activos disponibles.</Alert>
      ) : bedMap?.rooms.length === 0 ? (
        <Alert severity="info">El servicio seleccionado no tiene salas activas.</Alert>
      ) : (
        visibleRooms.map((room) => (
          <RoomMap
            key={room.id}
            room={room}
            selectedBedId={selection?.bed.id}
            registerTrigger={registerTrigger}
            onSelect={(selectedRoom, bed) => {
              const next = { room: selectedRoom, bed }
              selectionRef.current = next
              setSelection(next)
            }}
          />
        ))
      )}

      <OccupancyDrawer
        service={bedMap?.service ?? null}
        selection={selection}
        onClose={closePanel}
        canMove={canMutateTransfers}
        onMove={() => setMoveOpen(true)}
        onOpenPatient={onOpenPatient}
      />
      <MovePatientDialog
        open={moveOpen}
        admission={selection?.bed.occupancy ? {
          id: selection.bed.occupancy.admission.id,
          current_location: {
            service_id: bedMap?.service.id ?? null,
            care_unit_id: selection.bed.id,
          },
        } : null}
        services={services ?? []}
        csrfToken={csrfToken}
        onClose={() => setMoveOpen(false)}
        onCompleted={() => {
          setMoveOpen(false)
          closePanel()
          setTrayRefreshToken((value) => value + 1)
          if (selectedServiceId) void loadMap(selectedServiceId, true)
        }}
      />
      <FeedbackSnackbar
        open={Boolean(notice)}
        onClose={() => setNotice(null)}
        message={notice}
      />
    </Stack>
  )
}
