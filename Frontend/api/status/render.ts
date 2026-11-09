import {
  createCachedHealthProbe,
  probeApiHealth,
} from '../../server/api-health.js';

const headers = {
  'Cache-Control': 'no-store',
  'CDN-Cache-Control': 'no-store',
  'Vercel-CDN-Cache-Control': 'no-store',
  'X-Content-Type-Options': 'nosniff',
};

const status = createCachedHealthProbe(() => {
  // No Vercel, usar as variáveis do deployment, sem carregar .env ou Vite.
  const origin =
    process.env.RENDER_API_ORIGIN?.trim() ||
    process.env.API_PROXY_TARGET?.trim();
  if (!origin || new URL(origin).protocol !== 'https:') {
    throw new Error('Configure uma origem HTTPS para a API remota.');
  }
  // A validação restante rejeita credenciais, caminhos e parâmetros na origem.
  return probeApiHealth(origin);
});

export default {
  async fetch(request: Request): Promise<Response> {
    if (request.method !== 'GET') {
      return Response.json(
        { detail: 'Use GET.' },
        { status: 405, headers: { ...headers, Allow: 'GET' } },
      );
    }
    try {
      return Response.json(await status(), { headers });
    } catch {
      return Response.json(
        { detail: 'Status não configurado. Confira RENDER_API_ORIGIN no Vercel.' },
        { status: 503, headers },
      );
    }
  },
};
