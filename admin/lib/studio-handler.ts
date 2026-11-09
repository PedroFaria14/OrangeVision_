import { serializeError } from '@prisma/studio-core/data/bff';
import type { Query } from '@prisma/studio-core/data';
import { ConfigurationError } from './settings';
import { ReadOnlyError } from './database';

interface Dependencies {
  authorize(): Promise<boolean>;
  origin(): string;
  execute(query: Query<unknown>): Promise<Record<string, unknown>[]>;
}

function reply(data: unknown, status = 200) {
  return Response.json(data, { status, headers: {
    'Cache-Control': 'no-store, private',
    'X-Content-Type-Options': 'nosniff',
    Vary: 'Cookie, Origin',
  } });
}

function failure(message: string, status: number) {
  return reply([serializeError(new Error(message))], status);
}

function isQuery(value: unknown): value is Query<unknown> {
  if (!value || typeof value !== 'object') return false;
  const q = value as Record<string, unknown>;
  if (typeof q.sql !== 'string' || !q.sql.trim() || q.sql.length > 60000 ||
      !Array.isArray(q.parameters) || q.parameters.length > 1000) return false;
  if (q.transformations !== undefined) {
    if (!q.transformations || typeof q.transformations !== 'object' || Array.isArray(q.transformations)) return false;
    if (!Object.values(q.transformations).every(v => v === 'json-parse')) return false;
  }
  return true;
}

async function readBody(request: Request) {
  const reader = request.body?.getReader();
  if (!reader) return '';
  const chunks: Uint8Array[] = [];
  let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > 65536) {
        await reader.cancel();
        return null;
      }
      chunks.push(value);
    }
    return Buffer.concat(chunks).toString('utf8');
  } finally { reader.releaseLock(); }
}

export async function handleStudio(request: Request, dependencies: Dependencies) {
  try {
    if (!await dependencies.authorize()) return failure('Faça login com a conta administrativa.', 401);
    if (request.headers.get('origin') !== dependencies.origin()) return failure('Origem não permitida.', 403);
    if (!request.headers.get('content-type')?.toLowerCase().startsWith('application/json')) {
      return failure('Envie application/json.', 415);
    }
    const text = await readBody(request);
    if (text === null) return failure('Consulta acima do limite de 64 KiB.', 413);
    let body: Record<string, unknown>;
    try {
      const value: unknown = JSON.parse(text);
      if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error();
      body = value as Record<string, unknown>;
    } catch { return failure('Corpo da consulta inválido.', 400); }

    // A visualização é de leitura. Não são expostos batches, transações, LLM ou migrations.
    if (body.procedure !== 'query' || !isQuery(body.query)) return failure('Consulta não suportada.', 400);
    const rows = await dependencies.execute(body.query);
    // A Vercel limita o payload a 4.5 MB. Não exponha uma resposta parcial como se fosse completa.
    const result = [null, rows];
    if (Buffer.byteLength(JSON.stringify(result)) > 4_000_000) {
      return failure('Resultado muito grande. Reduza as linhas ou aplique filtros.', 413);
    }
    return reply(result);
  } catch (error) {
    if (error instanceof ConfigurationError) return failure(error.message, 503);
    if (error instanceof ReadOnlyError) return failure(error.message, 403);
    // Não devolve SQL, parâmetros, nomes internos, credenciais nem erros brutos do driver.
    return failure('Consulta indisponível ou não permitida. Revise a conexão de leitura e os filtros.', 422);
  }
}
