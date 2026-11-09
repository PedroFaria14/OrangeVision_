import { execFileSync, spawnSync } from 'node:child_process';
import process from 'node:process';
import console from 'node:console';
import { randomBytes } from 'node:crypto';
import { setTimeout } from 'node:timers/promises';
import { Client } from 'pg';

const name = `orangevision-prisma-test-${process.pid}`;
const password = randomBytes(24).toString('hex');
const docker = (...args) =>
  execFileSync('docker', args, {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  }).trim();
let started = false;
try {
  docker(
    'run',
    '--detach',
    '--rm',
    '--name',
    name,
    '--publish',
    '127.0.0.1::5432',
    '--env',
    `POSTGRES_PASSWORD=${password}`,
    '--env',
    'POSTGRES_DB=admin_test',
    'postgres:16-alpine',
  );
  started = true;
  const port = docker('port', name, '5432/tcp').split(':').at(-1);
  const writer = `postgresql://postgres:${password}@127.0.0.1:${port}/admin_test`;
  let client;
  for (let i = 0; i < 40; i++) {
    client = new Client({
      connectionString: writer,
      connectionTimeoutMillis: 1000,
    });
    try {
      await client.connect();
      break;
    } catch {
      await client.end().catch(() => {});
      client = undefined;
      await setTimeout(500);
    }
  }
  if (!client) throw new Error('PostgreSQL descartável indisponível.');
  try {
    await client.query(`
      CREATE TABLE public.admin_test (id serial PRIMARY KEY, name text, metadata jsonb);
      INSERT INTO public.admin_test (name, metadata) VALUES ('Laranja de teste', '{"sample":true}');
      CREATE ROLE admin_reader LOGIN PASSWORD '${password}';
      GRANT USAGE ON SCHEMA public TO admin_reader;
      GRANT SELECT ON ALL TABLES IN SCHEMA public TO admin_reader;
      CREATE ROLE admin_column_writer LOGIN PASSWORD '${password}';
      GRANT USAGE ON SCHEMA public TO admin_column_writer;
      GRANT SELECT, UPDATE(name) ON public.admin_test TO admin_column_writer;
      CREATE ROLE admin_schema_owner LOGIN PASSWORD '${password}';
      CREATE SCHEMA pgcustom AUTHORIZATION admin_schema_owner;
    `);
  } finally {
    await client.end();
  }
  const env = {
    ...process.env,
    ADMIN_TEST_DATABASE_URL: writer.replace('postgres:', 'admin_reader:'),
    ADMIN_TEST_WRITER_URL: writer,
    ADMIN_TEST_COLUMN_WRITER_URL: writer.replace(
      'postgres:',
      'admin_column_writer:',
    ),
    ADMIN_TEST_SCHEMA_OWNER_URL: writer.replace(
      'postgres:',
      'admin_schema_owner:',
    ),
    NEXTAUTH_URL: 'http://127.0.0.1:4178',
    NEXTAUTH_SECRET: randomBytes(48).toString('hex'),
    GITHUB_CLIENT_ID: 'local-oauth-fixture',
    GITHUB_CLIENT_SECRET: 'local-oauth-fixture',
    ADMIN_GITHUB_ID: '12345',
    STUDIO_DATABASE_URL: writer.replace('postgres:', 'admin_reader:'),
    RENDER_API_ORIGIN: 'https://orangevision-rs9g.onrender.com',
    VITE_API_ENABLED: 'false',
    ADMIN_TEST_UNCONFIGURED: process.argv.includes('--unconfigured') ? '1' : '',
  };
  delete env.VERCEL;
  if (process.argv.includes('--unconfigured')) {
    for (const key of [
      'NEXTAUTH_URL',
      'NEXTAUTH_SECRET',
      'GITHUB_CLIENT_ID',
      'GITHUB_CLIENT_SECRET',
      'ADMIN_GITHUB_ID',
      'STUDIO_DATABASE_URL',
    ])
      env[key] = '';
  }
  const args = process.argv.includes('--browser')
    ? [
        'node_modules/@playwright/test/cli.js',
        'test',
        '--config',
        'playwright.admin.config.ts',
      ]
    : ['--import', 'tsx', '--test', 'tests/admin/database.integration.ts'];
  const result = spawnSync(process.execPath, args, { env, stdio: 'inherit' });
  process.exitCode = result.status ?? 1;
} catch (error) {
  console.error('Falha no teste Prisma descartável:', error.name);
  process.exitCode = 1;
} finally {
  if (started) docker('stop', name);
}
