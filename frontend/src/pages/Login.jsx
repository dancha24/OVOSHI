import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getLeaderCabinetEntryPath, getSettings } from '../api/client'
import { sha256ArrayBufferUtf8 } from '../vendor/sha256Pkce.js'
import { useAuth, canAccessLeaderCabinet } from '../hooks/useAuth'

const VK_PKCE_VERIFIER_KEY = 'vkid_pkce_verifier'
const VK_STATE_KEY = 'vkid_state'

/** PKCE S256: BASE64URL(SHA256(verifier)). На HTTP нет crypto.subtle — только HTTPS и localhost — поэтому запасной SHA-256. */
async function sha256Base64Url(input) {
  let bytes
  const subtle = globalThis.crypto?.subtle
  if (subtle) {
    const enc = new TextEncoder()
    const digest = await subtle.digest('SHA-256', enc.encode(input))
    bytes = new Uint8Array(digest)
  } else {
    const buf = sha256ArrayBufferUtf8(input)
    bytes = new Uint8Array(buf)
  }
  let binary = ''
  for (const b of bytes) binary += String.fromCharCode(b)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

function randomUrlSafe(size = 64) {
  const arr = new Uint8Array(size)
  crypto.getRandomValues(arr)
  let binary = ''
  for (const b of arr) binary += String.fromCharCode(b)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

function apiPath(path) {
  const p = path.startsWith('/') ? path : `/${path}`
  const origin = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
  return origin ? `${origin}${p}` : p
}

export default function Login() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { setUser } = useAuth()
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [clientId, setClientId] = useState(() => (import.meta.env.VITE_VK_ID || '').trim())
  const [vkPublicUrl, setVkPublicUrl] = useState('')
  const [registerGroupUrl, setRegisterGroupUrl] = useState(null)
  const [guestCabinetMsg, setGuestCabinetMsg] = useState(false)
  const [associateCabinetMsg, setAssociateCabinetMsg] = useState(false)
  const [bannedMsg, setBannedMsg] = useState(false)
  const handledVkCallbackRef = useRef(null)

  useEffect(() => {
    if (searchParams.get('cabinet_guest') === '1') {
      setGuestCabinetMsg(true)
    }
  }, [searchParams])

  useEffect(() => {
    getSettings()
      .then((s) => setVkPublicUrl(typeof s.vk_public_url === 'string' ? s.vk_public_url : ''))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (clientId) return
    fetch(apiPath('/api/auth/vkid/config/'), { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        if (j && typeof j.client_id === 'string' && j.client_id.trim()) setClientId(j.client_id.trim())
      })
      .catch(() => {})
  }, [clientId])

  const startVkIdFlow = async () => {
    if (!clientId) {
      setError('VK ID не настроен: задайте VK_CLIENT_ID на бэкенде или VITE_VK_ID во фронте.')
      return
    }
    setBusy(true)
    setError(null)
    setRegisterGroupUrl(null)
    try {
      const codeVerifier = randomUrlSafe(72)
      const codeChallenge = await sha256Base64Url(codeVerifier)
      const state = randomUrlSafe(32)
      const redirectUri = `${window.location.origin}/login`

      sessionStorage.setItem(VK_PKCE_VERIFIER_KEY, codeVerifier)
      sessionStorage.setItem(VK_STATE_KEY, state)

      const sp = new URLSearchParams()
      sp.set('response_type', 'code')
      sp.set('client_id', clientId)
      sp.set('redirect_uri', redirectUri)
      sp.set('state', state)
      sp.set('scope', 'email vkid.personal_info')
      sp.set('code_challenge', codeChallenge)
      sp.set('code_challenge_method', 'S256')
      window.location.href = `https://id.vk.ru/authorize?${sp.toString()}`
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setBusy(false)
    }
  }

  useEffect(() => {
    const code = searchParams.get('code')
    const deviceId = searchParams.get('device_id')
    const state = searchParams.get('state')
    if (!code || !deviceId || !state) return

    const callbackKey = `${code}:${deviceId}:${state}`
    if (handledVkCallbackRef.current === callbackKey) return
    handledVkCallbackRef.current = callbackKey

    const storedState = sessionStorage.getItem(VK_STATE_KEY) ?? ''
    const codeVerifier = sessionStorage.getItem(VK_PKCE_VERIFIER_KEY) ?? ''
    const redirectUri = `${window.location.origin}/login`

    const clearVkSession = () => {
      sessionStorage.removeItem(VK_STATE_KEY)
      sessionStorage.removeItem(VK_PKCE_VERIFIER_KEY)
      const clean = new URL(window.location.href)
      clean.searchParams.delete('code')
      clean.searchParams.delete('device_id')
      clean.searchParams.delete('state')
      clean.searchParams.delete('expires_in')
      clean.searchParams.delete('ext_id')
      clean.searchParams.delete('type')
      window.history.replaceState(null, '', clean.toString())
    }

    if (!storedState || storedState !== state || !codeVerifier) {
      clearVkSession()
      setError('VK ID: не прошла проверка state или PKCE. Попробуйте войти снова.')
      return
    }

    void (async () => {
      setBusy(true)
      setError(null)
      setRegisterGroupUrl(null)
      try {
        const r = await fetch(apiPath('/api/auth/vkid/complete/'), {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            code,
            device_id: deviceId,
            code_verifier: codeVerifier,
            state,
            redirect_uri: redirectUri,
          }),
        })
        const txt = await r.text()
        if (!r.ok) {
          const trimmed = (txt || '').trim()
          const looksLikeHtml =
            trimmed.startsWith('<!DOCTYPE') || trimmed.startsWith('<html') || trimmed.startsWith('<HTML')
          if (looksLikeHtml || trimmed.includes('ProgrammingError')) {
            setRegisterGroupUrl(null)
            throw new Error(
              'Ошибка на сервере при входе. Чаще всего не применены миграции базы: на бэкенде выполните '
                + '`python manage.py migrate` и перезапустите приложение. Подробности — в логах Django.',
            )
          }
          let msg = `Ошибка ${r.status}`
          let groupUrl = null
          try {
            const j = JSON.parse(txt)
            if (j.code === 'guest_no_cabinet') {
              setGuestCabinetMsg(true)
            }
            if (j.code === 'associate_no_cabinet') {
              setAssociateCabinetMsg(true)
            }
            if (j.code === 'banned_no_access') {
              setBannedMsg(true)
            }
            if (typeof j.error === 'string' && j.error.trim()) msg = j.error.trim()
            if (typeof j.vk_group_url === 'string' && j.vk_group_url.trim()) {
              groupUrl = j.vk_group_url.trim()
            }
          } catch {
            if (trimmed) msg = trimmed.slice(0, 400)
          }
          setRegisterGroupUrl(groupUrl)
          throw new Error(msg)
        }
        const user = JSON.parse(txt)
        setUser(user)
        clearVkSession()
        if (canAccessLeaderCabinet(user)) {
          const path = await getLeaderCabinetEntryPath()
          navigate(path, { replace: true })
        } else {
          navigate('/profile', { replace: true })
        }
      } catch (err) {
        clearVkSession()
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        setBusy(false)
      }
    })()
  }, [searchParams, navigate, setUser])

  return (
    <div className="row justify-content-center">
      <div className="col-12 col-md-10 col-lg-5">
        <div className="card vk-card border-0 shadow-none">
          <div className="card-body p-4 p-md-5">
            <h2 className="h4 mb-3">Вход</h2>
            <p className="text-secondary small mb-3">
              Вход только для участников клана (не гостей). Гости пользуются только ботом ВКонтакте в сообществе;
              после принятия заявки лидером здесь можно войти тем же аккаунтом ВК.
            </p>
            {guestCabinetMsg && (
              <div className="alert alert-info small mb-3" role="alert">
                Кабинет на сайте недоступен для гостей. Пишите боту в группе; когда заявку примут, снова нажмите
                «Войти через ВКонтакте».
              </div>
            )}
            {associateCabinetMsg && (
              <div className="alert alert-info small mb-3" role="alert">
                Кабинет на сайте недоступен для соучастников (турниры, исключённые из клана). Пользуйтесь ботом ВКонтакте.
              </div>
            )}
            {bannedMsg && (
              <div className="alert alert-danger small mb-3" role="alert">
                Доступ к сайту заблокирован администрацией клана.
              </div>
            )}
            {vkPublicUrl ? (
              <p className="small mb-3">
                <a href={vkPublicUrl} target="_blank" rel="noopener noreferrer">
                  Регистрация — напишите боту в группе ВК
                </a>
              </p>
            ) : (
              <p className="text-muted small mb-3">
                Регистрация — только через группу ВКонтакте (ссылку на сообщество можно задать в настройках сайта).
              </p>
            )}
            {error && (
              <div className="alert alert-danger" role="alert">
                <p className="small mb-2">{error}</p>
                {registerGroupUrl && (
                  <a href={registerGroupUrl} className="alert-link fw-semibold" target="_blank" rel="noopener noreferrer">
                    Перейти в сообщество ВКонтакте
                  </a>
                )}
              </div>
            )}
            <button
              type="button"
              className="btn btn-primary w-100 py-2"
              disabled={busy}
              onClick={() => void startVkIdFlow()}
            >
              {busy ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />
                  Подождите…
                </>
              ) : (
                'Войти через ВКонтакте'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
