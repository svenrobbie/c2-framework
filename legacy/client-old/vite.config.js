import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/',
  build: {
    outDir: '../server/static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/socket.io': 'http://localhost:4444',
      '/api': 'http://localhost:4444',
      '/send_command': 'http://localhost:4444',
    }
  }
})
