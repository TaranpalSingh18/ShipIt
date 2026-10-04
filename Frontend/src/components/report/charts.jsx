import { useId, useState } from 'react'

/* Interactive SVG charts for the web report. Geometry mirrors Backend/routes/report/charts.py. */

function Tip({ tip }) {
  if (!tip) return null
  return (
    <div className="viz-tip" style={{ left: `${tip.x}%`, top: `${tip.y}%` }} role="status">
      <strong>{tip.title}</strong>
      {tip.body && <span>{tip.body}</span>}
    </div>
  )
}

export function Ring({ value = 0, size = 132, stroke = 12, label = 'Readiness', className = '' }) {
  const id = useId()
  const score = Math.max(0, Math.min(100, Math.round(value)))
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  return (
    <svg
      className={`ring ${className}`}
      viewBox={`0 0 ${size} ${size}`}
      width={size}
      height={size}
      role="img"
      aria-label={`${label} ${score} out of 100`}
    >
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="var(--accent-2)" />
          <stop offset="1" stopColor="var(--accent)" />
        </linearGradient>
      </defs>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" className="ring-track" strokeWidth={stroke} />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={`url(#${id})`}
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={`${(c * score) / 100} ${c}`}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        className="ring-arc"
      />
      <text x="50%" y="50%" dy="0.1em" textAnchor="middle" dominantBaseline="middle" className="ring-num">
        {score}
      </text>
      <text x="50%" y="50%" dy={size * 0.2} textAnchor="middle" className="ring-label">
        {label}
      </text>
    </svg>
  )
}

