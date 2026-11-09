import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createPostgresAdapter } from '@prisma/studio-core/data/postgres-core';
import { executeReadOnly, ReadOnlyError } from '../lib/database';
import type { Query } from '@prisma/studio-core/data';

// Use exclusivamente o banco descartável preparado por scripts/test-database.mjs.
if (!process.env.ADMIN_TEST_DATABASE_URL || !process.env.ADMIN_TEST_WRITER_URL) {
  throw new Error('Execute npm run test:database:docker para preparar o PostgreSQL descartável.');
}
process.env.STUDIO_DATABASE_URL = process.env.ADMIN_TEST_DATABASE_URL;

test('consulta parametrizada e transformações JSON funcionam com a role de leitura', async () => {
  assert.deepEqual(await executeReadOnly({
    sql: 'SELECT id, name, metadata::text AS metadata FROM public.admin_test WHERE id = $1',
    parameters: [1], transformations: { metadata: 'json-parse' },
  }), [{ id: 1, name: 'Laranja de teste', metadata: { sample: true } }]);
});

test('introspecção real do Studio reconhece as tabelas', async () => {
  const adapter = createPostgresAdapter({ executor: {
    async execute<T>(query: Query<T>) {
      try { return [null, await executeReadOnly(query) as T[]] as [null, T[]]; }
      catch (error) { return [error as Error]; }
    },
  } });
  const [error, result] = await adapter.introspect({});
  assert.equal(error, null);
  assert.ok(result?.schemas.public.tables.admin_test);
});

test('bloqueia escrita direta, CTE de escrita e múltiplos statements', async () => {
  for (const sql of [
    "UPDATE public.admin_test SET name='modificado'",
    "WITH deleted AS (DELETE FROM public.admin_test RETURNING *) SELECT * FROM deleted",
    "SELECT 1; COMMIT; DELETE FROM public.admin_test",
    "SELECT set_config('transaction_read_only', 'off', true)",
    'SELECT nextval(\'public.admin_test_id_seq\')',
  ]) {
    await assert.rejects(executeReadOnly({ sql, parameters: [] }));
  }
  assert.equal((await executeReadOnly({ sql: 'SELECT count(*)::int AS count FROM public.admin_test', parameters: [] }))[0].count, 1);
});

test('recusa uma credencial de escrita mesmo quando a consulta seria SELECT', async () => {
  const reader = process.env.STUDIO_DATABASE_URL;
  try {
    process.env.STUDIO_DATABASE_URL = process.env.ADMIN_TEST_WRITER_URL;
    await assert.rejects(executeReadOnly({ sql: 'SELECT 1', parameters: [] }), ReadOnlyError);
  } finally { process.env.STUDIO_DATABASE_URL = reader; }
});

test('estado de sessão não persiste entre consultas', async () => {
  await executeReadOnly({ sql: "SELECT set_config('application_name', 'alterado', false)", parameters: [] });
  const rows = await executeReadOnly({ sql: "SELECT current_setting('application_name') AS name", parameters: [] });
  assert.equal(rows[0].name, 'orangevision-admin-reader');
});
