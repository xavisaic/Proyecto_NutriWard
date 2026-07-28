import {
  Alert,
  Box,
  Button,
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
  Paper,
  Select,
  Stack,
  Switch,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
} from '@mui/material'
import { Plus, UserPen, X } from 'lucide-react'
import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'

import {
  ApiError,
  apiRequest,
  HospitalStructure,
  NutritionistServiceAssignmentList,
  Role,
  RoleList,
  User,
  UserList,
} from '../../shared/services/api'

interface AdministrationDashboardProps {
  canManage: boolean
  csrfToken: string
}

interface UserDialogState {
  user?: User
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : 'No fue posible completar la operación.'
}

function UserDialog({
  state,
  csrfToken,
  onClose,
  onSaved,
}: {
  state: UserDialogState
  csrfToken: string
  onClose: () => void
  onSaved: () => Promise<void>
}) {
  const [email, setEmail] = useState(state.user?.email ?? '')
  const [fullName, setFullName] = useState(state.user?.full_name ?? '')
  const [password, setPassword] = useState('')
  const [isActive, setIsActive] = useState(state.user?.is_active ?? true)
  const [error, setError] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setIsSaving(true)
    setError('')
    try {
      const isEditing = Boolean(state.user)
      await apiRequest(
        isEditing ? `/users/${state.user!.id}` : '/users',
        {
          method: isEditing ? 'PATCH' : 'POST',
          body: JSON.stringify({
            email,
            full_name: fullName,
            is_active: isActive,
            ...(!isEditing ? { password } : {}),
          }),
        },
        csrfToken,
      )
      await onSaved()
      onClose()
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Dialog open onClose={isSaving ? undefined : onClose} fullWidth maxWidth="sm">
      <Box component="form" onSubmit={(event) => void submit(event)}>
        <DialogTitle>{state.user ? 'Editar usuario' : 'Crear usuario'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {error && <Alert severity="error">{error}</Alert>}
            <TextField
              label="Nombre completo"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              required
              inputProps={{ maxLength: 160 }}
            />
            <TextField
              label="Correo electrónico"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              inputProps={{ maxLength: 320 }}
            />
            {!state.user && (
              <TextField
                label="Contraseña inicial"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                inputProps={{ minLength: 8, maxLength: 256 }}
                helperText="Mínimo 8 caracteres."
              />
            )}
            <FormControlLabel
              control={
                <Switch
                  checked={isActive}
                  onChange={(event) => setIsActive(event.target.checked)}
                />
              }
              label={isActive ? 'Usuario activo' : 'Usuario inactivo'}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button onClick={onClose} disabled={isSaving}>
            Cancelar
          </Button>
          <Button type="submit" variant="contained" disabled={isSaving}>
            {isSaving ? 'Guardando…' : state.user ? 'Guardar cambios' : 'Crear usuario'}
          </Button>
        </DialogActions>
      </Box>
    </Dialog>
  )
}

export function AdministrationDashboard({
  canManage,
  csrfToken,
}: AdministrationDashboardProps) {
  const [view, setView] = useState<'users' | 'assignments'>('users')
  const [users, setUsers] = useState<User[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [assignments, setAssignments] = useState<
    NutritionistServiceAssignmentList['items']
  >([])
  const [services, setServices] = useState<HospitalStructure['items']>([])
  const [roleSelections, setRoleSelections] = useState<Record<string, string>>({})
  const [nutritionistId, setNutritionistId] = useState('')
  const [serviceId, setServiceId] = useState('')
  const [dialog, setDialog] = useState<UserDialogState | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')

  const loadData = useCallback(async () => {
    setError('')
    try {
      const [userResponse, roleResponse, assignmentResponse, structureResponse] =
        await Promise.all([
          apiRequest<UserList>('/users?offset=0&limit=100'),
          apiRequest<RoleList>('/roles'),
          apiRequest<NutritionistServiceAssignmentList>(
            '/nutritionist-service-assignments?include_inactive=true',
          ),
          apiRequest<HospitalStructure>('/hospital/structure?include_inactive=false'),
        ])
      setUsers(userResponse.items)
      setRoles(roleResponse.items)
      setAssignments(assignmentResponse.items)
      setServices(structureResponse.items)
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadData()
  }, [loadData])

  const nutritionists = useMemo(
    () =>
      users.filter(
        (user) => user.is_active && user.roles.includes('nutricionista'),
      ),
    [users],
  )

  async function mutate(operation: () => Promise<unknown>) {
    setIsSaving(true)
    setError('')
    try {
      await operation()
      await loadData()
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setIsSaving(false)
    }
  }

  function availableRoles(user: User) {
    return roles.filter((role) => !user.roles.includes(role.name))
  }

  if (isLoading) {
    return (
      <Stack alignItems="center" sx={{ py: 8 }}>
        <CircularProgress aria-label="Cargando administración" />
      </Stack>
    )
  }

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" component="h1" fontWeight={800}>
          Administración
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 0.5 }}>
          Gestión de usuarios, roles y coberturas habituales por servicio.
        </Typography>
      </Box>

      <Paper variant="outlined">
        <Tabs
          value={view}
          onChange={(_, nextView) => setView(nextView)}
          aria-label="Vistas de administración"
        >
          <Tab value="users" label="Usuarios y roles" />
          <Tab value="assignments" label="Asignaciones de servicios" />
        </Tabs>
      </Paper>

      {error && <Alert severity="error">{error}</Alert>}

      {view === 'users' && (
        <Stack spacing={2}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="h6" component="h2" fontWeight={750}>
              Usuarios y roles
            </Typography>
            {canManage && (
              <Button
                variant="contained"
                startIcon={<Plus size={18} />}
                onClick={() => setDialog({})}
              >
                Crear usuario
              </Button>
            )}
          </Stack>
          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Usuario</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell>Roles</TableCell>
                  {canManage && <TableCell align="right">Acciones</TableCell>}
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <Typography fontWeight={700}>{user.full_name}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {user.email}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        color={user.is_active ? 'success' : 'default'}
                        label={user.is_active ? 'Activo' : 'Inactivo'}
                      />
                    </TableCell>
                    <TableCell>
                      <Stack direction="row" gap={0.75} flexWrap="wrap">
                        {user.roles.map((roleName) => {
                          const role = roles.find((item) => item.name === roleName)
                          return (
                            <Chip
                              key={roleName}
                              size="small"
                              label={roleName}
                              onDelete={
                                canManage && role
                                  ? () =>
                                      void mutate(() =>
                                        apiRequest(
                                          `/users/${user.id}/roles/${role.id}`,
                                          { method: 'DELETE' },
                                          csrfToken,
                                        ),
                                      )
                                  : undefined
                              }
                              deleteIcon={<X size={14} />}
                              aria-label={`Rol ${roleName} de ${user.full_name}`}
                            />
                          )
                        })}
                        {user.roles.length === 0 && (
                          <Typography variant="body2" color="text.secondary">
                            Sin roles
                          </Typography>
                        )}
                      </Stack>
                      {canManage && user.is_active && availableRoles(user).length > 0 && (
                        <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                          <FormControl size="small" sx={{ minWidth: 150 }}>
                            <InputLabel id={`role-label-${user.id}`}>Nuevo rol</InputLabel>
                            <Select
                              labelId={`role-label-${user.id}`}
                              label="Nuevo rol"
                              value={roleSelections[user.id] ?? ''}
                              onChange={(event) =>
                                setRoleSelections((current) => ({
                                  ...current,
                                  [user.id]: event.target.value,
                                }))
                              }
                            >
                              {availableRoles(user).map((role) => (
                                <MenuItem key={role.id} value={role.id}>
                                  {role.name}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                          <Button
                            size="small"
                            disabled={!roleSelections[user.id] || isSaving}
                            onClick={() =>
                              void mutate(() =>
                                apiRequest(
                                  `/users/${user.id}/roles`,
                                  {
                                    method: 'POST',
                                    body: JSON.stringify({
                                      role_id: roleSelections[user.id],
                                    }),
                                  },
                                  csrfToken,
                                ),
                              )
                            }
                          >
                            Asignar rol
                          </Button>
                        </Stack>
                      )}
                    </TableCell>
                    {canManage && (
                      <TableCell align="right">
                        <Button
                          size="small"
                          startIcon={<UserPen size={16} />}
                          onClick={() => setDialog({ user })}
                        >
                          Editar
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Stack>
      )}

      {view === 'assignments' && (
        <Stack spacing={2}>
          <Box>
            <Typography variant="h6" component="h2" fontWeight={750}>
              Asignaciones de servicios
            </Typography>
            <Alert severity="info" icon={false} sx={{ mt: 1 }}>
              Estas asignaciones representan la cobertura habitual del nutricionista; no son
              exclusivas ni restringen apoyos en otros servicios.
            </Alert>
          </Box>

          {canManage && (
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Stack
                direction={{ xs: 'column', md: 'row' }}
                spacing={2}
                alignItems={{ md: 'center' }}
              >
                <FormControl fullWidth size="small">
                  <InputLabel id="nutritionist-label">Nutricionista</InputLabel>
                  <Select
                    labelId="nutritionist-label"
                    label="Nutricionista"
                    value={nutritionistId}
                    onChange={(event) => setNutritionistId(event.target.value)}
                  >
                    {nutritionists.map((user) => (
                      <MenuItem key={user.id} value={user.id}>
                        {user.full_name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl fullWidth size="small">
                  <InputLabel id="service-label">Servicio habitual</InputLabel>
                  <Select
                    labelId="service-label"
                    label="Servicio habitual"
                    value={serviceId}
                    onChange={(event) => setServiceId(event.target.value)}
                  >
                    {services.map((service) => (
                      <MenuItem key={service.id} value={service.id}>
                        {service.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <Button
                  variant="contained"
                  sx={{ whiteSpace: 'nowrap' }}
                  disabled={!nutritionistId || !serviceId || isSaving}
                  onClick={() =>
                    void mutate(() =>
                      apiRequest(
                        '/nutritionist-service-assignments',
                        {
                          method: 'POST',
                          body: JSON.stringify({
                            nutritionist_user_id: nutritionistId,
                            service_id: serviceId,
                          }),
                        },
                        csrfToken,
                      ),
                    )
                  }
                >
                  Agregar asignación
                </Button>
              </Stack>
            </Paper>
          )}

          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Nutricionista</TableCell>
                  <TableCell>Servicio habitual</TableCell>
                  <TableCell>Estado</TableCell>
                  {canManage && <TableCell align="right">Acciones</TableCell>}
                </TableRow>
              </TableHead>
              <TableBody>
                {assignments.map((assignment) => (
                  <TableRow key={assignment.id}>
                    <TableCell>
                      <Typography fontWeight={700}>
                        {assignment.nutritionist_name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {assignment.nutritionist_email}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {assignment.service_name}{' '}
                      <Typography component="span" variant="caption" color="text.secondary">
                        ({assignment.service_code})
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        color={assignment.is_active ? 'success' : 'default'}
                        label={assignment.is_active ? 'Activa' : 'Inactiva'}
                      />
                    </TableCell>
                    {canManage && (
                      <TableCell align="right">
                        {assignment.is_active && (
                          <Button
                            size="small"
                            color="warning"
                            disabled={isSaving}
                            onClick={() =>
                              void mutate(() =>
                                apiRequest(
                                  `/nutritionist-service-assignments/${assignment.id}`,
                                  { method: 'DELETE' },
                                  csrfToken,
                                ),
                              )
                            }
                          >
                            Inactivar
                          </Button>
                        )}
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Stack>
      )}

      {dialog && (
        <UserDialog
          state={dialog}
          csrfToken={csrfToken}
          onClose={() => setDialog(null)}
          onSaved={loadData}
        />
      )}
    </Stack>
  )
}
