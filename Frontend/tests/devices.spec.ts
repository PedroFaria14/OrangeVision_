import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const user = {
  id: '00000000-0000-4000-8000-000000000001',
  name: 'Pessoa Teste',
  email: 'device@example.test',
};
const device = {
  id: '00000000-0000-4000-8000-000000000002',
  name: 'Raspberry Bancada 1',
  created_at: '2026-11-06T12:00:00Z',
  can_manage_credentials: true,
};
const secret = 'synthetic_test_credential_not_a_real_secret_123';
const listing = (items = [device]) => ({
  items,
  registration_enabled: true,
  managed_count: items.length,
  max_devices: 5,
  api_base_url: 'https://api.example.test',
});

test.beforeEach(async ({ page }) => {
  // Toda chamada é local/sintética, inclusive recursos opcionais do layout.
  await page.route('**/api/**', (r) =>
    r.fulfill({ status: 404, json: { detail: 'fixture' } }),
  );
  await page.route('**/api/auth/session', (r) =>
    r.fulfill({ json: { user, csrf_token: 'test-csrf' } }),
  );
  await page.route('**/api/inspections/config', (r) =>
    r.fulfill({ json: { enabled: true, ownership: 'inspection-session' } }),
  );
  await page.route('**/api/inspections/current', (r) =>
    r.fulfill({ json: [] }),
  );
  await page.route('**/api/inspections/devices', (r) =>
    r.fulfill({ json: [device] }),
  );
  await page.route('**/api/samples/config', (r) =>
    r.fulfill({
      json: { enabled: true, processing: 'device', max_upload_bytes: 5242880 },
    }),
  );
  await page.route('**/api/samples/executors', (r) =>
    r.fulfill({ json: [device] }),
  );
  await page.route('**/api/samples?*', (r) =>
    r.fulfill({ json: { items: [], total: 0 } }),
  );
  await page.route('**/api/devices', (r) => r.fulfill({ json: listing() }));
});

test('cadastro vazio envia CSRF e mostra segredo uma única vez sem persistência', async ({
  page,
  context,
}) => {
  let created = false;
  let calls = 0;
  await page.route('**/api/devices', async (r) => {
    if (r.request().method() === 'GET')
      return r.fulfill({ json: listing(created ? [device] : []) });
    calls++;
    const body = r.request().postDataJSON();
    expect(Object.keys(body).sort()).toEqual(['name', 'request_id']);
    expect(body.name).toBe(device.name);
    expect(body.request_id).toMatch(/^[a-f0-9-]{36}$/);
    expect(r.request().headers()['x-csrf-token']).toBe('test-csrf');
    expect(r.request().headers().authorization).toBeUndefined();
    created = true;
    return r.fulfill({
      status: 201,
      json: { device, credential: secret, replayed: false },
    });
  });
  await page.goto('/dashboard/dispositivos');
  await expect(
    page.getByText(/Você ainda não tem equipamentos vinculados/),
  ).toBeVisible();
  await page.getByLabel('Nome do equipamento').fill(`  ${device.name}  `);
  await page
    .getByRole('button', { name: 'Cadastrar equipamento', exact: true })
    .click();
  const field = page.getByLabel('Credencial de conexão', { exact: true });
  await expect(field).toHaveValue(secret);
  await expect(field).toHaveAttribute('type', 'password');
  await expect(
    page.getByLabel('ID do equipamento', { exact: true }),
  ).toHaveValue(device.id);
  await expect(page.getByLabel('URL da Web API')).toHaveValue(
    'https://api.example.test',
  );
  await expect(
    page.getByRole('heading', { name: 'Dados para conectar o Raspberry' }),
  ).toBeVisible();
  await page
    .getByRole('button', { name: 'Mostrar credencial', exact: true })
    .click();
  await expect(field).toHaveAttribute('type', 'text');
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page
    .getByRole('button', { name: 'Copiar configuração do Raspberry' })
    .click();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(
    `DEVICE_ID=${device.id}\nWEB_API_BASE_URL=https://api.example.test\nDEVICE_INGEST_CREDENTIAL=${secret}\n`,
  );
  expect(
    await page.evaluate(() => [
      Object.keys(localStorage),
      Object.keys(sessionStorage),
    ]),
  ).toEqual([[], []]);
  expect(page.url()).not.toContain(secret);
  await page.getByRole('button', { name: 'Já guardei a credencial' }).click();
  await expect(field).toHaveCount(0);
  await page.reload();
  await expect(
    page.getByRole('heading', { name: device.name, exact: true }),
  ).toBeVisible();
  await expect(field).toHaveCount(0);
  expect(calls).toBe(1);
  await expect(
    page.getByRole('region', { name: 'Como conectar seu Raspberry' }),
  ).toBeVisible();
});

