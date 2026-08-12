import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { BedDouble, Inbox } from 'lucide-react'
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'

import {
  ApiError,
  apiRequest,
  BedMap,
  HospitalService,
  TransferRequest,
  TransferRequestList,
  TransferStatus,
} from '../../shared/services/api'

const REFRESH_INTERVAL_MS = 45_000

const statusLabels: Record<TransferStatus, string> = {
  requested: 'Solicitado',
  pending_reception: 'Pendiente de recepción',
  accepted: 'Aceptado',
  pending_bed: 'Aceptado, pendiente de cama',
  assigned_to_bed: 'Asignado a cama',
  rejected: 'Rechazado',
  returned: 'Devuelto',
  cancelled: 'Cancelado',
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 409) {
    return `La disponibilidad o el estado cambió: ${error.message} Refresque los datos.`
  }
  return error instanceof ApiError ? error.message : 'No fue posible completar la operación.'
}

function elapsed(value: string): string {
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60_000))
  if (minutes < 1) return 'Hace menos de un minuto'
  if (minutes < 60) return `Hace ${minutes} min`
  const hours = Math.floor(minutes / 60)
  return `Hace ${hours} h`
}

type FreeBed = {
  id: string
  code: string
  label: string | null
  roomCode: string
  roomName: string
  serviceCode: string
  serviceName: string
}

async function loadFreeBeds(serviceId: string, currentBedId?: string): Promise<FreeBed[]> {
  const map = await apiRequest<BedMap>(`/bed-map?service_id=${encodeURIComponent(serviceId)}`)
  return map.rooms.flatMap((room) => room.beds
    .filter((bed) => bed.status === 'free' && bed.id !== currentBedId)
    .map((bed) => ({
      id: bed.id,
      code: bed.code,
      label: bed.label,
      roomCode: room.code,
      roomName: room.name,
      serviceCode: map.service.code,
      serviceName: map.service.name,
    })))
}

