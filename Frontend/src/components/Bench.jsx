import { useEffect, useRef, useState } from 'react'
import PdfReader from './PdfReader'
import {
  apiUrl,
  createProject,
  friendlyError,
  getTask,
  runQuery,
  startPdf,
  writeBench,
} from '../api'
import {
  DIMENSIONS,
  asList,
  asText,
  findSentiment,
  formatElapsed,
  leadFrom,
  phaseLabel,
  prefersReducedMotion,
  readAnswer,
  readTaskPayload,
  secondsLabel,
} from '../format'

const PDF_BUSY = ['QUEUED', 'PENDING', 'STARTED', 'RETRY']

function RunWait({ elapsed }) {
  return (
    <div className="wait">
      <p role="status">
        Running the questions. Discovery, then product context, then market intel, then customer voice. This page fills in when the run finishes.
      </p>
      <p className="clock" aria-hidden="true">{formatElapsed(elapsed)}</p>
      <div className="track" aria-hidden="true"><span /></div>
    </div>
  )
}

function longestPhase(phases) {
  return phases.reduce(
    (best, phase) => (phase.duration_s > (best?.duration_s || 0) ? phase : best),
    null,
  )
}

function PhaseBar({ phases, total }) {
  const longest = longestPhase(phases)
  const [pinned, setPinned] = useState(longest?.phase || '')
  const [hover, setHover] = useState('')
  const active = phases.find((phase) => phase.phase === (hover || pinned)) || longest

  if (!phases.length || !active) return null

  return (
    <div className="block">
      <div className="phases">
        {phases.map((phase) => {
          const on = phase.phase === active.phase
          return (
            <button
              key={phase.phase}
              type="button"
              className={on ? 'phase on' : 'phase'}
              style={{ flexGrow: Math.max(Number(phase.duration_s) || 0, 0.25), flexBasis: 0 }}
              onClick={() => setPinned(phase.phase)}
              onMouseEnter={() => setHover(phase.phase)}
              onMouseLeave={() => setHover('')}
              onFocus={() => setHover(phase.phase)}
              onBlur={() => setHover('')}
            >
              <span className="sr-only">
                {phaseLabel(phase.phase)}, {secondsLabel(phase.duration_s)}
              </span>
            </button>
          )
        })}
      </div>
      <p className="phase-read">
        {phaseLabel(active.phase)} took {secondsLabel(active.duration_s)}. The run took {secondsLabel(total)}.
      </p>
    </div>
  )
}

function CompetitorBoard({ competitors, voice }) {
  const [name, setName] = useState(competitors[0]?.comp_name || '')
  const selectedRef = useRef(null)
  const fromKeyboard = useRef(false)
  const selected = competitors.find((item) => item.comp_name === name) || competitors[0]
  const sentiment = selected ? findSentiment(voice, selected.comp_name) : null
  const complaints = asList(sentiment?.common_complaints).map((item) => String(item))

  useEffect(() => {
    if (!fromKeyboard.current) return
    fromKeyboard.current = false
    selectedRef.current?.focus()
  }, [name])

  function move(delta) {
    const index = competitors.findIndex((item) => item.comp_name === selected?.comp_name)
    const next = competitors[Math.min(competitors.length - 1, Math.max(0, index + delta))]
    if (!next || next.comp_name === selected?.comp_name) return
    fromKeyboard.current = true
    setName(next.comp_name)
  }

  function onKeyDown(event) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      move(1)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      move(-1)
    } else if (event.key === 'Home') {
      event.preventDefault()
      fromKeyboard.current = true
      setName(competitors[0].comp_name)
    } else if (event.key === 'End') {
      event.preventDefault()
      fromKeyboard.current = true
      setName(competitors[competitors.length - 1].comp_name)
    }
  }

  if (!selected) return null

  return (
    <div className="pair">
      <div role="listbox" aria-label="Competitors" className="options" onKeyDown={onKeyDown}>
        {competitors.map((item) => {
          const isSelected = item.comp_name === selected.comp_name
          return (
            <button
              key={item.comp_name}
              type="button"
              role="option"
              aria-selected={isSelected}
              tabIndex={isSelected ? 0 : -1}
              ref={isSelected ? selectedRef : null}
              className={isSelected ? 'option on' : 'option'}
              onClick={() => setName(item.comp_name)}
            >
              {item.comp_name}
            </button>
          )
        })}
      </div>
      <div className="detail" aria-live="polite">
        <h3>{selected.comp_name}</h3>
        {selected.competitor_because && <p className="prose">{selected.competitor_because}</p>}
        {sentiment?.what_users_use && <p className="prose">{sentiment.what_users_use}</p>}
        {sentiment?.satisfaction_summary && <p className="prose">{sentiment.satisfaction_summary}</p>}
        {complaints.length > 0 && (
          <ul className="plain">
            {complaints.map((item) => <li key={item}>{item}</li>)}
          </ul>
        )}
        {!sentiment && (
          <p>No customer complaints were tied to this name.</p>
        )}
      </div>
    </div>
  )
}