test('resposta perdida repete o mesmo comando e não duplica cadastro nem reenvia segredo', async ({
  page,
}) => {
  const commands: unknown[] = [];
  await page.route('**/api/devices', (r) => {
    if (r.request().method() === 'GET')
      return r.fulfill({ json: listing(commands.length ? [device] : []) });
    commands.push(r.request().postDataJSON());
    return commands.length === 1
      ? r.abort('failed')
      : r.fulfill({ json: { device, credential: null, replayed: true } });
  });
  await page.goto('/dashboard/dispositivos');
  await page.getByLabel('Nome do equipamento').fill(device.name);
  await page
    .getByRole('button', { name: 'Cadastrar equipamento', exact: true })
    .click();
  await expect(
    page.getByRole('button', { name: 'Cadastrar equipamento', exact: true }),
  ).toBeDisabled();
  await page.getByRole('button', { name: 'Tentar confirmar operação' }).click();
  await expect(page.getByText(/o segredo não é reenviado/)).toBeVisible();
  expect(commands).toHaveLength(2);
  expect(commands[0]).toEqual(commands[1]);
  await expect(page.getByLabel('Credencial de conexão')).toHaveCount(0);
});

test('rotação exige confirmação e não aparece em equipamento compartilhado', async ({
  page,
}) => {
  const shared = {
    ...device,
    id: '00000000-0000-4000-8000-000000000003',
    name: 'Compartilhado',
    can_manage_credentials: false,
  };
  await page.route('**/api/devices', (r) =>
    r.fulfill({ json: listing([device, shared]) }),
  );
  let calls = 0;
  await page.route(`**/api/devices/${device.id}/credentials`, (r) => {
    calls++;
    expect(r.request().headers()['x-csrf-token']).toBe('test-csrf');
    expect(Object.keys(r.request().postDataJSON())).toEqual(['request_id']);
    return r.fulfill({ json: { device, credential: secret, replayed: false } });
  });
  await page.goto('/dashboard/dispositivos');
  const rotate = page.getByRole('button', {
    name: 'Gerar nova credencial',
    exact: true,
  });
  await expect(rotate).toHaveCount(1);
  await rotate.click();
  await expect(page.getByRole('dialog')).toContainText('será revogada');
  await page.getByRole('button', { name: 'Cancelar', exact: true }).click();
  expect(calls).toBe(0);
  await rotate.click();
  await page.getByRole('button', { name: 'Confirmar nova credencial' }).click();
  await expect(page.getByLabel('Credencial de conexão')).toHaveValue(secret);
  expect(calls).toBe(1);
});

for (const state of [
  'migration',
  'limit',
  'unpublished',
  'incompatible',
] as const) {
  test(`estado ${state} impede cadastro sem afirmar lista vazia`, async ({
    page,
  }) => {
    await page.route('**/api/devices', (r) =>
      r.fulfill({
        status: state === 'unpublished' ? 404 : 200,
        json:
          state === 'incompatible'
            ? { items: 'invalid' }
            : {
                ...listing(),
                registration_enabled: state !== 'migration',
                managed_count: state === 'limit' ? 5 : 1,
              },
      }),
    );
    await page.goto('/dashboard/dispositivos');
    const message = {
      migration: /migration 006/,
      limit: /O limite de equipamentos/,
      unpublished: /ainda não foi publicado/,
      incompatible: /resposta da API é incompatível/,
    }[state];
    await expect(page.getByText(message)).toBeVisible();
    await expect(
      page.getByText(/Você ainda não tem equipamentos vinculados/),
    ).toHaveCount(0);
    const submit = page.getByRole('button', {
      name: 'Cadastrar equipamento',
      exact: true,
    });
    if (state === 'migration' || state === 'limit')
      await expect(submit).toBeDisabled();
    else await expect(submit).toHaveCount(0);
  });
}

