import { useState, useEffect, createContext, useContext } from 'react'
import { getMe, cabinetLogoutUrl } from '../api/client'

const AuthContext = createContext({ user: null, loading: true, setUser: () => {} })

/** Редирект VK ID на /login?code&device_id&state — куки сессии появляются только после POST /vkid/complete/.
 * Параллельный getMe() без куки даёт 401 и потом перезаписывает setUser(null) уже после успешного входа. */
function isVkIdLoginCallbackUrl() {
  if (typeof window === 'undefined') return false
  const path = window.location.pathname
  if (path !== '/login' && !path.endsWith('/login')) return false
  const q = new URLSearchParams(window.location.search)
  return !!(q.get('code') && q.get('device_id') && q.get('state'))
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isVkIdLoginCallbackUrl()) {
      setLoading(false)
      return
    }
    let cancelled = false
    getMe()
      .then((data) => {
        if (!cancelled) setUser(data)
      })
      .catch((err) => {
        if (cancelled) return
        const code = err?.response?.data?.code
        if (
          err?.response?.status === 403
          && (code === 'guest_no_cabinet'
            || code === 'associate_no_cabinet'
            || code === 'banned_no_access')
        ) {
          window.location.replace(cabinetLogoutUrl())
          return
        }
        setUser(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, setUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}

/** Лидер, заместитель или суперпользователь — кабинет /leader/*. */
export function canAccessLeaderCabinet(user) {
  return Boolean(
    user?.can_access_leader_cabinet
    || user?.is_superuser
    || user?.role === 'leader'
    || user?.role === 'deputy',
  )
}

/** Настройки сайта — только лидер (и Django superuser). */
export function canManageSettings(user) {
  return Boolean(
    user?.can_manage_settings || user?.is_superuser || user?.role === 'leader',
  )
}

/** Начисление и списание ОК по журналу — лидер, заместитель, superuser. */
export function canManageClanPoints(user) {
  return Boolean(
    user?.can_manage_clan_points
    || user?.is_superuser
    || user?.role === 'leader'
    || user?.role === 'deputy',
  )
}

/** Django /admin/ — staff или superuser (как в админке Django). */
export function canAccessDjangoAdmin(user) {
  return Boolean(user?.is_staff || user?.is_superuser)
}
