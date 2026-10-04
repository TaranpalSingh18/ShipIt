import { useMemo, useState } from 'react'
import { apiUrl } from '../../api'
import { Dots, Meter, PositioningMap, Radar, RiskHeat, Severity, TamCircles } from './charts'

const SAT_TONE = { high: 'good', mixed: 'warn', low: 'risk' }
const title = (s = '') => s.charAt(0).toUpperCase() + s.slice(1)

export function Cite({ ids, onCite }) {
  const list = (ids || []).filter((id) => Number.isInteger(id)).slice(0, 4)
  if (!list.length) return null
  return (
    <sup className="cite">
      {list.map((id) => (
        <button type="button" key={id} onClick={() => onCite(id)} aria-label={`Source ${id}`}>
          {id}
        </button>
      ))}
    </sup>
  )
}

// Report images are either data URIs (older memos) or API paths.
const media = (src) => (src?.startsWith('/api/') ? apiUrl(src) : src)

export function Logo({ comp, size = 'md' }) {
  if (comp?.logo) return <img className={`logo ${size}`} src={media(comp.logo)} alt="" />
  const words = String(comp?.name || '?').split(/\s+/).filter(Boolean)
  const initials = ((words[0]?.[0] || '?') + (words[1]?.[0] || words[0]?.[1] || '')).toUpperCase()
  return (
    <span className={`logo ${size} avatar`} aria-hidden="true">
      {initials}
    </span>
  )
}

function Section({ id, kicker, heading, lede, children }) {
  return (
    <section id={id} className="r-section" aria-labelledby={`${id}-h`}>
      <header className="r-head">
        <p className="r-kicker">{kicker}</p>
        <h2 id={`${id}-h`} className="display">
          {heading}
        </h2>
        {lede && <p className="r-lede">{lede}</p>}
      </header>
      {children}
    </section>
  )
}

