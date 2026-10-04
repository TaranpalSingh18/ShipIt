import { useEffect, useRef, useState } from 'react'
import { friendlyError, login, signup, writeSession } from '../api'
import { prefersReducedMotion } from '../format'

const SAMPLE = {
  idea: 'Company-specific mock interviews for final-year engineers during campus placement season.',
  answers: [
    { label: 'Who it is for', text: 'Final-year engineering students sitting campus placements.' },
    { label: 'The pain', text: 'Practice sets are generic. The round they face belongs to the company visiting that week.' },
    { label: 'How often', text: 'Once a year, packed into a six to eight week season.' },
    { label: 'What they use now', text: 'LeetCode, YouTube playlists, and a senior who already sat the round.' },
    { label: 'Why this is better', text: 'Questions mapped to the companies that actually visit their campus.' },
    { label: 'What you have checked', text: 'Not yet. The teardown is how you find out if the gap is real.' },
  ],
}

const LAST_STEP = SAMPLE.answers.length

const BEATS = [
  {
    title: 'Write the idea',
    text: 'One paragraph is enough. Who it is for, and what is going wrong for them.',
  },
  {
    title: 'Answer the six',
    text: 'ShipIt asks who, the pain, how often, what they use now, why this is different, and what you have already checked.',
  },
  {
    title: 'Read the page',
    text: 'When the answers hold, you get a one-page teardown. Open it here, or take the PDF with you.',
  },
]

export default function Gate({ onSession }) {
  const reduced = prefersReducedMotion()
  const [step, setStep] = useState(reduced ? LAST_STEP : 0)
  const [playing, setPlaying] = useState(!reduced)
  const [mode, setMode] = useState('signup')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const nameRef = useRef(null)
  const emailRef = useRef(null)
  const pendingFocus = useRef('')

  useEffect(() => {
    if (!playing || reduced || step >= LAST_STEP) return undefined
    const id = setTimeout(() => setStep((current) => current + 1), 850)
    return () => clearTimeout(id)
  }, [playing, reduced, step])

  useEffect(() => {
    const which = pendingFocus.current
    if (!which) return undefined
    pendingFocus.current = ''
    const field = which === 'signup' ? nameRef.current : emailRef.current
    const frame = requestAnimationFrame(() => {
      document.getElementById('account')?.scrollIntoView({
        behavior: reduced ? 'auto' : 'smooth',
        block: 'start',
      })
      field?.focus()
    })
    return () => cancelAnimationFrame(frame)
  }, [mode, reduced])

  function revealThrough(index) {
    setPlaying(false)
    setStep(index + 1)
  }

  function replay() {
    setStep(0)
    setPlaying(!reduced)
  }

  function openAccount(next) {
    pendingFocus.current = next
    setMode(next)
    setError('')
    if (next === mode) {
      const field = next === 'signup' ? nameRef.current : emailRef.current
      document.getElementById('account')?.scrollIntoView({
        behavior: reduced ? 'auto' : 'smooth',
        block: 'start',
      })
      field?.focus()
      pendingFocus.current = ''
    }
  }

  function switchMode(next) {
    setMode(next)
    setError('')
    setPassword('')
  }

  async function onSubmit(event) {
    event.preventDefault()
    const cleanEmail = email.trim()
    const cleanName = name.trim()
    if (mode === 'signup' && !cleanName) {
      setError('Add your name.')
      return
    }
    if (!cleanEmail || !cleanEmail.includes('@')) {
      setError('Enter the email you want on the account.')
      return
    }
    if (password.length < 4) {
      setError('Use at least 4 characters in the password.')
      return
    }

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
      const session = {
        token: auth.access_token,
        email: cleanEmail,
        name: cleanName,
      }
      writeSession(session)
      onSession(session)
    } catch (err) {
      setError(friendlyError(err))
    } finally {
      setSubmitting(false)
    }
  }

  const accountLabel = mode === 'signup' ? 'Create account' : 'Log in'
  const cleared = step >= LAST_STEP

  return (
    <div className="page land-page">
      <div className="land">
        <header className="land-bar">
          <p className="mark">ShipIt</p>
          <button type="button" className="quiet" onClick={() => openAccount('login')}>
            Log in
          </button>
        </header>

        <div className="land-hero">
          <div className="land-copy">
            <h1>Question the idea before you build it.</h1>
            <p className="intro">
              Write the idea down. ShipIt asks the six questions founders skip, looks up who already serves that customer, and hands you a teardown you can read on the page.
            </p>
            <div className="actions">
              <button type="button" className="btn" onClick={() => openAccount('signup')}>
                Start a case
              </button>
              <button type="button" className="quiet" onClick={() => openAccount('login')}>
                I already have an account
              </button>
            </div>
          </div>

          <section className="casefile" aria-label="A sample idea">
            <p className="sample-kicker">A sample idea</p>
            <p className="sample-idea">{SAMPLE.idea}</p>
            <ul className="dims">
              {SAMPLE.answers.map((item, index) => {
                const open = step > index
                return (
                  <li key={item.label} className={open ? 'dim answered' : 'dim waiting'}>
                    <span className="sq" aria-hidden="true" />
                    <button type="button" aria-expanded={open} onClick={() => revealThrough(index)}>
                      <span className="dim-label">{item.label}</span>
                      <span className={open ? 'reveal open' : 'reveal'}>
                        <span className="reveal-inner">
                          <span className="dim-answer">{item.text}</span>
                        </span>
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
            <p className={cleared ? 'file-stamp reveal open' : 'file-stamp reveal'}>
              <span className="reveal-inner">
                <span>Cleared for a teardown</span>
              </span>
            </p>
            <button type="button" className="quiet" onClick={replay}>
              {reduced ? 'Start the sample over' : 'Play the sample again'}
            </button>
          </section>
        </div>

        <div className="land-rest">
        <section className="beats" aria-label="How a case moves">
          {BEATS.map((beat) => (
            <article key={beat.title}>
              <h2>{beat.title}</h2>
              <p>{beat.text}</p>
            </article>
          ))}
        </section>

        <form id="account" className="account form" onSubmit={onSubmit} noValidate>
          <h2>{accountLabel}</h2>
          {mode === 'signup' && (
            <label className="field">
              <span>Name</span>
              <input
                ref={nameRef}
                value={name}
                onChange={(event) => setName(event.target.value)}
                autoComplete="name"
                maxLength={100}
              />
            </label>
          )}
          <label className="field">
            <span>Email</span>
            <input
              ref={emailRef}
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
            />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
              minLength={4}
            />
          </label>
          {error && <p className="error" role="alert">{error}</p>}
          <div className="actions">
            <button className="btn" type="submit" disabled={submitting}>
              {submitting ? (mode === 'signup' ? 'Creating the account' : 'Logging in') : accountLabel}
            </button>
            {mode === 'signup' ? (
              <button type="button" className="quiet" onClick={() => switchMode('login')}>
                I already have an account
              </button>
            ) : (
              <button type="button" className="quiet" onClick={() => switchMode('signup')}>
                I need an account
              </button>
            )}
          </div>
        </form>
        </div>
      </div>
    </div>
  )
}
