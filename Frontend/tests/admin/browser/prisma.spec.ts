import { test, expect, type BrowserContext } from '@playwright/test';
import { encode } from '@auth/core/jwt';

async function session(context: BrowserContext, id = '12345', maxAge = 3600) {
  const name = 'orangevision_admin_session';
  const secret = process.env.NEXTAUTH_SECRET!;
  const value = await encode({
    secret,
    salt: name,
    token: { githubId: id, provider: 'github', sub: id },
    maxAge,
  });
  await context.addCookies([
    {
      name,
      value,
      domain: '127.0.0.1',
      path: '/api/admin',
      httpOnly: true,
      sameSite: 'Lax',
    },
  ]);
}

if (process.env.ADMIN_TEST_UNCONFIGURED) {
  test('a rota existe mesmo antes dos secrets e informa o que configurar', async ({
    page,
  }) => {
    await page.goto('/admin/prisma');
    await expect(
      page.getByRole('heading', { name: 'Prisma Studio' }),
    ).toBeVisible();
    await expect(
      page.getByText('A rota do Prisma está instalada.', { exact: false }),
    ).toBeVisible();
    await expect(
      page.getByText('Página não encontrada.', { exact: false }),
    ).toHaveCount(0);
  });
} else {
  test('rota real do site mostra login e API nega dados a visitantes', async ({
    page,
  }) => {
    await page.goto('/admin/prisma');
    await expect(
      page.getByRole('button', { name: 'Entrar com GitHub' }),
    ).toBeVisible();
    await expect(
      page.getByText('Página não encontrada.', { exact: false }),
    ).toHaveCount(0);
    const response = await page.request.post('/api/admin/studio', {
      headers: { Origin: 'http://127.0.0.1:4178' },
      data: {
        procedure: 'query',
        query: { sql: 'SELECT * FROM admin_test', parameters: [] },
      },
    });
    expect(response.status()).toBe(401);
    expect(await response.text()).not.toContain('Laranja de teste');
  });

  test('outra identidade e sessão expirada não abrem o Studio', async ({
    page,
    context,
  }) => {
    for (const [id, maxAge] of [
      ['99999', 3600],
      ['12345', -120],
    ] as const) {
      await context.clearCookies();
      await session(context, id, maxAge);
      await page.goto('/admin/prisma');
      await expect(
        page.getByRole('button', { name: 'Entrar com GitHub' }),
      ).toBeVisible();
      await expect(page.locator('iframe')).toHaveCount(0);
    }
  });

  test('login OAuth usa callback no mesmo projeto com state e PKCE', async ({
    page,
  }) => {
    let target = '';
    await page.route('https://github.com/**', (route) => route.abort());
    await page.route('**/api/admin/auth/signin/github', async (route) => {
      const response = await route.fetch({ maxRedirects: 0 });
      target = response.headers().location ?? '';
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: '<p>GitHub fixture</p>',
      });
    });
    await page.goto('/admin/prisma');
    await page.getByRole('button', { name: 'Entrar com GitHub' }).click();
    await expect
      .poll(() => target)
      .toContain('github.com/login/oauth/authorize');
    const url = new URL(target);
    expect(url.searchParams.get('redirect_uri')).toBe(
      'http://127.0.0.1:4178/api/admin/auth/callback/github',
    );
    expect(url.searchParams.get('state')).toBeTruthy();
    expect(url.searchParams.get('code_challenge_method')).toBe('S256');
  });

  test('Studio lê PostgreSQL real de teste, não altera o CSS do site e faz logout', async ({
    page,
    context,
  }) => {
    const errors: string[] = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await session(context);
    await page.goto('/admin/prisma');
    const frame = page.frameLocator(
      'iframe[title="Prisma Studio — banco de dados"]',
    );
    await expect(
      frame.getByText('admin_test', { exact: true }).first(),
    ).toBeVisible({ timeout: 20000 });
    await frame.getByText('admin_test', { exact: true }).first().click();
    await expect(
      frame.getByText('Laranja de teste', { exact: true }).first(),
    ).toBeVisible();
    expect(
      await page.evaluate(() => getComputedStyle(document.body).fontFamily),
    ).toContain('Roboto');
    expect(errors).toEqual([]);
    await page.getByRole('button', { name: 'Sair do painel' }).click();
    await expect(
      page.getByRole('button', { name: 'Entrar com GitHub' }),
    ).toBeVisible();
    await expect(page.locator('iframe')).toHaveCount(0);
  });

  test('API autenticada bloqueia escrita e CSRF, preservando os dados', async ({
    page,
    context,
  }) => {
    await session(context);
    const post = (sql: string, origin = 'http://127.0.0.1:4178') =>
      page.request.post('/api/admin/studio', {
        headers: { Origin: origin },
        data: { procedure: 'query', query: { sql, parameters: [] } },
      });
    expect((await post('SELECT 1', 'https://evil.example')).status()).toBe(403);
    expect((await post('DELETE FROM public.admin_test')).status()).toBe(403);
    expect(
      (
        await post(
          'WITH removed AS (DELETE FROM public.admin_test RETURNING *) SELECT * FROM removed',
        )
      ).status(),
    ).toBe(422);
    const response = await post('SELECT name FROM public.admin_test');
    expect(response.status()).toBe(200);
    expect(await response.json()).toEqual([
      null,
      [{ name: 'Laranja de teste' }],
    ]);
    expect(response.headers()['cache-control']).toContain('no-store');
  });

  test('cookie administrativo não é enviado ao proxy /api/auth do site', async ({
    page,
    context,
  }) => {
    await session(context);
    let cookie = '';
    await page.route('**/api/auth/session', async (route) => {
      cookie = route.request().headers().cookie ?? '';
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: '{}',
      });
    });
    await page.goto('/admin/prisma');
    await page.evaluate(() => fetch('/api/auth/session'));
    expect(cookie).not.toContain('orangevision_admin_session');
  });

  test('login funciona em tela móvel e preserva navegação de volta ao site', async ({
    page,
  }) => {
    await page.route('**/api/status/render', (route) =>
      route.fulfill({ contentType: 'application/json', body: '{}' }),
    );
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/admin/prisma');
    const button = page.getByRole('button', { name: 'Entrar com GitHub' });
    await expect(button).toBeVisible();
    await button.focus();
    await expect(button).toBeFocused();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.getByRole('link', { name: 'Voltar ao OrangeVision' }).click();
    await expect(page).toHaveURL('http://127.0.0.1:4178/');
  });
}
