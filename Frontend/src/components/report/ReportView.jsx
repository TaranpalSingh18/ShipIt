import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { downloadReportPdf, friendlyError, getReport, startReport } from '../../api'
import ReportProgress from '../workspace/ReportProgress'
import { Ring } from './charts'
import {
  Business,
  HeadToHead,
  Landscape,
  Logo,
  Market,
  NextSteps,
  Problem,
  Risks,
  SourcesList,
  Summary,
  ValueProp,
  VerdictSection,
  Voice,
} from './sections'
import './report.css'

const TOC = [
  ['summary', 'Summary'],
  ['problem', 'Problem & customer'],
  ['solution', 'Value proposition'],
  ['market', 'Market'],
  ['landscape', 'Competitors'],
  ['h2h', 'Head-to-head'],
  ['voice', 'Voice of customer'],
  ['business', 'Business model'],
  ['risks', 'Risks & moats'],
  ['verdict', 'Verdict'],
  ['next', 'Next steps'],
]

function citedIds(r) {
  const ids = new Set()
  const m = r.market
  ;[m.tam, m.sam, m.som, m.cagr].forEach((f) => f.source_ids.forEach((id) => ids.add(id)))
  m.trends.forEach((t) => t.source_ids.forEach((id) => ids.add(id)))
  r.competition.competitors.forEach((c) => c.source_ids.forEach((id) => ids.add(id)))
  return ids
}

function useScrollSpy(ids, enabled) {
  const [active, setActive] = useState(ids[0])
  useEffect(() => {
    if (!enabled) return undefined
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible[0]) setActive(visible[0].target.id)
      },
      { rootMargin: '-90px 0px -60% 0px' },
    )
    ids.forEach((id) => {
      const node = document.getElementById(id)
      if (node) observer.observe(node)
    })
    return () => observer.disconnect()
  }, [ids, enabled])
  return active
}

