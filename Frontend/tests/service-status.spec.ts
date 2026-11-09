import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('status remoto: verificação, falha, recuperação e interface mobile acessível', async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.route('**/api/auth/session', (route) =>
    route.fulfill({ status: 401, json: { detail: 'Sem sessão' } }),
  );
  let healthy = false;
  await page.route('**/api/status/render', async (route) => {
    expect(route.request().headers()['cookie']).toBeUndefined();
    expect(route.request().headers()['authorization']).toBeUndefined();
    await route.fulfill({
      json: {
        state: healthy ? 'available' : 'unavailable',
        checkedAt: '2026-10-29T12:00:00.000Z',
        durationMs: 123,
        httpStatus: healthy ? 200 : 503,
      },
    });
  });
  await page.goto('/login');
  const status = page.getByRole('region', { name: 'Status da API do Render' });
  await expect(status.getByText('Indisponível', { exact: true })).toBeVisible();
  await expect(status.getByText(/HTTP 503/)).toBeVisible();
  healthy = true;
  await status.getByRole('button', { name: 'Verificar novamente' }).click();
  await expect(status.getByText('Disponível', { exact: true })).toBeVisible();
  await expect(status.getByText(/HTTP 200/)).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  const accessibility = await new AxeBuilder({ page })
    .include('section[aria-label="Status da API do Render"]')
    .analyze();
  expect(accessibility.violations).toEqual([]);
  await page.route('**/api/status/render', (route) =>
    route.fulfill({ status: 502, json: {} }),
  );
  await status.getByRole('button', { name: 'Verificar novamente' }).click();
  await expect(
    status.getByText('Status não confirmado', { exact: true }),
  ).toBeVisible();
  await expect(status.getByText(/Última resposta/)).toBeVisible();
});
