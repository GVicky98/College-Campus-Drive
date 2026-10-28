import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [vue(), tailwindcss()],
    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
    server: {
      port: 5173,
      // The browser talks to the Vite server only; /api is forwarded to FastAPI (same origin, so cookies work).
      proxy: { '/api': { target: env.VITE_DEV_PROXY_TARGET || 'http://127.0.0.1:8000', changeOrigin: false } },
    },
  }
})
