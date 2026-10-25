import type { IncomingMessage, ServerResponse } from 'node:http';
import type { Plugin, ProxyOptions } from 'vite';

export const DEFAULT_API_TARGET = 'https://orangevision.onrender.com';
const loopback = /^(localhost|127\.0\.0\.1|\[::1\])(?::\d{1,5})?$/i;

function localRequest(
  req: IncomingMessage,
  res: ServerResponse,
  next: () => void,
) {
  if (!req.url?.match(/^\/api(?:\/|\?|$)/)) return next();
  const host = req.headers.host || '';
  const origin = req.headers.origin;
  const mutating = !['GET', 'HEAD', 'OPTIONS'].includes(req.method || '');
  const protocol = (req.socket as { encrypted?: boolean }).encrypted
    ? 'https'
    : 'http';
  let expected = '';
  try {
    expected = new URL(`${protocol}://${host}`).origin;
  } catch {
    /* Rejeita host inválido. */
  }
  if (
    !loopback.test(host) ||
    !expected ||
    (origin !== undefined && origin !== expected) ||
    (mutating && !origin) ||
    req.headers['sec-fetch-site'] === 'cross-site'
  ) {
    res.statusCode = 403;
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.setHeader('Cache-Control', 'no-store');
    res.end(
      JSON.stringify({
        detail:
          'O proxy de desenvolvimento aceita somente a própria origem local.',
      }),
    );
    return;
  }
  next();
}

export function createDevApiProxy(value = DEFAULT_API_TARGET): {
  plugin: Plugin;
  proxy: ProxyOptions;
} {
  const target = new URL(value);
  if (
    target.username ||
    target.password ||
    target.search ||
    target.hash ||
    target.pathname !== '/'
  )
    throw new Error(
      'API_PROXY_TARGET deve conter somente a origem da API, sem credenciais/caminho.',
    );
  if (
    target.protocol !== 'https:' &&
    !(
      target.protocol === 'http:' &&
      ['localhost', '127.0.0.1', '[::1]'].includes(target.hostname)
    )
  )
    throw new Error(
      'A API remota exige HTTPS. HTTP é permitido somente em loopback.',
    );
  return {
    plugin: {
      name: 'orangevision-local-api-origin',
      configureServer(server) {
        server.middlewares.use(localRequest);
      },
      configurePreviewServer(server) {
        server.middlewares.use(localRequest);
      },
    },
    proxy: {
      target: target.origin,
      changeOrigin: true,
      secure: true,
      cookieDomainRewrite: '',
      proxyTimeout: 60000,
      configure(proxy) {
        proxy.on('proxyReq', (outgoing, incoming) => {
          // O guard acima valida a origem local antes de representar este gateway na API.
          outgoing.setHeader('Origin', target.origin);
          const cookies = (incoming.headers.cookie || '')
            .split(';')
            .map((cookie) => cookie.trim())
            .filter((cookie) => cookie.startsWith('orangevision_session='));
          if (cookies.length) outgoing.setHeader('Cookie', cookies.join('; '));
          else outgoing.removeHeader('Cookie');
        });
        proxy.on('proxyRes', (response) => {
          // Adaptação apenas do gateway HTTP de loopback. A API remota mantém Secure/HTTPS.
          const cookies = response.headers['set-cookie'];
          if (cookies)
            response.headers['set-cookie'] = cookies
              .filter((cookie) => cookie.startsWith('orangevision_session='))
              .map((cookie) => cookie.replace(/;\s*Secure(?=;|$)/gi, ''));
          delete response.headers['access-control-allow-origin'];
          delete response.headers['access-control-allow-credentials'];
        });
      },
    },
  };
}
