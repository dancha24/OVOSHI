import axios from 'axios'

// В dev задать VITE_API_URL=http://localhost:8000 чтобы cookie сессии отправлялись на бэкенд
export const apiOrigin = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL.replace(/\/$/, '')
  : ''

function readCookie(name) {
  const prefix = `; ${document.cookie}`
  const parts = prefix.split(`; ${name}=`)
  if (parts.length < 2) return null
  return parts.pop().split(';').shift() || null
}

const baseURL = apiOrigin ? `${apiOrigin}/api` : '/api'
const client = axios.create({
  baseURL,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

// SessionAuthentication в DRF требует X-CSRFToken для POST/PATCH/PUT/DELETE
client.interceptors.request.use((config) => {
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }
  const m = (config.method || 'get').toLowerCase()
  if (!['get', 'head', 'options', 'trace'].includes(m)) {
    const t = readCookie('csrftoken')
    if (t) {
      config.headers = config.headers || {}
      config.headers['X-CSRFToken'] = t
    }
  }
  return config
})

export async function getSettings() {
  const { data } = await client.get('/settings/')
  return data
}

/** Сброс сессии гостя (роль guest): Django allauth logout, возврат на /login */
export function cabinetLogoutUrl() {
  const next = `${window.location.origin}/login`
  const prefix = apiOrigin || ''
  return `${prefix}/accounts/logout/?next=${encodeURIComponent(next)}`
}

export async function getMe() {
  const { data } = await client.get('/auth/me/')
  return data
}

export async function patchProfile(payload) {
  const { data } = await client.patch('/auth/me/', payload)
  return data
}

export async function getParticipants() {
  const { data } = await client.get('/participants/')
  return data
}

export async function patchParticipant(id, payload) {
  const { data } = await client.patch(`/participants/${id}/`, payload)
  return data
}

export async function postParticipantKick(id, payload) {
  const { data } = await client.post(`/participants/${id}/kick/`, payload)
  return data
}

export async function postParticipantBan(id, payload) {
  const { data } = await client.post(`/participants/${id}/ban/`, payload)
  return data
}

export async function postParticipantUnban(id) {
  const { data } = await client.post(`/participants/${id}/unban/`, {})
  return data
}

export async function getOkLedger(participantId) {
  const { data } = await client.get(`/participants/${participantId}/ok-ledger/`)
  return data
}

export async function postOkLedger(participantId, payload) {
  const { data } = await client.post(`/participants/${participantId}/ok-ledger/`, payload)
  return data
}

export async function getApplications(params = {}) {
  const { data } = await client.get('/applications/', { params })
  return data
}

/** Куда вести лидера/заместителя после входа: заявки, если есть pending, иначе участники. */
export async function getLeaderCabinetEntryPath() {
  try {
    const rows = await getApplications({ status: 'pending' })
    return rows.length > 0 ? '/leader/applications' : '/leader/participants'
  } catch {
    return '/leader/participants'
  }
}

export async function patchApplication(id, payload) {
  const { data } = await client.patch(`/applications/${id}/`, payload)
  return data
}

export async function patchSettings(payload) {
  const { data } = await client.patch('/settings/', payload)
  return data
}

/** Все лоты (включая неактивные) — лидер / заместитель, см. ?all=1 на бэкенде. */
export async function getShopLotsAll() {
  const { data } = await client.get('/shop/lots/', { params: { all: '1' } })
  return data
}

export async function createShopLot(payload) {
  const { data } = await client.post('/shop/lots/', payload)
  return data
}

export async function patchShopLot(id, payload) {
  const { data } = await client.patch(`/shop/lots/${id}/`, payload)
  return data
}

export async function deleteShopLot(id) {
  await client.delete(`/shop/lots/${id}/`)
}
