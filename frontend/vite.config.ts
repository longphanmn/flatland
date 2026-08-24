import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // production is reached via http://world.minhnhan.in → :5173
    allowedHosts: ['world.minhnhan.in'],
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        timeout: 5000,
        // Suppress ECONNREFUSED spam when backend is reloading; retry once
        configure: (proxy) => {
          let lastLog = 0
          proxy.on('error', (_err, _req, _res) => {
            const now = Date.now()
            if (now - lastLog > 5000) {
              lastLog = now
              console.log('[proxy] backend unreachable (retrying)…')
            }
          })
        },
      },
      '/ws': { target: 'ws://localhost:8000', ws: true, timeout: 5000 },
      '/wiki': { target: 'http://localhost:8000', changeOrigin: true, timeout: 5000 },
      '/guide': { target: 'http://localhost:8000', changeOrigin: true, timeout: 5000 },
      '/docs': { target: 'http://localhost:8000', changeOrigin: true, timeout: 5000 },
      '/openapi.json': { target: 'http://localhost:8000', changeOrigin: true, timeout: 5000 },
      '/redoc': { target: 'http://localhost:8000', changeOrigin: true, timeout: 5000 },
    },
  },
})
