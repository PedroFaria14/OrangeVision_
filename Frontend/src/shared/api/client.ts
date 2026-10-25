export class ApiError extends Error {
  constructor(public readonly status: number) {
    super(
      status === 403
        ? 'Acesso não autorizado.'
        : status === 429
          ? 'Muitas tentativas. Aguarde 15 minutos.'
          : 'Não foi possível concluir a solicitação.',
    );
  }
}

// O cliente de transporte não depende de app/features.
const base = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
if (!base.startsWith('/') || base.startsWith('//'))
  throw new Error('VITE_API_BASE_URL deve usar a mesma origem.');

export async function requestJson(
  path: string,
  options: RequestInit = {},
): Promise<unknown> {
  const timeout = AbortSignal.timeout(15_000);
  const signal = options.signal
    ? AbortSignal.any([options.signal, timeout])
    : timeout;
  const response = await fetch(`${base}${path}`, {
    ...options,
    signal,
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/auth/'))
      window.dispatchEvent(new Event('orangevision:session-expired'));
    throw new ApiError(response.status);
  }
  if (response.status === 204) return null;
  return response.json();
}

export function getJson(path: string, signal?: AbortSignal) {
  return requestJson(path, { signal });
}
