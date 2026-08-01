import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Pagination,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import Grid from '@mui/material/Grid2'
import { BedDouble, LogOut, Plus, RefreshCw, Search, UserRound, UserRoundCheck } from 'lucide-react'
import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'

import {
  Admission,
  AdmissionList,
  ApiError,
  apiRequest,
  HospitalCareUnit,
  HospitalStructure,
  IdentityStatus,
  Patient,
  PatientList,
} from '../../shared/services/api'

interface PatientsDashboardProps {
  canMutate: boolean
  csrfToken: string
}

const IDENTITY_LABELS: Record<IdentityStatus, string> = {
  unidentified: 'Paciente NN',
  provisional: 'Provisorio',
  identified: 'Identificado',
}

const IDENTITY_COLORS: Record<IdentityStatus, 'warning' | 'info' | 'success'> = {
  unidentified: 'warning',
  provisional: 'info',
  identified: 'success',
}

function patientName(patient: Patient): string {
  if (patient.identity_status === 'unidentified') {
    return `Paciente NN · ${patient.temporary_identifier}`
  }
  const name = [patient.given_names, patient.first_surname, patient.second_surname]
    .filter(Boolean)
    .join(' ')
  return name || `Ficha provisoria · ${patient.temporary_identifier}`
}

function formatRut(rut: string | null): string {
  if (!rut) return 'Sin RUT confirmado'
  const [body, digit] = rut.split('-')
  return `${body.replace(/\B(?=(\d{3})+(?!\d))/g, '.')}-${digit}`
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function requestError(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : 'No fue posible completar la operación.'
}

function PatientCreateDialog({
  csrfToken,
  onClose,
  onCreated,
}: {
  csrfToken: string
  onClose: () => void
  onCreated: (patient: Patient) => void
}) {
  const [kind, setKind] = useState<'identified' | 'unidentified'>('identified')
  const [rut, setRut] = useState('')
  const [givenNames, setGivenNames] = useState('')
  const [firstSurname, setFirstSurname] = useState('')
  const [secondSurname, setSecondSurname] = useState('')
  const [description, setDescription] = useState('')
  const [hospitalIdentifier, setHospitalIdentifier] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const patient = kind === 'unidentified'
        ? await apiRequest<Patient>(
          '/patients/unidentified',
          {
            method: 'POST',
            body: JSON.stringify({
              provisional_description: description || null,
              hospital_identifier: hospitalIdentifier || null,
            }),
          },
          csrfToken,
        )
        : await apiRequest<Patient>(
          '/patients',
          {
            method: 'POST',
            body: JSON.stringify({
              rut,
              given_names: givenNames,
              first_surname: firstSurname,
              second_surname: secondSurname || null,
              hospital_identifier: hospitalIdentifier || null,
            }),
          },
          csrfToken,
        )
      onCreated(patient)
    } catch (caught) {
      setError(requestError(caught))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open fullWidth maxWidth="sm" onClose={saving ? undefined : onClose}>
      <Box component="form" onSubmit={(event) => void submit(event)}>
        <DialogTitle>Crear paciente</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {error && <Alert severity="error">{error}</Alert>}
            <FormControl fullWidth>
              <InputLabel id="patient-kind-label">Tipo de ficha</InputLabel>
              <Select
                labelId="patient-kind-label"
                label="Tipo de ficha"
                value={kind}
                onChange={(event) => setKind(event.target.value as typeof kind)}
              >
                <MenuItem value="identified">Paciente identificado</MenuItem>
                <MenuItem value="unidentified">Paciente NN</MenuItem>
              </Select>
            </FormControl>
            {kind === 'identified' ? (
              <>
                <TextField required label="RUT" value={rut} onChange={(event) => setRut(event.target.value)} />
                <TextField required label="Nombres" value={givenNames} onChange={(event) => setGivenNames(event.target.value)} />
                <TextField required label="Primer apellido" value={firstSurname} onChange={(event) => setFirstSurname(event.target.value)} />
                <TextField label="Segundo apellido" value={secondSurname} onChange={(event) => setSecondSurname(event.target.value)} />
              </>
            ) : (
              <TextField
                autoFocus
                label="Descripción provisoria"
                value={description}
                multiline
                minRows={3}
                onChange={(event) => setDescription(event.target.value)}
                helperText="El sistema asignará un identificador NN único."
              />
            )}
            <TextField
              label="Identificador hospitalario"
              value={hospitalIdentifier}
              onChange={(event) => setHospitalIdentifier(event.target.value)}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button onClick={onClose} disabled={saving}>Cancelar</Button>
          <Button variant="contained" type="submit" disabled={saving}>
            {saving ? 'Guardando…' : kind === 'identified' ? 'Crear paciente' : 'Crear paciente NN'}
          </Button>
        </DialogActions>
      </Box>
    </Dialog>
  )
}

