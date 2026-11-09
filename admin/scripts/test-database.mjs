import { execFileSync, spawnSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { setTimeout } from 'node:timers/promises';
import { Client } from 'pg';

const name = `orangevision-admin-test-${process.pid}`;
const password = randomBytes(24).toString('hex');
const docker = (...args) => execFileSync('docker', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
let started = false;
try {
  docker('run', '--detach', '--rm', '--name', name,
    '--publish', '127.0.0.1::5432', '--env', `POSTGRES_PASSWORD=${password}`,
    '--env', 'POSTGRES_DB=admin_test', 'postgres:16-alpine');
  started = true;
  const port = docker('port', name, '5432/tcp').split(':').at(-1);
  const writer = `postgresql://postgres:${password}@127.0.0.1:${port}/admin_test`;
  let client;
  for (let i = 0; i < 40; i++) {
    client = new Client({ connectionString: writer, connectionTimeoutMillis: 1000 });
    try { await client.connect(); break; }
    catch { await client.end().catch(() => {}); client = undefined; await setTimeout(500); }
  }
  if (!client) throw new Error('PostgreSQL descartável não ficou disponível.');
  try {
    await client.query(`
      CREATE TABLE public.admin_test (id serial PRIMARY KEY, name text, metadata jsonb);
      INSERT INTO public.admin_test (name, metadata) VALUES ('Laranja de teste', '{"sample":true}');
      CREATE ROLE admin_reader LOGIN PASSWORD '${password}';
      GRANT USAGE ON SCHEMA public TO admin_reader;
      GRANT SELECT ON ALL TABLES IN SCHEMA public TO admin_reader;
    `);
  } finally { await client.end(); }
  const env = {
    ...process.env,
    ADMIN_TEST_DATABASE_URL: writer.replace('postgres:', 'admin_reader:'),
    ADMIN_TEST_WRITER_URL: writer,
  };
  if (process.argv.includes('--browser')) {
    Object.assign(env, {
      NEXTAUTH_URL: 'http://127.0.0.1:3001',
      NEXTAUTH_SECRET: randomBytes(48).toString('hex'),
      GITHUB_CLIENT_ID: 'local-browser-fixture',
      GITHUB_CLIENT_SECRET: 'local-browser-fixture',
      ADMIN_GITHUB_ID: '12345',
      STUDIO_DATABASE_URL: env.ADMIN_TEST_DATABASE_URL,
    });
    delete env.VERCEL;
  }
  const args = process.argv.includes('--browser')
    ? ['node_modules/@playwright/test/cli.js', 'test']
    : ['--import', 'tsx', '--test', 'tests/database.integration.ts'];
  const result = spawnSync(process.execPath, args, { env, stdio: 'inherit' });
  process.exitCode = result.status ?? 1;
} catch {
  console.error('Falha ao preparar/executar o teste descartável. Confira Docker e a imagem postgres:16-alpine.');
  process.exitCode = 1;
} finally {
  if (started) docker('stop', name);
}
