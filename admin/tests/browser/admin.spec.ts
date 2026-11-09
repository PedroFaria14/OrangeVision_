import { test, expect, type BrowserContext } from '@playwright/test';
import { encode } from 'next-auth/jwt';

// Somente os testes conhecem este segredo efêmero, injetado no servidor descartável.
// Não existe rota ou flag de bypass na aplicação publicada.
async function session(context: BrowserContext, id: string, maxAge = 3600) {
  const secret = process.env.NEXTAUTH_SECRET;
  if (!secret) throw new Error('Use npm run test:e2e.');
  const value = await encode({ secret, token: { sub: id, githubId: id, provider: 'github' }, maxAge });
  await context.addCookies([{ name: 'next-auth.session-token', value, url: 'http://127.0.0.1:3001', httpOnly: true, sameSite: 'Lax' }]);
}

test('visitante vai ao login e a API não entrega dados sem sessão', async ({ page, request }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole('button', { name: 'Entrar com GitHub' })).toBeVisible();
  const response = await request.post('/api/studio', {
    headers: { Origin: 'http://127.0.0.1:3001' },
    data: { procedure: 'query', query: { sql: 'SELECT * FROM public.admin_test', parameters: [] } },
  });
  expect(response.status()).toBe(401);
  expect(await response.text()).not.toContain('Laranja de teste');
  expect(response.headers()['cache-control']).toContain('no-store');
});

test('identidade fora da allowlist e sessão expirada não autorizam acesso', async ({ context, page }) => {
  for (const [id, maxAge] of [['99999', 3600], ['12345', -120]] as const) {
    await context.clearCookies();
    await session(context, id, maxAge);
    await page.goto('/');
    await expect(page).toHaveURL(/\/login$/);
  }
});

test('login dispara GitHub OAuth com state e PKCE, sem abrir a rede externa no teste', async ({ page }) => {
  const provider = await page.request.get('/api/auth/providers');
  expect(provider.status()).toBe(200);
  expect((await provider.json()).github.id).toBe('github');
  let oauthUrl = '';
  await page.route('https://github.com/**', async route => {
    oauthUrl = route.request().url();
    await route.fulfill({ contentType: 'text/html', body: '<p>OAuth fixture</p>' });
  });
  await page.goto('/login');
  await page.getByRole('button', { name: 'Entrar com GitHub' }).click();
  await expect.poll(() => oauthUrl).toContain('github.com/login/oauth/authorize');
  const url = new URL(oauthUrl);
  expect(url.searchParams.get('state')).toBeTruthy();
  expect(url.searchParams.get('code_challenge')).toBeTruthy();
  expect(url.searchParams.get('code_challenge_method')).toBe('S256');
  expect(url.searchParams.get('redirect_uri')).toBe('http://127.0.0.1:3001/api/auth/callback/github');
});

test('administrador vê o Studio com dados reais de teste e pode encerrar a sessão', async ({ page, context }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await session(context, '12345');
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Banco de dados' })).toBeVisible();
  await expect(page.getByText('admin_test', { exact: true }).first()).toBeVisible({ timeout: 20000 });
  await page.getByText('admin_test', { exact: true }).first().click();
  await expect(page.getByText('Laranja de teste', { exact: true }).first()).toBeVisible({ timeout: 15000 });
  expect(errors).toEqual([]);
  await page.getByRole('button', { name: 'Sair', exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goto('/');
  await expect(page).toHaveURL(/\/login$/);
});

test('API autenticada bloqueia escrita e CSRF; devolve SELECT no contrato do Studio', async ({ context, page }) => {
  await session(context, '12345');
  const post = (sql: string, origin = 'http://127.0.0.1:3001') => page.request.post('/api/studio', {
    headers: { Origin: origin }, data: { procedure: 'query', query: { sql, parameters: [] } },
  });
  expect((await post('SELECT 1', 'https://externo.example')).status()).toBe(403);
  expect((await post('DELETE FROM public.admin_test')).status()).toBe(403);
  expect((await post('WITH deleted AS (DELETE FROM public.admin_test RETURNING *) SELECT * FROM deleted')).status()).toBe(422);
  const response = await post('SELECT name FROM public.admin_test');
  expect(response.status()).toBe(200);
  expect(await response.json()).toEqual([null, [{ name: 'Laranja de teste' }]]);
});

test('login mantém conteúdo legível e sem overflow em viewport móvel', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/login');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.getByRole('button', { name: 'Entrar com GitHub' }).focus();
  await expect(page.getByRole('button', { name: 'Entrar com GitHub' })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