export function MovePatientDialog({
  open,
  admission,
  services,
  csrfToken,
  onClose,
  onCompleted,
}: {
  open: boolean
  admission: {
    id: string
    current_location: { service_id: string | null; care_unit_id: string } | null
  } | null
  services: HospitalService[]
  csrfToken: string
  onClose: () => void
  onCompleted: () => void
}) {
  const currentServiceId = admission?.current_location?.service_id ?? ''
  const [destinationServiceId, setDestinationServiceId] = useState('')
  const [mode, setMode] = useState<'direct' | 'reception_tray'>('direct')
  const [bedId, setBedId] = useState('')
  const [reason, setReason] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [beds, setBeds] = useState<FreeBed[]>([])
  const [loadingBeds, setLoadingBeds] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const requestId = useRef(0)
  const sameService = Boolean(destinationServiceId && destinationServiceId === currentServiceId)
  const requiresBed = sameService || mode === 'direct'

  useEffect(() => {
    if (!open) return
    setDestinationServiceId('')
    setMode('direct')
    setBedId('')
    setReason('')
    setConfirmed(false)
    setBeds([])
    setError(null)
  }, [open, admission?.id])

  useEffect(() => {
    if (!open || !destinationServiceId || !requiresBed) {
      setBeds([])
      setBedId('')
      return
    }
    const currentRequest = ++requestId.current
    setLoadingBeds(true)
    void loadFreeBeds(destinationServiceId, admission?.current_location?.care_unit_id)
      .then((nextBeds) => {
        if (currentRequest === requestId.current) setBeds(nextBeds)
      })
      .catch((caught) => {
        if (currentRequest === requestId.current) setError(errorMessage(caught))
      })
      .finally(() => {
        if (currentRequest === requestId.current) setLoadingBeds(false)
      })
  }, [admission?.current_location?.care_unit_id, destinationServiceId, open, requiresBed])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!admission || !destinationServiceId || !confirmed || (requiresBed && !bedId)) return
    setSaving(true)
    setError(null)
    try {
      if (sameService) {
        await apiRequest(
          `/admissions/${admission.id}/location`,
          { method: 'POST', body: JSON.stringify({ care_unit_id: bedId, reason: reason.trim() }) },
          csrfToken,
        )
      } else {
        await apiRequest(
          '/transfer-requests',
          {
            method: 'POST',
            body: JSON.stringify({
              admission_id: admission.id,
              destination_service_id: destinationServiceId,
              transfer_mode: mode,
              destination_care_unit_id: mode === 'direct' ? bedId : null,
              reason: reason.trim() || null,
            }),
          },
          csrfToken,
        )
      }
      onCompleted()
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} fullWidth maxWidth="sm" onClose={saving ? undefined : onClose}>
      <Box component="form" onSubmit={(event) => void submit(event)}>
        <DialogTitle>Mover paciente</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {error && <Alert severity="error">{error}</Alert>}
            <FormControl required fullWidth>
              <InputLabel id="transfer-service-label">Servicio destino</InputLabel>
              <Select
                labelId="transfer-service-label"
                label="Servicio destino"
                value={destinationServiceId}
                autoFocus
                onChange={(event) => {
                  setDestinationServiceId(event.target.value)
                  setBedId('')
                  setConfirmed(false)
                }}
              >
                {services.filter((service) => service.is_active).map((service) => (
                  <MenuItem key={service.id} value={service.id}>{service.code} · {service.name}</MenuItem>
                ))}
              </Select>
            </FormControl>
            {destinationServiceId && !sameService && (
              <FormControl fullWidth>
                <InputLabel id="transfer-mode-label">Modalidad</InputLabel>
                <Select
                  labelId="transfer-mode-label"
                  label="Modalidad"
                  value={mode}
                  onChange={(event) => {
                    setMode(event.target.value as 'direct' | 'reception_tray')
                    setBedId('')
                    setConfirmed(false)
                  }}
                >
                  <MenuItem value="direct">Asignar directamente una cama destino</MenuItem>
                  <MenuItem value="reception_tray">Enviar a bandeja de recepción</MenuItem>
                </Select>
              </FormControl>
            )}
            {destinationServiceId && (
              <Alert severity={mode === 'reception_tray' && !sameService ? 'info' : 'warning'}>
                {sameService
                  ? 'Este cambio cerrará la ubicación actual y ocupará la nueva cama dentro del mismo servicio.'
                  : mode === 'direct'
                    ? 'La cama destino se ocupará inmediatamente al confirmar.'
                    : 'El paciente continuará en su cama actual hasta que recepción acepte y asigne una cama.'}
              </Alert>
            )}
            {requiresBed && destinationServiceId && (
              <FormControl required fullWidth disabled={loadingBeds}>
                <InputLabel id="transfer-bed-label">Cama destino</InputLabel>
                <Select
                  labelId="transfer-bed-label"
                  label="Cama destino"
                  value={bedId}
                  onChange={(event) => setBedId(event.target.value)}
                >
                  {beds.map((bed) => (
                    <MenuItem key={bed.id} value={bed.id}>
                      {bed.serviceCode} · {bed.roomCode} {bed.roomName} · {bed.label || `Cama ${bed.code}`}
                    </MenuItem>
                  ))}
                </Select>
                {loadingBeds && <CircularProgress size={18} sx={{ mt: 1 }} aria-label="Cargando camas libres" />}
                {!loadingBeds && beds.length === 0 && <Typography variant="caption">No hay camas libres disponibles.</Typography>}
              </FormControl>
            )}
            <TextField
              label="Motivo del traslado (opcional)"
              value={reason}
              inputProps={{ minLength: 3, maxLength: 500 }}
              onChange={(event) => setReason(event.target.value)}
              multiline
              minRows={2}
            />
            <FormControlLabel
              control={<Checkbox checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />}
              label="Confirmo el cambio operacional indicado"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={saving}>Cancelar</Button>
          <Button
            type="submit"
            variant="contained"
            disabled={saving || !destinationServiceId || !confirmed || (requiresBed && !bedId)}
          >
            {saving ? 'Procesando…' : sameService ? 'Cambiar cama' : mode === 'direct' ? 'Confirmar traslado directo' : 'Enviar a bandeja'}
          </Button>
        </DialogActions>
      </Box>
    </Dialog>
  )
}

type ActionKind = 'accept' | 'accept-bed' | 'assign-bed' | 'reject' | 'return' | 'cancel'