/* ---------------- summary ---------------- */
export function Summary({ r, onCite }) {
  const { narrative: n, market: m, meta } = r
  return (
    <Section id="summary" kicker="Executive summary" heading="The memo in one page">
      <div className="kpis">
        <div className="kpi">
          <span className="k-label">Total addressable market</span>
          <span className={`k-val ${m.tam.value_usd == null ? 'nf' : ''}`}>{m.tam.display || 'Not found'}</span>
          <span className="k-sub">
            {m.tam.value_usd != null ? m.tam.label : 'No sourced figure in research'} <Cite ids={m.tam.source_ids} onCite={onCite} />
          </span>
        </div>
        <div className="kpi">
          <span className="k-label">Market growth</span>
          <span className={`k-val ${m.cagr.value_usd == null ? 'nf' : ''}`}>{m.cagr.display || 'Not found'}</span>
          <span className="k-sub">
            {m.cagr.value_usd != null ? 'Compound annual growth' : 'No sourced growth rate'} <Cite ids={m.cagr.source_ids} onCite={onCite} />
          </span>
        </div>
        <div className="kpi">
          <span className="k-label">Competitors benchmarked</span>
          <span className="k-val">{meta.competitors_analysed}</span>
          <span className="k-sub">{meta.pain_signals} customer pain signals</span>
        </div>
        <div className="kpi">
          <span className="k-label">Evidence strength</span>
          <span className={`k-val ev-${meta.evidence}`}>{title(meta.evidence)}</span>
          <span className="k-sub">{r.sources.length} web sources consulted</span>
        </div>
      </div>

      <div className="exec">
        <div className="exec-text">
          {n.executive_summary.map((p, i) => (
            <p key={i} className={i === 0 ? 'first' : ''}>
              {p}
            </p>
          ))}
        </div>
        <div className="exec-side">
          <div className="list-card good">
            <h3>Why invest</h3>
            <ol className="ticks">
              {n.why_invest.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ol>
          </div>
          <div className="list-card risk">
            <h3>Key risks</h3>
            <ol className="ticks">
              {n.key_risks.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </Section>
  )
}

/* ---------------- problem ---------------- */
export function Problem({ r }) {
  const n = r.narrative
  return (
    <Section
      id="problem"
      kicker="Problem & customer"
      heading="Who hurts, how badly, and what they do today"
      lede="Pains are rated for severity out of five and backed, where we found one, by what real users say."
    >
      <div className="pain-grid">
        {n.pains.map((pain) => (
          <article className="pain" key={pain.id}>
            <div className="pain-top">
              <span className="chip p">{pain.id}</span>
              <Severity value={pain.severity} />
            </div>
            <h3>{pain.title}</h3>
            <p>{pain.detail}</p>
            {pain.quote && (
              <blockquote>
                “{pain.quote}”<cite>{pain.quote_by || 'User review'}</cite>
              </blockquote>
            )}
          </article>
        ))}
      </div>

      <h3 className="block-title">Customer segments</h3>
      <div className="tbl-wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th>Segment</th>
              <th>Job to be done</th>
              <th>Frequency</th>
              <th>Uses today</th>
              <th>Willingness to pay</th>
            </tr>
          </thead>
          <tbody>
            {n.segments.map((s, i) => {
              const [level, ...rest] = String(s.willingness_to_pay || '').split(' ')
              const tone = level.toLowerCase().replace(/[^a-z]/g, '')
              return (
                <tr key={i}>
                  <td className="strong">{s.name}</td>
                  <td>{s.job_to_be_done}</td>
                  <td>{s.frequency}</td>
                  <td>{s.current_solution}</td>
                  <td>
                    <span className={`pill wtp-${tone}`}>{title(tone)}</span>
                    <div className="tiny">{rest.join(' ').replace(/^[\s–—:,-]+/, '')}</div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {n.why_now.length > 0 && (
        <>
          <h3 className="block-title">Why now</h3>
          <div className="why-now">
            {n.why_now.map((w, i) => (
              <div className="wn" key={i}>
                <h4>{w.signal}</h4>
                <p>{w.detail}</p>
              </div>
            ))}
          </div>
        </>
      )}
    </Section>
  )
}

/* ---------------- value proposition ---------------- */
export function ValueProp({ r }) {
  const n = r.narrative
  const vp = n.value_prop
  const [focus, setFocus] = useState(null)
  const links = useMemo(() => {
    const map = {}
    vp.pain_relievers.forEach((rl) => {
      map[rl.id] = rl.relieves
      map[rl.relieves] = rl.id
    })
    vp.gain_creators.forEach((cr) => {
      map[cr.id] = cr.creates
      map[cr.creates] = cr.id
    })
    return map
  }, [vp])
  const lit = (id) => focus && (focus === id || links[focus] === id)
  const hover = (id) => ({
    onMouseEnter: () => setFocus(id),
    onMouseLeave: () => setFocus(null),
    onFocus: () => setFocus(id),
    onBlur: () => setFocus(null),
    tabIndex: 0,
  })
  // A render helper, not a component: a nested component type would remount on every hover.
  const item = (key, id, kind, text) => (
    <li key={key} className={`vp-item ${lit(id) ? 'lit' : ''} ${focus && !lit(id) && id ? 'dim' : ''}`} {...(id ? hover(id) : {})}>
      {id && <span className={`chip ${kind}`}>{id}</span>}
      <span>{text}</span>
    </li>
  )
  return (
    <Section
      id="solution"
      kicker="Solution & value proposition"
      heading="How the product fits the customer"
      lede="Hover any pain or gain to see which part of the product answers it."
    >
      <div className="canvas">
        <div className="vmap">
          <p className="shape-cap">Value map</p>
          <div className="square">
            <div className="zone z-products">
              <h4>Products & services</h4>
              <ul>
                {vp.products.map((p, i) => (
                  item(i, null, null, p)
                ))}
              </ul>
            </div>
            <div className="zone z-creators">
              <h4>Gain creators</h4>
              <ul>
                {vp.gain_creators.map((c) => (
                  item(c.id, c.id, "c", c.text)
                ))}
              </ul>
            </div>
            <div className="zone z-relievers">
              <h4>Pain relievers</h4>
              <ul>
                {vp.pain_relievers.map((c) => (
                  item(c.id, c.id, "r", c.text)
                ))}
              </ul>
            </div>
          </div>
        </div>
        <div className="fit-arrow" aria-hidden="true">
          <span>Fit</span>
        </div>
        <div className="cprof">
          <p className="shape-cap">Customer profile</p>
          <div className="circle">
            <div className="zone z-gains">
              <h4>Gains</h4>
              <ul>
                {vp.gains.map((g) => (
                  item(g.id, g.id, "g", g.text)
                ))}
              </ul>
            </div>
            <div className="zone z-pains">
              <h4>Pains</h4>
              <ul>
                {n.pains.map((p) => (
                  item(p.id, p.id, "p", p.title)
                ))}
              </ul>
            </div>
            <div className="zone z-jobs">
              <h4>Customer jobs</h4>
              <ul>
                {vp.jobs.map((j, i) => (
                  item(i, null, null, j)
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div className="two">
        <div>
          <h3 className="block-title">Before and after</h3>
          <div className="tbl-wrap">
            <table className="tbl ba">
              <thead>
                <tr>
                  <th />
                  <th>Today</th>
                  <th>With {n.product_name}</th>
                </tr>
              </thead>
              <tbody>
                {n.before_after.map((row, i) => (
                  <tr key={i}>
                    <td className="strong">{row.aspect}</td>
                    <td className="before">{row.before}</td>
                    <td className="after">{row.after}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div>
          <h3 className="block-title">User journey</h3>
          <ol className="journey">
            {n.journey.map((step, i) => (
              <li key={i}>
                <span className="j-num">{i + 1}</span>
                <div>
                  <h4>{step.title}</h4>
                  <p>{step.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </Section>
  )
}

/* ---------------- market ---------------- */
export function Market({ r, onCite }) {
  const m = r.market
  const rows = [
    ['TAM', m.tam],
    ['SAM', m.sam],
    ['SOM', m.som],
    ['CAGR', m.cagr],
  ]
  return (
    <Section
      id="market"
      kicker="Market opportunity"
      heading="How big this can get"
      lede="Every figure is quoted from a cited source or derived from one, with the arithmetic shown. Anything we couldn’t source says “Not found” instead of guessing."
    >
      <div className="market-top">
        <TamCircles tam={m.tam} sam={m.sam} som={m.som} />
        <div className="growth">
          <span className="g-label">Annual growth</span>
          <span className={`g-val ${m.cagr.value_usd == null ? 'nf' : ''}`}>{m.cagr.display || 'Not found'}</span>
          {m.cagr.value_usd != null && (
            <span className="g-bar">
              <span style={{ width: `${Math.min(100, m.cagr.value_usd * 3)}%` }} />
            </span>
          )}
          <span className="g-sub">
            {m.cagr.value_usd != null ? m.cagr.label : 'No source in the research stated a growth rate.'} <Cite ids={m.cagr.source_ids} onCite={onCite} />
          </span>
        </div>
      </div>

      <div className="tbl-wrap">
        <table className="tbl figures">
          <thead>
            <tr>
              <th />
              <th>Definition</th>
              <th>Value</th>
              <th>Method</th>
              <th>Confidence</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([key, f]) => (
              <tr key={key}>
                <td>
                  <span className="pill key">{key}</span>
                </td>
                <td>
                  {f.label || '—'}
                  {f.note && <div className="tiny">{f.note}</div>}
                </td>
                <td className={`num ${f.value_usd == null ? 'nf' : ''}`}>{f.display || 'Not found'}</td>
                <td>{title(f.method) || '—'}</td>
                <td>
                  <span className={`conf c-${f.confidence}`} aria-hidden="true">
                    <i />
                    <i />
                    <i />
                  </span>
                  {title(f.confidence)}
                </td>
                <td>
                  {f.source_ids.length ? <Cite ids={f.source_ids} onCite={onCite} /> : f.value_usd != null ? <span className="tiny">From TAM</span> : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="two">
        <div>
          <h3 className="block-title">Sizing logic</h3>
          {m.sizing_logic.length ? (
            <ol className="steps">
              {m.sizing_logic.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
          ) : (
            <p className="empty">No derivation was possible without a sourced TAM. Size it bottom-up next: number of target buyers × annual price.</p>
          )}
        </div>
        <div>
          <h3 className="block-title">Market trends</h3>
          {m.trends.length === 0 && <p className="empty">The research didn’t surface sourced trends for this market.</p>}
          {m.trends.map((t, i) => (
            <div className="trend" key={i}>
              <h4>
                {t.title} <Cite ids={t.source_ids} onCite={onCite} />
              </h4>
              <p>{t.detail}</p>
            </div>
          ))}
        </div>
      </div>
    </Section>
  )
}

/* ---------------- competitors ---------------- */
const SORTS = {
  threat: (c) => ({ high: 3, medium: 2, low: 1 })[c.threat] || 0,
  satisfaction: (c) => (c.satisfaction === 'unknown' ? -1 : c.satisfaction_score),
  name: (c) => c.name.toLowerCase(),
}

export function Landscape({ r, onCite }) {
  const [view, setView] = useState('cards')
  const [sort, setSort] = useState({ key: 'threat', dir: -1 })
  const comps = useMemo(() => {
    const list = [...r.competition.competitors]
    const fn = SORTS[sort.key]
    return list.sort((a, b) => (fn(a) > fn(b) ? 1 : fn(a) < fn(b) ? -1 : 0) * sort.dir)
  }, [r, sort])
  const header = (key, label) => (
    <th aria-sort={sort.key === key ? (sort.dir === 1 ? 'ascending' : 'descending') : 'none'}>
      <button type="button" className="sort" onClick={() => setSort((s) => ({ key, dir: s.key === key ? -s.dir : -1 }))}>
        {label}
        <span aria-hidden="true">{sort.key === key ? (sort.dir === 1 ? '↑' : '↓') : '↕'}</span>
      </button>
    </th>
  )

  return (
    <Section
      id="landscape"
      kicker="Competitive landscape"
      heading="Who else is solving this"
      lede="Company facts come from cited sources; a dash means we found none. Satisfaction and complaints come from public reviews and forums."
    >
      <div className="seg-ctl" role="group" aria-label="Competitor view">
        <button type="button" aria-pressed={view === 'cards'} onClick={() => setView('cards')}>
          Cards
        </button>
        <button type="button" aria-pressed={view === 'table'} onClick={() => setView('table')}>
          Table
        </button>
      </div>

      {view === 'cards' ? (
        <div className="comp-grid">
          {comps.map((c) => (
            <article className="comp" key={c.name}>
              <div className="shot">
                {c.screenshot ? <img src={media(c.screenshot)} alt={`${c.name} homepage`} /> : <div className="shot-empty"><Logo comp={c} size="lg" /></div>}
                <span className={`threat t-${c.threat}`}>{title(c.threat)} threat</span>
              </div>
              <div className="comp-body">
                <div className="comp-id">
                  <Logo comp={c} />
                  <div>
                    <h3>{c.name}</h3>
                    {c.domain ? (
                      <a className="domain" href={`https://${c.domain}`} target="_blank" rel="noreferrer">
                        {c.domain}
                      </a>
                    ) : (
                      <span className="domain">website unknown</span>
                    )}
                  </div>
                </div>
                <p className="tagline">{c.tagline}</p>
                <dl className="facts">
                  {[
                    ['Founded', c.founded],
                    ['HQ', c.hq],
                    ['Funding', c.funding],
                    ['Pricing', c.pricing],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <dt>{k}</dt>
                      <dd>{v || '—'}</dd>
                    </div>
                  ))}
                </dl>
                <div className="sat">
                  <span>Satisfaction</span>
                  <Meter value={c.satisfaction_score} tone={SAT_TONE[c.satisfaction]} empty={c.satisfaction === 'unknown'} />
                  <b>{c.satisfaction === 'unknown' ? 'No data' : title(c.satisfaction)}</b>
                </div>
                {c.top_complaint && (
                  <p className="complaint">
                    <b>Top complaint</b> {c.top_complaint}
                  </p>
                )}
                {(c.strengths.length > 0 || c.weaknesses.length > 0) && (
                  <div className="sw">
                    <ul>
                      {c.strengths.map((s, i) => (
                        <li key={i} className="plus">
                          {s}
                        </li>
                      ))}
                    </ul>
                    <ul>
                      {c.weaknesses.map((s, i) => (
                        <li key={i} className="minus">
                          {s}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {c.source_ids.length > 0 && (
                  <p className="srcs">
                    Sources <Cite ids={c.source_ids} onCite={onCite} />
                  </p>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="tbl-wrap">
          <table className="tbl comp-tbl">
            <thead>
              <tr>
                {header('name', 'Competitor')}
                <th>Founded</th>
                <th>Funding</th>
                <th>Pricing</th>
                {header('satisfaction', 'Satisfaction')}
                {header('threat', 'Threat')}
              </tr>
            </thead>
            <tbody>
              {comps.map((c) => (
                <tr key={c.name}>
                  <td>
                    <span className="cell-id">
                      <Logo comp={c} size="sm" />
                      <span className="strong">{c.name}</span>
                    </span>
                    <div className="tiny">{c.tagline}</div>
                  </td>
                  <td>{c.founded || '—'}</td>
                  <td>{c.funding || '—'}</td>
                  <td>
                    {c.pricing || '—'} <Cite ids={c.pricing ? c.source_ids : []} onCite={onCite} />
                  </td>
                  <td>
                    <span className="sat inline">
                      <Meter value={c.satisfaction_score} tone={SAT_TONE[c.satisfaction]} empty={c.satisfaction === 'unknown'} />
                      <b>{c.satisfaction === 'unknown' ? 'No data' : title(c.satisfaction)}</b>
                    </span>
                  </td>
                  <td>
                    <span className={`threat static t-${c.threat}`}>{title(c.threat)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  )
}

/* ---------------- head to head ---------------- */
export function HeadToHead({ r }) {
  const c = r.competition
  const fm = c.feature_matrix
  const [hl, setHl] = useState(null)
  return (
    <Section id="h2h" kicker="Head-to-head" heading="Where we win, and where we don’t" lede="Our column shows what the product will offer at launch, not a roadmap.">
      <div className="tbl-wrap">
        <table className="matrix">
          <thead>
            <tr>
              <th />
              {fm.rows.map((row, i) => (
                <th key={row.name} className={`${i === 0 ? 'us' : ''} ${hl === row.name ? 'hl' : ''}`} scope="col">
                  {row.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {fm.capabilities.map((cap, ci) => (
              <tr key={cap}>
                <th scope="row" className="cap">
                  {cap}
                </th>
                {fm.rows.map((row, i) => (
                  <td key={row.name} className={`${i === 0 ? 'us' : ''} ${hl === row.name ? 'hl' : ''}`}>
                    <Dots score={row.scores[ci] ?? 0} />
                  </td>
                ))}
              </tr>
            ))}
            <tr className="total">
              <th scope="row" className="cap">
                Coverage
              </th>
              {fm.rows.map((row, i) => (
                <td key={row.name} className={`${i === 0 ? 'us' : ''} ${hl === row.name ? 'hl' : ''}`}>
                  {Math.round((row.scores.reduce((a, b) => a + b, 0) / Math.max(1, fm.capabilities.length * 2)) * 100)}%
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
      <div className="legend">
        <span>
          <Dots score={2} /> Full
        </span>
        <span>
          <Dots score={1} /> Partial
        </span>
        <span>
          <Dots score={0} /> None
        </span>
      </div>

      {c.positioning.points.length > 0 && (
        <div className="pos">
          <div>
            <h3 className="block-title">
              Positioning map <span className="tag">Analyst assessment</span>
            </h3>
            <PositioningMap positioning={c.positioning} highlight={hl} onHighlight={setHl} />
          </div>
          <ol className="pos-notes">
            {c.positioning.points.map((p, i) => (
              <li
                key={p.name}
                className={`${p.is_us ? 'us' : ''} ${hl === p.name ? 'hl' : ''}`}
                onMouseEnter={() => setHl(p.name)}
                onMouseLeave={() => setHl(null)}
              >
                <span className="pn-num">{p.is_us ? '★' : i + 1}</span>
                <div>
                  <b>{p.name}</b>
                  <p>{p.rationale}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      {c.differentiation && (
        <div className="callout">
          <p className="callout-k">Why we win</p>
          <p>{c.differentiation}</p>
        </div>
      )}
    </Section>
  )
}

/* ---------------- voice ---------------- */
export function Voice({ r }) {
  const v = r.customer_voice
  const comps = r.competition.competitors
  const themes = r.competition.complaint_themes
  const max = Math.max(1, ...themes.map((t) => t.mentions))
  const byName = Object.fromEntries(v.competitor_sentiment.map((s) => [s.name.toLowerCase(), s]))
  return (
    <Section id="voice" kicker="Voice of the customer" heading="What users actually say" lede="Synthesised from public reviews, forums and comparison sites about each competitor.">
      {v.current_solutions.length > 0 && (
        <div className="chips-row">
          <span className="chips-label">What people use today</span>
          {v.current_solutions.map((s, i) => (
            <span className="chip-lg" key={i}>
              {s}
            </span>
          ))}
        </div>
      )}
      <div className="two">
        <div>
          <h3 className="block-title">Sentiment by competitor</h3>
          {comps.map((c) => {
            const s = byName[c.name.toLowerCase()]
            return (
              <details className="sent" key={c.name} open={Boolean(s?.common_complaints?.length)}>
                <summary>
                  <Logo comp={c} size="sm" />
                  <b>{c.name}</b>
                  <Meter value={c.satisfaction_score} tone={SAT_TONE[c.satisfaction]} empty={c.satisfaction === 'unknown'} />
                  <span className="sat-val">{c.satisfaction === 'unknown' ? 'No data' : title(c.satisfaction)}</span>
                </summary>
                {s?.common_complaints?.length ? (
                  <ul className="complaints">
                    {s.common_complaints.map((item, i) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="tiny pad">No complaints found in the research.</p>
                )}
              </details>
            )
          })}
        </div>
        <div>
          <h3 className="block-title">Recurring complaint themes</h3>
          {themes.map((t, i) => (
            <div className="theme" key={i}>
              <div className="theme-head">
                <b>{t.theme}</b>
                <span>
                  {t.mentions} mention{t.mentions === 1 ? '' : 's'}
                </span>
              </div>
              <div className="hbar">
                <span style={{ width: `${(t.mentions / max) * 100}%` }} />
              </div>
              <p className="tiny">“{t.example}”</p>
            </div>
          ))}
        </div>
      </div>

      <h3 className="block-title">Market gaps and our angle</h3>
      <div className="tbl-wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th>Gap</th>
              <th>Evidence</th>
              <th>How we close it</th>
            </tr>
          </thead>
          <tbody>
            {v.market_gaps.map((g, i) => (
              <tr key={i}>
                <td className="strong">{g.gap}</td>
                <td>{g.evidence}</td>
                <td className="after">{g.product_opportunity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  )
}

/* ---------------- business ---------------- */
export function Business({ r, onCite }) {
  const bm = r.strategy.business_model
  const priced = r.competition.competitors.filter((c) => c.pricing)
  return (
    <Section id="business" kicker={bm.revenue_model || 'Business model'} heading="How it makes money" lede={bm.summary}>
      <div className="tiers">
        {bm.pricing_tiers.map((t, i) => (
          <div className={`tier ${i === 1 ? 'feat' : ''}`} key={i}>
            {i === 1 && <span className="tier-flag">Core plan</span>}
            <p className="tier-name">{t.name}</p>
            <p className="tier-price display">{t.price}</p>
            <p className="tier-for">{t.for_who}</p>
            <ul>
              {t.includes.map((item, j) => (
                <li key={j}>{item}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      {priced.length > 0 && (
        <div className="bench-prices">
          <span className="chips-label">Competitor pricing</span>
          {priced.map((c) => (
            <span className="bp" key={c.name}>
              <Logo comp={c} size="sm" />
              <b>{c.name}</b> {c.pricing} <Cite ids={c.source_ids} onCite={onCite} />
            </span>
          ))}
        </div>
      )}

      <h3 className="block-title">
        Unit economics <span className="tag warn">Assumptions, not data</span>
      </h3>
      <div className="ue">
        {bm.unit_economics.map((u, i) => (
          <div className="ue-tile" key={i}>
            <p className="ue-m">{u.metric}</p>
            <p className="ue-v display">{u.value}</p>
            <p className="tiny">{u.assumption}</p>
          </div>
        ))}
      </div>

      <h3 className="block-title">Go-to-market</h3>
      <div className="tbl-wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th>Channel</th>
              <th>Tactic</th>
              <th>Priority</th>
            </tr>
          </thead>
          <tbody>
            {bm.gtm.map((g, i) => (
              <tr key={i}>
                <td className="strong">{g.channel}</td>
                <td>{g.tactic}</td>
                <td>
                  <span className={`pill pr-${g.priority.toLowerCase()}`}>{title(g.priority)}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  )
}

/* ---------------- risk ---------------- */
export function Risks({ r }) {
  const s = r.strategy
  const [active, setActive] = useState(null)
  return (
    <Section id="risks" kicker="Moats, risks & mitigations" heading="What could kill this, and the plan for each">
      <div className="risk-wrap">
        <RiskHeat risks={s.risks} active={active} onActive={setActive} />
        <div className="tbl-wrap">
          <table className="tbl risks">
            <thead>
              <tr>
                <th>#</th>
                <th>Risk</th>
                <th>L × I</th>
                <th>Mitigation</th>
              </tr>
            </thead>
            <tbody>
              {s.risks.map((risk, i) => (
                <tr key={i} className={active === i + 1 ? 'hl' : ''} onMouseEnter={() => setActive(i + 1)} onMouseLeave={() => setActive(null)}>
                  <td>
                    <span className="rk static">{i + 1}</span>
                  </td>
                  <td className="strong">
                    {risk.risk}
                    <div className="tiny">{title(risk.category)}</div>
                  </td>
                  <td className="num">
                    {risk.likelihood} × {risk.impact}
                  </td>
                  <td>{risk.mitigation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="two">
        <div>
          <h3 className="block-title">
            Moats <span className="tag">Strength today</span>
          </h3>
          {s.moats.map((m, i) => (
            <div className="moat" key={i}>
              <div className="moat-head">
                <b>{m.name}</b>
                <span className="seg" aria-label={`Strength ${m.strength} of 5`}>
                  {[0, 1, 2, 3, 4].map((k) => (
                    <i key={k} className={k < m.strength ? 'on' : ''} />
                  ))}
                </span>
              </div>
              <p>{m.detail}</p>
            </div>
          ))}
        </div>
        <div>
          <h3 className="block-title">Growth opportunities</h3>
          {s.opportunities.map((o, i) => (
            <div className="opp" key={i}>
              <h4>{o.title}</h4>
              <p>{o.detail}</p>
            </div>
          ))}
        </div>
      </div>
    </Section>
  )
}

/* ---------------- verdict ---------------- */
export function VerdictSection({ r }) {
  const s = r.strategy
  return (
    <Section id="verdict" kicker="Verdict" heading={s.verdict.label}>
      <p className="verdict-head">{s.verdict.headline}</p>
      <div className="score-wrap">
        <Radar scores={s.scorecard} />
        <div className="tbl-wrap">
          <table className="tbl scores">
            <thead>
              <tr>
                <th>Dimension</th>
                <th>Score</th>
                <th>Why</th>
              </tr>
            </thead>
            <tbody>
              {s.scorecard.map((sc) => (
                <tr key={sc.dimension}>
                  <td className="strong">{sc.dimension}</td>
                  <td className="nowrap">
                    <span className="sbar">
                      <span style={{ width: `${sc.score * 10}%` }} />
                    </span>
                    <b>{sc.score}</b>
                    <span className="muted">/10</span>
                  </td>
                  <td>{sc.rationale}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="verdict-body">
        {s.verdict.paragraphs.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>
      {s.verdict.bottom_line && (
        <div className="callout">
          <p className="callout-k">Bottom line</p>
          <p>{s.verdict.bottom_line}</p>
        </div>
      )}
    </Section>
  )
}

/* ---------------- next steps ---------------- */
export function NextSteps({ r }) {
  const s = r.strategy
  return (
    <Section id="next" kicker="Next steps" heading="The next 90 days" lede="Each milestone is a measurable test. Hitting it moves the scorecard; missing it is a signal to change course.">
      <ol className="milestones">
        {s.milestones.map((ms, i) => (
          <li className="ms" key={i}>
            <span className="ms-h">{ms.horizon}</span>
            <span className="ms-dot" aria-hidden="true" />
            <h4>{ms.goal}</h4>
            <dl>
              <dt>Metric</dt>
              <dd>{ms.metric}</dd>
              <dt>Target</dt>
              <dd className="target">{ms.target}</dd>
            </dl>
          </li>
        ))}
      </ol>
      <h3 className="block-title">Questions an investor will ask</h3>
      <div className="qa">
        {s.investor_qa.map((qa, i) => (
          <details key={i} className="qa-item" open={i === 0}>
            <summary>{qa.question}</summary>
            <p>{qa.answer}</p>
          </details>
        ))}
      </div>
    </Section>
  )
}

/* ---------------- sources ---------------- */
export function SourcesList({ sources, cited, activeId }) {
  return (
    <ol className="sources">
      {sources.map((s) => (
        <li key={s.id} id={`src-${s.id}`} className={`${cited.has(s.id) ? 'cited' : ''} ${activeId === s.id ? 'flash' : ''}`}>
          <span className="s-id">{s.id}</span>
          <a href={s.url} target="_blank" rel="noreferrer">
            {s.title}
          </a>
          <span className="s-url">{s.domain}</span>
        </li>
      ))}
    </ol>
  )
}
