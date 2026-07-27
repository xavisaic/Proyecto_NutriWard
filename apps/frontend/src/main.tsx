import React from 'react'
import ReactDOM from 'react-dom/client'
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material'

import { AppRouter } from './app/router'
import { AuthProvider } from './modules/auth/AuthContext'

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#126b5b', dark: '#0b4b40' },
    secondary: { main: '#315b7d' },
  },
  shape: { borderRadius: 8 },
  typography: { fontFamily: '"Segoe UI", Arial, sans-serif' },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </ThemeProvider>
  </React.StrictMode>,
)
