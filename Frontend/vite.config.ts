import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';
import { createDevApiProxy } from './dev-api-proxy.ts';
import { createRenderStatusPlugin, probeApiHealth } from './dev-api-status.ts';
import { resolveApiConfig } from './dev-api-config.ts';
import { createAdminPlugin } from './dev-admin.ts';
export default defineConfig(({ mode }) => {
  const root = fileURLToPath(new URL('.', import.meta.url));
  const env = loadEnv(mode, root, '');
  const config = resolveApiConfig(env);
  const api = createDevApiProxy(config.proxyTarget);
  return {
    plugins: [
      react(),
      createAdminPlugin({ ...process.env, ...env }),
      api.plugin,
      createRenderStatusPlugin(() => probeApiHealth(config.renderOrigin)),
    ],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    build: {
      rolldownOptions: {
        input: {
          main: fileURLToPath(new URL('./index.html', import.meta.url)),
          'admin-prisma': fileURLToPath(
            new URL('./admin-prisma.html', import.meta.url),
          ),
        },
      },
    },
    server: {
      host: '127.0.0.1',
      port: 5173,
      strictPort: true,
      proxy: { '/api': api.proxy },
    },
    preview: { host: '127.0.0.1', proxy: { '/api': api.proxy } },
  };
});
