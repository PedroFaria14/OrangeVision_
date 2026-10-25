import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';
import { createDevApiProxy } from './dev-api-proxy.ts';
export default defineConfig(({ mode }) => {
  const root = fileURLToPath(new URL('.', import.meta.url));
  const env = loadEnv(mode, root, '');
  const api = createDevApiProxy(env.API_PROXY_TARGET);
  return {
    plugins: [react(), api.plugin],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: {
      host: '127.0.0.1',
      port: 5174,
      strictPort: true,
      proxy: { '/api': api.proxy },
    },
    preview: { host: '127.0.0.1', proxy: { '/api': api.proxy } },
  };
});
