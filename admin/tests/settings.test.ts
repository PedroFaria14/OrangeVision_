import assert from 'node:assert/strict';
import { test } from 'node:test';
import { authSettings, databaseUrl, ConfigurationError } from '../lib/settings';

test('configuração de autenticação exige segredo, ID numérico e HTTPS remoto', () => {
  const previous = { ...process.env };
  try {
    Object.assign(process.env, {
      NEXTAUTH_URL: 'https://admin.example.test', NEXTAUTH_SECRET: 'test-only-'.repeat(8),
      GITHUB_CLIENT_ID: 'example', GITHUB_CLIENT_SECRET: 'example', ADMIN_GITHUB_ID: '12345',
    });
    delete process.env.VERCEL;
    assert.equal(authSettings().origin, 'https://admin.example.test');
    process.env.ADMIN_GITHUB_ID = 'nome-de-usuario';
    assert.throws(authSettings, ConfigurationError);
    process.env.ADMIN_GITHUB_ID = '12345';
    process.env.NEXTAUTH_URL = 'http://admin.example.test';
    assert.throws(authSettings, ConfigurationError);
    process.env.NEXTAUTH_URL = 'http://127.0.0.1:3001';
    assert.equal(authSettings().origin, 'http://127.0.0.1:3001');
    process.env.VERCEL = '1';
    assert.throws(authSettings, ConfigurationError);
    process.env.NEXTAUTH_URL = 'https://admin.example.test';
    process.env.NEXTAUTH_SECRET = '';
    assert.throws(authSettings, ConfigurationError);
  } finally { process.env = previous; }
});

test('a conexão exige PostgreSQL com TLS remoto e não usa fallback da API', () => {
  const previous = { ...process.env };
  try {
    delete process.env.STUDIO_DATABASE_URL;
    process.env.DATABASE_URL = 'postgresql://owner:example@host/db';
    assert.throws(databaseUrl, ConfigurationError);
    process.env.STUDIO_DATABASE_URL = 'postgresql://reader:example@db.example/db?sslmode=disable';
    assert.throws(databaseUrl, ConfigurationError);
    process.env.STUDIO_DATABASE_URL = 'postgresql://reader:example@db.example/db?sslmode=require';
    assert.match(databaseUrl(), /sslmode=require/);
    process.env.STUDIO_DATABASE_URL = 'https://db.example';
    assert.throws(databaseUrl, ConfigurationError);
  } finally { process.env = previous; }
});
