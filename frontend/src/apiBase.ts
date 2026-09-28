// Where the API lives. Empty = same origin (local development, or one service serving both).
// On GitHub Pages the interface is static and the API runs elsewhere (Render): VITE_API_URL points to it.
export const API_BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

// Every call in the app uses relative "/api/..." paths: prefix them once, here, when the API is remote.
if (API_BASE) {
  const nativeFetch = window.fetch.bind(window)
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) =>
    nativeFetch(typeof input === 'string' && input.startsWith('/api') ? API_BASE + input : input, init)
}

/** WebSocket address of an API path (wss:// when the API is served over HTTPS). */
export const wsUrl = (path: string) => (API_BASE || `${location.protocol}//${location.host}`).replace(/^http/, 'ws') + path

/** Public file (logo…) under the site's base path ("/" locally, "/Jiser/" on GitHub Pages). */
export const asset = (name: string) => `${import.meta.env.BASE_URL}${name}`
