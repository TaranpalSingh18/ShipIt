import { useRef, useState } from 'react'
import { friendlyError, login, signup, writeSession } from '../api'
import { prefersReducedMotion } from '../format'
import { Ring } from './report/charts'
import { ThemeToggle } from './TopBar'
import './landing.css'

const PAGES = [
  ['Executive one-pager', 'Verdict, readiness score, market size, why invest and key risks.'],
  ['Problem & customer', 'Pains rated for severity, with real user quotes and segments.'],
  ['Value proposition', 'A proper canvas: every pain matched to the feature that answers it.'],
  ['Market opportunity', 'TAM, SAM, SOM and growth, each with its source and method.'],
  ['Competitive landscape', 'Homepages, logos, founding year, funding and pricing per rival.'],
  ['Head-to-head', 'Feature matrix and a positioning map with reasons for each placement.'],
  ['Voice of the customer', 'What users complain about, and the gaps those complaints reveal.'],
  ['Business model', 'Pricing tiers benchmarked against rivals, plus the go-to-market plan.'],
  ['Risks & moats', 'A likelihood × impact heatmap, with a mitigation for every risk.'],
  ['Verdict', 'A five-part scorecard and a plain judgement: strong, promising, or not yet.'],
  ['Next 90 days', 'Measurable milestones and the hard questions investors will ask.'],
  ['Sources', 'Every page read during research, numbered and linked.'],
]

const STEPS = [
  ['Describe the idea', 'One paragraph: who it’s for and what goes wrong for them.'],
  ['Answer what’s missing', 'ShipIt checks six things investors ask first and asks about any gaps.'],
  ['Get the memo', 'Research runs in a couple of minutes. Read it here or download the PDF.'],
]

function MemoStack() {
  return (
    <div className="stack" aria-hidden="true">
      <div className="sheet s3">
        <div className="mini-h">Head-to-head</div>
        <div className="mini-matrix">
          {Array.from({ length: 24 }, (_, i) => (
            <i key={i} className={i % 4 === 0 ? 'us' : i % 3 === 0 ? 'half' : i % 5 === 0 ? 'full' : ''} />
          ))}
        </div>
      </div>
      <div className="sheet s2">
        <div className="mini-h">Competitive landscape</div>
        <div className="mini-cards">
          {['#3a7bd5', '#7c3aed', '#f59e0b', '#10b981'].map((c) => (
            <div key={c}>
              <span style={{ background: `linear-gradient(135deg, ${c}, transparent)` }} />
              <b />
              <b className="short" />
            </div>
          ))}
        </div>
      </div>
      <div className="sheet s1">
        <div className="cover">
          <div className="cover-glow" />
          <div className="cover-top">
            <span className="cover-brand">
              <i /> ShipIt / Investor memo
            </span>
          </div>
          <div className="cover-main">
            <div>
              <span className="cover-pill">Promising</span>
              <p className="cover-name">MockPath</p>
              <p className="cover-line">Interview-practice roadmaps for final-year students.</p>
            </div>
            <Ring value={72} size={92} stroke={9} label="Ready" className="cover-ring" />
          </div>
        </div>
        <div className="cover-kpis">
          <div>
            <span>TAM</span>
            <b>$1.28B</b>
          </div>
          <div>
            <span>Growth</span>
            <b>10.6%</b>
          </div>
          <div>
            <span>Rivals</span>
            <b>5</b>
          </div>
        </div>
        <div className="cover-lines">
          <i />
          <i />
          <i className="short" />
          <i />
          <i className="short" />
        </div>
      </div>
    </div>
  )
}