function pdfCopy(status, payload, waitedLong) {
  if (payload?.status === 'success') return 'The teardown is ready.'
  if (payload?.status === 'needs_more_info') return 'The teardown still has open questions.'
  if (payload?.status === 'error' || status === 'FAILURE') {
    return payload?.detail || 'The teardown failed. Start it again.'
  }
  if (status === 'SUCCESS') return payload?.detail || 'The teardown finished without a file.'
  if (status === 'STARTED') return 'Writing the teardown.'
  if (status === 'RETRY') return 'The worker is retrying the teardown.'
  if (waitedLong && (status === 'QUEUED' || status === 'PENDING')) {
    return 'Still waiting for a worker. Start Celery if this stays here.'
  }
  if (status) return 'Queued. Waiting for a worker to start the teardown.'
  return ''
}

export default function Bench({ session, onSignOut, restored }) {
  const saved = restored || {}
  const [caseName, setCaseName] = useState(saved.caseName || '')
  const [projectId, setProjectId] = useState(saved.projectId || null)
  const [idea, setIdea] = useState(saved.idea || '')
  const [result, setResult] = useState(saved.result || null)
  const [drafts, setDrafts] = useState(saved.drafts || {})
  const [running, setRunning] = useState(false)
  const [runElapsed, setRunElapsed] = useState(0)
  const [error, setError] = useState('')
  const [pdfTaskId, setPdfTaskId] = useState(saved.pdfTaskId || '')
  const [pdfStatus, setPdfStatus] = useState(saved.pdfStatus || '')
  const [pdfPayload, setPdfPayload] = useState(saved.pdfPayload || null)
  const [pdfElapsed, setPdfElapsed] = useState(0)
  const [pdfError, setPdfError] = useState('')
  const [reading, setReading] = useState(false)
  const abortRef = useRef(null)
  const resultRef = useRef(null)
  const followRef = useRef(null)
  const skippedMount = useRef(true)
  const pdfStatusRef = useRef(pdfStatus)

  const locked = Boolean(result)
  const questions = asList(result?.follow_up_questions).map((item) => String(item))
  const openKey = questions.join('|')
  const phases = asList(result?.pipeline_timing?.phases).filter((item) => item && item.phase)
  const competitors = asList(result?.market_analysis).filter((item) => item && item.comp_name)
  const voice = result?.customer_voice && typeof result.customer_voice === 'object' ? result.customer_voice : {}
  const solutions = asList(voice.current_solutions).map((item) => String(item))
  const gaps = asList(voice.market_gaps).filter((item) => item && typeof item === 'object' && item.gap)
  const features = asList(voice.recommended_features).map((item) => String(item))
  const context = asText(result?.product_context)
  const pdfBusy = PDF_BUSY.includes(pdfStatus)
  const waitedLong = pdfElapsed > 15000
  const statusLine = pdfError || pdfCopy(pdfStatus, pdfPayload, waitedLong)

  useEffect(() => {
    writeBench({
      email: session.email,
      projectId,
      caseName,
      idea,
      result,
      drafts,
      pdfTaskId,
      pdfStatus,
      pdfPayload,
    })
  }, [session.email, projectId, caseName, idea, result, drafts, pdfTaskId, pdfStatus, pdfPayload])

  useEffect(() => {
    if (!running) return undefined
    const started = Date.now()
    const id = setInterval(() => setRunElapsed(Date.now() - started), 1000)
    return () => clearInterval(id)
  }, [running])

  useEffect(() => {
    if (!pdfBusy) return undefined
    const started = Date.now()
    const id = setInterval(() => setPdfElapsed(Date.now() - started), 1000)
    return () => clearInterval(id)
  }, [pdfBusy])

  useEffect(() => {
    pdfStatusRef.current = pdfStatus
  }, [pdfStatus])

  useEffect(() => {
    if (!pdfTaskId) return undefined
    if (pdfStatusRef.current === 'SUCCESS' || pdfStatusRef.current === 'FAILURE') return undefined

    let cancelled = false
    let timer

    const poll = async () => {
      try {
        const data = await getTask(session.token, pdfTaskId)
        if (cancelled) return
        const payload = readTaskPayload(data.result)
        const nextStatus = data.status || 'PENDING'
        setPdfStatus(nextStatus)
        setPdfPayload(payload)
        if (payload?.status === 'needs_more_info') {
          setResult((current) => ({
            ...(current || {}),
            fully_answered: false,
            follow_up_questions: payload.follow_up_questions || [],
            question_mapping: payload.question_mapping || current?.question_mapping || {},
          }))
        }
        if (nextStatus === 'SUCCESS' || nextStatus === 'FAILURE') return
      } catch (err) {
        if (cancelled || err.name === 'AbortError') return
        setPdfError(friendlyError(err))
        setPdfStatus('FAILURE')
        return
      }
      timer = setTimeout(poll, 3000)
    }

    timer = setTimeout(poll, 800)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [pdfTaskId, session.token])

  useEffect(() => {
    if (skippedMount.current) {
      skippedMount.current = false
      return
    }
    if (!result || running) return
    const behavior = prefersReducedMotion() ? 'auto' : 'smooth'
    const target = questions.length ? followRef.current : resultRef.current
    target?.scrollIntoView({ behavior, block: 'start' })
    if (questions.length) followRef.current?.querySelector('textarea')?.focus()
  }, [openKey, result, running, questions.length])

  function resetCase() {
    abortRef.current?.abort()
    setCaseName('')
    setProjectId(null)
    setIdea('')
    setResult(null)
    setDrafts({})
    setRunning(false)
    setError('')
    setPdfTaskId('')
    setPdfStatus('')
    setPdfPayload(null)
    setPdfError('')
    setPdfElapsed(0)
    setRunElapsed(0)
  }

  async function ensureProject(signal) {
    if (projectId) return projectId
    const created = await createProject(session.token, caseName.trim() || 'Untitled', signal)
    setProjectId(created.project_id)
    if (created.project_name) setCaseName(created.project_name)
    return created.project_id
  }

  function applyResult(queryResponse) {
    setResult(queryResponse)
    setDrafts((current) => {
      const next = {}
      for (const question of asList(queryResponse.follow_up_questions)) {
        next[question] = current[question] || ''
      }
      return next
    })
  }

  async function submitQuery(text) {
    const controller = new AbortController()
    abortRef.current = controller
    setRunning(true)
    setError('')
    setRunElapsed(0)
    try {
      const id = await ensureProject(controller.signal)
      const data = await runQuery(session.token, id, text, controller.signal)
      const queryResponse = data?.query_response
      if (!queryResponse || typeof queryResponse !== 'object') {
        throw new Error('The questions came back in an unexpected shape.')
      }
      applyResult(queryResponse)
    } catch (err) {
      if (err.name === 'AbortError') return
      if (err.status === 401) {
        onSignOut()
        return
      }
      setError(friendlyError(err))
    } finally {
      setRunning(false)
    }
  }

  function onRun(event) {
    event.preventDefault()
    const text = idea.trim()
    if (text.length < 20) {
      setError('Add a bit more. A sentence about who it’s for and what hurts is enough to start.')
      return
    }
    submitQuery(text)
  }

  function onFollowUp(event) {
    event.preventDefault()
    const text = questions
      .map((question) => {
        const answer = (drafts[question] || '').trim()
        return answer ? `${question}\n${answer}` : ''
      })
      .filter(Boolean)
      .join('\n\n')
    if (!text) {
      setError('Write an answer to at least one open question.')
      return
    }
    submitQuery(text)
  }

  function focusQuestion(key) {
    const question = DIMENSIONS.find((item) => item.key === key)?.question
    const node = question
      ? followRef.current?.querySelector(`[data-question="${CSS.escape(question)}"]`)
      : null
    if (node) {
      node.focus()
      return
    }
    followRef.current?.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' })
  }

  async function onWritePdf() {
    const text = asText(result?.user_query) || idea.trim()
    if (!projectId || !text) {
      setPdfError('Run the questions before writing the PDF.')
      return
    }
    setPdfError('')
    setReading(false)
    setPdfPayload(null)
    setPdfElapsed(0)
    setPdfStatus('QUEUED')
    try {
      const data = await startPdf(session.token, projectId, text)
      if (data?.status === 'success' || data?.status === 'needs_more_info' || data?.status === 'error') {
        setPdfStatus(data.status === 'error' ? 'FAILURE' : 'SUCCESS')
        setPdfPayload(data)
        if (data.status === 'needs_more_info') {
          setResult((current) => ({
            ...(current || {}),
            fully_answered: false,
            follow_up_questions: data.follow_up_questions || [],
            question_mapping: data.question_mapping || current?.question_mapping || {},
          }))
        }
        if (data.status === 'error') {
          setPdfError(data.detail || 'The teardown failed. Start it again.')
        }
        return
      }
      if (!data?.task_id) throw new Error('The PDF run did not return a task.')
      setPdfTaskId(data.task_id)
    } catch (err) {
      if (err.status === 401) {
        onSignOut()
        return
      }
      setPdfStatus('FAILURE')
      setPdfError(friendlyError(err))
    }
  }

  const downloadUrl = pdfPayload?.status === 'success' ? pdfPayload.download_url : ''

  return (
    <div className="page">
      <div className="sheet wide">
        <header className="top">
          <p className="mark">ShipIt</p>
          <div className="who">
            <span>{session.email}</span>
            {(result || projectId) && (
              <button type="button" className="quiet" onClick={resetCase}>New case</button>
            )}
            <button type="button" className="quiet" onClick={onSignOut}>Sign out</button>
          </div>
        </header>

        {locked ? (
          <h1>{caseName.trim() || 'Untitled'}</h1>
        ) : (
          <label className="field title-field">
            <span>Case name</span>
            <input
              className="title-input"
              value={caseName}
              onChange={(event) => setCaseName(event.target.value)}
              placeholder="Campus mock interviews"
              maxLength={80}
            />
          </label>
        )}

        <form className="form" onSubmit={onRun} noValidate>
          <label className="field">
            <span>The idea</span>
            <textarea
              className="idea"
              value={idea}
              onChange={(event) => setIdea(event.target.value)}
              readOnly={locked}
              placeholder="Final-year engineers need company-specific mock interviews during placement season, and LeetCode doesn’t rehearse the round they’ll actually sit."
            />
          </label>
          {!locked && (
            <p className="hint">Include who it’s for if you know. Missing pieces come back as questions.</p>
          )}
          {!locked && (
            <div className="actions">
              <button className="btn" type="submit" disabled={running}>
                {running ? 'Running the questions' : 'Run the questions'}
              </button>
            </div>
          )}
          {!questions.length && error && <p className="error" role="alert">{error}</p>}
          {!questions.length && running && <RunWait elapsed={runElapsed} />}
        </form>

        <div className="stack" ref={resultRef}>
          <section className="block">
            <h2>The six questions</h2>
            {!result && !running && (
              <p>These are the six questions the run checks. What you already covered in the idea stays. The rest comes back for an answer.</p>
            )}
            <ul className="dims">
              {DIMENSIONS.map((item) => {
                const answer = result ? readAnswer(result.question_mapping, item.key) : null
                const state = !result ? 'waiting' : answer.answered ? 'answered' : 'open'
                return (
                  <li key={item.key} className={`dim ${state}`}>
                    <span className="sq" aria-hidden="true" />
                    {state === 'open' ? (
                      <button type="button" onClick={() => focusQuestion(item.key)}>
                        <span className="dim-label">{item.label}</span>
                        <span className="dim-answer">Still open. Answer this.</span>
                      </button>
                    ) : (
                      <div>
                        <span className="dim-label">{item.label}</span>
                        {answer?.answer && <span className="dim-answer">{answer.answer}</span>}
                      </div>
                    )}
                  </li>
                )
              })}
            </ul>
          </section>

          {questions.length > 0 && (
            <form className="form" onSubmit={onFollowUp} ref={followRef} noValidate>
              <h2>Still open</h2>
              {questions.map((question) => (
                <label className="field" key={question}>
                  <span>{question}</span>
                  <textarea
                    rows={3}
                    data-question={question}
                    value={drafts[question] || ''}
                    onChange={(event) => {
                      const value = event.target.value
                      setDrafts((current) => ({ ...current, [question]: value }))
                    }}
                  />
                </label>
              ))}
              <div className="actions">
                <button className="btn" type="submit" disabled={running}>
                  {running ? 'Adding these answers' : 'Add these answers'}
                </button>
              </div>
              {error && <p className="error" role="alert">{error}</p>}
              {running && <RunWait elapsed={runElapsed} />}
            </form>
          )}

          {phases.length > 0 && (
            <PhaseBar phases={phases} total={result?.pipeline_timing?.total_s} />
          )}

          {result?.fully_answered && context && (
            <section className="block">
              <h2>What this is</h2>
              <p className="prose">{context}</p>
            </section>
          )}

          {result?.fully_answered && (
            <section className="block">
              <h2>Competitors</h2>
              {competitors.length > 0 ? (
                <CompetitorBoard
                  key={competitors.map((item) => item.comp_name).join('|')}
                  competitors={competitors}
                  voice={voice}
                />
              ) : (
                <p>No named competitors came back from the search.</p>
              )}
            </section>
          )}

          {solutions.length > 0 && (
            <section className="block">
              <h2>What people use today</h2>
              <ul className="plain">
                {solutions.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </section>
          )}

          {gaps.length > 0 && (
            <section className="block">
              <h2>What customers still need</h2>
              <ul className="gaps">
                {gaps.map((item) => (
                  <li key={item.gap}>
                    <h3>{item.gap}</h3>
                    {item.evidence && <p>{item.evidence}</p>}
                    {item.product_opportunity && <p className="build">{item.product_opportunity}</p>}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {features.length > 0 && (
            <section className="block">
              <h2>What to build from those gaps</h2>
              <ul className="plain">
                {features.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </section>
          )}

          {result?.fully_answered && (
            <section className="stamp">
              <p>{pdfPayload?.product_name || leadFrom(context) || 'The six questions are answered.'}</p>
              {pdfPayload?.status === 'success' && pdfPayload.product_name && (
                <p className="stamp-sub">The teardown is ready.</p>
              )}
              {!context && pdfPayload?.status !== 'success' && (
                <p className="stamp-sub">The write-up was empty. Writing the PDF runs the research again.</p>
              )}
              {statusLine && pdfPayload?.status !== 'success' && (
                <p className="stamp-sub" role="status">{statusLine}</p>
              )}
              {pdfBusy && <p className="clock light" aria-hidden="true">{formatElapsed(pdfElapsed)}</p>}
              {downloadUrl ? (
                <div className="stamp-actions">
                  <button type="button" className="btn" onClick={() => setReading(true)}>
                    Read the teardown
                  </button>
                  <a href={apiUrl(downloadUrl)}>Download the PDF</a>
                </div>
              ) : (
                <button className="btn" type="button" onClick={onWritePdf} disabled={pdfBusy}>
                  {pdfBusy ? 'Writing the PDF' : 'Write the PDF'}
                </button>
              )}
            </section>
          )}
        </div>
      </div>
      {reading && downloadUrl && (
        <PdfReader
          title={pdfPayload?.product_name || caseName.trim() || 'Teardown'}
          viewUrl={`${apiUrl(downloadUrl)}?view=1`}
          downloadUrl={apiUrl(downloadUrl)}
          onClose={() => setReading(false)}
        />
      )}
    </div>
  )
}