function IdentityDialog({
  csrfToken,
  patient,
  onClose,
  onUpdated,
}: {
  csrfToken: string
  patient: Patient
  onClose: () => void
  onUpdated: (patient: Patient) => void
}) {
  const [rut, setRut] = useState('')
  const [givenNames, setGivenNames] = useState('')
  const [firstSurname, setFirstSurname] = useState('')
  const [reason, setReason] = useState('')
  const [canonical, setCanonical] = useState<Patient | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function identify(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    setCanonical(null)
    try {
      const updated = await apiRequest<Patient>(
        `/patients/${patient.id}/identity`,
        {
          method: 'PATCH',
          body: JSON.stringify({ rut, given_names: givenNames, first_surname: firstSurname }),
        },
        csrfToken,
      )
      onUpdated(updated)
    } catch (caught) {
      setError(requestError(caught))
      if (caught instanceof ApiError && caught.status === 409) {
        try {
          const matches = await apiRequest<PatientList>(`/patients?q=${encodeURIComponent(rut)}`)
          setCanonical(matches.items.find((item) => item.id !== patient.id && item.rut) ?? null)
        } catch {
          // The original conflict remains visible.
        }
      }
    } finally {
      setSaving(false)
    }
  }

  async function reconcile() {
    if (!canonical || !window.confirm('¿Confirma la conciliación de ambas fichas? Esta acción conserva todo el historial.')) return
    setSaving(true)
    setError(null)
    try {
      const updated = await apiRequest<Patient>(
        `/patients/${patient.id}/reconcile`,
        {
          method: 'POST',
          body: JSON.stringify({ rut: canonical.rut, reason }),
        },
        csrfToken,
      )
      onUpdated(updated)
    } catch (caught) {
      setError(requestError(caught))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open fullWidth maxWidth="md" onClose={saving ? undefined : onClose}>
      <Box component="form" onSubmit={(event) => void identify(event)}>
        <DialogTitle>Identificar paciente NN</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {error && <Alert severity={canonical ? 'warning' : 'error'}>{error}</Alert>}
            <Alert severity="info">
              La ficha conservará el identificador {patient.temporary_identifier}, sus hospitalizaciones y ubicaciones.
            </Alert>
            <TextField required label="RUT confirmado" value={rut} onChange={(event) => setRut(event.target.value)} />
            <TextField required label="Nombres" value={givenNames} onChange={(event) => setGivenNames(event.target.value)} />
            <TextField required label="Primer apellido" value={firstSurname} onChange={(event) => setFirstSurname(event.target.value)} />
            {canonical && (
              <>
                <Divider />
                <Typography variant="h6">Conciliación requerida</Typography>
                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="overline">Ficha provisoria</Typography>
                        <Typography fontWeight={750}>{patientName(patient)}</Typography>
                        <Typography variant="body2">{patient.active_admission ? 'Hospitalización activa' : 'Sin hospitalización activa'}</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="overline">Ficha canónica</Typography>
                        <Typography fontWeight={750}>{patientName(canonical)}</Typography>
                        <Typography variant="body2">{formatRut(canonical.rut)}</Typography>
                        <Typography variant="body2">{canonical.active_admission ? 'Hospitalización activa' : 'Sin hospitalización activa'}</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
                <TextField
                  required
                  label="Motivo de conciliación"
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  inputProps={{ minLength: 10 }}
                  multiline
                  minRows={2}
                />
              </>
            )}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button onClick={onClose} disabled={saving}>Cancelar</Button>
          {canonical ? (
            <Button
              variant="contained"
              color="warning"
              disabled={saving || reason.trim().length < 10}
              onClick={() => void reconcile()}
            >
              Conciliar fichas
            </Button>
          ) : (
            <Button variant="contained" type="submit" disabled={saving}>Confirmar identidad</Button>
          )}
        </DialogActions>
      </Box>
    </Dialog>
  )
}

function LocationDialog({
  admission,
  beds,
  csrfToken,
  occupied,
  onClose,
  onUpdated,
}: {
  admission: Admission
  beds: Array<HospitalCareUnit & { roomName: string; serviceName: string }>
  csrfToken: string
  occupied: Map<string, string>
  onClose: () => void
  onUpdated: () => void
}) {
  const [careUnitId, setCareUnitId] = useState('')
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const isTransfer = Boolean(admission.current_location)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await apiRequest(
        `/admissions/${admission.id}/location`,
        {
          method: 'POST',
          body: JSON.stringify({ care_unit_id: careUnitId, reason: reason || null }),
        },
        csrfToken,
      )
      onUpdated()
    } catch (caught) {
      setError(
        caught instanceof ApiError && caught.status === 409
          ? `Conflicto: ${caught.message} Revise otra cama sin perder los datos ingresados.`
          : requestError(caught),
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open fullWidth maxWidth="sm" onClose={saving ? undefined : onClose}>
      <Box component="form" onSubmit={(event) => void submit(event)}>
        <DialogTitle>{isTransfer ? 'Trasladar de cama' : 'Asignar cama inicial'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {error && <Alert severity="error">{error}</Alert>}
            <FormControl required fullWidth>
              <InputLabel id="bed-label">Cama</InputLabel>
              <Select
                labelId="bed-label"
                label="Cama"
                value={careUnitId}
                onChange={(event) => setCareUnitId(event.target.value)}
              >
                {beds.map((bed) => {
                  const occupant = occupied.get(bed.id)
                  const isCurrent = admission.current_location?.care_unit_id === bed.id
                  return (
                    <MenuItem key={bed.id} value={bed.id} disabled={Boolean(occupant) || isCurrent}>
                      {bed.serviceName} · {bed.roomName} · {bed.label || `Cama ${bed.code}`}
                      {occupant ? ' — Ocupada' : isCurrent ? ' — Ubicación actual' : ' — Disponible'}
                    </MenuItem>
                  )
                })}
              </Select>
            </FormControl>
            <TextField
              label="Motivo"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              multiline
              minRows={2}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button onClick={onClose} disabled={saving}>Cancelar</Button>
          <Button type="submit" variant="contained" disabled={saving || !careUnitId}>
            {isTransfer ? 'Confirmar traslado' : 'Asignar cama'}
          </Button>
        </DialogActions>
      </Box>
    </Dialog>
  )
}

export function PatientsDashboard({ canMutate, csrfToken }: PatientsDashboardProps) {
  const [patients, setPatients] = useState<PatientList | null>(null)
  const [query, setQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [identityStatus, setIdentityStatus] = useState<IdentityStatus | ''>('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<Patient | null>(null)
  const [structure, setStructure] = useState<HospitalStructure | null>(null)
  const [activeAdmissions, setActiveAdmissions] = useState<AdmissionList | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [identityOpen, setIdentityOpen] = useState(false)
  const [locationOpen, setLocationOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ page: String(page), page_size: '10' })
      if (submittedQuery) params.set('q', submittedQuery)
      if (identityStatus) params.set('identity_status', identityStatus)
      const [patientResponse, hospitalResponse, admissionResponse] = await Promise.all([
        apiRequest<PatientList>(`/patients?${params}`),
        apiRequest<HospitalStructure>('/hospital/structure'),
        apiRequest<AdmissionList>('/admissions/active'),
      ])
      setPatients(patientResponse)
      setStructure(hospitalResponse)
      setActiveAdmissions(admissionResponse)
      if (selected) {
        const refreshed = await apiRequest<Patient>(`/patients/${selected.id}`)
        setSelected(refreshed)
      }
    } catch (caught) {
      setError(requestError(caught))
    } finally {
      setLoading(false)
    }
  }, [identityStatus, page, selected?.id, submittedQuery])

  useEffect(() => {
    void load()
  }, [load])

  const beds = useMemo(
    () => (structure?.items.flatMap((service) =>
      service.rooms.flatMap((room) =>
        room.care_units
          .filter((careUnit) => careUnit.unit_type === 'bed' && careUnit.is_active)
          .map((careUnit) => ({
            ...careUnit,
            roomName: room.name,
            serviceName: service.name,
          })),
      ),
    ) ?? []),
    [structure],
  )
  const occupied = useMemo(
    () => new Map(
      (activeAdmissions?.items ?? [])
        .filter((admission) => admission.current_location)
        .map((admission) => [
          admission.current_location!.care_unit_id,
          admission.admission_identifier,
        ]),
    ),
    [activeAdmissions],
  )

  async function openPatient(patientId: string) {
    setError(null)
    try {
      setSelected(await apiRequest<Patient>(`/patients/${patientId}`))
    } catch (caught) {
      setError(requestError(caught))
    }
  }

  async function createAdmission() {
    if (!selected) return
    try {
      await apiRequest(
        '/admissions',
        { method: 'POST', body: JSON.stringify({ patient_id: selected.id }) },
        csrfToken,
      )
      await load()
    } catch (caught) {
      setError(requestError(caught))
    }
  }

  async function endAdmission() {
    if (!selected?.active_admission) return
    if (!window.confirm('¿Confirma el término de esta hospitalización? La cama vigente será liberada.')) return
    try {
      await apiRequest(
        `/admissions/${selected.active_admission.id}/status`,
        {
          method: 'PATCH',
          body: JSON.stringify({ status: 'discharged', reason: 'Alta registrada desde ficha de paciente.' }),
        },
        csrfToken,
      )
      await load()
    } catch (caught) {
      setError(requestError(caught))
    }
  }

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" gap={2}>
        <Box>
          <Typography variant="h4" fontWeight={800}>Pacientes</Typography>
          <Typography color="text.secondary">
            Identidad, hospitalizaciones y ubicación actual con trazabilidad completa.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button startIcon={<RefreshCw size={17} />} onClick={() => void load()}>Actualizar</Button>
          {canMutate && (
            <Button variant="contained" startIcon={<Plus size={17} />} onClick={() => setCreateOpen(true)}>
              Crear paciente
            </Button>
          )}
        </Stack>
      </Stack>

      <Card variant="outlined">
        <CardContent>
          <Box
            component="form"
            onSubmit={(event) => {
              event.preventDefault()
              setPage(1)
              setSubmittedQuery(query)
            }}
          >
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              <TextField
                fullWidth
                label="Buscar por nombre, RUT o identificador"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
              <FormControl sx={{ minWidth: 190 }}>
                <InputLabel id="identity-filter-label">Estado de identidad</InputLabel>
                <Select
                  labelId="identity-filter-label"
                  label="Estado de identidad"
                  value={identityStatus}
                  onChange={(event) => {
                    setIdentityStatus(event.target.value as IdentityStatus | '')
                    setPage(1)
                  }}
                >
                  <MenuItem value="">Todos</MenuItem>
                  <MenuItem value="unidentified">Paciente NN</MenuItem>
                  <MenuItem value="provisional">Provisorio</MenuItem>
                  <MenuItem value="identified">Identificado</MenuItem>
                </Select>
              </FormControl>
              <Button type="submit" variant="outlined" startIcon={<Search size={17} />}>Buscar</Button>
            </Stack>
          </Box>
        </CardContent>
      </Card>

      {error && <Alert severity="error">{error}</Alert>}
      {loading && !patients ? (
        <Box sx={{ py: 6, textAlign: 'center' }}><CircularProgress /></Box>
      ) : patients?.items.length === 0 ? (
        <Alert severity="info">No hay pacientes que coincidan con la búsqueda.</Alert>
      ) : (
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, lg: selected ? 5 : 12 }}>
            <Stack spacing={1.5}>
              {patients?.items.map((patient) => (
                <Card key={patient.id} variant="outlined">
                  <CardActionArea onClick={() => void openPatient(patient.id)}>
                    <CardContent>
                      <Stack direction="row" justifyContent="space-between" gap={2}>
                        <Box>
                          <Typography fontWeight={800}>{patientName(patient)}</Typography>
                          <Typography variant="body2" color="text.secondary">
                            {formatRut(patient.rut)}
                            {patient.hospital_identifier ? ` · ${patient.hospital_identifier}` : ''}
                          </Typography>
                        </Box>
                        <Chip
                          label={IDENTITY_LABELS[patient.identity_status]}
                          color={IDENTITY_COLORS[patient.identity_status]}
                          size="small"
                        />
                      </Stack>
                      {patient.active_admission && (
                        <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1.5 }}>
                          <BedDouble size={16} />
                          <Typography variant="body2">
                            {patient.active_admission.current_location
                              ? `${patient.active_admission.current_location.service_name} · ${patient.active_admission.current_location.room_name} · ${patient.active_admission.current_location.care_unit_label || patient.active_admission.current_location.care_unit_code}`
                              : 'Hospitalización activa sin cama'}
                          </Typography>
                        </Stack>
                      )}
                    </CardContent>
                  </CardActionArea>
                </Card>
              ))}
              {patients && patients.total > patients.page_size && (
                <Pagination
                  page={page}
                  count={Math.ceil(patients.total / patients.page_size)}
                  onChange={(_, nextPage) => setPage(nextPage)}
                />
              )}
            </Stack>
          </Grid>

          {selected && (
            <Grid size={{ xs: 12, lg: 7 }}>
              <Card variant="outlined">
                <CardContent>
                  <Stack spacing={2}>
                    <Stack direction="row" justifyContent="space-between" gap={2}>
                      <Box>
                        <Typography variant="overline">Ficha del paciente</Typography>
                        <Typography variant="h5" fontWeight={800}>{patientName(selected)}</Typography>
                        <Typography color="text.secondary">{formatRut(selected.rut)}</Typography>
                      </Box>
                      <Chip
                        label={IDENTITY_LABELS[selected.identity_status]}
                        color={IDENTITY_COLORS[selected.identity_status]}
                      />
                    </Stack>
                    {selected.provisional_description && (
                      <Alert severity="info">{selected.provisional_description}</Alert>
                    )}
                    {canMutate && selected.identity_status !== 'identified' && (
                      <Button
                        startIcon={<UserRoundCheck size={17} />}
                        variant="outlined"
                        onClick={() => setIdentityOpen(true)}
                      >
                        Identificar paciente
                      </Button>
                    )}
                    <Divider />
                    <Typography variant="h6">Hospitalización actual</Typography>
                    {!selected.active_admission ? (
                      <Stack alignItems="flex-start" spacing={1}>
                        <Typography color="text.secondary">Sin hospitalización activa.</Typography>
                        {canMutate && (
                          <Button variant="contained" startIcon={<Plus size={17} />} onClick={() => void createAdmission()}>
                            Crear hospitalización
                          </Button>
                        )}
                      </Stack>
                    ) : (
                      <Stack spacing={1.5}>
                        <Typography fontWeight={750}>{selected.active_admission.admission_identifier}</Typography>
                        <Typography variant="body2">
                          Ingreso: {formatDateTime(selected.active_admission.admitted_at)}
                        </Typography>
                        {selected.active_admission.current_location ? (
                          <Alert severity="success" icon={<BedDouble size={20} />}>
                            <strong>{selected.active_admission.current_location.service_name}</strong>
                            {' · '}{selected.active_admission.current_location.room_name}
                            {' · '}{selected.active_admission.current_location.care_unit_label || `Cama ${selected.active_admission.current_location.care_unit_code}`}
                          </Alert>
                        ) : (
                          <Alert severity="warning">Hospitalización activa sin cama asignada.</Alert>
                        )}
                        {canMutate && (
                          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                            <Button variant="outlined" startIcon={<BedDouble size={17} />} onClick={() => setLocationOpen(true)}>
                              {selected.active_admission.current_location ? 'Trasladar de cama' : 'Asignar cama inicial'}
                            </Button>
                            <Button color="error" startIcon={<LogOut size={17} />} onClick={() => void endAdmission()}>
                              Terminar hospitalización
                            </Button>
                          </Stack>
                        )}
                      </Stack>
                    )}
                    {selected.admissions && selected.admissions.length > 0 && (
                      <>
                        <Divider />
                        <Typography variant="subtitle1" fontWeight={750}>
                          Historial ({selected.admissions.length})
                        </Typography>
                        {selected.admissions.map((admission) => (
                          <Typography key={admission.id} variant="body2">
                            {admission.admission_identifier} · {admission.status} · {formatDateTime(admission.admitted_at)}
                          </Typography>
                        ))}
                      </>
                    )}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>
      )}

      {canMutate && createOpen && (
        <PatientCreateDialog
          csrfToken={csrfToken}
          onClose={() => setCreateOpen(false)}
          onCreated={(patient) => {
            setCreateOpen(false)
            setSelected(patient)
            void load()
          }}
        />
      )}
      {canMutate && identityOpen && selected && (
        <IdentityDialog
          csrfToken={csrfToken}
          patient={selected}
          onClose={() => setIdentityOpen(false)}
          onUpdated={(patient) => {
            setIdentityOpen(false)
            setSelected(patient)
            void load()
          }}
        />
      )}
      {canMutate && locationOpen && selected?.active_admission && (
        <LocationDialog
          admission={selected.active_admission}
          beds={beds}
          occupied={occupied}
          csrfToken={csrfToken}
          onClose={() => setLocationOpen(false)}
          onUpdated={() => {
            setLocationOpen(false)
            void load()
          }}
        />
      )}
    </Stack>
  )
}