export default function ReportView({ session, onSignOut }) {
  const { reportId } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [drawer, setDrawer] = useState(null)
  const [busy, setBusy] = useState('')
  const drawerRef = useRef(null)

  // Stale responses are ignored rather than aborted: aborting a request mid-flight can
  // leave Vite's dev proxy holding the next request on the same connection.
  useEffect(() => {
    let live = true
    let timer
    const tick = async () => {
      try {
        const next = await getReport(session.token, reportId)
        if (!live) return
        setData(next)
        setError('')
        if (next.status === 'pending' || next.status === 'running') timer = setTimeout(tick, 2500)
      } catch (err) {
        if (!live) return
        if (err.status === 401) onSignOut()
        else setError(friendlyError(err))
      }
    }
    tick()
    return () => {
      live = false
      clearTimeout(timer)
    }
  }, [session.token, reportId, onSignOut])

  const r = data?.report
  const cited = useMemo(() => (r ? citedIds(r) : new Set()), [r])
  const active = useScrollSpy(
    TOC.map(([id]) => id),
    Boolean(r),
  )

  useEffect(() => {
    if (!drawer) return undefined
    const onKey = (e) => e.key === 'Escape' && setDrawer(null)
    document.addEventListener('keydown', onKey)
    drawerRef.current?.focus()
    if (drawer.id) {
      requestAnimationFrame(() => document.getElementById(`src-${drawer.id}`)?.scrollIntoView({ block: 'center' }))
    }
    return () => document.removeEventListener('keydown', onKey)
  }, [drawer])

  const onCite = useCallback((id) => setDrawer({ id }), [])

  async function download() {
    setBusy('pdf')
    try {
      const name = (r?.narrative?.product_name || 'investor-memo').replace(/[^\w-]+/g, '_')
      await downloadReportPdf(session.token, reportId, `${name}_investor_memo.pdf`)
    } catch (err) {
      if (err.status === 401) onSignOut()
      else setError(friendlyError(err))
    } finally {
      setBusy('')
    }
  }

  async function regenerate() {
    if (!data?.project_id) return
    setBusy('regen')
    try {
      const next = await startReport(session.token, data.project_id)
      navigate(`/app/report/${next.id}`)
    } catch (err) {
      setError(friendlyError(err))
    } finally {
      setBusy('')
    }
  }

  if (!data) {
    return (
      <main className="shell r-empty">
        {error ? (
          <>
            <p className="error">{error}</p>
            <Link className="btn ghost" to="/app">
              Back to cases
            </Link>
          </>
        ) : (
          <span className="spinner" role="status" aria-label="Loading the memo" />
        )}
      </main>
    )
  }

  if (data.status !== 'success' || !r) {
    return (
      <main className="shell r-empty">
        <ReportProgress report={data} />
        <Link className="btn ghost" to={`/app/case/${data.project_id}`}>
          Back to the case
        </Link>
      </main>
    )
  }

  const n = r.narrative
  const verdictClass = r.strategy.verdict.label.toLowerCase().replace(/\s+/g, '-')
  const generated = new Date(r.meta.generated_at).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })

  return (
    <div className="report">
      <header className="r-hero">
        <div className="r-hero-bg" aria-hidden="true" />
        <div className="shell r-hero-in">
          <div className="r-hero-copy">
            <nav className="crumbs" aria-label="Breadcrumb">
              <Link to="/app">Cases</Link>
              <span aria-hidden="true">/</span>
              <Link to={`/app/case/${data.project_id}`}>{n.product_name}</Link>
              <span aria-hidden="true">/</span>
              <span aria-current="page">Investor memo</span>
            </nav>
            <span className={`badge ${verdictClass}`}>{r.strategy.verdict.label}</span>
            <h1 className="display">{n.product_name}</h1>
            <p className="r-oneliner">{n.one_liner}</p>
            <div className="r-actions">
              <button type="button" className="btn lg" onClick={download} disabled={busy === 'pdf'}>
                {busy === 'pdf' ? <span className="spinner" aria-hidden="true" /> : <DownloadIcon />}
                Download PDF
              </button>
              <button type="button" className="btn ghost lg" onClick={regenerate} disabled={busy === 'regen'}>
                Write a new version
              </button>
            </div>
            {error && <p className="error">{error}</p>}
            <p className="r-meta">
              {generated} · {r.sources.length} sources · {r.competition.competitors.length} competitors
            </p>
          </div>
          <div className="r-hero-ring">
            <Ring value={r.meta.readiness} size={176} stroke={14} />
            <p>Investor readiness</p>
            <div className="r-bench">
              {r.competition.competitors.map((c) => (
                <span key={c.name} title={c.name}>
                  <Logo comp={c} size="sm" />
                </span>
              ))}
            </div>
          </div>
        </div>
        <div className="shell">
          <div className="r-verdict">
            <span>Verdict</span>
            <p>{r.strategy.verdict.headline || r.strategy.verdict.bottom_line}</p>
          </div>
        </div>
      </header>

      <div className="shell r-layout">
        <aside className="toc" aria-label="Sections">
          <ol>
            {TOC.map(([id, label]) => (
              <li key={id}>
                <a href={`#${id}`} className={active === id ? 'on' : ''} aria-current={active === id ? 'true' : undefined}>
                  {label}
                </a>
              </li>
            ))}
          </ol>
          <button type="button" className="toc-src" onClick={() => setDrawer({})}>
            {r.sources.length} sources
          </button>
        </aside>
        <label className="toc-mobile">
          <span className="sr-only">Jump to section</span>
          <select
            value={active}
            onChange={(e) => document.getElementById(e.target.value)?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
          >
            {TOC.map(([id, label]) => (
              <option key={id} value={id}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <main className="r-main">
          <Summary r={r} onCite={onCite} />
          <Problem r={r} />
          <ValueProp r={r} />
          <Market r={r} onCite={onCite} />
          <Landscape r={r} onCite={onCite} />
          <HeadToHead r={r} />
          <Voice r={r} />
          <Business r={r} onCite={onCite} />
          <Risks r={r} />
          <VerdictSection r={r} />
          <NextSteps r={r} />
        </main>
      </div>

      {drawer && (
        <div className="drawer-wrap" onClick={() => setDrawer(null)}>
          <aside
            className="drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="src-h"
            tabIndex={-1}
            ref={drawerRef}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="drawer-head">
              <h2 id="src-h">Sources</h2>
              <button type="button" className="icon-btn" onClick={() => setDrawer(null)} aria-label="Close sources">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
            </div>
            <p className="hint">Highlighted sources are cited in the memo. The rest were read during research.</p>
            <SourcesList sources={r.sources} cited={cited} activeId={drawer.id} />
          </aside>
        </div>
      )}
    </div>
  )
}

function DownloadIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 4v11M7 10l5 5 5-5M5 20h14" />
    </svg>
  )
}
