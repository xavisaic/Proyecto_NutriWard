import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from 'react'

import { ApiError, apiRequest, Session } from '../../shared/services/api'

interface AuthContextValue {
  session: Session | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let active = true
    apiRequest<Session>('/auth/me')
      .then((restoredSession) => {
        if (active) setSession(restoredSession)
      })
      .catch((error) => {
        if (active && (!(error instanceof ApiError) || error.status !== 401)) {
          console.error('No fue posible restaurar la sesión.', error)
        }
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      isLoading,
      login: async (email, password) => {
        const authenticatedSession = await apiRequest<Session>('/auth/login', {
          method: 'POST',
          body: JSON.stringify({ email, password }),
        })
        setSession(authenticatedSession)
      },
      logout: async () => {
        if (!session) return
        try {
          await apiRequest<void>(
            '/auth/logout',
            { method: 'POST' },
            session.csrf_token,
          )
        } catch (error) {
          if (!(error instanceof ApiError) || error.status !== 401) {
            console.error('No fue posible registrar el cierre de sesión.', error)
          }
        } finally {
          setSession(null)
        }
      },
    }),
    [isLoading, session],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth debe utilizarse dentro de AuthProvider.')
  }
  return context
}
