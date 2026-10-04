export const DIMENSIONS = [
  {
    key: 'customer_segment',
    label: 'Who it is for',
    question: 'Which customer segment are you specifically targeting?',
  },
  {
    key: 'pain_point',
    label: 'The pain',
    question: 'What is the biggest pain point for these customers?',
  },
  {
    key: 'frequency',
    label: 'How often',
    question: 'How frequently does this problem occur?',
  },
  {
    key: 'current_solution',
    label: 'What they use now',
    question: 'How are customers currently solving this problem?',
  },
  {
    key: 'advantage',
    label: 'Why this is better',
    question: 'How is your solution better than existing alternatives?',
  },
  {
    key: 'validation',
    label: 'What you have checked',
    question: 'Have you conducted customer interviews or validated the problem?',
  },
]

const PHASE_LABELS = {
  phase1_product_discovery: 'Discovery',
  phase2_product_context: 'Product context',
  phase2_build_market_query: 'Search query',
  phase3_market_tavily_search: 'Market search',
  phase3_market_llm_competitors: 'Naming competitors',
  phase4_voice_competitor_research: 'Customer voice',
  phase4_voice_llm_synthesis: 'Gap analysis',
}

export function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function formatElapsed(ms) {
  const total = Math.max(0, Math.floor(ms / 1000))
  const minutes = Math.floor(total / 60)
  const seconds = total % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

export function phaseLabel(phase) {
  if (PHASE_LABELS[phase]) return PHASE_LABELS[phase]
  return String(phase || '')
    .replace(/^phase\d+_/, '')
    .replaceAll('_', ' ')
}

export function secondsLabel(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return '0 seconds'
  const shown = n >= 10 ? String(Math.round(n)) : String(Math.round(n * 10) / 10)
  return `${shown} ${shown === '1' ? 'second' : 'seconds'}`
}

export function asList(value) {
  return Array.isArray(value) ? value.filter(Boolean) : []
}

export function asText(value) {
  if (typeof value === 'string') return value.trim()
  if (!value) return ''
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return ''
  }
}

export function readAnswer(mapping, key) {
  const value = mapping?.[key]
  if (!value || typeof value !== 'object') return { answered: false, answer: '' }
  const answer = String(value.answer || '').trim()
  return { answered: Boolean(value.answered) && Boolean(answer), answer }
}

export function leadFrom(text) {
  const clean = asText(text).replace(/\s+/g, ' ').trim()
  if (!clean) return ''
  const sentence = clean.match(/^[^.!?]+[.!?]/)
  const lead = (sentence ? sentence[0] : clean).trim()
  if (lead.length <= 180) return lead
  const cut = lead.slice(0, 180)
  const lastSpace = cut.lastIndexOf(' ')
  return `${(lastSpace > 60 ? cut.slice(0, lastSpace) : cut).trim()}…`
}

export function readTaskPayload(result) {
  if (!result) return null
  if (typeof result === 'string') return { status: 'error', detail: result }
  if (typeof result !== 'object') return { status: 'error', detail: 'The teardown failed.' }
  if (result.exc_message) {
    const msg = Array.isArray(result.exc_message)
      ? result.exc_message.join(' ')
      : String(result.exc_message)
    return { status: 'error', detail: msg || 'The teardown failed.' }
  }
  return result
}

export function findSentiment(voice, name) {
  const list = asList(voice?.competitor_sentiment).filter((item) => item && typeof item === 'object')
  const target = String(name || '').trim().toLowerCase()
  if (!target) return null
  return (
    list.find((item) => String(item.name || '').trim().toLowerCase() === target) ||
    list.find((item) => {
      const other = String(item.name || '').trim().toLowerCase()
      return other && (target.includes(other) || other.includes(target))
    }) ||
    null
  )
}
