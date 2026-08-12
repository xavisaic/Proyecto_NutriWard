import { Alert, Snackbar } from '@mui/material'

interface FeedbackSnackbarProps {
  open: boolean
  message: string | null
  onClose: () => void
  severity?: 'success' | 'info' | 'warning' | 'error'
}

export function FeedbackSnackbar({ open, message, onClose, severity = 'info' }: FeedbackSnackbarProps) {
  return (
    <Snackbar open={open} autoHideDuration={6000} onClose={onClose} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
      <Alert severity={severity} variant="filled" onClose={onClose} sx={{ width: '100%' }}>
        {message}
      </Alert>
    </Snackbar>
  )
}