for (const count of [0, 1, 2]) {
  test(`inspeções e amostras selecionam equipamento com ${count} autorizados`, async ({
    page,
  }) => {
    const items = [
      device,
      {
        ...device,
        id: '00000000-0000-4000-8000-000000000003',
        name: 'Segundo Raspberry',
      },
    ].slice(0, count);
    await page.route('**/api/inspections/devices', (r) =>
      r.fulfill({ json: items }),
    );
    await page.route('**/api/samples/executors', (r) =>
      r.fulfill({ json: items }),
    );
    for (const path of ['/dashboard/inspecoes', '/dashboard/amostras']) {
      await page.goto(path);
      if (!count) {
        await expect(
          page
            .locator('main')
            .getByRole('link', { name: 'Equipamentos', exact: true }),
        ).toBeVisible();
        continue;
      }
      const select = page.getByRole('combobox', {
        name: 'Equipamento autorizado',
      });
      await expect(select).toBeVisible();
      if (count === 1) await expect(select).toContainText(device.name);
      else {
        await expect(select).not.toContainText(device.name);
        await select.click();
        await page
          .getByRole('option', { name: 'Segundo Raspberry', exact: true })
          .click();
        await expect(select).toContainText('Segundo Raspberry');
      }
    }
  });
}

test('equipamentos móvel sem overflow e sem violações de acessibilidade', async ({
  page,
}) => {
  for (const width of [320, 375, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/dashboard/dispositivos');
    const guide = page.getByRole('region', {
      name: 'Como conectar seu Raspberry',
    });
    await expect(guide.getByRole('listitem')).toHaveCount(4);
    await expect(guide).toContainText('Nas versões sem esse assistente');
    const help = guide.locator('summary');
    await help.focus();
    await page.keyboard.press('Enter');
    await expect(
      guide.getByText(/Sem internet ou API indisponível:/),
    ).toBeVisible();
    await expect(guide).toContainText(
      'Não é necessário cadastrar outro equipamento',
    );
    await expect(guide).toContainText('O ID e o histórico serão preservados.');
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  }
});

test('logout e troca de conta descartam credencial e lista da conta anterior', async ({
  page,
}) => {
  let active: typeof user | null = user;
  const second = {
    ...user,
    id: '00000000-0000-4000-8000-000000000004',
    email: 'second@example.test',
  };
  await page.route('**/api/auth/session', (r) =>
    r.fulfill({
      status: active ? 200 : 401,
      json: active
        ? { user: active, csrf_token: 'test-csrf' }
        : { detail: 'Sem sessão' },
    }),
  );
  await page.route('**/api/auth/logout', (r) => {
    active = null;
    return r.fulfill({ status: 204 });
  });
  await page.route('**/api/auth/login', (r) => {
    active = second;
    return r.fulfill({ json: { user: second, csrf_token: 'new-csrf' } });
  });
  await page.route('**/api/devices', (r) =>
    r.fulfill({
      json:
        r.request().method() === 'GET'
          ? listing(active?.id === user.id ? [device] : [])
          : { device, credential: secret, replayed: false },
    }),
  );
  await page.goto('/dashboard/dispositivos');
  await page.getByLabel('Nome do equipamento').fill('Novo Raspberry');
  await page
    .getByRole('button', { name: 'Cadastrar equipamento', exact: true })
    .click();
  await expect(page.getByLabel('Credencial de conexão')).toHaveValue(secret);
  await page
    .getByRole('button', { name: 'Sair da conta', exact: true })
    .click();
  await expect(page).toHaveURL(/\/login/);
  await page.getByLabel('E-mail', { exact: false }).fill(second.email);
  await page.getByLabel(/^Senha/).fill('uma frase bastante longa');
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await page.getByRole('link', { name: 'Equipamentos', exact: true }).click();
  await expect(
    page.getByText(/Você ainda não tem equipamentos vinculados/),
  ).toBeVisible();
  await expect(page.getByLabel('Credencial de conexão')).toHaveCount(0);
  await expect(
    page.getByRole('heading', { name: device.name, exact: true }),
  ).toHaveCount(0);
});