function TransferActionDialog({
  transfer,
  action,
  csrfToken,
  onClose,
  onCompleted,
}: {
  transfer: TransferRequest
  action: ActionKind
  csrfToken: string
  onClose: () => void
  onCompleted: () => void
}) {
  const needsBed = action === 'accept-bed' || action === 'assign-bed'
  const requiresReason = action === 'reject' || action === 'return' || action === 'cancel'
  const [beds, setBeds] = useState<FreeBed[]>([])
  const [bedId, setBedId] = useState('')
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!needsBed) return
    void loadFreeBeds(transfer.destination_service.id)
      .then(setBeds)
      .catch((caught) => setError(errorMessage(caught)))
  }, [needsBed, transfer.destination_service.id])

  const labels: Record<ActionKind, string> = {
    accept: 'Aceptar y dejar pendiente de cama',
    'accept-bed': 'Aceptar y asignar cama',
    'assign-bed': 'Asignar cama',
    reject: 'Rechazar solicitud',
    return: 'Devolver solicitud',
    cancel: 'Cancelar solicitud',
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    const endpoint = action === 'accept-bed' ? 'accept' : action
    const body = needsBed
      ? { destination_care_unit_id: bedId, observation: reason.trim() || null }
      : action === 'accept'
        ? { destination_care_unit_id: null, observation: reason.trim() || null }
        : { reason: reason.trim() }
    try {
      await apiRequest(
        `/transfer-requests/${transfer.id}/${endpoint}`,
        { method: 'POST', body: JSON.stringify(body) },
        csrfToken,
      )
      onCompleted()
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open fullWidth maxWidth="sm" onClose={saving ? undefined : onClose}>
      <Box component="form" onSubmit={(event) => void submit(event)}>
        <DialogTitle>{labels[action]}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {error && <Alert severity="error">{error}</Alert>}
            <Typography>{transfer.patient.display_name} · {transfer.origin_service.name} → {transfer.destination_service.name}</Typography>
            {needsBed && (
              <FormControl required fullWidth>
                <InputLabel id="reception-bed-label">Cama libre</InputLabel>
                <Select labelId="reception-bed-label" label="Cama libre" value={bedId} autoFocus onChange={(event) => setBedId(event.target.value)}>
                  {beds.map((bed) => (
                    <MenuItem key={bed.id} value={bed.id}>{bed.serviceCode} · {bed.roomCode} · {bed.label || `Cama ${bed.code}`}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
            <TextField
              required={requiresReason}
              autoFocus={!needsBed}
              label={requiresReason ? 'Motivo obligatorio' : 'Observación opcional'}
              value={reason}
              inputProps={{ minLength: requiresReason ? 3 : 0, maxLength: 500 }}
              onChange={(event) => setReason(event.target.value)}
              multiline
              minRows={2}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={saving}>Volver</Button>
          <Button type="submit" variant="contained" disabled={saving || (needsBed && !bedId) || (requiresReason && reason.trim().length < 3)}>
            {saving ? 'Procesando…' : labels[action]}
          </Button>
        </DialogActions>
      </Box>
    </Dialog>
  )
}

export function ReceptionTray({
  serviceId,
  canMutate,
  csrfToken,
  refreshToken = 0,
  onMutation,
}: {
  serviceId: string
  canMutate: boolean
  csrfToken: string
  refreshToken?: number
  onMutation: () => void
}) {
  const [data, setData] = useState<TransferRequestList | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [action, setAction] = useState<{ transfer: TransferRequest; kind: ActionKind } | null>(null)
  const sequence = useRef(0)
  const validData = useRef<TransferRequestList | null>(null)
  const previousRefreshToken = useRef(refreshToken)

  const load = useCallback(async (background = false) => {
    const current = ++sequence.current
    if (background) setRefreshing(true)
    else setLoading(true)
    setError(null)
    try {
      const next = await apiRequest<TransferRequestList>(
        `/transfer-requests/reception-tray?service_id=${encodeURIComponent(serviceId)}&page_size=100`,
      )
      if (current !== sequence.current) return
      const normalized = Array.isArray(next?.items)
        ? next
        : { items: [], total: 0, page: 1, page_size: 100 }
      setData(normalized)
      validData.current = normalized
    } catch (caught) {
      if (current !== sequence.current) return
      setError(errorMessage(caught))
      if (!validData.current) setData(null)
    } finally {
      if (current === sequence.current) {
        setLoading(false)
        setRefreshing(false)
      }
    }
  }, [serviceId])

  useEffect(() => {
    validData.current = null
    setData(null)
    void load(false)
  }, [load])

  useEffect(() => {
    if (previousRefreshToken.current === refreshToken) return
    previousRefreshToken.current = refreshToken
    void load(true)
  }, [load, refreshToken])

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void load(true)
    }, REFRESH_INTERVAL_MS)
    const visible = () => {
      if (document.visibilityState === 'visible') void load(true)
    }
    document.addEventListener('visibilitychange', visible)
    return () => {
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', visible)
      sequence.current += 1
    }
  }, [load])

  const sections = useMemo(() => ({
    pending_reception: data?.items.filter((item) => item.status === 'pending_reception') ?? [],
    pending_bed: data?.items.filter((item) => item.status === 'pending_bed') ?? [],
  }), [data])

  async function completed() {
    setAction(null)
    await load(true)
    onMutation()
  }

  return (
    <Card variant="outlined" component="section" aria-labelledby="reception-tray-title">
      <CardContent>
        <Stack spacing={2}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" gap={2}>
            <Stack direction="row" alignItems="center" gap={1}>
              <Inbox size={21} aria-hidden="true" />
              <Typography id="reception-tray-title" component="h2" variant="h6" fontWeight={850}>Bandeja del servicio</Typography>
              <Chip label={`${data?.total ?? 0} pendientes`} color="primary" size="small" />
            </Stack>
            {refreshing && <CircularProgress size={18} aria-label="Actualizando bandeja" />}
          </Stack>
          {error && (
            <Alert severity={data ? 'warning' : 'error'} action={<Button color="inherit" onClick={() => void load(Boolean(data))}>Reintentar</Button>}>
              {data ? 'No se pudo refrescar; se conservan los últimos datos válidos. ' : ''}{error}
            </Alert>
          )}
          {loading && !data ? (
            <Box sx={{ py: 3, textAlign: 'center' }}><CircularProgress aria-label="Cargando bandeja" /></Box>
          ) : data?.items.length === 0 ? (
            <Alert severity="info">No hay solicitudes pendientes para este servicio.</Alert>
          ) : (
            (['pending_reception', 'pending_bed'] as const).map((status) => (
              <Stack key={status} spacing={1}>
                <Typography component="h3" fontWeight={800}>
                  {status === 'pending_reception' ? 'Pendientes de recepción' : 'Aceptados, pendientes de cama'} ({sections[status].length})
                </Typography>
                {sections[status].length === 0 ? (
                  <Typography variant="body2" color="text.secondary">Sin solicitudes en este estado.</Typography>
                ) : sections[status].map((transfer) => (
                  <Card key={transfer.id} variant="outlined">
                    <CardContent>
                      <Stack spacing={1.25}>
                        <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={1}>
                          <Box>
                            <Typography fontWeight={850}>{transfer.patient.display_name}</Typography>
                            <Typography variant="body2">
                              {transfer.patient.age_years === null ? 'Edad no registrada' : `${transfer.patient.age_years} años${transfer.patient.age_is_estimated ? ' · estimada' : ''}`}
                            </Typography>
                          </Box>
                          <Stack direction="row" gap={0.75} flexWrap="wrap">
                            <Chip size="small" label={statusLabels[transfer.status]} />
                            {transfer.has_coverage_support && <Chip size="small" color="warning" label="Cobertura/apoyo" />}
                          </Stack>
                        </Stack>
                        <Typography variant="body2">
                          Origen: {transfer.current_origin_location
                            ? `${transfer.current_origin_location.service_name} · ${transfer.current_origin_location.room_name} · ${transfer.current_origin_location.care_unit_label || transfer.current_origin_location.care_unit_code}`
                            : transfer.origin_service.name}
                        </Typography>
                        <Typography variant="body2"><strong>Motivo:</strong> {transfer.request_reason || 'Sin motivo informado'}</Typography>
                        <Typography variant="caption" color="text.secondary">{elapsed(transfer.requested_at)}</Typography>
                        {canMutate && (
                          <Stack direction="row" gap={1} flexWrap="wrap">
                            {transfer.status === 'pending_reception' && (
                              <>
                                <Button size="small" onClick={() => setAction({ transfer, kind: 'accept' })}>Aceptar sin cama</Button>
                                <Button size="small" variant="contained" onClick={() => setAction({ transfer, kind: 'accept-bed' })}>Aceptar y asignar</Button>
                                <Button size="small" color="error" onClick={() => setAction({ transfer, kind: 'reject' })}>Rechazar</Button>
                              </>
                            )}
                            {transfer.status === 'pending_bed' && (
                              <>
                                <Button size="small" variant="contained" startIcon={<BedDouble size={16} />} onClick={() => setAction({ transfer, kind: 'assign-bed' })}>Asignar cama</Button>
                                <Button size="small" color="warning" onClick={() => setAction({ transfer, kind: 'return' })}>Devolver</Button>
                              </>
                            )}
                            <Button size="small" color="inherit" onClick={() => setAction({ transfer, kind: 'cancel' })}>Cancelar solicitud</Button>
                          </Stack>
                        )}
                      </Stack>
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            ))
          )}
        </Stack>
      </CardContent>
      {action && (
        <TransferActionDialog
          transfer={action.transfer}
          action={action.kind}
          csrfToken={csrfToken}
          onClose={() => setAction(null)}
          onCompleted={() => void completed()}
        />
      )}
    </Card>
  )
}

export const transferStatusLabels = statusLabels
