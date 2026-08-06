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
  Snackbar,
  Stack,
  Typography,
} from '@mui/material'
import { CheckCircle2, CircleAlert, RefreshCw, UserRound, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

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

const REFRESH_INTERVAL_MS = 45_000
const ALL_ROOMS = 'all'
const SERVICE_PREFERENCE_PREFIX = 'nutriward:bed-map:service:'

interface BedMapDashboardProps {
  userId?: string
  isNutritionist?: boolean
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

function bedTitle(bed: BedMapBed): string {
  return bed.label || `Cama ${bed.code}`
}

function accessibleBedLabel(bed: BedMapBed): string {
  const title = bedTitle(bed)
  return bed.occupancy
    ? `${title}, ocupada por ${bed.occupancy.patient.display_name}`
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
  onSelect,
  registerTrigger,
}: {
  bed: BedMapBed
  positioned?: boolean
  onSelect: (bed: BedMapBed) => void
  registerTrigger: (bedId: string, element: HTMLButtonElement | null) => void
}) {
  const occupied = bed.status === 'occupied' && bed.occupancy
  const layout = bed.layout

  return (
    <ButtonBase
      ref={(element) => registerTrigger(bed.id, element)}
      aria-label={accessibleBedLabel(bed)}
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
        borderColor: occupied ? 'warning.dark' : 'success.dark',
        borderRadius: 2,
        bgcolor: occupied ? '#fff8e1' : '#edf7ed',
        p: 1.5,
        alignSelf: 'stretch',
        ...(positioned && layout
          ? {
              gridColumn: `${layout.grid_x + 1} / span ${layout.width}`,
              gridRow: `${layout.grid_y + 1} / span ${layout.height}`,
            }
          : {}),
        '&:focus-visible': { outline: '3px solid', outlineColor: 'primary.main', outlineOffset: 2 },
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
  onSelect,
  registerTrigger,
}: {
  beds: BedMapBed[]
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
        <BedBlock key={bed.id} bed={bed} onSelect={onSelect} registerTrigger={registerTrigger} />
      ))}
    </Box>
  )
}

function RoomMap({
  room,
  onSelect,
  registerTrigger,
}: {
  room: BedMapRoom
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
}: {
  service: BedMap['service'] | null
  selection: Selection | null
  onClose: () => void
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
            <Alert severity="info">Régimen: No disponible en esta fase</Alert>
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
    <Stack spacing={3}>
      <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={2}>
        <Box>
          <Typography component="h1" variant="h4" fontWeight={850}>Mapa de camas</Typography>
          <Typography color="text.secondary">Estado operacional actual por servicio y sala.</Typography>
        </Box>
        <Stack direction="row" alignItems="center" spacing={1.5}>
          {refreshing && <CircularProgress size={18} aria-label="Actualizando mapa" />}
          {bedMap && <Typography variant="caption" color="text.secondary">{updatedAgo(bedMap.generated_at, clock)}</Typography>}
          <Button
            variant="outlined"
            startIcon={<RefreshCw size={17} />}
            disabled={!selectedServiceId || refreshing}
            onClick={() => void loadMap(selectedServiceId, Boolean(bedMap))}
          >
            Actualizar
          </Button>
        </Stack>
      </Stack>

      <Card variant="outlined">
        <CardContent>
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
        </CardContent>
      </Card>

      {refreshError && (
        <Alert
          severity="warning"
          action={<Button color="inherit" size="small" onClick={() => void loadMap(selectedServiceId, true)}>Reintentar</Button>}
        >
          No fue posible actualizar el mapa. Se conserva la última información válida. {refreshError}
        </Alert>
      )}

      {initialLoading && !bedMap ? (
        <Box sx={{ py: 7, textAlign: 'center' }}>
          <CircularProgress aria-label="Cargando mapa de camas" />
          <Typography sx={{ mt: 1.5 }} color="text.secondary">Cargando mapa de camas…</Typography>
        </Box>
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
            registerTrigger={registerTrigger}
            onSelect={(selectedRoom, bed) => {
              const next = { room: selectedRoom, bed }
              selectionRef.current = next
              setSelection(next)
            }}
          />
        ))
      )}

      <OccupancyDrawer service={bedMap?.service ?? null} selection={selection} onClose={closePanel} />
      <Snackbar
        open={Boolean(notice)}
        autoHideDuration={6000}
        onClose={() => setNotice(null)}
        message={notice}
      />
    </Stack>
  )
}
