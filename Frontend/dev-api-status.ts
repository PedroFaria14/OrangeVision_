import type { Plugin, ViteDevServer } from 'vite';
import { createCachedHealthProbe, type ApiHealth } from './server/api-health.ts';

export { probeApiHealth } from './server/api-health.ts';
export type { ApiHealth } from './server/api-health.ts';
export const RENDER_STATUS_PATH = '/api/status/render';

export function createRenderStatusPlugin(
  probe: () => Promise<ApiHealth>,
): Plugin {
  const status = createCachedHealthProbe(probe);
  const configure = (server: Pick<ViteDevServer, 'middlewares'>) => {
    server.middlewares.use((req, res, next) => {
      if (req.url?.split('?')[0] !== RENDER_STATUS_PATH) return next();
      res.setHeader('Cache-Control', 'no-store');
      res.setHeader('X-Content-Type-Options', 'nosniff');
      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      if (req.method !== 'GET') {
        res.setHeader('Allow', 'GET');
        res.writeHead(405);
        res.end(JSON.stringify({ detail: 'Use GET.' }));
        return;
      }
      // O destino vem da configuração do servidor, nunca da query string.
      void status()
        .then((value) => {
          res.end(JSON.stringify(value));
        })
        .catch(() => {
          res.writeHead(502);
          res.end(
            JSON.stringify({ detail: 'Não foi possível consultar o status.' }),
          );
        });
    });
  };
  return {
    name: 'orangevision-render-status',
    configureServer: configure,
    configurePreviewServer: configure,
  };
}
