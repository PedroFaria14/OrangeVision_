import { serializeError } from '@prisma/studio-core/data/bff';
import type { Query } from '@prisma/studio-core/data';
import {
  authSettings,
  ConfigurationError,
  type AdminEnvironment,
} from './settings.js';
import { executeReadOnly, ReadOnlyError } from './database.js';
import { isAdmin } from './auth.js';
import { limitedBody, privateHeaders } from './http.js';

function reply(data: unknown, status = 200) {
  return Response.json(data, { status, headers: privateHeaders });
}

function failure(message: string, status: number) {
  return reply([serializeError(new Error(message))], status);
}

function isQuery(value: unknown): value is Query<unknown> {
  if (!value || typeof value !== 'object') return false;
  const q = value as Record<string, unknown>;
  if (
    typeof q.sql !== 'string' ||
    !q.sql.trim() ||
    q.sql.length > 60000 ||
    !Array.isArray(q.parameters) ||
    q.parameters.length > 1000
  )
    return false;
  if (q.transformations !== undefined) {
    if (
      !q.transformations ||
      typeof q.transformations !== 'object' ||
      Array.isArray(q.transformations)
    )
      return false;
    if (!Object.values(q.transformations).every((v) => v === 'json-parse'))
      return false;
  }
  return true;
}

export async function handleAdminStudio(
  request: Request,
  env: AdminEnvironment = process.env,
) {
  try {
    if (request.method !== 'POST') return failure('Use POST.', 405);
    if (!(await isAdmin(request, env)))
      return failure('Faça login com a conta administrativa.', 401);
    if (request.headers.get('origin') !== authSettings(env).origin)
      return failure('Origem não permitida.', 403);
    if (
      !request.headers
        .get('content-type')
        ?.toLowerCase()
        .startsWith('application/json')
    ) {
      return failure('Envie application/json.', 415);
    }
    const text = await limitedBody(request);
    if (text === null)
      return failure('Consulta acima do limite de 64 KiB.', 413);
    let body: Record<string, unknown>;
    try {
      const value: unknown = JSON.parse(text);
      if (!value || typeof value !== 'object' || Array.isArray(value))
        throw new Error();
      body = value as Record<string, unknown>;
    } catch {
      return failure('Corpo da consulta inválido.', 400);
    }
    if (body.procedure !== 'query' || !isQuery(body.query))
      return failure('Consulta não suportada.', 400);
    const result = [null, await executeReadOnly(body.query, env)];
    if (Buffer.byteLength(JSON.stringify(result)) > 4_000_000) {
      return failure(
        'Resultado muito grande. Reduza as linhas ou aplique filtros.',
        413,
      );
    }
    return reply(result);
  } catch (error) {
    if (error instanceof ConfigurationError) return failure(error.message, 503);
    if (error instanceof ReadOnlyError) return failure(error.message, 403);
    return failure(
      'Consulta indisponível ou não permitida. Revise a conexão de leitura e os filtros.',
      422,
    );
  }
}
