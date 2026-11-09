import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const user = {
  id: '00000000-0000-4000-8000-000000000001',
  name: 'Pessoa Teste',
  email: 'person@example.com',
};
const device = {
  id: '00000000-0000-4000-8000-000000000002',
  name: 'Bancada de teste',
};
const inspection = {
  id: '00000000-0000-4000-8000-000000000003',
  device_id: device.id,
  user_id: user.id,
  operator_name: user.name,
  state: 'pending',
  created_at: '2026-10-20T15:00:00Z',
  pairing_expires_at: '2026-10-20T15:05:00Z',
  started_at: null,
  authorization_expires_at: null,
  closed_at: null,
};

test.beforeEach(async ({ page }) => {
  await page.route('**/api/auth/session', (route) =>
    route.fulfill({ json: { user, csrf_token: 'test-only-csrf' } }),
  );
  await page.route('**/api/inspections/config', (route) =>
    route.fulfill({ json: { enabled: true, ownership: 'inspection-session' } }),
  );
  await page.route('**/api/inspections/devices', (route) =>
    route.fulfill({ json: [device] }),
  );
  await page.route('**/api/inspections/current', (route) =>
    route.fulfill({ json: [] }),
  );
});

test('recurso desativado continua opcional e não solicita câmera', async ({
  page,
}) => {
  await page.route('**/api/inspections/config', (route) =>
    route.fulfill({ json: { enabled: false, ownership: 'device-access' } }),
  );
  await page.goto('/dashboard/inspecoes');
  await expect(
    page.getByText(/Inspeções são opcionais e estão desativadas/),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Iniciar inspeção', exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole('link', { name: 'Inspeções', exact: true }),
  ).toHaveCount(0);
});

test('início usa csrf, comando estável e código temporário sem segredo de equipamento', async ({
  page,
}) => {
  let created = false;
  let calls = 0;
  await page.route('**/api/inspections/current', (route) =>
    route.fulfill({ json: created ? [inspection] : [] }),
  );
  await page.route('**/api/inspections', (route) => {
    calls++;
    created = true;
    const payload = route.request().postDataJSON();
    expect(payload.device_id).toBe(device.id);
    expect(payload.pairing_code.length).toBeGreaterThanOrEqual(32);
    expect(payload.user_id).toBeUndefined();
    expect(route.request().headers()['x-csrf-token']).toBe('test-only-csrf');
    expect(route.request().headers().authorization).toBeUndefined();
    return route.fulfill({ status: 201, json: inspection });
  });
  await page.goto('/dashboard/inspecoes');
  await page.getByLabel('Equipamento autorizado').click();
  await page.getByRole('option', { name: device.name }).click();
  await page
    .getByRole('button', { name: 'Iniciar inspeção', exact: true })
    .click();
  await expect(
    page.getByText('Aguardando pareamento', { exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel('Código temporário de pareamento')).toHaveValue(
    /^[a-f0-9]{32}$/,
  );
  expect(calls).toBe(1);
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([]);
  await expect(page.getByRole('button', { name: /Capturar/ })).toHaveCount(0);
});

test('encerramento ativo aguarda confirmação local e mantém código fora do cache persistente', async ({
  page,
}) => {
  let closing = false;
  const active = {
    ...inspection,
    state: 'active',
    started_at: '2026-10-20T15:01:00Z',
    authorization_expires_at: '2026-10-20T23:01:00Z',
  };
  await page.route('**/api/inspections/current', (route) =>
    route.fulfill({
      json: [{ ...active, state: closing ? 'closing' : 'active' }],
    }),
  );
  await page.route(`**/api/inspections/${inspection.id}/close`, (route) => {
    closing = true;
    return route.fulfill({
      json: { ...active, state: 'closed', closed_at: '2026-10-20T16:00:00Z' },
    });
  });
  await page.goto('/dashboard/inspecoes');
  await page.getByRole('button', { name: 'Encerrar inspeção' }).click();
  // Sessão ativa pede confirmação; "Manter sessão" não envia nada.
  await page.getByRole('button', { name: 'Manter sessão' }).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  expect(closing).toBe(false);
  await page.getByRole('button', { name: 'Encerrar inspeção' }).click();
  await expect(page.getByText(/A sessão é encerrada na hora/)).toBeVisible();
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Encerrar inspeção' })
    .click();
  await expect.poll(() => closing).toBe(true);
});

test('sessões encerradas ou expiradas não permitem novo encerramento; pendente antiga pode ser liberada', async ({
  page,
}) => {
  let closeCalls = 0;
  await page.route('**/api/inspections/current', (route) =>
    route.fulfill({
      json: ['closing', 'closed', 'expired'].map((state, index) => ({
        ...inspection,
        id: `00000000-0000-4000-8000-${String(index + 10).padStart(12, '0')}`,
        state,
        closed_at: state === 'closed' ? '2026-10-20T16:00:00Z' : null,
      })),
    }),
  );
  await page.route('**/api/inspections/*/close', (route) => {
    closeCalls++;
    return route.fulfill({ json: inspection });
  });
  await page.goto('/dashboard/inspecoes');
  const buttons = page.getByRole('button', {
    name: 'Encerrar inspeção',
    exact: true,
  });
  await expect(buttons).toHaveCount(3);
  await expect(buttons.nth(0)).toBeEnabled();
  await expect(buttons.nth(1)).toBeDisabled();
  await expect(buttons.nth(2)).toBeDisabled();
  expect(closeCalls).toBe(0);
});

test('inspeções sem equipamento autorizado mostram orientação sem inventar dispositivo', async ({
  page,
}) => {
  await page.route('**/api/inspections/devices', (route) =>
    route.fulfill({ json: [] }),
  );
  await page.goto('/dashboard/inspecoes');
  await expect(page.getByText(/Nenhum equipamento foi liberado/)).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Iniciar inspeção', exact: true }),
  ).toHaveCount(0);
});

test('inspeção móvel e pendente passam em responsividade e acessibilidade', async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.route('**/api/inspections/current', (route) =>
    route.fulfill({ json: [inspection] }),
  );
  await page.goto('/dashboard/inspecoes');
  await expect(
    page.getByText('Aguardando pareamento', { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(
    result.violations.map((item) => ({
      id: item.id,
      targets: item.nodes.map((node) => node.target),
    })),
  ).toEqual([]);
});

test('início sem resposta pode ser confirmado com o mesmo comando mesmo após consultar a sessão', async ({
  page,
}) => {
  let created = false;
  const commands: unknown[] = [];
  await page.route('**/api/inspections/current', (route) =>
    route.fulfill({ json: created ? [inspection] : [] }),
  );
  await page.route('**/api/inspections', (route) => {
    commands.push(route.request().postDataJSON());
    created = true;
    return commands.length === 1
      ? route.abort('failed')
      : route.fulfill({ status: 201, json: inspection });
  });
  await page.goto('/dashboard/inspecoes');
  await page.getByLabel('Equipamento autorizado').click();
  await page.getByRole('option', { name: device.name }).click();
  await page
    .getByRole('button', { name: 'Iniciar inspeção', exact: true })
    .click();
  await expect(page.getByText(/Início não confirmado/)).toBeVisible();
  await page.getByRole('button', { name: 'Atualizar sessões' }).click();
  await expect(
    page.getByText('Aguardando pareamento', { exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Tentar confirmar início' }).click();
  await expect(
    page.getByLabel('Código temporário de pareamento'),
  ).toBeVisible();
  expect(commands).toHaveLength(2);
  expect(commands[0]).toEqual(commands[1]);
});
