import { CssBaseline, PaletteMode, ThemeProvider } from '@mui/material'
import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from 'react'

import { createNutriwardTheme } from './theme'

export type AppearancePreference = 'light' | 'dark' | 'system'

interface AppearanceContextValue {
  preference: AppearancePreference
  resolvedMode: PaletteMode
  setPreference: (preference: AppearancePreference) => void
}

const GUEST_SCOPE = 'guest'
const STORAGE_PREFIX = 'nutriward:appearance:'
const AppearanceContext = createContext<AppearanceContextValue | null>(null)

function isPreference(value: string | null): value is AppearancePreference {
  return value === 'light' || value === 'dark' || value === 'system'
}

export function appearanceStorageKey(userId?: string) {
  return `${STORAGE_PREFIX}${userId ?? GUEST_SCOPE}`
}

function readPreference(userId?: string): AppearancePreference | null {
  try {
    const value = window.localStorage.getItem(appearanceStorageKey(userId))
    return isPreference(value) ? value : null
  } catch {
    return null
  }
}

function writePreference(userId: string | undefined, preference: AppearancePreference) {
  try {
    window.localStorage.setItem(appearanceStorageKey(userId), preference)
  } catch {
    // La preferencia sigue activa en memoria cuando el almacenamiento no está disponible.
  }
}

function systemUsesDarkMode() {
  return typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function AppearanceProvider({ children, userId }: { children: ReactNode; userId?: string }) {
  const [preference, setPreferenceState] = useState<AppearancePreference>(
    () => readPreference(userId) ?? 'light',
  )
  const [systemDark, setSystemDark] = useState(systemUsesDarkMode)

  useEffect(() => {
    const stored = readPreference(userId)
    if (stored) {
      setPreferenceState(stored)
      return
    }

    const fallback = userId ? (readPreference() ?? 'light') : 'light'
    setPreferenceState(fallback)
    if (userId) writePreference(userId, fallback)
  }, [userId])

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const query = window.matchMedia('(prefers-color-scheme: dark)')
    const update = (event: MediaQueryListEvent) => setSystemDark(event.matches)
    setSystemDark(query.matches)
    query.addEventListener?.('change', update)
    return () => query.removeEventListener?.('change', update)
  }, [])

  const resolvedMode: PaletteMode = preference === 'system'
    ? (systemDark ? 'dark' : 'light')
    : preference
  const theme = useMemo(() => createNutriwardTheme(resolvedMode), [resolvedMode])

  useEffect(() => {
    document.documentElement.style.colorScheme = resolvedMode
    document.documentElement.dataset.colorScheme = resolvedMode
  }, [resolvedMode])

  const value = useMemo<AppearanceContextValue>(() => ({
    preference,
    resolvedMode,
    setPreference: (nextPreference) => {
      setPreferenceState(nextPreference)
      writePreference(userId, nextPreference)
    },
  }), [preference, resolvedMode, userId])

  return (
    <AppearanceContext.Provider value={value}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </AppearanceContext.Provider>
  )
}

export function useAppearance() {
  const context = useContext(AppearanceContext)
  if (!context) throw new Error('useAppearance debe utilizarse dentro de AppearanceProvider.')
  return context
}
