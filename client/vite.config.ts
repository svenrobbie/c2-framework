import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    build: {
      outDir: '../server/static',
      emptyOutDir: true,
    },
    server: {
      port: 3000,
      proxy: {
        '/socket.io': {
          target: 'http://localhost:4444',
          ws: true,
        },
        '/api': {
          target: 'http://localhost:4444',
        },
      },
      hmr: process.env.DISABLE_HMR !== 'true',
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
    },
  };
});
