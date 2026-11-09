import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { encode } from '@auth/core/jwt';
import {
  adminAuthConfig,
  handleAdminAuth,
  isAdmin,
} from '../../server/admin/auth.ts';
import { handleAdminStudio } from '../../server/admin/studio.ts';

const origin = 'https://orange-vision.vercel.app';
const env = {
  NEXTAUTH_URL: origin,
  NEXTAUTH_SECRET: 'test-only-admin-secret-'.repeat(4),
  GITHUB_CLIENT_ID: 'fixture-client',
  GITHUB_CLIENT_SECRET: 'fixture-private-client',
  ADMIN_GITHUB_ID: '12345',
};
async function cookie(id = '12345', maxAge = 3600) {
  const name = '__Secure-orangevision_admin_session';
  const token = await encode({
    secret: env.NEXTAUTH_SECRET,
    salt: name,
    maxAge,
    token: { githubId: id, provider: 'github', sub: id },
  });
  return `${name}=${token}`;
}
function studio(
  body: unknown,
  session = '',
  requestOrigin: string | null = origin,
) {
  return new Request(`${origin}/api/admin/studio`, {
    method: 'POST',
    headers: {
      cookie: session,
      'Content-Type': 'application/json',
      ...(requestOrigin ? { Origin: requestOrigin } : {}),
    },
    body: JSON.stringify(body),
  });
}

test('a rota de autenticação falha fechada sem configuração e não vaza secrets', async () => {
  const response = await handleAdminAuth(
    new Request(`${origin}/api/admin/auth/session`),
    {},
  );
  assert.equal(response.status, 503);
  assert.match(response.headers.get('cache-control')!, /no-store/);
  assert.doesNotMatch(await response.text(), /fixture-private/);
});

test('visitantes, identidade fora da allowlist, cookie forjado e sessão expirada são recusados', async () => {
  for (const value of [
    '',
    'orangevision_admin_session=invalid',
    await cookie('99999'),
    await cookie('12345', -120),
  ]) {
    assert.equal(
      await isAdmin(
        new Request(`${origin}/api/admin/studio`, {
          headers: { cookie: value },
        }),
        env,
      ),
      false,
    );
  }
  assert.equal(
    await isAdmin(
      new Request(`${origin}/api/admin/studio`, {
        headers: { cookie: await cookie() },
      }),
      env,
    ),
    true,
  );
});

test('callback de login aceita apenas GitHub e o ID imutável configurado', async () => {
  const signIn = adminAuthConfig(env).callbacks!.signIn!;
  const account = {
    provider: 'github',
    type: 'oauth' as const,
    providerAccountId: '12345',
  };
  assert.equal(
    await signIn({ user: { id: '12345' }, account, profile: { id: '12345' } }),
    true,
  );
  assert.equal(
    await signIn({ user: { id: '99999' }, account, profile: { id: '99999' } }),
    false,
  );
  assert.equal(
    await signIn({
      user: { id: '12345' },
      account: { ...account, provider: 'other' },
      profile: { id: '12345' },
    }),
    false,
  );
});

test('API exige sessão antes de tocar no banco, mesmo recebendo SQL malicioso', async () => {
  const response = await handleAdminStudio(
    studio({
      procedure: 'query',
      query: { sql: 'DELETE FROM users', parameters: [] },
    }),
    env,
  );
  assert.equal(response.status, 401);
  assert.match(response.headers.get('cache-control')!, /no-store/);
});

test('CSRF é bloqueado em autenticação e consultas, inclusive quando autenticado', async () => {
  const session = await cookie();
  for (const invalidOrigin of ['https://evil.example', null]) {
    assert.equal(
      (await handleAdminStudio(studio({}, session, invalidOrigin), env)).status,
      403,
    );
  }
  const response = await handleAdminAuth(
    new Request(`${origin}/api/admin/auth/signout`, {
      method: 'POST',
      headers: { Origin: 'https://evil.example' },
      body: '',
    }),
    env,
  );
  assert.equal(response.status, 403);
});