export default function Landing({ onSession }) {
  const reduced = prefersReducedMotion()
  const [mode, setMode] = useState('signup')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const nameRef = useRef(null)
  const emailRef = useRef(null)

  function openAccount(next) {
    setMode(next)
    setError('')
    document.getElementById('account')?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'center' })
    requestAnimationFrame(() => (next === 'signup' ? nameRef.current : emailRef.current)?.focus({ preventScroll: true }))
  }

  async function onSubmit(event) {
    event.preventDefault()
    const cleanEmail = email.trim()
    const cleanName = name.trim()
    if (mode === 'signup' && !cleanName) return setError('Add your name.')
    if (!cleanEmail.includes('@')) return setError('Enter the email you want on the account.')
    if (password.length < 4) return setError('Use at least 4 characters in the password.')

    setSubmitting(true)
    setError('')
    try {
      if (mode === 'signup') {
        try {
          await signup(cleanName, cleanEmail, password)
        } catch (err) {
          if (err.message === 'User is existing') {
            setMode('login')
            setError('That email already has an account. Enter the password to log in.')
            return
          }
          throw err
        }
      }
      const auth = await login(cleanEmail, password)
      const session = { token: auth.access_token, email: cleanEmail, name: cleanName }
      writeSession(session)
      onSession(session)
    } catch (err) {
      setError(friendlyError(err))
    } finally {
      setSubmitting(false)
    }
  }

  const label = mode === 'signup' ? 'Create account' : 'Log in'

  return (
    <div className="land">
      <header className="land-bar shell">
        <span className="wordmark">
          <span className="wordmark-mark" aria-hidden="true" />
          ShipIt
        </span>
        <div className="topbar-end">
          <ThemeToggle />
          <button type="button" className="btn ghost sm" onClick={() => openAccount('login')}>
            Log in
          </button>
        </div>
      </header>

      <section className="hero shell">
        <div className="hero-copy">
          <h1 className="display">Your idea, read the way an investor reads it.</h1>
          <p className="hero-sub">
            ShipIt questions your startup idea, researches the market and every competitor it can find, and writes a 12-page investor memo where each number links to its source.
          </p>
          <div className="hero-cta">
            <button type="button" className="btn lg" onClick={() => openAccount('signup')}>
              Start a case
            </button>
            <button type="button" className="btn quiet lg" onClick={() => openAccount('login')}>
              I have an account
            </button>
          </div>
        </div>
        <MemoStack />
      </section>

      <section className="pages shell" aria-labelledby="pages-h">
        <div className="sec-intro">
          <h2 id="pages-h" className="display">
            Twelve pages, in the order an investor reads them
          </h2>
          <p>Every page is also an interactive report in the app, with sortable tables and charts you can hover.</p>
        </div>
        <ol className="page-list">
          {PAGES.map(([title, text], i) => (
            <li key={title}>
              <span className="pg-n">{String(i + 1).padStart(2, '0')}</span>
              <div>
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="proof shell" aria-labelledby="proof-h">
        <div className="proof-copy">
          <h2 id="proof-h" className="display">
            Numbers you can defend in the room
          </h2>
          <p>
            Market sizes, funding and pricing only appear when a source states them. When the research comes up empty, the memo says <em>Not found</em> instead of inventing a figure, and tells you how to size it yourself.
          </p>
        </div>
        <div className="proof-demo" aria-hidden="true">
          <div className="pd-row">
            <span className="pd-k">TAM</span>
            <span className="pd-v">$1.28B</span>
            <span className="pd-src">[30] AI Interview Software Market, 2025</span>
          </div>
          <div className="pd-row">
            <span className="pd-k">CAGR</span>
            <span className="pd-v">10.6%</span>
            <span className="pd-src">[30] Same report, 2026–2035</span>
          </div>
          <div className="pd-row nf">
            <span className="pd-k">Funding</span>
            <span className="pd-v">Not found</span>
            <span className="pd-src">No source stated it, so it stays blank</span>
          </div>
        </div>
      </section>

      <section className="how shell" aria-labelledby="how-h">
        <h2 id="how-h" className="display">
          How a case works
        </h2>
        <ol className="how-steps">
          {STEPS.map(([title, text], i) => (
            <li key={title}>
              <span className="how-n">{i + 1}</span>
              <h3>{title}</h3>
              <p>{text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="account-wrap shell">
        <form id="account" className="account" onSubmit={onSubmit} noValidate>
          <h2 className="display">{label}</h2>
          <p className="hint">{mode === 'signup' ? 'Your cases and memos are saved to this account.' : 'Welcome back.'}</p>
          {mode === 'signup' && (
            <label className="field">
              <span>Name</span>
              <input ref={nameRef} className="input" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" maxLength={100} />
            </label>
          )}
          <label className="field">
            <span>Email</span>
            <input ref={emailRef} className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
            />
          </label>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <button className="btn lg" type="submit" disabled={submitting}>
            {submitting ? (mode === 'signup' ? 'Creating your account…' : 'Logging in…') : label}
          </button>
          <button
            type="button"
            className="btn quiet"
            onClick={() => {
              setMode(mode === 'signup' ? 'login' : 'signup')
              setError('')
              setPassword('')
            }}
          >
            {mode === 'signup' ? 'I already have an account' : 'I need an account'}
          </button>
        </form>
      </section>

      <footer className="land-foot shell">
        <span>ShipIt</span>
        <span>Investor memos for ideas that aren’t built yet.</span>
      </footer>
    </div>
  )
}
