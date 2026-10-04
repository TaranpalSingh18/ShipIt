import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
const proxyTarget = globalThis.process?.env?.VITE_PROXY_TARGET || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: proxyTarget, changeOrigin: true, timeout: 600_000, proxyTimeout: 600_000 },
    },
  },
})
