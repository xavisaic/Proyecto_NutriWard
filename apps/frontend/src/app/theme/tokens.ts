import { PaletteMode } from '@mui/material'

const lightColors = {
  primary: { light: '#DCECE7', main: '#155E54', dark: '#0E463F', contrast: '#FFFFFF' },
  secondary: { light: '#E3EBF0', main: '#48657A', dark: '#344C5E', contrast: '#FFFFFF' },
  background: { default: '#F5F4EF', subtle: '#EFEEE8', paper: '#FFFEFB', elevated: '#FFFFFF' },
  text: { primary: '#24312E', secondary: '#5C6965', disabled: '#8C9692' },
  border: { subtle: '#E6E7E2', default: '#D6DAD5', strong: '#AEB8B3' },
  success: { light: '#E5F2E9', main: '#397557', dark: '#28563F', contrast: '#FFFFFF' },
  warning: { light: '#FFF1D2', main: '#9A6700', dark: '#704B00', contrast: '#2E2100' },
  error: { light: '#FBE8E6', main: '#B54747', dark: '#873535', contrast: '#FFFFFF' },
  info: { light: '#E4EFF5', main: '#47728A', dark: '#31566A', contrast: '#FFFFFF' },
  transfer: { light: '#EEEAF8', main: '#68549A', dark: '#4E3C7A', border: '#9B8BC4', contrast: '#FFFFFF' },
  operational: {
    bedFree: { background: '#EDF6EF', border: '#397557', foreground: '#28563F' },
    bedOccupied: { background: '#FFF6DF', border: '#9A6700', foreground: '#704B00' },
    bedSelected: { background: '#E6F1EE', border: '#155E54', foreground: '#0E463F' },
    transferPending: { background: '#EEEAF8', border: '#68549A', foreground: '#4E3C7A' },
  },
} as const

const darkColors = {
  primary: { light: '#1E4A43', main: '#68B8A6', dark: '#A8D5C8', contrast: '#0C1A17' },
  secondary: { light: '#273844', main: '#82A4BC', dark: '#BCD0DE', contrast: '#111A20' },
  background: { default: '#111816', subtle: '#19211F', paper: '#17201E', elevated: '#1D2825' },
  text: { primary: '#F0F3F0', secondary: '#B2BDB8', disabled: '#7B8883' },
  border: { subtle: '#26322F', default: '#35433F', strong: '#596964' },
  success: { light: '#173125', main: '#70B88D', dark: '#A8D8B9', contrast: '#0C1A11' },
  warning: { light: '#342A13', main: '#D8A544', dark: '#F2D18A', contrast: '#201700' },
  error: { light: '#371E1E', main: '#E17A78', dark: '#F0A5A3', contrast: '#220E0E' },
  info: { light: '#1B2F39', main: '#76A8C1', dark: '#B3D1E0', contrast: '#0C171D' },
  transfer: { light: '#2D2740', main: '#A692D4', dark: '#CABDE8', border: '#7869A0', contrast: '#171124' },
  operational: {
    bedFree: { background: '#172B21', border: '#70B88D', foreground: '#B8DEC5' },
    bedOccupied: { background: '#302713', border: '#D8A544', foreground: '#F2D18A' },
    bedSelected: { background: '#19322D', border: '#68B8A6', foreground: '#B9E0D6' },
    transferPending: { background: '#2D2740', border: '#A692D4', foreground: '#D6CBEF' },
  },
} as const

const sharedTokens = {
  spacing: { xxs: 4, xs: 8, sm: 12, md: 16, lg: 24, xl: 32, xxl: 40, section: 48 },
  radii: { xs: 6, sm: 10, md: 14, lg: 18, pill: 999 },
  motion: {
    duration: { fast: 150, standard: 180, deliberate: 200 },
    easing: {
      standard: 'cubic-bezier(0.2, 0, 0, 1)',
      enter: 'cubic-bezier(0, 0, 0.2, 1)',
      exit: 'cubic-bezier(0.4, 0, 1, 1)',
    },
  },
  breakpoints: { xs: 0, sm: 600, md: 900, lg: 1200, xl: 1536 },
  layout: { navigationWidth: 248, appBarHeight: 64, contentMaxWidth: 1536 },
} as const

export function createNutriwardTokens(mode: PaletteMode) {
  return {
    ...sharedTokens,
    mode,
    colors: mode === 'dark' ? darkColors : lightColors,
    shadows: mode === 'dark'
      ? {
          none: 'none',
          low: '0 1px 2px rgba(0, 0, 0, 0.28), 0 5px 18px rgba(0, 0, 0, 0.18)',
          medium: '0 12px 34px rgba(0, 0, 0, 0.32)',
          high: '0 22px 58px rgba(0, 0, 0, 0.42)',
        }
      : {
          none: 'none',
          low: '0 1px 2px rgba(27, 48, 43, 0.06), 0 4px 14px rgba(27, 48, 43, 0.04)',
          medium: '0 10px 30px rgba(27, 48, 43, 0.10)',
          high: '0 18px 50px rgba(27, 48, 43, 0.14)',
        },
  } as const
}

export type NutriWardTokens = ReturnType<typeof createNutriwardTokens>

// Tema claro estable para pruebas y consumidores que no requieren cambio dinámico.
export const nutriwardTokens = createNutriwardTokens('light')
