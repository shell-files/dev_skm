import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: "/",
  server: {
    host: '0.0.0.0',
    port: 80,
    allowedHosts: ['localhost','skm.weareithero.cloud','skm.myapp.com'],
    proxy: {
        '/api': {
          target: 'http://skm.weareithero.cloud', // 원래 찌르려던 백엔드 주소
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''), 
        }
      }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@stores': fileURLToPath(new URL('./src/stores', import.meta.url)),
      '@components': fileURLToPath(new URL('./src/components', import.meta.url)),
      '@styles': fileURLToPath(new URL('./src/styles', import.meta.url)),
      '@errors': fileURLToPath(new URL('./src/homes/errors', import.meta.url)),
      '@onboards': fileURLToPath(new URL('./src/homes/onboards', import.meta.url)),
      '@reports': fileURLToPath(new URL('./src/homes/reports', import.meta.url)),
      '@gates': fileURLToPath(new URL('./src/homes/gates', import.meta.url)),
      '@logins': fileURLToPath(new URL('./src/homes/logins', import.meta.url)),
      '@mains': fileURLToPath(new URL('./src/homes/mains', import.meta.url)),
      '@assets': fileURLToPath(new URL('./src/assets', import.meta.url)),
      '@hooks': fileURLToPath(new URL('./src/hooks', import.meta.url)),
      '@utils': fileURLToPath(new URL('./src/utils', import.meta.url)),
    }
  },
})
