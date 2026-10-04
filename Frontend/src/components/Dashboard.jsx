import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { friendlyError, listProjects } from '../api'
import { Ring } from './report/charts'
import './dashboard.css'

function status(p) {
  const r = p.latest_report
  if (r?.status === 'success') return { cls: String(r.verdict || '').toLowerCase().replace(/\s+/g, '-'), text: r.verdict }
  if (r && (r.status === 'pending' || r.status === 'running')) return { cls: 'running', text: 'Writing memo' }
  if (r?.status === 'failed') return { cls: 'failed', text: 'Memo failed' }
  if (p.fully_answered) return { cls: 'promising', text: 'Ready for memo' }
  return { cls: 'plain', text: 'Questions open' }
}

export default function Dashboard({ session, onSignOut }) {
  const [projects, setProjects] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let live = true
    listProjects(session.token)
      .then((list) => live && setProjects(list))
      .catch((err) => {
        if (!live) return
        if (err.status === 401) onSignOut()
        else setError(friendlyError(err))
      })
    return () => {
      live = false
    }
  }, [session.token, onSignOut])

  return (
    <main className="shell dash">
      <header className="page-head">
        <div>
          <h1 className="display">Your cases</h1>
          <p>Each case is one idea, worked through the six questions and into an investor memo.</p>
        </div>
        <Link className="btn lg" to="/app/new">
          New case
        </Link>
      </header>

      {error && <p className="error">{error}</p>}
      {!projects && !error && <span className="spinner" role="status" aria-label="Loading cases" />}

      {projects && projects.length === 0 && (
        <div className="dash-empty">
          <h2 className="display">Start with one paragraph.</h2>
          <p>Describe who the idea is for and what goes wrong for them. ShipIt asks what’s missing, researches the market, and writes the memo.</p>
          <Link className="btn lg" to="/app/new">
            Start a case
          </Link>
        </div>
      )}

      {projects && projects.length > 0 && (
        <ul className="cases">
          {projects.map((p) => {
            const s = status(p)
            const r = p.latest_report
            const to = r?.status === 'success' ? `/app/report/${r.id}` : `/app/case/${p.id}`
            return (
              <li key={p.id}>
                <Link to={to} className="case">
                  <div className="case-score">
                    {r?.status === 'success' ? (
                      <Ring value={r.readiness} size={64} stroke={6} label="" />
                    ) : (
                      <span className="case-score-empty" aria-hidden="true" />
                    )}
                  </div>
                  <div className="case-body">
                    <div className="case-top">
                      <h2>{r?.product_name || p.name || 'Untitled'}</h2>
                      <span className={`badge ${s.cls}`}>{s.text}</span>
                    </div>
                    <p className="case-idea">{p.idea || 'No idea written yet.'}</p>
                    <p className="case-meta">
                      {p.updated_at && `Updated ${new Date(p.updated_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })}`}
                      {p.competitors > 0 && ` · ${p.competitors} competitors found`}
                    </p>
                  </div>
                </Link>
                {r?.status === 'success' && (
                  <Link className="case-alt" to={`/app/case/${p.id}`}>
                    Open case
                  </Link>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </main>
  )
}
