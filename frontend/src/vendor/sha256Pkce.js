/**
 * PKCE S256 без crypto.subtle (HTTP в Safari и т.п.).
 * Вендор: js-sha256 0.11.1 (MIT) — js-sha256.min.js, лицензия: js-sha256-LICENSE.txt
 */
import './js-sha256.min.js'

function sha256Api() {
  const api = globalThis.sha256
  if (!api || typeof api.arrayBuffer !== 'function') {
    throw new Error('Встроенный SHA-256 не загрузился')
  }
  return api
}

/** @param {string} message UTF-8 строка (для PKCE verifier — ASCII) */
export function sha256ArrayBufferUtf8(message) {
  return sha256Api().arrayBuffer(message)
}
