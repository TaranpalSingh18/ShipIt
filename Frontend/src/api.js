const base = import.meta.env.VITE_API_URL || ''

export function apiUrl(path) {
  return `${base}${path}`
}

function detailMessage(data, fallback) {
  if (!data) return fallback
  if (typeof data === 'string') return data
  const detail = data.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail)) {
    const text = detail
      .map((item) => (item && item.msg) || '')
      .filter(Boolean)
      .join(' ')
    if (text) return text
  }
  return fallback
}

export async function api(path, { method = 'GET', token, body, form, signal } = {}) {
  const headers = {}
  if (token) headers.Authorization = `Bearer ${token}`

  let payload
  if (form) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    payload = new URLSearchParams(form)
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  let response
  try {
    response = await fetch(apiUrl(path), { method, headers, body: payload, signal })
  } catch (err) {
    if (err.name === 'AbortError') throw err
    const network = new Error('The server didn’t respond. Check that the API is running and try again.')
    network.cause = err
    throw network
  }

  const text = await response.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (!response.ok) {
    const offline = response.status === 502 || response.status === 503 || response.status === 504
    const error = new Error(
      offline
        ? 'The server didn’t respond. Check that the API is running and try again.'
        : detailMessage(data, response.statusText || 'Request failed'),
    )
    error.status = response.status
    error.data = data
    throw error
  }

  return data
}

export function friendlyError(err) {
  const msg = err?.message || 'The request failed.'
  if (msg === 'User is existing') return 'That email already has an account.'
  if (msg === 'User - Not found' || msg === 'Invalid credentials') {
    return 'That email and password don’t match.'
  }
  if (msg === 'Could not validate credentials') return 'This session expired. Log in again.'
  return msg
}

export function signup(name, email, password, signal) {
  return api('/api/signup', {
    method: 'POST',
    body: { name, email, password },
    signal,
  })
}

export function login(email, password, signal) {
  return api('/api/login', {
    method: 'POST',
    form: { username: email, password },
    signal,
  })
}

export function currentUser(token, signal) {
  return api('/api/query', { token, signal })
}

export function createProject(token, projectName, signal) {
  return api('/api/projects', {
    method: 'POST',
    token,
    body: { project_name: projectName },
    signal,
  })
}

export function runQuery(token, projectId, userQuery, signal) {
  return api('/api/query', {
    method: 'POST',
    token,
    body: { project_id: projectId, user_query: userQuery },
    signal,
  })
}

export function listProjects(token, signal) {
  return api('/api/projects', { token, signal })
}

export function getProject(token, projectId, signal) {
  return api(`/api/projects/${projectId}`, { token, signal })
}

export function startReport(token, projectId, signal) {
  return api(`/api/projects/${projectId}/reports`, { method: 'POST', token, signal })
}

export function getReport(token, reportId, signal) {
  return api(`/api/reports/${reportId}`, { token, signal })
}

/** Fetch the PDF with the auth header, then hand it to the browser as a download. */
export async function downloadReportPdf(token, reportId, filename = 'investor-memo.pdf') {
  let response
  try {
    response = await fetch(apiUrl(`/api/reports/${reportId}/pdf`), {
      headers: { Authorization: `Bearer ${token}` },
    })
  } catch {
    throw new Error('The server didn’t respond. Check that the API is running and try again.')
  }
  if (!response.ok) {
    const error = new Error(response.status === 404 ? 'The PDF isn’t ready yet.' : 'The download failed.')
    error.status = response.status
    throw error
  }
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.append(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 10_000)
}

const SESSION_KEY = 'shipit.session'
const BENCH_KEY = 'shipit.bench' // legacy key, cleared on sign-out

export function readSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const data = JSON.parse(raw)
    if (!data?.token || !data?.email) return null
    return { token: data.token, email: data.email, name: data.name || '' }
  } catch {
    return null
  }
}

export function writeSession(session) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY)
  try {
    sessionStorage.removeItem(BENCH_KEY)
  } catch {
    /* storage can be blocked */
  }
}