export function TamCircles({ tam, sam, som }) {
  const [active, setActive] = useState(null)
  const figures = [
    ['TAM', tam, 'var(--tam-1)'],
    ['SAM', sam, 'var(--tam-2)'],
    ['SOM', som, 'var(--tam-3)'],
  ]
  const height = 260
  const maxR = height / 2 - 4
  const known = figures.map(([, f]) => f?.value_usd).filter(Boolean)
  const top = known.length ? Math.max(...known) : 1
  const fallback = [1, 0.66, 0.36]
  const radii = []
  figures.forEach(([, f], i) => {
    let ratio = f?.value_usd && known.length ? Math.max(Math.sqrt(f.value_usd / top), i === 2 ? 0.22 : 0.4) : fallback[i]
    if (radii.length) ratio = Math.min(ratio, radii[i - 1] / maxR - 0.08)
    radii.push(maxR * ratio)
  })
  const cx = maxR + 4
  const bottom = height - 4
  return (
    <div className="tam-viz">
      <svg viewBox={`0 0 ${cx * 2 + 4} ${height}`} role="img" aria-label="Market size circles">
        {figures.map(([key, f, color], i) => (
          <g
            key={key}
            onMouseEnter={() => setActive(key)}
            onMouseLeave={() => setActive(null)}
            className={`tam-c ${active && active !== key ? 'dim' : ''}`}
          >
            <circle
              cx={cx}
              cy={bottom - radii[i]}
              r={radii[i]}
              fill={color}
              stroke="var(--surface)"
              strokeWidth="2"
              strokeDasharray={f?.value_usd ? undefined : '5 5'}
              fillOpacity={f?.value_usd ? 1 : 0.25}
            />
            <text x={cx} y={bottom - 2 * radii[i] + 18} textAnchor="middle" className="tam-in">
              {key}
            </text>
          </g>
        ))}
      </svg>
      <dl className="tam-legend">
        {figures.map(([key, f, color]) => (
          <div
            key={key}
            className={active === key ? 'on' : ''}
            onMouseEnter={() => setActive(key)}
            onMouseLeave={() => setActive(null)}
          >
            <dt>
              <i style={{ background: color }} />
              {key}
            </dt>
            <dd className={f?.value_usd ? '' : 'nf'}>{f?.display || 'Not found'}</dd>
            <dd className="sub">{f?.label || (f?.value_usd ? '' : 'No sourced figure')}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

function overlaps(a, b) {
  return a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3]
}

export function PositioningMap({ positioning, highlight, onHighlight }) {
  const [tip, setTip] = useState(null)
  const points = positioning?.points || []
  const size = 420
  const pad = { l: 34, b: 34, t: 10, r: 10 }
  const w = size - pad.l - pad.r
  const h = size - pad.t - pad.b
  const px = (v) => pad.l + (w * v) / 100
  const py = (v) => pad.t + h * (1 - v / 100)
  const ordered = points.map((p, i) => ({ ...p, n: i + 1 })).sort((a, b) => Number(a.is_us) - Number(b.is_us))
  const dots = ordered.map((p) => [px(p.x), py(p.y)])
  const placed = []
  const labels = ordered.map((p) => {
    const cx = px(p.x)
    const cy = py(p.y)
    const width = p.name.length * 6.6 + 6
    const options = [
      [13, -10, 'start'],
      [-13, -10, 'end'],
      [13, 16, 'start'],
      [-13, 16, 'end'],
      [0, -16, 'middle'],
      [0, 24, 'middle'],
    ]
    let chosen = null
    for (const [dx, dy, anchor] of options) {
      const x = cx + dx
      const y = cy + dy
      const left = anchor === 'start' ? x : anchor === 'end' ? x - width : x - width / 2
      const box = [left, y - 10, left + width, y + 3]
      const inside = box[0] >= pad.l - 2 && box[2] <= pad.l + w + 2 && box[1] >= pad.t && box[3] <= pad.t + h
      const clash =
        placed.some((b) => overlaps(box, b)) ||
        dots.some(([ox, oy]) => (ox !== cx || oy !== cy) && overlaps(box, [ox - 9, oy - 9, ox + 9, oy + 9]))
      if (inside && !clash) {
        chosen = { x, y, anchor, box }
        break
      }
      if (!chosen && inside) chosen = { x, y, anchor, box, fallback: true }
    }
    chosen ||= { x: cx + 13, y: cy - 10, anchor: 'start', box: [cx, cy, cx, cy] }
    placed.push(chosen.box)
    return chosen
  })

  return (
    <div className="viz pm-viz">
      <svg viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`Positioning map: ${positioning?.x_axis?.label} against ${positioning?.y_axis?.label}`}>
        <rect x={pad.l} y={pad.t} width={w} height={h} className="pm-bg" rx="6" />
        <rect x={px(50)} y={pad.t} width={w / 2} height={h / 2} className="pm-best" />
        <line x1={px(50)} y1={pad.t} x2={px(50)} y2={pad.t + h} className="pm-mid" />
        <line x1={pad.l} y1={py(50)} x2={pad.l + w} y2={py(50)} className="pm-mid" />
        <text x={pad.l} y={size - 10} className="pm-end">
          {positioning?.x_axis?.low}
        </text>
        <text x={pad.l + w} y={size - 10} textAnchor="end" className="pm-end">
          {positioning?.x_axis?.high} →
        </text>
        <text x={pad.l + w / 2} y={size - 10} textAnchor="middle" className="pm-axis">
          {positioning?.x_axis?.label}
        </text>
        <text transform={`translate(14 ${pad.t + h}) rotate(-90)`} className="pm-end">
          {positioning?.y_axis?.low}
        </text>
        <text transform={`translate(14 ${pad.t}) rotate(-90)`} textAnchor="end" className="pm-end">
          {positioning?.y_axis?.high} →
        </text>
        <text transform={`translate(14 ${pad.t + h / 2}) rotate(-90)`} textAnchor="middle" className="pm-axis">
          {positioning?.y_axis?.label}
        </text>
        {ordered.map((p, i) => {
          const cx = px(p.x)
          const cy = py(p.y)
          const on = highlight === p.name
          const show = () => {
            setTip({ x: (cx / size) * 100, y: (cy / size) * 100, title: p.name, body: p.rationale })
            onHighlight?.(p.name)
          }
          const hide = () => {
            setTip(null)
            onHighlight?.(null)
          }
          return (
            <g
              key={p.name + i}
              className={`pm-pt ${p.is_us ? 'us' : ''} ${on ? 'on' : ''}`}
              onMouseEnter={show}
              onMouseLeave={hide}
              onFocus={show}
              onBlur={hide}
              tabIndex={0}
              role="button"
              aria-label={`${p.name}: ${p.rationale}`}
            >
              <circle cx={cx} cy={cy} r="18" className="pm-hit" />
              {p.is_us && <circle cx={cx} cy={cy} r="17" className="pm-halo" />}
              <circle cx={cx} cy={cy} r={p.is_us ? 9 : 8} className="pm-dot" />
              {!p.is_us && (
                <text x={cx} y={cy + 3.5} textAnchor="middle" className="pm-num">
                  {p.n}
                </text>
              )}
              <text x={labels[i].x} y={labels[i].y} textAnchor={labels[i].anchor} className="pm-label">
                {p.name}
              </text>
            </g>
          )
        })}
      </svg>
      <Tip tip={tip} />
    </div>
  )
}

export function Radar({ scores = [] }) {
  const [tip, setTip] = useState(null)
  const n = scores.length
  if (n < 3) return null
  const size = 320
  const c = size / 2
  const R = size / 2 - 78
  const pt = (i, v) => {
    const a = -Math.PI / 2 + (2 * Math.PI * i) / n
    return [c + ((R * v) / 10) * Math.cos(a), c + ((R * v) / 10) * Math.sin(a)]
  }
  const poly = (v) => scores.map((_, i) => pt(i, typeof v === 'function' ? v(i) : v).join(',')).join(' ')
  return (
    <div className="viz radar-viz">
      <svg viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`Scorecard: ${scores.map((s) => `${s.dimension} ${s.score}`).join(', ')}`}>
        {[2, 4, 6, 8, 10].map((l) => (
          <polygon key={l} points={poly(l)} className="rd-ring" />
        ))}
        {scores.map((_, i) => {
          const [x, y] = pt(i, 10)
          return <line key={i} x1={c} y1={c} x2={x} y2={y} className="rd-spoke" />
        })}
        <polygon points={poly((i) => scores[i].score)} className="rd-shape" />
        {scores.map((s, i) => {
          const [x, y] = pt(i, s.score)
          const [lx, ly] = pt(i, 12.6)
          const anchor = Math.abs(lx - c) < 8 ? 'middle' : lx > c ? 'start' : 'end'
          const show = () => setTip({ x: (x / size) * 100, y: (y / size) * 100, title: `${s.dimension} · ${s.score}/10`, body: s.rationale })
          return (
            <g key={s.dimension} onMouseEnter={show} onMouseLeave={() => setTip(null)} onFocus={show} onBlur={() => setTip(null)} tabIndex={0}>
              <circle cx={x} cy={y} r="14" className="rd-hit" />
              <circle cx={x} cy={y} r="5" className="rd-dot" />
              <text x={lx} y={ly} textAnchor={anchor} dominantBaseline="middle" className="rd-label">
                {s.dimension}
                <tspan className="rd-val" dx="5">
                  {s.score}
                </tspan>
              </text>
            </g>
          )
        })}
      </svg>
      <Tip tip={tip} />
    </div>
  )
}

export function RiskHeat({ risks = [], active, onActive }) {
  const cells = {}
  risks.forEach((r, i) => {
    const key = `${r.likelihood}-${r.impact}`
    ;(cells[key] ||= []).push(i + 1)
  })
  return (
    <div className="heat" role="img" aria-label="Risk heatmap by likelihood and impact">
      <span className="heat-y">Likelihood</span>
      <div className="heat-grid">
        {[3, 2, 1].map((l) =>
          [1, 2, 3].map((im) => (
            <div key={`${l}-${im}`} className={`cell lvl${l * im}`}>
              {(cells[`${l}-${im}`] || []).map((n) => (
                <button
                  type="button"
                  key={n}
                  className={`rk ${active === n ? 'on' : ''}`}
                  onMouseEnter={() => onActive?.(n)}
                  onMouseLeave={() => onActive?.(null)}
                  onFocus={() => onActive?.(n)}
                  onBlur={() => onActive?.(null)}
                  aria-label={`Risk ${n}: ${risks[n - 1]?.risk}`}
                >
                  {n}
                </button>
              ))}
            </div>
          )),
        )}
      </div>
      <div className="heat-ticks">
        <span>Low</span>
        <span>Med</span>
        <span>High</span>
      </div>
      <span className="heat-x">Impact</span>
    </div>
  )
}

export function Dots({ score }) {
  const label = ['None', 'Partial', 'Full'][score] || 'None'
  return <span className={`dot-score s${score}`} title={label} aria-label={label} />
}

export function Meter({ value, tone, empty }) {
  return (
    <span className={`meter ${empty ? 'nodata' : ''}`} aria-hidden="true">
      <span className={`fill ${tone || ''}`} style={{ width: `${empty ? 0 : value}%` }} />
    </span>
  )
}

export function Severity({ value = 0 }) {
  return (
    <span className="sev" aria-label={`Severity ${value} of 5`}>
      {[0, 1, 2, 3, 4].map((i) => (
        <i key={i} className={i < value ? 'on' : ''} />
      ))}
    </span>
  )
}
