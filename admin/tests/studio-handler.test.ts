import assert from 'node:assert/strict';
import { test } from 'node:test';
import { handleStudio } from '../lib/studio-handler';
import { ConfigurationError } from '../lib/settings';
import { ReadOnlyError } from '../lib/database';

const origin = 'https://admin.example.test';
const valid = { procedure: 'query', query: { sql: 'SELECT $1 AS value', parameters: ['value'] } };
function request(body: unknown = valid, requestOrigin: string | null = origin) {
  return new Request(`${origin}/api/studio`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(requestOrigin ? { Origin: requestOrigin } : {}) },
    body: JSON.stringify(body),
  });
}
const dependencies = {
  authorize: async () => true,
  origin: () => origin,
  execute: async () => [{ value: 'value' }],
};

test('nega acesso anônimo antes de consultar ou validar o corpo', async () => {
  let calls = 0;
  const response = await handleStudio(request(), {
    ...dependencies, authorize: async () => false,
    execute: async () => { calls++; return []; },
  });
  assert.equal(response.status, 401);
  assert.equal(calls, 0);
  assert.match(response.headers.get('cache-control')!, /no-store/);
});

test('nega CSRF com origem externa ou ausente, mesmo autenticado', async () => {
  for (const badOrigin of ['https://evil.example', null]) {
    const response = await handleStudio(request(valid, badOrigin), dependencies);
    assert.equal(response.status, 403);
  }
});

test('respeita o envelope BFF e não armazena dados privados em cache', async () => {
  const response = await handleStudio(request(), dependencies);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), [null, [{ value: 'value' }]]);
  assert.match(response.headers.get('cache-control')!, /no-store/);
});

test('rejeita formato inválido, operações de batch e SQL acima do limite', async () => {
  for (const body of [null, [], {}, { procedure: 'transaction', queries: [valid.query] },
    { procedure: 'sequence', sequence: [valid.query, valid.query] },
    { ...valid, query: { sql: 'SELECT 1', parameters: {} } },
    { ...valid, query: { ...valid.query, transformations: { field: 'execute' } } }]) {
    assert.equal((await handleStudio(request(body), dependencies)).status, 400);
  }
  assert.equal((await handleStudio(request({ data: 'x'.repeat(66000) }), dependencies)).status, 413);
});

test('rejeita JSON malformado e content-type incompatível', async () => {
  const headers = { Origin: origin, 'Content-Type': 'application/json' };
  const malformed = new Request(`${origin}/api/studio`, { method: 'POST', headers, body: '{bad' });
  assert.equal((await handleStudio(malformed, dependencies)).status, 400);
  const form = new Request(`${origin}/api/studio`, { method: 'POST', headers: { Origin: origin }, body: 'sql=SELECT+1' });
  assert.equal((await handleStudio(form, dependencies)).status, 415);
});

test('não vaza URL de banco, SQL ou stack de erros do driver', async () => {
  const response = await handleStudio(request(), {
    ...dependencies, execute: async () => { throw new Error('postgresql://owner:PRIVATE@host/db SELECT private'); },
  });
  assert.equal(response.status, 422);
  assert.doesNotMatch(await response.text(), /PRIVATE|postgresql|SELECT private|stack/);
});

test('falha fechada quando falta configuração ou a role tem privilégios', async () => {
  const missing = await handleStudio(request(), { ...dependencies, authorize: async () => { throw new ConfigurationError(); } });
  assert.equal(missing.status, 503);
  const unsafe = await handleStudio(request(), { ...dependencies, execute: async () => { throw new ReadOnlyError(); } });
  assert.equal(unsafe.status, 403);
});

test('não envia resultados acima do limite da Vercel nem trunca silenciosamente', async () => {
  const response = await handleStudio(request(), {
    ...dependencies, execute: async () => [{ value: 'x'.repeat(4_000_001) }],
  });
  assert.equal(response.status, 413);
});
