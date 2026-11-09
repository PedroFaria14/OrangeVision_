export type ApiHealth = {
  state: 'available' | 'unavailable' | 'unreachable' | 'unexpected';
  checkedAt: string;
  durationMs: number;
  httpStatus: number | null;
};

async function healthBody(response: Response): Promise<unknown> {
  const reader = response.body?.getReader();
  if (!reader) throw new Error('Empty health response');
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 8192) {
        await reader.cancel();
        throw new Error('Health response too large');
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const body = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    body.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return JSON.parse(new TextDecoder().decode(body));
}

export async function probeApiHealth(
  origin: string,
  timeoutMs = 10000,
): Promise<ApiHealth> {
  const target = new URL(origin);
  if (
    target.username ||
    target.password ||
    target.search ||
    target.hash ||
    target.pathname !== '/' ||
    (target.protocol !== 'https:' &&
      !(
        target.protocol === 'http:' &&
        ['127.0.0.1', 'localhost', '[::1]'].includes(target.hostname)
      ))
  )
    throw new Error(
      'Use uma origem HTTPS ou HTTP de loopback, sem caminho/credenciais.',
    );

  const start = performance.now();
  let httpStatus: number | null = null;
  let state: ApiHealth['state'] = 'unreachable';
  try {
    const response = await fetch(new URL('/health', target), {
      signal: AbortSignal.timeout(timeoutMs),
      redirect: 'manual',
      credentials: 'omit',
      headers: { Accept: 'application/json' },
    });
    httpStatus = response.status;
    if (!response.ok) {
      state = 'unavailable';
      await response.body?.cancel();
    } else {
      state = 'unexpected';
      const body = await healthBody(response);
      if (
        body &&
        typeof body === 'object' &&
        'status' in body &&
        body.status === 'ok' &&
        'service' in body &&
        body.service === 'orangevision-web'
      )
        state = 'available';
    }
  } catch {
    // Não expor corpo remoto, detalhes de rede ou configuração privada.
    state = httpStatus === null ? 'unreachable' : 'unexpected';
  }
  return {
    state,
    checkedAt: new Date().toISOString(),
    durationMs: Math.round(performance.now() - start),
    httpStatus,
  };
}

export function createCachedHealthProbe(
  probe: () => Promise<ApiHealth>,
): () => Promise<ApiHealth> {
  let cached: ApiHealth | undefined;
  let pending: Promise<ApiHealth> | undefined;
  return () => {
    if (cached && Date.now() - Date.parse(cached.checkedAt) < 15000)
      return Promise.resolve(cached);
    pending ??= probe()
      .then((value) => {
        cached = value;
        return value;
      })
      .finally(() => {
        pending = undefined;
      });
    return pending;
  };
}
