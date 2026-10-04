import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { createProject, friendlyError, getProject, getReport, runQuery, startReport } from '../../api'
import { DIMENSIONS, asList, asText, findSentiment, formatElapsed, prefersReducedMotion, readAnswer } from '../../format'
import ReportProgress from './ReportProgress'
import './workspace.css'

const RUN_STEPS = [
  'Checking your answers to the six questions',
  'Writing a product brief',
  'Searching the web for competitors',
  'Reading reviews and forums about them',
  'Finding gaps in the market',
]

function RunWait({ elapsed }) {
  return (
    <div className="runwait" role="status" aria-live="polite">
      <div className="runwait-head">
        <span className="spinner" aria-hidden="true" />
        <strong>Researching your idea</strong>
        <span className="rp-time">{formatElapsed(elapsed)}</span>
      </div>
      <ul>
        {RUN_STEPS.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ul>
      <p className="hint">This takes one to three minutes when every question is answered, and a few seconds when some are still open.</p>
    </div>
  )
}

function Progress6({ answered }) {
  const r = 26
  const c = 2 * Math.PI * r
  return (
    <svg className="p6" viewBox="0 0 64 64" width="64" height="64" aria-hidden="true">
      <circle cx="32" cy="32" r={r} fill="none" strokeWidth="6" className="p6-track" />
      <circle
        cx="32"
        cy="32"
        r={r}
        fill="none"
        strokeWidth="6"
        strokeLinecap="round"
        className="p6-arc"
        strokeDasharray={`${(c * answered) / 6} ${c}`}
        transform="rotate(-90 32 32)"
      />
      <text x="32" y="37" textAnchor="middle" className="p6-num">
        {answered}/6
      </text>
    </svg>
  )
}

export default function Workspace({ session, onSignOut }) {
  const { projectId: routeId } = useParams()
  const navigate = useNavigate()
  const projectId = routeId ? Number(routeId) : null
  const [loading, setLoading] = useState(Boolean(projectId))
  const [caseName, setCaseName] = useState('')
  const [idea, setIdea] = useState('')
  const [result, setResult] = useState(null)
  const [drafts, setDrafts] = useState({})
  const [reports, setReports] = useState([])
  const [running, setRunning] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [error, setError] = useState('')
  const [live, setLive] = useState(null)
  const abortRef = useRef(null)
  const followRef = useRef(null)

  const fail = useCallback(
    (err) => {
      if (err?.name === 'AbortError') return
      if (err?.status === 401) onSignOut()
      else setError(friendlyError(err))
    },
    [onSignOut],
  )

  // Load an existing case from the server.
  useEffect(() => {
    if (!projectId) return undefined
    let live = true
    getProject(session.token, projectId)
      .then((data) => {
        if (!live) return
        setCaseName(data.name || '')
        setIdea(data.idea || '')
        setResult(data.query_response?.question_mapping && Object.keys(data.query_response.question_mapping).length ? data.query_response : null)
        setReports(data.reports || [])
        const running = (data.reports || []).find((r) => r.status === 'pending' || r.status === 'running')
        if (running) setLive(running)
      })
      .catch((err) => live && fail(err))
      .finally(() => live && setLoading(false))
    return () => {
      live = false
    }
  }, [projectId, session.token, fail])

  useEffect(() => {
    if (!running) return undefined
    const started = Date.now()
    const id = setInterval(() => setElapsed(Date.now() - started), 1000)
    return () => clearInterval(id)
  }, [running])

  // Poll a memo that is being written.
  const liveId = live && (live.status === 'pending' || live.status === 'running') ? live.id : null
  useEffect(() => {
    if (!liveId) return undefined
    let timer
    let active = true
    const tick = async () => {
      try {
        const next = await getReport(session.token, liveId)
        if (!active) return
        setLive(next)
        if (next.status === 'pending' || next.status === 'running') timer = setTimeout(tick, 2500)
        else setReports((list) => [next, ...list.filter((r) => r.id !== next.id)])
      } catch (err) {
        if (active) fail(err)
      }
    }
    timer = setTimeout(tick, 1200)
    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [liveId, session.token, fail])

  const questions = asList(result?.follow_up_questions).map(String)
  const mapping = result?.question_mapping || {}
  const answeredCount = DIMENSIONS.filter((d) => readAnswer(mapping, d.key).answered).length
  const ready = Boolean(result?.fully_answered)
  const competitors = asList(result?.market_analysis).filter((c) => c?.comp_name)
  const voice = result?.customer_voice || {}
  const gaps = asList(voice.market_gaps).filter((g) => g?.gap)
  const context = asText(result?.product_context)
  const latestDone = reports.find((r) => r.status === 'success')

  async function submit(text) {
    const controller = new AbortController()
    abortRef.current = controller
    setRunning(true)
    setError('')
    setElapsed(0)
    try {
      let id = projectId
      if (!id) {
        const created = await createProject(session.token, caseName.trim() || 'Untitled', controller.signal)
        id = created.project_id
      }
      const data = await runQuery(session.token, id, text, controller.signal)
      const next = data?.query_response
      if (!next || typeof next !== 'object') throw new Error('The research came back in an unexpected shape. Try again.')
      setResult(next)
      setDrafts({})
      if (!projectId) navigate(`/app/case/${id}`, { replace: true })
      requestAnimationFrame(() => {
        const target = next.fully_answered ? document.getElementById('findings') : followRef.current
        target?.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' })
        if (!next.fully_answered) followRef.current?.querySelector('textarea')?.focus()
      })
    } catch (err) {
      fail(err)
    } finally {
      setRunning(false)
    }
  }

  function onRun(event) {
    event.preventDefault()
    const text = idea.trim()
    if (text.length < 20) {
      setError('Add a little more: one sentence on who it’s for and what goes wrong for them is enough.')
      return
    }
    submit(text)
  }

  function onFollowUp(event) {
    event.preventDefault()
    const text = questions
      .map((q) => ((drafts[q] || '').trim() ? `${q}\n${drafts[q].trim()}` : ''))
      .filter(Boolean)
      .join('\n\n')
    if (!text) {
      setError('Answer at least one of the open questions.')
      return
    }
    submit(text)
  }

  async function writeMemo() {
    setError('')
    try {
      const next = await startReport(session.token, projectId)
      setLive(next)
    } catch (err) {
      fail(err)
    }
  }

  if (loading) {
    return (
      <main className="shell ws-loading">
        <span className="spinner" role="status" aria-label="Loading the case" />
      </main>
    )
  }

  return (
    <main className="shell ws">
      <div className="ws-main">
        <header className="ws-head">
          <Link to="/app" className="back">
            All cases
          </Link>
          {result ? (
            <h1 className="display">
              {(caseName && caseName !== 'Untitled' ? caseName : latestDone?.product_name) || 'Untitled case'}
            </h1>
          ) : (
            <label className="name-field">
              <span className="sr-only">Case name</span>
              <input
                className="display"
                value={caseName}
                onChange={(e) => setCaseName(e.target.value)}
                placeholder="Name this case"
                maxLength={80}
              />
            </label>
          )}
        </header>

        <section className="ws-block" aria-labelledby="idea-h">
          <h2 id="idea-h" className="ws-h">
            <span className="ws-step">1</span>The idea
          </h2>
          <form onSubmit={onRun} className="idea-form">
            <textarea
              className="textarea idea"
              value={idea}
              onChange={(e) => setIdea(e.target.value)}
              readOnly={Boolean(result)}
              rows={5}
              placeholder="Example: A tool that gives final-year engineering students company-specific mock interviews during placement season. Practice today is generic, and students fail rounds they could have prepared for."
              aria-describedby="idea-hint"
            />
            {!result && (
              <div className="row">
                <p id="idea-hint" className="hint">
                  Say who it’s for, what goes wrong for them, and how you’d fix it. ShipIt asks about anything missing.
                </p>
                <button className="btn lg" type="submit" disabled={running}>
                  {running ? 'Researching…' : 'Research this idea'}
                </button>
              </div>
            )}
          </form>
          {running && !result && <RunWait elapsed={elapsed} />}
        </section>

        {result && (
          <section className="ws-block" aria-labelledby="six-h">
            <h2 id="six-h" className="ws-h">
              <span className="ws-step">2</span>The six questions investors ask first
            </h2>
            <ol className="six">
              {DIMENSIONS.map((d) => {
                const a = readAnswer(mapping, d.key)
                return (
                  <li key={d.key} className={a.answered ? 'ok' : 'open'}>
                    <span className="six-mark" aria-hidden="true">
                      {a.answered ? (
                        <svg viewBox="0 0 16 16" width="14" height="14">
                          <path d="M3 8.5l3 3 7-7" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      ) : (
                        '?'
                      )}
                    </span>
                    <div>
                      <h3>{d.label}</h3>
                      <p>{a.answered ? a.answer : d.question}</p>
                    </div>
                    <span className="sr-only">{a.answered ? 'Answered' : 'Still open'}</span>
                  </li>
                )
              })}
            </ol>

            {questions.length > 0 && (
              <form className="follow" ref={followRef} onSubmit={onFollowUp}>
                <h3>Still open</h3>
                <p className="hint">Answer what you can. Short, specific answers make a stronger memo.</p>
                {questions.map((q) => (
                  <label className="field" key={q}>
                    <span>{q}</span>
                    <textarea
                      className="textarea"
                      rows={3}
                      value={drafts[q] || ''}
                      onChange={(e) => setDrafts((d) => ({ ...d, [q]: e.target.value }))}
                    />
                  </label>
                ))}
                <button className="btn lg" type="submit" disabled={running}>
                  {running ? 'Researching…' : 'Send answers'}
                </button>
              </form>
            )}
            {running && result && <RunWait elapsed={elapsed} />}
          </section>
        )}

        {ready && (
          <section className="ws-block" id="findings" aria-labelledby="find-h">
            <h2 id="find-h" className="ws-h">
              <span className="ws-step">3</span>What the research found
            </h2>
            {context && (
              <details className="brief">
                <summary>Product brief</summary>
                <div className="brief-text">{context}</div>
              </details>
            )}
            {competitors.length > 0 && (
              <>
                <h3 className="ws-sub">Competitors ({competitors.length})</h3>
                <ul className="found-comps">
                  {competitors.map((c) => {
                    const s = findSentiment(voice, c.comp_name)
                    return (
                      <li key={c.comp_name}>
                        <div className="fc-top">
                          <b>{c.comp_name}</b>
                          {s?.satisfaction_summary && <span className="fc-sat">{String(s.satisfaction_summary).split(/[—–.-]/)[0]}</span>}
                        </div>
                        <p>{c.competitor_because}</p>
                      </li>
                    )
                  })}
                </ul>
              </>
            )}
            {gaps.length > 0 && (
              <>
                <h3 className="ws-sub">Gaps in the market</h3>
                <ul className="found-gaps">
                  {gaps.map((g) => (
                    <li key={g.gap}>
                      <b>{g.gap}</b>
                      <p>{g.product_opportunity}</p>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </section>
        )}
        {error && (
          <p className="error ws-error" role="alert">
            {error}
          </p>
        )}
      </div>

      <aside className="ws-rail" aria-label="Investor memo">
        <div className="rail-card">
          <div className="rail-top">
            <Progress6 answered={answeredCount} />
            <div>
              <p className="rail-k">{ready ? 'Ready for the memo' : result ? 'Questions answered' : 'Start with the idea'}</p>
              <p className="hint">
                {ready
                  ? 'All six questions hold. ShipIt can write the investor memo.'
                  : result
                    ? 'Answer the open questions to unlock the memo.'
                    : 'Write a paragraph and ShipIt checks it against six questions.'}
              </p>
            </div>
          </div>

          {liveId ? (
            <ReportProgress report={live} />
          ) : live?.status === 'success' || latestDone ? (
            <div className="rail-done">
              {live?.status === 'success' && <ReportProgress report={live} />}
              <Link className="btn lg block" to={`/app/report/${(live?.status === 'success' ? live : latestDone).id}`}>
                Open the memo
              </Link>
              <button type="button" className="btn ghost block" onClick={writeMemo} disabled={!ready}>
                Write a new version
              </button>
            </div>
          ) : (
            <>
              {live?.status === 'failed' && <ReportProgress report={live} />}
              <button type="button" className="btn lg block" disabled={!ready || !projectId} onClick={writeMemo}>
                {live?.status === 'failed' ? 'Try again' : 'Write the investor memo'}
              </button>
            </>
          )}

          <ul className="rail-includes">
            <li>12-page PDF with an executive one-pager</li>
            <li>Sourced market size and growth</li>
            <li>Competitor logos, homepages, pricing and funding</li>
            <li>Feature matrix, positioning map and risk register</li>
            <li>Verdict, scorecard and a 90-day plan</li>
          </ul>
        </div>

        {reports.filter((r) => r.status === 'success').length > 0 && (
          <div className="rail-card">
            <p className="rail-k">Earlier memos</p>
            <ul className="history">
              {reports
                .filter((r) => r.status === 'success')
                .map((r) => (
                  <li key={r.id}>
                    <Link to={`/app/report/${r.id}`}>
                      <span>{new Date(r.created_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}</span>
                      <span className={`badge ${String(r.verdict || '').toLowerCase().replace(/\s+/g, '-')}`}>{r.verdict}</span>
                    </Link>
                  </li>
                ))}
            </ul>
          </div>
        )}
      </aside>
    </main>
  )
}
