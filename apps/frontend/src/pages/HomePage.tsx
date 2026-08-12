import { Building2, LayoutDashboard, Settings, UsersRound } from 'lucide-react'
import { useMemo, useState } from 'react'

import { AdministrationDashboard } from '../modules/administration/AdministrationDashboard'
import { useAuth } from '../modules/auth/AuthContext'
import { BedMapDashboard } from '../modules/bed-map/BedMapDashboard'
import { HospitalDashboard } from '../modules/hospital/HospitalDashboard'
import { PatientsDashboard } from '../modules/patients/PatientsDashboard'
import { AppNavigationItem, AppShell } from '../shared/layout'

type ModuleId = 'hospital' | 'bed-map' | 'patients' | 'administration'

export function HomePage() {
  const { logout, session } = useAuth()
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
  const initialModule: ModuleId = user.roles.includes('alimentacion') && !canReadPatients
    ? 'bed-map'
    : user.roles.includes('nutricionista') && !canReadAdministration
      ? 'patients'
      : 'hospital'
  const [module, setModule] = useState<ModuleId>(initialModule)

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
    ...(canReadAdministration ? [{
      id: 'administration' as const,
      label: 'Administración',
      description: 'Usuarios y asignaciones',
      icon: Settings,
    }] : []),
  ], [canReadAdministration, canReadBedMap, canReadPatients])

  return (
    <AppShell
      user={user}
      items={navigationItems}
      activeModule={module}
      onNavigate={setModule}
      onLogout={() => void logout()}
    >
      {module === 'hospital' ? (
        <HospitalDashboard
          canEdit={canEdit}
          canDelete={canDelete}
          csrfToken={session!.csrf_token}
        />
      ) : module === 'bed-map' ? (
        <BedMapDashboard
          userId={user.id}
          isNutritionist={user.roles.includes('nutricionista')}
          canMutateTransfers={canMutatePatients}
          csrfToken={session!.csrf_token}
        />
      ) : module === 'patients' ? (
        <PatientsDashboard
          canMutate={canMutatePatients}
          canResolveActiveConflicts={user.roles.includes('jefatura')}
          csrfToken={session!.csrf_token}
        />
      ) : (
        <AdministrationDashboard canManage={canDelete} csrfToken={session!.csrf_token} />
      )}
    </AppShell>
  )
}
