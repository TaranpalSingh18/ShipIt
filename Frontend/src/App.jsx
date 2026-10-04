import { useCallback, useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { clearSession, currentUser, readSession } from './api'
import Dashboard from './components/Dashboard'
import Landing from './components/Landing'
import ReportView from './components/report/ReportView'
import TopBar from './components/TopBar'
import Workspace from './components/workspace/Workspace'

export default function App() {
  const [session, setSession] = useState(() => readSession())
  const [checking, setChecking] = useState(() => Boolean(readSession()))
  const [apiNote, setApiNote] = useState('')

  useEffect(() => {
    if (!session) return undefined
    let cancelled = false
    currentUser(session.token)
      .then((data) => {
        if (cancelled) return
        if (data?.user_email && data.user_email !== session.email) {
          setSession({ ...session, email: data.user_email })
        }
        setApiNote('')
      })
      .catch((err) => {
        if (cancelled) return
        if (err.status === 401) {
          clearSession()
          setSession(null)
          return
        }
        setApiNote(err.message)
      })
      .finally(() => {
        if (!cancelled) setChecking(false)
      })
    return () => {
      cancelled = true
    }
  }, [session])

  // Stable identity: pages use it in effect dependencies.
  const signOut = useCallback(() => {
    clearSession()
    setSession(null)
    setApiNote('')
  }, [])

  if (checking) {
    return (
      <div className="splash" role="status">
        <span className="spinner" aria-hidden="true" />
        <span className="sr-only">Checking your session</span>
      </div>
    )
  }

  const authed = (element) => (session ? element : <Navigate to="/" replace />)
  const props = { session, onSignOut: signOut }

  return (
    <BrowserRouter>
      {apiNote && (
        <p className="banner" role="status">
          {apiNote}
        </p>
      )}
      <Routes>
        <Route
          path="/"
          element={session ? <Navigate to="/app" replace /> : <Landing onSession={setSession} />}
        />
        <Route
          path="/app/*"
          element={authed(
            <>
              <TopBar session={session} onSignOut={signOut} />
              <Routes>
                <Route index element={<Dashboard {...props} />} />
                <Route path="new" element={<Workspace key="new" {...props} />} />
                <Route path="case/:projectId" element={<Workspace {...props} />} />
                <Route path="report/:reportId" element={<ReportView {...props} />} />
                <Route path="*" element={<Navigate to="/app" replace />} />
              </Routes>
            </>,
          )}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
