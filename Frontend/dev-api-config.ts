import { loadEnv } from 'vite';
import { fileURLToPath } from 'node:url';

export function resolveApiConfig(values: Record<string, string | undefined>) {
  const remote =
    values.RENDER_API_ORIGIN?.trim() || values.API_PROXY_TARGET?.trim();
  if (!remote) {
    throw new Error(
      'Configure RENDER_API_ORIGIN ou API_PROXY_TARGET no .env do frontend.',
    );
  }
  const url = new URL(remote);
  if (
    url.protocol !== 'https:' ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== '/'
  ) {
    throw new Error(
      'RENDER_API_ORIGIN deve ser uma origem HTTPS sem caminho ou credenciais. Configure-a separadamente ao usar uma API local.',
    );
  }
  return {
    renderOrigin: url.origin,
    proxyTarget: values.API_PROXY_TARGET?.trim() || url.origin,
  };
}

export function loadFrontendApiConfig(mode = 'development') {
  const root = fileURLToPath(new URL('.', import.meta.url));
  // O Vite aplica .env, variantes do modo e, por último, variáveis do processo.
  // .env.example não participa desse carregamento.
  return resolveApiConfig(loadEnv(mode, root, ''));
}
