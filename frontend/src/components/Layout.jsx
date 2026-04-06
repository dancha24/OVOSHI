import { useCallback } from 'react'
import { Outlet, Link, NavLink } from 'react-router-dom'
import { cabinetLogoutUrl } from '../api/client'
import { useAuth, canAccessLeaderCabinet, canManageSettings, canAccessDjangoAdmin } from '../hooks/useAuth'
import {
  IconAdmin,
  IconInbox,
  IconLogin,
  IconLogout,
  IconPeople,
  IconProfile,
  IconSettings,
  IconShop,
} from './VkNavIcons'

const apiBase = import.meta.env.VITE_API_URL || ''
const MOBILE_OFFCANVAS_ID = 'ovoshiSidebarOffcanvas'

function navLinkClass({ isActive }) {
  return `vk-nav-link d-flex align-items-center gap-3${isActive ? ' vk-nav-link--active' : ''}`
}

/**
 * Закрыть мобильное меню тем же Bootstrap, что открыл offcanvas (из bundle в main.jsx).
 * Нельзя вешать data-bs-dismiss на <a>: Bootstrap делает preventDefault и ломает Router и выход.
 */
function closeMobileOffcanvas() {
  const el = document.getElementById(MOBILE_OFFCANVAS_ID)
  if (!el?.classList.contains('show')) return
  el.querySelector('.offcanvas-header button.btn-close')?.click()
}

/**
 * @param {{ user: object | null, loading: boolean, onMobileItemClick?: () => void }} props
 */
function SidebarNav({ user, loading, onMobileItemClick }) {
  const onTap = onMobileItemClick
    ? () => {
        onMobileItemClick()
      }
    : undefined

  return (
    <nav className="nav flex-column px-2 py-2 gap-0 flex-grow-1">
      {loading ? (
        <div className="px-3 py-2 vk-text-muted small">Загрузка…</div>
      ) : user ? (
        <>
          {canAccessLeaderCabinet(user) && (
            <>
              <NavLink to="/leader/participants" className={navLinkClass} onClick={onTap}>
                <span className="vk-nav-icon" aria-hidden>
                  <IconPeople />
                </span>
                Участники
              </NavLink>
              <NavLink to="/leader/applications" className={navLinkClass} onClick={onTap}>
                <span className="vk-nav-icon" aria-hidden>
                  <IconInbox />
                </span>
                Заявки
              </NavLink>
            </>
          )}
          <NavLink to="/profile" className={navLinkClass} onClick={onTap}>
            <span className="vk-nav-icon" aria-hidden>
              <IconProfile />
            </span>
            Мой профиль
          </NavLink>
          {canAccessLeaderCabinet(user) && (
            <>
              <NavLink to="/leader/lots" className={navLinkClass} onClick={onTap}>
                <span className="vk-nav-icon" aria-hidden>
                  <IconShop />
                </span>
                Лоты
              </NavLink>
              {canManageSettings(user) && (
                <NavLink to="/leader/settings" className={navLinkClass} onClick={onTap}>
                  <span className="vk-nav-icon" aria-hidden>
                    <IconSettings />
                  </span>
                  Настройки
                </NavLink>
              )}
            </>
          )}
          {canAccessDjangoAdmin(user) && (
            <a
              className="vk-nav-link d-flex align-items-center gap-3"
              href={`${apiBase}/admin/`}
              onClick={onTap}
            >
              <span className="vk-nav-icon" aria-hidden>
                <IconAdmin />
              </span>
              Админка
            </a>
          )}
          <div className="mt-auto pt-2">
            <div className="vk-nav-separator mb-2" role="presentation" />
            <a className="vk-nav-link d-flex align-items-center gap-3" href={cabinetLogoutUrl()} onClick={onTap}>
              <span className="vk-nav-icon" aria-hidden>
                <IconLogout />
              </span>
              Выйти
            </a>
          </div>
        </>
      ) : (
        <NavLink to="/login" className={navLinkClass} onClick={onTap}>
          <span className="vk-nav-icon" aria-hidden>
            <IconLogin />
          </span>
          Войти
        </NavLink>
      )}
    </nav>
  )
}

function SidebarBrand({ onMobileItemClick }) {
  return (
    <Link
      className="vk-sidebar-brand d-flex align-items-center gap-2 text-decoration-none flex-shrink-0"
      to="/"
      onClick={onMobileItemClick}
    >
      <img src="/logo.png" alt="" width={32} height={32} className="rounded-2" />
      <span className="fw-semibold vk-sidebar-brand__text">OVOSHI</span>
    </Link>
  )
}

export default function Layout() {
  const { user, loading } = useAuth()
  const onMobileNavClick = useCallback(() => {
    closeMobileOffcanvas()
  }, [])

  return (
    <div className="d-flex min-vh-100 vk-shell">
      <aside className="vk-sidebar d-none d-md-flex flex-column flex-shrink-0">
        <div className="px-2 pt-3 pb-2">
          <SidebarBrand />
        </div>
        <SidebarNav user={user} loading={loading} />
      </aside>

      <div className="flex-grow-1 d-flex flex-column min-vh-100 min-w-0 vk-main-column">
        <header className="d-md-none vk-mobile-bar d-flex align-items-center gap-2 px-2 py-2 flex-shrink-0">
          <button
            className="btn btn-link vk-mobile-menu-btn p-2 border-0 shadow-none"
            type="button"
            data-bs-toggle="offcanvas"
            data-bs-target="#ovoshiSidebarOffcanvas"
            aria-controls="ovoshiSidebarOffcanvas"
            aria-label="Открыть меню"
          >
            <span className="vk-toggler-icon d-block" aria-hidden />
          </button>
          <Link className="text-decoration-none d-flex align-items-center gap-2 vk-mobile-bar__title" to="/">
            <img src="/logo.png" alt="" width={28} height={28} className="rounded-2" />
            <span className="fw-semibold">OVOSHI</span>
          </Link>
        </header>

        <div
          className="offcanvas offcanvas-start vk-offcanvas d-md-none"
          tabIndex="-1"
          id="ovoshiSidebarOffcanvas"
          aria-labelledby="ovoshiSidebarOffcanvasLabel"
        >
          <div className="offcanvas-header vk-offcanvas-header border-0 pb-0">
            <h5 className="offcanvas-title vk-offcanvas-title mb-0" id="ovoshiSidebarOffcanvasLabel">
              Меню
            </h5>
            <button
              type="button"
              className="btn-close btn-close-white opacity-75"
              data-bs-dismiss="offcanvas"
              aria-label="Закрыть"
            />
          </div>
          <div className="offcanvas-body p-0 d-flex flex-column flex-grow-1 pt-2">
            <div className="px-2 pb-2">
              <SidebarBrand onMobileItemClick={onMobileNavClick} />
            </div>
            <SidebarNav user={user} loading={loading} onMobileItemClick={onMobileNavClick} />
          </div>
        </div>

        <main className="container py-4 flex-grow-1 vk-main">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
