import { PaletteMode } from '@mui/material'
import { alpha, createTheme, responsiveFontSizes } from '@mui/material/styles'

import { createNutriwardTokens, NutriWardTokens } from './tokens'

declare module '@mui/material/styles' {
  interface Theme {
    nutriward: NutriWardTokens
  }

  interface ThemeOptions {
    nutriward?: NutriWardTokens
  }
}

export function createNutriwardTheme(mode: PaletteMode) {
  const tokens = createNutriwardTokens(mode)
  const { colors, motion, radii } = tokens
  const baseTheme = createTheme({
  nutriward: tokens,
  spacing: (factor: number) => `${factor * 8}px`,
  breakpoints: { values: tokens.breakpoints },
  shape: { borderRadius: radii.sm },
  transitions: {
    duration: {
      shortest: motion.duration.fast,
      shorter: motion.duration.fast,
      short: motion.duration.standard,
      standard: motion.duration.standard,
      complex: motion.duration.deliberate,
      enteringScreen: motion.duration.deliberate,
      leavingScreen: motion.duration.fast,
    },
    easing: {
      easeInOut: motion.easing.standard,
      easeOut: motion.easing.enter,
      easeIn: motion.easing.exit,
      sharp: motion.easing.exit,
    },
  },
  palette: {
    mode,
    primary: {
      light: colors.primary.light,
      main: colors.primary.main,
      dark: colors.primary.dark,
      contrastText: colors.primary.contrast,
    },
    secondary: {
      light: colors.secondary.light,
      main: colors.secondary.main,
      dark: colors.secondary.dark,
      contrastText: colors.secondary.contrast,
    },
    background: {
      default: colors.background.default,
      paper: colors.background.paper,
    },
    text: colors.text,
    divider: colors.border.default,
    success: {
      light: colors.success.light,
      main: colors.success.main,
      dark: colors.success.dark,
      contrastText: colors.success.contrast,
    },
    warning: {
      light: colors.warning.light,
      main: colors.warning.main,
      dark: colors.warning.dark,
      contrastText: colors.warning.contrast,
    },
    error: {
      light: colors.error.light,
      main: colors.error.main,
      dark: colors.error.dark,
      contrastText: colors.error.contrast,
    },
    info: {
      light: colors.info.light,
      main: colors.info.main,
      dark: colors.info.dark,
      contrastText: colors.info.contrast,
    },
    action: {
      active: colors.text.secondary,
      hover: alpha(colors.primary.main, 0.07),
      selected: alpha(colors.primary.main, 0.12),
      disabled: colors.text.disabled,
      disabledBackground: colors.background.subtle,
      focus: alpha(colors.primary.main, 0.18),
    },
  },
  typography: {
    fontFamily: 'Inter, "Segoe UI", Roboto, Arial, sans-serif',
    h1: { fontSize: '2rem', lineHeight: 1.2, fontWeight: 760, letterSpacing: '-0.025em' },
    h2: { fontSize: '1.5rem', lineHeight: 1.25, fontWeight: 750, letterSpacing: '-0.015em' },
    h3: { fontSize: '1.25rem', lineHeight: 1.3, fontWeight: 740 },
    h4: { fontSize: '1.75rem', lineHeight: 1.25, fontWeight: 760, letterSpacing: '-0.02em' },
    h5: { fontSize: '1.25rem', lineHeight: 1.35, fontWeight: 740 },
    h6: { fontSize: '1.05rem', lineHeight: 1.4, fontWeight: 730 },
    subtitle1: { fontWeight: 700 },
    body1: { fontSize: '0.9375rem', lineHeight: 1.55 },
    body2: { fontSize: '0.875rem', lineHeight: 1.5 },
    button: { fontSize: '0.875rem', fontWeight: 720, textTransform: 'none' },
    overline: { fontSize: '0.6875rem', lineHeight: 1.6, fontWeight: 780, letterSpacing: '0.08em' },
    caption: { fontSize: '0.75rem', lineHeight: 1.45 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        html: { minWidth: 320, backgroundColor: colors.background.default },
        body: { minWidth: 320, overflowX: 'hidden' },
        '#root': { minHeight: '100vh' },
        '::selection': { backgroundColor: colors.primary.light, color: colors.primary.dark },
        '*:focus-visible': {
          outline: `3px solid ${alpha(colors.primary.main, 0.62)}`,
          outlineOffset: 2,
        },
        '@media (prefers-reduced-motion: reduce)': {
          '*, *::before, *::after': {
            animationDuration: '0.01ms !important',
            animationIterationCount: '1 !important',
            scrollBehavior: 'auto !important',
            transitionDuration: '0.01ms !important',
          },
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: {
          minHeight: 40,
          borderRadius: radii.sm,
          paddingInline: 16,
          transition: `background-color ${motion.duration.standard}ms ${motion.easing.standard}, border-color ${motion.duration.standard}ms ${motion.easing.standard}, box-shadow ${motion.duration.standard}ms ${motion.easing.standard}, transform ${motion.duration.standard}ms ${motion.easing.standard}`,
          '&:active:not(.Mui-disabled)': { transform: 'translateY(1px)' },
        },
        sizeSmall: { minHeight: 34, paddingInline: 12 },
        containedPrimary: {
          '&:hover': { backgroundColor: colors.primary.dark },
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          minWidth: 40,
          minHeight: 40,
          borderRadius: radii.sm,
          transition: `background-color ${motion.duration.standard}ms ${motion.easing.standard}, color ${motion.duration.standard}ms ${motion.easing.standard}`,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: 'none' },
        outlined: { borderColor: colors.border.default },
      },
    },
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: { borderRadius: radii.md, boxShadow: tokens.shadows.low },
      },
    },
    MuiCardContent: {
      styleOverrides: { root: { padding: 20, '&:last-child': { paddingBottom: 20 } } },
    },
    MuiTextField: {
      defaultProps: { size: 'small', variant: 'outlined' },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: radii.sm,
          backgroundColor: colors.background.elevated,
          transition: `box-shadow ${motion.duration.standard}ms ${motion.easing.standard}`,
          '&.Mui-focused': { boxShadow: `0 0 0 3px ${alpha(colors.primary.main, 0.13)}` },
          '& .MuiOutlinedInput-notchedOutline': { borderColor: colors.border.strong },
          '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: colors.primary.main },
        },
      },
    },
    MuiSelect: {
      defaultProps: { size: 'small' },
    },
    MuiTabs: {
      styleOverrides: { root: { minHeight: 44 }, indicator: { height: 3, borderRadius: '3px 3px 0 0' } },
    },
    MuiTab: {
      styleOverrides: { root: { minHeight: 44, textTransform: 'none', fontWeight: 700 } },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: radii.pill, fontWeight: 700 },
        sizeSmall: { minHeight: 24 },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: { borderRadius: radii.sm, border: '1px solid', alignItems: 'center' },
        standardSuccess: { borderColor: alpha(colors.success.main, 0.32), backgroundColor: colors.success.light },
        standardWarning: { borderColor: alpha(colors.warning.main, 0.32), backgroundColor: colors.warning.light },
        standardError: { borderColor: alpha(colors.error.main, 0.32), backgroundColor: colors.error.light },
        standardInfo: { borderColor: alpha(colors.info.main, 0.32), backgroundColor: colors.info.light },
      },
    },
    MuiDialog: {
      defaultProps: { transitionDuration: motion.duration.deliberate },
      styleOverrides: { paper: { borderRadius: radii.lg, boxShadow: tokens.shadows.high } },
    },
    MuiDialogTitle: { styleOverrides: { root: { fontWeight: 750, paddingBottom: 12 } } },
    MuiDrawer: {
      defaultProps: { transitionDuration: motion.duration.deliberate },
      styleOverrides: { paper: { backgroundColor: colors.background.paper, borderColor: colors.border.default } },
    },
    MuiTooltip: {
      defaultProps: { arrow: true, enterDelay: 450 },
      styleOverrides: { tooltip: { borderRadius: radii.xs, fontSize: '0.75rem' } },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: colors.border.subtle, paddingBlock: 12 },
        head: { color: colors.text.secondary, fontWeight: 760, backgroundColor: colors.background.subtle },
      },
    },
    MuiAppBar: {
      defaultProps: { color: 'inherit', elevation: 0 },
      styleOverrides: {
        root: {
          backgroundColor: alpha(colors.background.paper, 0.96),
          borderBottom: `1px solid ${colors.border.default}`,
          color: colors.text.primary,
          backdropFilter: 'blur(10px)',
        },
      },
    },
    MuiSnackbarContent: {
      styleOverrides: { root: { borderRadius: radii.sm, boxShadow: tokens.shadows.medium } },
    },
  },
  })

  return responsiveFontSizes(baseTheme, { breakpoints: ['sm', 'md', 'lg'] })
}

export const nutriwardTheme = createNutriwardTheme('light')
