import { useEffect, useState } from 'react'
import { formatElapsed } from '../../format'

const STEPS = [
  { at: 0, label: 'Queued' },
  { at: 8, label: 'Researching competitors' },
  { at: 30, label: 'Sizing the market and writing' },
  { at: 75, label: 'Capturing logos and homepages' },
  { at: 90, label: 'Designing the PDF' },
]

export default function ReportProgress({ report }) {
  const [now, setNow] = useState(() => Date.now())
  const failed = report?.status === 'failed'
  const done = report?.status === 'success'
  const progress = report?.progress ?? 0
  const started = report?.created_at ? new Date(report.created_at).getTime() : now

  useEffect(() => {
    if (done || failed) return undefined
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [done, failed])

  const current = STEPS.reduce((acc, step, i) => (progress >= step.at ? i : acc), 0)

  return (
    <div className={`rp ${failed ? 'failed' : ''}`} role="status" aria-live="polite">
      <div className="rp-head">
        <span className="rp-title">{failed ? 'The memo didn’t finish' : done ? 'Memo ready' : 'Writing the investor memo'}</span>
        {!done && !failed && <span className="rp-time">{formatElapsed(now - started)}</span>}
      </div>
      <div className="rp-bar" aria-hidden="true">
        <span style={{ width: `${done ? 100 : Math.max(4, progress)}%` }} />
      </div>
      {failed ? (
        <p className="error">{report.error || 'Something went wrong while writing the memo.'} Start it again from the case.</p>
      ) : (
        <ol className="rp-steps">
          {STEPS.map((step, i) => {
            const state = done || i < current ? 'done' : i === current ? 'now' : 'todo'
            return (
              <li key={step.label} className={state}>
                <span className="rp-dot" aria-hidden="true" />
                {step.label}
                {state === 'now' && report?.stage && report.stage !== step.label && <em>{report.stage}</em>}
              </li>
            )
          })}
        </ol>
      )}
      {!done && !failed && <p className="hint">Usually one to three minutes. You can leave this page; the memo keeps writing.</p>}
    </div>
  )
}
