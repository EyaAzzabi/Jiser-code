import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The FastAPI backend runs on :8000; /api is proxied so the app has a single origin.
// JISER_BASE: sub-path of the published site ("/Jiser/" on GitHub Pages, "/" otherwise).
export default defineConfig({
  base: process.env.JISER_BASE ?? '/',
  plugins: [react(), tailwindcss()],
  server: {
    proxy: { '/api': { target: process.env.JISER_API ?? 'http://127.0.0.1:8000', ws: true } },
  },
})
