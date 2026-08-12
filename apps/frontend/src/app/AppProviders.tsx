import { ReactNode } from 'react'

import { AuthProvider, useAuth } from '../modules/auth/AuthContext'
import { AppearanceProvider } from './theme/AppearanceContext'

function SessionAppearanceProvider({ children }: { children: ReactNode }) {
  const { session } = useAuth()
  return <AppearanceProvider userId={session?.user.id}>{children}</AppearanceProvider>
}

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <SessionAppearanceProvider>{children}</SessionAppearanceProvider>
    </AuthProvider>
  )
}