test('valida procedures, formato e limite de corpo antes de acessar o banco', async () => {
  const session = await cookie();
  for (const value of [
    null,
    [],
    {},
    { procedure: 'transaction', queries: [] },
    { procedure: 'query', query: { sql: 'SELECT 1', parameters: {} } },
    {
      procedure: 'query',
      query: {
        sql: 'SELECT 1',
        parameters: [],
        transformations: { field: 'execute' },
      },
    },
  ]) {
    assert.equal(
      (await handleAdminStudio(studio(value, session), env)).status,
      400,
    );
  }
  assert.equal(
    (await handleAdminStudio(studio({ data: 'x'.repeat(66000) }, session), env))
      .status,
    413,
  );
});

test('rewrite da Vercel gera callback no domínio atual com state, PKCE e cookies isolados', async () => {
  const csrf = await handleAdminAuth(
    new Request(`${origin}/api/admin/auth?__path=csrf`),
    env,
  );
  const { csrfToken } = (await csrf.json()) as { csrfToken: string };
  const cookies = csrf.headers
    .getSetCookie()
    .map((value) => value.split(';')[0])
    .join('; ');
  assert.ok(csrfToken);
  assert.ok(
    csrf.headers
      .getSetCookie()
      .every(
        (value) =>
          value.includes('Path=/api/admin/auth') &&
          value.includes('HttpOnly') &&
          value.includes('Secure'),
      ),
  );
  const response = await handleAdminAuth(
    new Request(`${origin}/api/admin/auth?__path=signin/github`, {
      method: 'POST',
      headers: {
        cookie: cookies,
        Origin: origin,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        csrfToken,
        callbackUrl: `${origin}/admin/prisma`,
      }),
    }),
    env,
  );
  assert.equal(response.status, 302);
  const redirect = new URL(response.headers.get('location')!);
  assert.equal(redirect.origin, 'https://github.com');
  assert.equal(
    redirect.searchParams.get('redirect_uri'),
    `${origin}/api/admin/auth/callback/github`,
  );
  assert.ok(redirect.searchParams.get('state'));
  assert.equal(redirect.searchParams.get('code_challenge_method'), 'S256');
  assert.ok(redirect.searchParams.get('code_challenge'));
});

test('signin sem CSRF não inicia OAuth e redirect externo não é aceito', async () => {
  const response = await handleAdminAuth(
    new Request(`${origin}/api/admin/auth/signin/github`, {
      method: 'POST',
      headers: {
        Origin: origin,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: 'callbackUrl=https%3A%2F%2Fevil.example',
    }),
    env,
  );
  assert.notEqual(
    new URL(response.headers.get('location')!).origin,
    'https://github.com',
  );
  const redirect = adminAuthConfig(env).callbacks!.redirect!;
  assert.equal(
    await redirect({ url: 'https://evil.example', baseUrl: origin }),
    `${origin}/admin/prisma`,
  );
});

test('configuração Vercel mantém o Render e reserva /api/admin antes do proxy público', async () => {
  const config = JSON.parse(
    await readFile(new URL('../../vercel.json', import.meta.url), 'utf8'),
  );
  const routes = config.routes as {
    src?: string;
    dest?: string;
    status?: number;
  }[];
  const authIndex = routes.findIndex((r) => r.src === '/api/admin/auth/(.*)');
  const reservedIndex = routes.findIndex((r) => r.status === 404);
  const renderIndex = routes.findIndex((r) => r.src === '/api/(.*)');
  assert.ok(
    authIndex >= 0 && reservedIndex > authIndex && renderIndex > reservedIndex,
  );
  assert.equal(routes[authIndex].dest, '/api/admin/auth?__path=$1');
  assert.equal(
    routes[renderIndex].dest,
    'https://orangevision-rs9g.onrender.com/api/$1',
  );
});
