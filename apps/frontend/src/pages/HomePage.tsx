import { Building2, LayoutDashboard, Settings, UtensilsCrossed, UsersRound } from 'lucide-react'
import { useEffect, useMemo } from 'react'
import { useLocation, useRoute, useSearch } from 'wouter'

import { AdministrationDashboard } from '../modules/administration/AdministrationDashboard'
import { useAuth } from '../modules/auth/AuthContext'
import { BedMapDashboard } from '../modules/bed-map/BedMapDashboard'
import { HospitalDashboard } from '../modules/hospital/HospitalDashboard'
import { PatientChartPage } from '../modules/patients/PatientChartPage'
import { PatientsDashboard } from '../modules/patients/PatientsDashboard'
import { FoodProductionDashboard } from '../modules/food-production/FoodProductionDashboard'
import { AppNavigationItem, AppShell } from '../shared/layout'

type ModuleId = 'hospital' | 'bed-map' | 'patients' | 'food-production' | 'administration'

const MODULE_PATHS: Record<ModuleId, string> = {
  hospital: '/hospital',
  'bed-map': '/bed-map',
  patients: '/patients',
  'food-production': '/food-production',
  administration: '/administration',
}

export function HomePage() {
  const { logout, session } = useAuth()
  const [location, navigate] = useLocation()
  const search = useSearch()
  const [, detailRoute] = useRoute('/patients/:patientId/:tab')
  const [, patientRoute] = useRoute('/patients/:patientId')
  const user = session!.user
  const canEdit = user.roles.some((role) => role === 'administrador' || role === 'jefatura')
  const canDelete = user.roles.includes('administrador')
  const canReadAdministration = user.roles.some(
    (role) => role === 'administrador' || role === 'jefatura',
  )
  const canReadPatients = user.roles.some(
    (role) => role === 'administrador' || role === 'jefatura' || role === 'nutricionista',
  )
  const canMutatePatients = user.roles.some(
    (role) => role === 'jefatura' || role === 'nutricionista',
  )
  const canReadBedMap = user.roles.some((role) =>
    ['administrador', 'jefatura', 'nutricionista', 'alimentacion'].includes(role),
  )
  const canReadFoodProduction = user.roles.some((role) => role === 'jefatura' || role === 'alimentacion')
  const defaultPath = user.roles.includes('alimentacion') && !canReadPatients
    ? '/bed-map'
    : user.roles.includes('nutricionista') && !canReadAdministration
      ? '/patients'
      : '/hospital'

  useEffect(() => {
    if (location === '/') navigate(defaultPath, { replace: true })
    if (location.startsWith('/patients') && !canReadPatients) {
      navigate(defaultPath, { replace: true })
    }
    if (location.startsWith('/administration') && !canReadAdministration) {
      navigate(defaultPath, { replace: true })
    }
    if (location.startsWith('/food-production') && !canReadFoodProduction) {
      navigate(defaultPath, { replace: true })
    }
  }, [canReadAdministration, canReadFoodProduction, canReadPatients, defaultPath, location, navigate])

  const activeModule: ModuleId = location.startsWith('/patients')
    ? 'patients'
    : location.startsWith('/food-production')
      ? 'food-production'
    : location.startsWith('/bed-map')
      ? 'bed-map'
      : location.startsWith('/administration')
        ? 'administration'
        : 'hospital'

  const navigationItems = useMemo<AppNavigationItem<ModuleId>[]>(() => [
    {
      id: 'hospital',
      label: 'Estructura hospitalaria',
      description: 'Servicios, salas y camas',
      icon: Building2,
    },
    ...(canReadBedMap ? [{
      id: 'bed-map' as const,
      label: 'Mapa de camas',
      description: 'Ocupación y traslados',
      icon: LayoutDashboard,
    }] : []),
    ...(canReadPatients ? [{
      id: 'patients' as const,
      label: 'Pacientes',
      description: 'Fichas y hospitalizaciones',
      icon: UsersRound,
    }] : []),
    ...(canReadFoodProduction ? [{
      id: 'food-production' as const,
      label: 'Producción alimentaria',
      description: 'Raciones y preparaciones NE',
      icon: UtensilsCrossed,
    }] : []),
    ...(canReadAdministration ? [{
      id: 'administration' as const,
      label: 'Administración',
      description: 'Usuarios y asignaciones',
      icon: Settings,
    }] : []),
  ], [canReadAdministration, canReadBedMap, canReadFoodProduction, canReadPatients])

  function openPatient(patientId: string, admissionId?: string) {
    const params = new URLSearchParams()
    if (admissionId) params.set('admission_id', admissionId)
    const source = `${location}${search ? `?${search}` : ''}`
    params.set('return_to', source)
    navigate(`/patients/${patientId}/summary?${params}`)
  }

  let content
  if (detailRoute && canReadPatients) {
    content = (
      <PatientChartPage
        patientId={detailRoute.patientId}
        requestedTab={detailRoute.tab}
        search={search}
        roles={user.roles}
        csrfToken={session!.csrf_token}
        onNavigate={(path, replace = false) => navigate(path, { replace })}
      />
    )
  } else if (patientRoute && canReadPatients) {
    const query = location.includes('?') ? location.slice(location.indexOf('?')) : ''
    navigate(`/patients/${patientRoute.patientId}/summary${query}`, { replace: true })
    content = null
  } else if (activeModule === 'hospital') {
    content = <HospitalDashboard canEdit={canEdit} canDelete={canDelete} csrfToken={session!.csrf_token} />
  } else if (activeModule === 'bed-map') {
    content = (
      <BedMapDashboard
        userId={user.id}
        isNutritionist={user.roles.includes('nutricionista')}
        canMutateTransfers={canMutatePatients}
        canReadFoodSafety={user.roles.some((role) => ['jefatura', 'nutricionista', 'alimentacion'].includes(role))}
        csrfToken={session!.csrf_token}
        onOpenPatient={canReadPatients ? openPatient : undefined}
      />
    )
  } else if (activeModule === 'patients') {
    content = (
      <PatientsDashboard
        canMutate={canMutatePatients}
        canResolveActiveConflicts={user.roles.includes('jefatura')}
        csrfToken={session!.csrf_token}
        onOpenPatient={openPatient}
        search={search}
        onSearchChange={(next) => navigate(`/patients${next ? `?${next}` : ''}`, { replace: true })}
      />
    )
  } else if (activeModule === 'food-production') {
    content = <FoodProductionDashboard />
  } else {
    content = <AdministrationDashboard canManage={canDelete} csrfToken={session!.csrf_token} />
  }

  return (
    <AppShell
      user={user}
      items={navigationItems}
      activeModule={activeModule}
      onNavigate={(module) => navigate(MODULE_PATHS[module])}
      onLogout={() => void logout()}
    >
      {content}
    </AppShell>
  )
}
