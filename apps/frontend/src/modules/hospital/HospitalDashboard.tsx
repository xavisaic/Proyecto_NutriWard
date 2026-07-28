import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import Grid from '@mui/material/Grid2'
import {
  BedDouble,
  Building2,
  DoorOpen,
  MapPinned,
  Pencil,
  Plus,
  Power,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'

import {
  ApiError,
  apiRequest,
  CareUnitType,
  HospitalCareUnit,
  HospitalRoom,
  HospitalService,
  HospitalStructure,
} from '../../shared/services/api'

type CreateKind = 'service' | 'room' | 'careUnit'

interface CreateTarget {
  kind: CreateKind
  parentId?: string
  parentName?: string
  suggestedCode?: string
}

interface EditTarget {
  kind: CreateKind
  entity: HospitalService | HospitalRoom | HospitalCareUnit
}

interface DeleteTarget {
  kind: CreateKind
  entity: HospitalService | HospitalRoom | HospitalCareUnit
}

interface HospitalDashboardProps {
  canEdit: boolean
  canDelete: boolean
  csrfToken: string
}

function entityLabel(kind: CreateKind): string {
  if (kind === 'service') return 'servicio'
  if (kind === 'room') return 'sala'
  return 'ubicación asistencial'
}

function newEntityLabel(kind: CreateKind): string {
  if (kind === 'service') return 'Nuevo servicio'
  if (kind === 'room') return 'Nueva sala'
  return 'Nueva ubicación asistencial'
}

const CARE_UNIT_TYPE_LABELS: Record<CareUnitType, string> = {
  bed: 'Cama',
  stretcher: 'Camilla',
  station: 'Puesto',
  box: 'Box',
}

function careUnitDisplayName(careUnit: HospitalCareUnit): string {
  return careUnit.label || `${CARE_UNIT_TYPE_LABELS[careUnit.unit_type]} ${careUnit.code}`
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : 'No fue posible completar la operación.'
}

function suggestCareUnitCode(careUnits: HospitalCareUnit[]): string {
  const numeric = careUnits
    .filter((careUnit) => /^\d+$/.test(careUnit.code))
    .map((careUnit) => ({ value: Number(careUnit.code), width: careUnit.code.length }))
  if (numeric.length > 0) {
    const next = Math.max(...numeric.map((item) => item.value)) + 1
    const width = Math.max(2, ...numeric.map((item) => item.width))
    return String(next).padStart(width, '0')
  }
  const prefixed = careUnits
    .map((careUnit) => /^C(\d+)$/i.exec(careUnit.code))
    .filter((match): match is RegExpExecArray => match !== null)
  if (prefixed.length > 0) {
    const next = Math.max(...prefixed.map((match) => Number(match[1]))) + 1
    const width = Math.max(2, ...prefixed.map((match) => match[1].length))
    return `C${String(next).padStart(width, '0')}`
  }
  return 'C01'
}

function CreateDialog({
  csrfToken,
  onClose,
  onCreated,
  target,
}: {
  csrfToken: string
  onClose: () => void
  onCreated: () => Promise<void>
  target: CreateTarget
}) {
  const [code, setCode] = useState(target.suggestedCode ?? '')
  const [name, setName] = useState('')
  const [detail, setDetail] = useState('')
  const [notes, setNotes] = useState('')
  const [gridX, setGridX] = useState(0)
  const [gridY, setGridY] = useState(0)
  const [unitType, setUnitType] = useState<CareUnitType>('bed')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const label = entityLabel(target.kind)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setIsSaving(true)
    setError(null)
    try {
      if (target.kind === 'service') {
        await apiRequest(
          '/hospital/services',
          {
            method: 'POST',
            body: JSON.stringify({ code, name, description: detail || null }),
          },
          csrfToken,
        )
      } else if (target.kind === 'room') {
        await apiRequest(
          '/hospital/rooms',
          {
            method: 'POST',
            body: JSON.stringify({
              service_id: target.parentId,
              code,
              name,
              floor: detail || null,
              notes: notes || null,
            }),
          },
          csrfToken,
        )
      } else {
        const careUnit = await apiRequest<HospitalCareUnit>(
          '/hospital/care-units',
          {
            method: 'POST',
            body: JSON.stringify({
              room_id: target.parentId,
              ...(code.trim() ? { code } : {}),
              label: name || null,
              unit_type: unitType,
            }),
          },
          csrfToken,
        )
        await apiRequest(
          `/hospital/care-units/${careUnit.id}/layout`,
          {
            method: 'PUT',
            body: JSON.stringify({
              grid_x: gridX,
              grid_y: gridY,
              width: 1,
              height: 1,
            }),
          },
          csrfToken,
        )
      }
      await onCreated()
      onClose()
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Dialog open onClose={isSaving ? undefined : onClose} fullWidth maxWidth="sm">
      <Box component="form" onSubmit={(event) => void handleSubmit(event)}>
        <DialogTitle>{newEntityLabel(target.kind)}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {target.parentName && (
              <Alert severity="info" icon={false}>
                Se agregará a <strong>{target.parentName}</strong>.
              </Alert>
            )}
            {error && <Alert severity="error">{error}</Alert>}
            <TextField
              autoFocus
              required={target.kind !== 'careUnit'}
              label="Código"
              value={code}
              inputProps={{ maxLength: 30 }}
              helperText={
                target.kind === 'careUnit'
                  ? 'Código sugerido automáticamente; puede reemplazarlo por el código institucional.'
                  : undefined
              }
              onChange={(event) => setCode(event.target.value)}
            />
            <TextField
              required={target.kind !== 'careUnit'}
              label={target.kind === 'careUnit' ? 'Etiqueta' : 'Nombre'}
              value={name}
              inputProps={{ maxLength: 120 }}
              onChange={(event) => setName(event.target.value)}
            />
            {target.kind !== 'careUnit' && (
              <TextField
                label={target.kind === 'service' ? 'Descripción' : 'Piso o sector'}
                value={detail}
                multiline={target.kind === 'service'}
                minRows={target.kind === 'service' ? 2 : undefined}
                onChange={(event) => setDetail(event.target.value)}
              />
            )}
            {target.kind === 'room' && (
              <TextField
                label="Observaciones"
                value={notes}
                multiline
                minRows={2}
                inputProps={{ maxLength: 500 }}
                onChange={(event) => setNotes(event.target.value)}
              />
            )}
            {target.kind === 'careUnit' && (
              <Stack spacing={2}>
                <FormControl fullWidth>
                  <InputLabel id="create-care-unit-type-label">Tipo</InputLabel>
                  <Select
                    labelId="create-care-unit-type-label"
                    label="Tipo"
                    value={unitType}
                    onChange={(event) => setUnitType(event.target.value as CareUnitType)}
                  >
                    {Object.entries(CARE_UNIT_TYPE_LABELS).map(([value, typeLabel]) => (
                      <MenuItem key={value} value={value}>{typeLabel}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <Stack direction="row" spacing={2}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Columna"
                    value={gridX}
                    inputProps={{ min: 0, max: 100 }}
                    onChange={(event) => setGridX(Number(event.target.value))}
                  />
                  <TextField
                    fullWidth
                    type="number"
                    label="Fila"
                    value={gridY}
                    inputProps={{ min: 0, max: 100 }}
                    onChange={(event) => setGridY(Number(event.target.value))}
                  />
                </Stack>
              </Stack>
            )}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button onClick={onClose} disabled={isSaving}>Cancelar</Button>
          <Button type="submit" variant="contained" disabled={isSaving}>
            {isSaving ? 'Guardando…' : `Crear ${label}`}
          </Button>
        </DialogActions>
      </Box>
    </Dialog>
  )
}

function EditDialog({
  csrfToken,
  onClose,
  onUpdated,
  target,
}: {
  csrfToken: string
  onClose: () => void
  onUpdated: () => Promise<void>
  target: EditTarget
}) {
  const { entity, kind } = target
  const [code, setCode] = useState(entity.code)
  const [name, setName] = useState(
    kind === 'service'
      ? (entity as HospitalService).name
      : kind === 'room'
        ? (entity as HospitalRoom).name
        : (entity as HospitalCareUnit).label ?? '',
  )
  const [detail, setDetail] = useState(
    kind === 'service'
      ? (entity as HospitalService).description ?? ''
      : kind === 'room'
        ? (entity as HospitalRoom).floor ?? ''
        : '',
  )
  const [notes, setNotes] = useState(
    kind === 'room' ? (entity as HospitalRoom).notes ?? '' : '',
  )
  const careUnit = kind === 'careUnit' ? entity as HospitalCareUnit : null
  const [unitType, setUnitType] = useState<CareUnitType>(careUnit?.unit_type ?? 'bed')
  const [gridX, setGridX] = useState(careUnit?.layout?.grid_x ?? 0)
  const [gridY, setGridY] = useState(careUnit?.layout?.grid_y ?? 0)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const label = entityLabel(kind)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setIsSaving(true)
    setError(null)
    try {
      const endpoint = kind === 'service'
        ? `/hospital/services/${entity.id}`
        : kind === 'room'
          ? `/hospital/rooms/${entity.id}`
          : `/hospital/care-units/${entity.id}`
      const body = kind === 'service'
        ? { code, name, description: detail || null }
        : kind === 'room'
          ? { code, name, floor: detail || null, notes: notes || null }
          : { code, label: name || null, unit_type: unitType }
      await apiRequest(endpoint, { method: 'PATCH', body: JSON.stringify(body) }, csrfToken)
      if (kind === 'careUnit') {
        await apiRequest(
          `/hospital/care-units/${entity.id}/layout`,
          {
            method: 'PUT',
            body: JSON.stringify({
              grid_x: gridX,
              grid_y: gridY,
              width: careUnit?.layout?.width ?? 1,
              height: careUnit?.layout?.height ?? 1,
            }),
          },
          csrfToken,
        )
      }
      await onUpdated()
      onClose()
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Dialog open onClose={isSaving ? undefined : onClose} fullWidth maxWidth="sm">
      <Box component="form" onSubmit={(event) => void handleSubmit(event)}>
        <DialogTitle sx={{ textTransform: 'capitalize' }}>Editar {label}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {error && <Alert severity="error">{error}</Alert>}
            <TextField
              autoFocus
              required
              label="Código"
              value={code}
              inputProps={{ maxLength: 30 }}
              onChange={(event) => setCode(event.target.value)}
            />
            <TextField
              required={kind !== 'careUnit'}
              label={kind === 'careUnit' ? 'Etiqueta' : 'Nombre'}
              value={name}
              inputProps={{ maxLength: 120 }}
              onChange={(event) => setName(event.target.value)}
            />
            {kind !== 'careUnit' && (
              <TextField
                label={kind === 'service' ? 'Descripción' : 'Piso o sector'}
                value={detail}
                multiline={kind === 'service'}
                minRows={kind === 'service' ? 2 : undefined}
                onChange={(event) => setDetail(event.target.value)}
              />
            )}
            {kind === 'room' && (
              <TextField
                label="Observaciones"
                value={notes}
                multiline
                minRows={2}
                inputProps={{ maxLength: 500 }}
                onChange={(event) => setNotes(event.target.value)}
              />
            )}
            {kind === 'careUnit' && (
              <Stack spacing={2}>
                <FormControl fullWidth>
                  <InputLabel id="edit-care-unit-type-label">Tipo</InputLabel>
                  <Select
                    labelId="edit-care-unit-type-label"
                    label="Tipo"
                    value={unitType}
                    onChange={(event) => setUnitType(event.target.value as CareUnitType)}
                  >
                    {Object.entries(CARE_UNIT_TYPE_LABELS).map(([value, typeLabel]) => (
                      <MenuItem key={value} value={value}>{typeLabel}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <Stack direction="row" spacing={2}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Columna"
                    value={gridX}
                    inputProps={{ min: 0, max: 100 }}
                    onChange={(event) => setGridX(Number(event.target.value))}
                  />
                  <TextField
                    fullWidth
                    type="number"
                    label="Fila"
                    value={gridY}
                    inputProps={{ min: 0, max: 100 }}
                    onChange={(event) => setGridY(Number(event.target.value))}
                  />
                </Stack>
              </Stack>
            )}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button onClick={onClose} disabled={isSaving}>Cancelar</Button>
          <Button type="submit" variant="contained" disabled={isSaving}>
            {isSaving ? 'Guardando…' : 'Guardar cambios'}
          </Button>
        </DialogActions>
      </Box>
    </Dialog>
  )
}

function DeleteDialog({
  csrfToken,
  onClose,
  onDeleted,
  target,
}: {
  csrfToken: string
  onClose: () => void
  onDeleted: () => Promise<void>
  target: DeleteTarget
}) {
  const [reason, setReason] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const label = entityLabel(target.kind)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setIsDeleting(true)
    setError(null)
    try {
      const endpoint = target.kind === 'service'
        ? `/hospital/services/${target.entity.id}`
        : target.kind === 'room'
          ? `/hospital/rooms/${target.entity.id}`
          : `/hospital/care-units/${target.entity.id}`
      await apiRequest(
        endpoint,
        { method: 'DELETE', body: JSON.stringify({ reason }) },
        csrfToken,
      )
      await onDeleted()
      onClose()
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <Dialog open onClose={isDeleting ? undefined : onClose} fullWidth maxWidth="sm">
      <Box component="form" onSubmit={(event) => void handleSubmit(event)}>
        <DialogTitle>Eliminar definitivamente</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <Alert severity="warning">
              Esta acción excepcional eliminará el registro de {label}. Solo debe utilizarse para
              registros creados por error y no se puede deshacer.
            </Alert>
            {error && <Alert severity="error">{error}</Alert>}
            <TextField
              autoFocus
              required
              multiline
              minRows={3}
              label="Motivo de eliminación"
              value={reason}
              inputProps={{ minLength: 10, maxLength: 500 }}
              helperText="Mínimo 10 caracteres. El motivo quedará en la auditoría."
              onChange={(event) => setReason(event.target.value)}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button onClick={onClose} disabled={isDeleting}>Cancelar</Button>
          <Button type="submit" color="error" variant="contained" disabled={isDeleting}>
            {isDeleting ? 'Eliminando…' : 'Eliminar definitivamente'}
          </Button>
        </DialogActions>
      </Box>
    </Dialog>
  )
}

export function HospitalDashboard({ canEdit, canDelete, csrfToken }: HospitalDashboardProps) {
  const [structure, setStructure] = useState<HospitalStructure | null>(null)
  const [showInactive, setShowInactive] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [createTarget, setCreateTarget] = useState<CreateTarget | null>(null)
  const [editTarget, setEditTarget] = useState<EditTarget | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null)
  const [busyEntityId, setBusyEntityId] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await apiRequest<HospitalStructure>(
        `/hospital/structure?include_inactive=${showInactive}`,
      )
      setStructure(response)
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setIsLoading(false)
    }
  }, [showInactive])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const counts = useMemo(() => {
    const services = structure?.items ?? []
    const rooms = services.flatMap((service) => service.rooms)
    const careUnits = rooms.flatMap((room) => room.care_units)
    return {
      services: services.filter((service) => service.is_active).length,
      rooms: rooms.filter((room) => room.is_active).length,
      careUnits: careUnits.filter((careUnit) => careUnit.is_active).length,
    }
  }, [structure])

  async function toggleEntity(
    kind: CreateKind,
    entity: HospitalService | HospitalRoom | HospitalCareUnit,
  ) {
    const endpoint = kind === 'service'
      ? `/hospital/services/${entity.id}`
      : kind === 'room'
        ? `/hospital/rooms/${entity.id}`
        : `/hospital/care-units/${entity.id}`
    const action = entity.is_active ? 'inactivar' : 'reactivar'
    if (!window.confirm(`¿Confirma que desea ${action} este ${entityLabel(kind)}?`)) return

    setBusyEntityId(entity.id)
    setError(null)
    try {
      await apiRequest(
        endpoint,
        {
          method: 'PATCH',
          body: JSON.stringify({ is_active: !entity.is_active }),
        },
        csrfToken,
      )
      await refresh()
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setBusyEntityId(null)
    }
  }

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" gap={2}>
        <Box>
          <Typography variant="overline" color="primary" fontWeight={800}>
            Fase 3 · Base hospitalaria
          </Typography>
          <Typography variant="h4" component="h1" fontWeight={800}>
            Estructura hospitalaria
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 0.5 }}>
            Servicios, salas y ubicaciones asistenciales con su distribución visual.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          {canEdit && (
            <Button
              variant="contained"
              startIcon={<Plus size={18} />}
              onClick={() => setCreateTarget({ kind: 'service' })}
            >
              Nuevo servicio
            </Button>
          )}
          <Tooltip title="Actualizar">
            <span>
              <IconButton
                onClick={() => void refresh()}
                disabled={isLoading}
                aria-label="Actualizar estructura"
              >
                <RefreshCw size={20} />
              </IconButton>
            </span>
          </Tooltip>
        </Stack>
      </Stack>

      <Grid container spacing={2}>
        {[
          { label: 'Servicios activos', value: counts.services, icon: <Building2 size={21} /> },
          { label: 'Salas activas', value: counts.rooms, icon: <DoorOpen size={21} /> },
          {
            label: 'Ubicaciones activas',
            value: counts.careUnits,
            icon: <BedDouble size={21} />,
          },
        ].map((summary) => (
          <Grid key={summary.label} size={{ xs: 12, sm: 4 }}>
            <Card variant="outlined">
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Box>
                    <Typography color="text.secondary" variant="body2">{summary.label}</Typography>
                    <Typography variant="h4" fontWeight={800}>{summary.value}</Typography>
                  </Box>
                  <Box sx={{ color: 'primary.main' }}>{summary.icon}</Box>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {canEdit && (
        <FormControlLabel
          control={
            <Switch
              checked={showInactive}
              onChange={(event) => setShowInactive(event.target.checked)}
            />
          }
          label="Mostrar elementos inactivos"
        />
      )}

      {error && <Alert severity="error">{error}</Alert>}
      {isLoading && !structure && (
        <Stack alignItems="center" sx={{ py: 8 }}>
          <CircularProgress aria-label="Cargando estructura hospitalaria" />
        </Stack>
      )}
      {!isLoading && structure?.items.length === 0 && (
        <Alert severity="info">
          No hay servicios para mostrar. {canEdit && 'Crea el primer servicio para comenzar.'}
        </Alert>
      )}

      <Stack spacing={2}>
        {structure?.items.map((service) => (
          <Card
            key={service.id}
            variant="outlined"
            sx={{ opacity: service.is_active ? 1 : 0.62, overflow: 'visible' }}
          >
            <CardContent sx={{ p: { xs: 2, md: 3 } }}>
              <Stack
                direction={{ xs: 'column', sm: 'row' }}
                justifyContent="space-between"
                gap={2}
              >
                <Stack direction="row" spacing={1.5} alignItems="flex-start">
                  <Building2 size={24} color="#126b5b" />
                  <Box>
                    <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap">
                      <Typography variant="h6" fontWeight={800}>{service.name}</Typography>
                      <Chip label={service.code} size="small" />
                      {!service.is_active && <Chip label="Inactivo" size="small" />}
                    </Stack>
                    {service.description && (
                      <Typography color="text.secondary" variant="body2" sx={{ mt: 0.5 }}>
                        {service.description}
                      </Typography>
                    )}
                  </Box>
                </Stack>
                {canEdit && (
                  <Stack direction="row" spacing={1}>
                    {service.is_active && (
                      <Button
                        size="small"
                        startIcon={<Plus size={16} />}
                        onClick={() => setCreateTarget({
                          kind: 'room',
                          parentId: service.id,
                          parentName: service.name,
                        })}
                      >
                        Agregar sala
                      </Button>
                    )}
                    <Tooltip title="Editar servicio">
                      <IconButton
                        size="small"
                        onClick={() => setEditTarget({ kind: 'service', entity: service })}
                        aria-label={`Editar servicio ${service.name}`}
                      >
                        <Pencil size={18} />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title={service.is_active ? 'Inactivar servicio' : 'Reactivar servicio'}>
                      <span>
                        <IconButton
                          size="small"
                          disabled={busyEntityId === service.id}
                          onClick={() => void toggleEntity('service', service)}
                          aria-label={service.is_active ? 'Inactivar servicio' : 'Reactivar servicio'}
                        >
                          <Power size={18} />
                        </IconButton>
                      </span>
                    </Tooltip>
                    {canDelete && !service.is_active && (
                      <Tooltip title="Eliminar registro erróneo">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => setDeleteTarget({ kind: 'service', entity: service })}
                          aria-label={`Eliminar definitivamente servicio ${service.name}`}
                        >
                          <Trash2 size={18} />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Stack>
                )}
              </Stack>

              <Divider sx={{ my: 2.5 }} />
              {service.rooms.length === 0 ? (
                <Typography color="text.secondary" variant="body2">Sin salas registradas.</Typography>
              ) : (
                <Grid container spacing={2}>
                  {service.rooms.map((room) => (
                    <Grid key={room.id} size={{ xs: 12, lg: 6 }}>
                      <Box
                        sx={{
                          border: '1px solid',
                          borderColor: 'divider',
                          borderRadius: 2,
                          p: 2,
                          height: '100%',
                          opacity: room.is_active ? 1 : 0.65,
                        }}
                      >
                        <Stack direction="row" justifyContent="space-between" gap={1}>
                          <Box>
                            <Stack direction="row" spacing={1} alignItems="center">
                              <DoorOpen size={18} />
                              <Typography fontWeight={750}>{room.name}</Typography>
                              <Chip label={room.code} size="small" variant="outlined" />
                            </Stack>
                            <Typography variant="caption" color="text.secondary">
                              {room.floor ?? 'Sector no indicado'} · {room.care_units.length} ubicaciones
                            </Typography>
                            {room.notes && (
                              <Typography
                                variant="caption"
                                color="text.secondary"
                                sx={{ display: 'block', mt: 0.5 }}
                              >
                                {room.notes}
                              </Typography>
                            )}
                          </Box>
                          {canEdit && (
                            <Stack direction="row">
                              {room.is_active && (
                                <Tooltip title="Agregar ubicación">
                                  <IconButton
                                    size="small"
                                    onClick={() => setCreateTarget({
                                      kind: 'careUnit',
                                      parentId: room.id,
                                      parentName: room.name,
                                      suggestedCode: suggestCareUnitCode(room.care_units),
                                    })}
                                    aria-label={`Agregar ubicación a ${room.name}`}
                                  >
                                    <Plus size={17} />
                                  </IconButton>
                                </Tooltip>
                              )}
                              <Tooltip title="Editar sala">
                                <IconButton
                                  size="small"
                                  onClick={() => setEditTarget({ kind: 'room', entity: room })}
                                  aria-label={`Editar sala ${room.name}`}
                                >
                                  <Pencil size={17} />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title={room.is_active ? 'Inactivar sala' : 'Reactivar sala'}>
                                <span>
                                  <IconButton
                                    size="small"
                                    disabled={busyEntityId === room.id}
                                    onClick={() => void toggleEntity('room', room)}
                                    aria-label={room.is_active ? 'Inactivar sala' : 'Reactivar sala'}
                                  >
                                    <Power size={17} />
                                  </IconButton>
                                </span>
                              </Tooltip>
                              {canDelete && !room.is_active && (
                                <Tooltip title="Eliminar registro erróneo">
                                  <IconButton
                                    size="small"
                                    color="error"
                                    onClick={() => setDeleteTarget({ kind: 'room', entity: room })}
                                    aria-label={`Eliminar definitivamente sala ${room.name}`}
                                  >
                                    <Trash2 size={17} />
                                  </IconButton>
                                </Tooltip>
                              )}
                            </Stack>
                          )}
                        </Stack>

                        <Stack direction="row" useFlexGap flexWrap="wrap" gap={1} sx={{ mt: 2 }}>
                          {room.care_units.map((careUnit) => (
                            <Box
                              key={careUnit.id}
                              sx={{
                                minWidth: 112,
                                border: '1px solid',
                                borderColor: careUnit.is_active ? 'primary.light' : 'divider',
                                bgcolor: careUnit.is_active
                                  ? 'rgba(18, 107, 91, 0.06)'
                                  : 'action.disabledBackground',
                                borderRadius: 1.5,
                                px: 1.25,
                                py: 1,
                                opacity: careUnit.is_active ? 1 : 0.62,
                              }}
                            >
                              <Stack direction="row" justifyContent="space-between" alignItems="center">
                                <BedDouble size={17} color={careUnit.is_active ? '#126b5b' : '#777'} />
                                {canEdit && (
                                  <Stack direction="row">
                                    <IconButton
                                      size="small"
                                      onClick={() => setEditTarget({ kind: 'careUnit', entity: careUnit })}
                                      aria-label={`Editar ubicación ${careUnitDisplayName(careUnit)}`}
                                      sx={{ p: 0.25 }}
                                    >
                                      <Pencil size={13} />
                                    </IconButton>
                                    <IconButton
                                      size="small"
                                      disabled={busyEntityId === careUnit.id}
                                      onClick={() => void toggleEntity('careUnit', careUnit)}
                                      aria-label={
                                        careUnit.is_active
                                          ? 'Inactivar ubicación'
                                          : 'Reactivar ubicación'
                                      }
                                      sx={{ p: 0.25 }}
                                    >
                                      <Power size={13} />
                                    </IconButton>
                                    {canDelete && !careUnit.is_active && (
                                      <IconButton
                                        size="small"
                                        color="error"
                                        onClick={() => setDeleteTarget({ kind: 'careUnit', entity: careUnit })}
                                        aria-label={
                                          `Eliminar definitivamente ubicación ${careUnitDisplayName(careUnit)}`
                                        }
                                        sx={{ p: 0.25 }}
                                      >
                                        <Trash2 size={13} />
                                      </IconButton>
                                    )}
                                  </Stack>
                                )}
                              </Stack>
                              <Typography variant="body2" fontWeight={750}>
                                {careUnitDisplayName(careUnit)}
                              </Typography>
                              <Chip
                                label={CARE_UNIT_TYPE_LABELS[careUnit.unit_type]}
                                size="small"
                                variant="outlined"
                                sx={{ height: 18, fontSize: 10, my: 0.4 }}
                              />
                              <Stack direction="row" spacing={0.5} alignItems="center">
                                <MapPinned size={11} />
                                <Typography variant="caption" color="text.secondary">
                                  {careUnit.layout
                                    ? `${careUnit.layout.grid_x}, ${careUnit.layout.grid_y}`
                                    : 'Sin posición'}
                                </Typography>
                              </Stack>
                            </Box>
                          ))}
                          {room.care_units.length === 0 && (
                            <Typography variant="body2" color="text.secondary">
                              Sin ubicaciones asistenciales.
                            </Typography>
                          )}
                        </Stack>
                      </Box>
                    </Grid>
                  ))}
                </Grid>
              )}
            </CardContent>
          </Card>
        ))}
      </Stack>

      {createTarget && (
        <CreateDialog
          target={createTarget}
          csrfToken={csrfToken}
          onClose={() => setCreateTarget(null)}
          onCreated={refresh}
        />
      )}
      {editTarget && (
        <EditDialog
          target={editTarget}
          csrfToken={csrfToken}
          onClose={() => setEditTarget(null)}
          onUpdated={refresh}
        />
      )}
      {deleteTarget && (
        <DeleteDialog
          target={deleteTarget}
          csrfToken={csrfToken}
          onClose={() => setDeleteTarget(null)}
          onDeleted={refresh}
        />
      )}
    </Stack>
  )
}
