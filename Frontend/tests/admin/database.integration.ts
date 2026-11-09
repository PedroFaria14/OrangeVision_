import assert from 'node:assert/strict';
import { test } from 'node:test';
import { executeReadOnly, ReadOnlyError } from '../../server/admin/database.ts';

if (
  !process.env.ADMIN_TEST_DATABASE_URL ||
  !process.env.ADMIN_TEST_WRITER_URL
) {
  throw new Error(
    'Use yarn test:admin:database para preparar o banco descartável.',
  );
}
const env = { STUDIO_DATABASE_URL: process.env.ADMIN_TEST_DATABASE_URL };

test('consulta parametrizada e JSON preservam dados e tipos', async () => {
  assert.deepEqual(
    await executeReadOnly(
      {
        sql: 'SELECT id, name, metadata::text AS metadata FROM public.admin_test WHERE id = $1',
        parameters: [1],
        transformations: { metadata: 'json-parse' },
      },
      env,
    ),
    [{ id: 1, name: 'Laranja de teste', metadata: { sample: true } }],
  );
});

test('PostgreSQL bloqueia CTE de escrita, sequência, múltiplos statements e tentativa de read-write', async () => {
  for (const sql of [
    'DELETE FROM public.admin_test',
    'WITH removed AS (DELETE FROM public.admin_test RETURNING *) SELECT * FROM removed',
    'SELECT 1; COMMIT; DELETE FROM public.admin_test',
    "SELECT set_config('transaction_read_only', 'off', true)",
    "SELECT nextval('public.admin_test_id_seq')",
  ])
    await assert.rejects(executeReadOnly({ sql, parameters: [] }, env));
  assert.equal(
    (
      await executeReadOnly(
        {
          sql: 'SELECT count(*)::int AS count FROM public.admin_test',
          parameters: [],
        },
        env,
      )
    )[0].count,
    1,
  );
});

test('owner, escrita em uma coluna e propriedade de schema de usuário são recusados até para SELECT', async () => {
  for (const value of [
    process.env.ADMIN_TEST_WRITER_URL,
    process.env.ADMIN_TEST_COLUMN_WRITER_URL,
    process.env.ADMIN_TEST_SCHEMA_OWNER_URL,
  ]) {
    await assert.rejects(
      executeReadOnly(
        { sql: 'SELECT 1', parameters: [] },
        { STUDIO_DATABASE_URL: value },
      ),
      ReadOnlyError,
    );
  }
});

test('SET da sessão não persiste na próxima consulta', async () => {
  await executeReadOnly(
    {
      sql: "SELECT set_config('application_name', 'changed', false)",
      parameters: [],
    },
    env,
  );
  const rows = await executeReadOnly(
    {
      sql: "SELECT current_setting('application_name') AS value",
      parameters: [],
    },
    env,
  );
  assert.equal(rows[0].value, 'orangevision-admin-reader');
});
