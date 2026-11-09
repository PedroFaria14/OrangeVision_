import { Readable } from 'node:stream';
import type { Plugin, ViteDevServer } from 'vite';
import { handleAdminAuth, ADMIN_AUTH_PATH } from './server/admin/auth.ts';
import { handleAdminStudio } from './server/admin/studio.ts';
import type { AdminEnvironment } from './server/admin/settings.ts';

export function createAdminPlugin(env: AdminEnvironment): Plugin {
  const configure = (server: Pick<ViteDevServer, 'middlewares'>) => {
    server.middlewares.use((req, res, next) => {
      const path = req.url?.split('?')[0] ?? '';
      if (!/^\/api\/admin(?:\/|$)/.test(path)) return next();
      // Intercepta antes do proxy público: cookies e OAuth nunca são enviados ao Render.
      void (async () => {
        const headers = new Headers();
        for (const [key, value] of Object.entries(req.headers)) {
          if (value !== undefined)
            headers.set(key, Array.isArray(value) ? value.join(', ') : value);
        }
        const request = new Request(
          new URL(req.url ?? '/', `http://${req.headers.host}`),
          {
            method: req.method,
            headers,
            ...(!['GET', 'HEAD'].includes(req.method ?? 'GET')
              ? {
                  body: Readable.toWeb(req) as ReadableStream<Uint8Array>,
                  duplex: 'half',
                }
              : {}),
          },
        );
        const response =
          path.startsWith(`${ADMIN_AUTH_PATH}/`) || path === ADMIN_AUTH_PATH
            ? await handleAdminAuth(request, env)
            : path === '/api/admin/studio'
              ? await handleAdminStudio(request, env)
              : Response.json(
                  { detail: 'Rota administrativa inexistente.' },
                  { status: 404 },
                );
        res.statusCode = response.status;
        for (const [key, value] of response.headers) {
          if (key !== 'set-cookie') res.setHeader(key, value);
        }
        const cookies = response.headers.getSetCookie();
        if (cookies.length) res.setHeader('Set-Cookie', cookies);
        res.end(await response.text());
      })().catch(() => {
        if (!res.headersSent)
          res.writeHead(503, {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-store',
          });
        res.end(
          JSON.stringify({ detail: 'Painel administrativo indisponível.' }),
        );
      });
    });
  };
  return {
    name: 'orangevision-admin',
    configureServer: configure,
    configurePreviewServer: configure,
  };
}
