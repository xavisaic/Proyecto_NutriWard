import { Redirect, Route, Switch } from 'wouter'

import { LoginPage } from '../modules/auth/LoginPage'
import { ProtectedRoute } from '../modules/auth/ProtectedRoute'
import { HomePage } from '../pages/HomePage'

export function AppRouter() {
  return (
    <Switch>
      <Route path="/login" component={LoginPage} />
      <Route path="/">
        {() => (
          <ProtectedRoute>
            <HomePage />
          </ProtectedRoute>
        )}
      </Route>
      <Route>
        <Redirect to="/" replace />
      </Route>
    </Switch>
  )
}
