import { Client } from 'pg';
import type { Query } from '@prisma/studio-core/data';
import { databaseUrl, type AdminEnvironment } from './settings.js';

export class ReadOnlyError extends Error {
  constructor(
    message = 'Use uma role exclusiva de leitura, sem propriedade ou privilégios administrativos.',
  ) {
    super(message);
  }
}

const roleCheck = `
SELECT
  NOT (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls)
  AND current_user = session_user
  AND NOT EXISTS (SELECT 1 FROM pg_auth_members WHERE member = r.oid)
  AND NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = current_database() AND datdba = r.oid)
  AND NOT has_database_privilege(current_user, current_database(), 'CREATE')
  AND NOT EXISTS (
    SELECT 1 FROM pg_namespace n
    WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'
      AND (n.nspowner = r.oid OR has_schema_privilege(current_user, n.oid, 'CREATE'))
  )
  AND NOT EXISTS (
    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'
      AND (c.relowner = r.oid OR
        (c.relkind IN ('r','p','v','m','f') AND
          (has_table_privilege(current_user, c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
           OR has_any_column_privilege(current_user, c.oid, 'INSERT,UPDATE,REFERENCES')))
        OR (c.relkind = 'S' AND has_sequence_privilege(current_user, c.oid, 'USAGE,UPDATE')))
  ) AS safe
FROM pg_roles r WHERE r.rolname = current_user`;

export async function executeReadOnly(
  query: Query<unknown>,
  env: AdminEnvironment = process.env,
) {
  if (!/^\s*(SELECT|WITH|SHOW|EXPLAIN)\b/i.test(query.sql)) {
    throw new ReadOnlyError('Este painel aceita somente consultas de leitura.');
  }
  const client = new Client({
    connectionString: databaseUrl(env),
    connectionTimeoutMillis: 5000,
    query_timeout: 12000,
    application_name: 'orangevision-admin-reader',
  });
  try {
    await client.connect();
    await client.query('BEGIN READ ONLY');
    await client.query("SET LOCAL statement_timeout = '10s'");
    await client.query("SET LOCAL lock_timeout = '2s'");
    const check = await client.query<{ safe: boolean }>(roleCheck);
    if (check.rows[0]?.safe !== true) throw new ReadOnlyError();
    const statement = {
      text: query.sql,
      values: [...query.parameters],
      queryMode: 'extended' as const,
    };
    const result = await client.query(statement);
    const rows: Record<string, unknown>[] = result.rows;
    for (const row of rows) {
      for (const [column, transformation] of Object.entries(
        query.transformations ?? {},
      )) {
        if (transformation === 'json-parse' && typeof row[column] === 'string')
          row[column] = JSON.parse(row[column]);
      }
    }
    return rows;
  } finally {
    // Fecha sem COMMIT: desfaz a transação e impede persistir SET/estado de sessão.
    await client.end().catch(() => {});
  }
}
