import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = env.VITE_API_BASE_URL || 'http://localhost:18080';
  const wsTarget = env.VITE_WS_BASE_URL || 'ws://localhost:18080';
  const devPort = Number(env.WEB_DEV_PORT || 15173);

  return {
    plugins: [react()],
    base: '/ui/',
    build: {
      outDir: '../api/webui',
      emptyOutDir: true,
    },
    server: {
      port: devPort,
      proxy: {
        '/scrape': apiTarget,
        '/health': apiTarget,
        '/ws': { target: wsTarget, ws: true },
      },
    },
  };
});
