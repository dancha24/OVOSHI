import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/** За NPM с TLS: страница с https://домен, а Vite внутри :3000 — без этого HMR лезет на неправильный порт. */
function hmrOverHttpsProxy() {
  const host = (process.env.VITE_HMR_HOST || '').trim()
  const protocol = (process.env.VITE_HMR_PROTOCOL || '').trim().toLowerCase()
  const portRaw = (process.env.VITE_HMR_CLIENT_PORT || '').trim()
  if (!host || !protocol || !portRaw) return undefined
  const clientPort = Number(portRaw)
  if (!Number.isFinite(clientPort)) return undefined
  return { host, protocol, clientPort }
}

const devHmr = hmrOverHttpsProxy()

/** Windows + Docker bind mount: native fs events часто не доходят до контейнера — без polling Vite не пересобирает. */
const usePoll =
  process.env.CHOKIDAR_USEPOLLING === '1' || process.env.VITE_USE_POLLING === '1'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    strictPort: true,
    ...(usePoll ? { watch: { usePolling: true, interval: 1000 } } : {}),
    // Dev за NPM/tunnel: любой Host (иначе после смены домена снова править список и перезапускать Vite).
    // Прод: `npm run build` — статика через nginx, этот dev-server не используется.
    allowedHosts: true,
    ...(devHmr ? { hmr: devHmr } : {}),
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/accounts': { target: 'http://localhost:8000', changeOrigin: true },
      // Не проксируем /admin — только Django. Кабинет лидера: /leader/*
      // Django admin в dev: http://localhost:59722/admin/ (порт backend из compose).
      '/media': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
