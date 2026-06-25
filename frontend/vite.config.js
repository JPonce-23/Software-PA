import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Important for Docker
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://host.docker.internal:8000', // Points to FastAPI running on Host machine
        changeOrigin: true,
        secure: false,
      }
    }
  }
})
