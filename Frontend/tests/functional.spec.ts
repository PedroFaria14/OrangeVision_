import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { comparisonFixture } from './fixtures/comparison';

const user = {
  id: '00000000-0000-4000-8000-000000000001',
  name: 'Pessoa Teste',
  email: 'person@example.com',
};
const device = '00000000-0000-4000-8000-000000000003';
const analysis = {
  id: '00000000-0000-4000-8000-000000000002',
  device_id: device,
  timestamp: '2026-10-20T12:00:00Z',
  classification: 'APROVADA',
  calibration_version: 'test-only',
  lot: null,
  image_url: null,
  synced_at: null,
  metrics: {
    orange_color_ratio: 0.75,
    abnormal_region_ratio: null,
    circularity: 0.85,
    asymmetry: 0.02,
    visual_score: 82,
  },
};
const png = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a1ioAAAAASUVORK5CYII=',
  'base64',
);
const sample = {
  id: analysis.id,
  filename: 'sample-test.png',
  width: 80,
  height: 60,
  state: 'received',
  device_id: null,
  metrics: null,
  classification: null,
  reason: null,
  calibration_version: null,
  algorithm_version: null,
  image_url: `/api/samples/${analysis.id}/image`,
  mask_url: null,
  created_at: analysis.timestamp,
  updated_at: analysis.timestamp,
  started_at: null,
  finished_at: null,
  claim_expires_at: null,
};

test.beforeEach(async ({ page }) => {
  await page.clock.install({ time: new Date('2026-10-20T15:00:00Z') });
  await page.route('**/api/auth/session', (r) =>
    r.fulfill({ json: { user, csrf_token: 'test-only-csrf' } }),
  );
  await page.route('**/api/inspections/config', (r) =>
    r.fulfill({ json: { enabled: false, ownership: 'device-access' } }),
  );
  await page.route('**/api/metrics/comparison?*', (r) =>
    r.fulfill({ json: comparisonFixture(r.request().url()) }),
  );
  await page.route('**/api/metrics/timeseries?*', (r) =>
    r.fulfill({
      json: {
        items: [
          {
            start: '2026-10-20T03:00:00Z',
            approved: 1,
            attention: 0,
            review: 0,
          },
        ],
        coverage: 'observed-only',
        granularity: 'day',
        timezone: 'America/Sao_Paulo',
        as_of: analysis.timestamp,
      },
    }),
  );
  await page.route('**/api/analyses?*', (r) =>
    r.fulfill({
      json: { items: [analysis], total: 1, as_of: analysis.timestamp },
    }),
  );
  await page.route(`**/api/analyses/${analysis.id}`, (r) =>
    r.fulfill({ json: analysis }),
  );
  await page.route('**/api/samples/config', (r) =>
    r.fulfill({
      json: { enabled: true, processing: 'device', max_upload_bytes: 5242880 },
    }),
  );
  await page.route('**/api/samples/executors', (r) =>
    r.fulfill({
      json: [
        {
          id: device,
          name: 'Equipamento de teste',
          executor_recent: false,
          last_seen_at: null,
        },
      ],
    }),
  );
  await page.route('**/api/samples?*', (r) =>
    r.fulfill({ json: { items: [], total: 0 } }),
  );
  await page.route('**/api/samples/*/image', (r) =>
    r.fulfill({ body: png, contentType: 'image/png' }),
  );
  await page.route('**/api/samples/*/mask*', (r) =>
    r.fulfill({ body: png, contentType: 'image/png' }),
  );
});

test('páginas públicas permanecem sem personalização', async ({ page }) => {
  for (const path of [
    '/',
    '/projeto',
    '/planejamento',
    '/desenvolvimento',
    '/resultados',
    '/equipe',
    '/referencias',
  ]) {
    await page.goto(path);
    await expect(page.locator('h1')).toHaveCount(1);
    await expect(page.locator('h1')).toBeVisible();
    await expect(
      page.locator('style,link[rel="stylesheet"],[style]'),
    ).toHaveCount(0);
  }
});

test('personalização cobre somente as rotas privadas e não vaza ao site em navegação SPA', async ({
  page,
}) => {
  for (const path of [
    '/dashboard',
    '/dashboard/historico',
    '/dashboard/perfil',
    '/dashboard/inspecoes',
    '/dashboard/amostras',
  ]) {
    await page.goto(path);
    await expect(page.locator('[data-dashboard-shell]')).toHaveCSS(
      'background-color',
      'rgb(244, 246, 248)',
    );
    await expect(page.locator('h1')).toHaveCount(1);
    await expect(
      page.getByRole('navigation', { name: 'Navegação da área logada' }),
    ).toBeVisible();
  }
  await page.getByRole('link', { name: 'Voltar ao site' }).click();
  await expect(page).toHaveURL('/');
  await expect(page.locator('[data-dashboard-shell]')).toHaveCount(0);
  expect(
    await page.locator('h1').evaluate((el) => getComputedStyle(el).fontFamily),
  ).toMatch(/Times|serif/i);
  await page.getByRole('link', { name: 'Dashboard', exact: true }).click();
  await expect(page.locator('[data-dashboard-shell]')).toBeVisible();
});

for (const width of [320, 390, 768, 1440]) {
  test(`área logada responsiva e acessível em ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/dashboard');
    await expect(
      page.getByRole('table', { name: 'Comparação entre períodos' }),
    ).toBeVisible();
    await expect(page.locator('[data-dashboard-shell]')).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
    if (width < 761) {
      const toggle = page.getByRole('button', {
        name: 'Abrir menu',
        exact: true,
      });
      await toggle.click();
      await expect(
        page.getByRole('navigation', { name: 'Navegação da área logada' }),
      ).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(toggle).toBeFocused();
      await toggle.click();
      await page.getByRole('link', { name: 'Histórico', exact: true }).click();
      await expect(
        page.getByRole('navigation', { name: 'Navegação da área logada' }),
      ).toBeHidden();
      await expect(page.getByRole('heading', { level: 1 })).toHaveText(
        'Histórico de análises',
      );
      await page.goto('/dashboard');
      await expect(
        page.getByRole('table', { name: 'Comparação entre períodos' }),
      ).toBeVisible();
    }
    await page.screenshot({
      path: info.outputPath(`dashboard-${width}.png`),
      fullPage: true,
    });
  });
}

test('login e cadastro básicos dão acesso ao dashboard personalizado e logout volta ao HTML básico', async ({
  page,
}) => {
  await page.route('**/api/auth/session', (r) =>
    r.fulfill({ status: 401, json: { detail: 'Sessão ausente' } }),
  );
  await page.route('**/api/auth/login', (r) =>
    r.fulfill({ json: { user, csrf_token: 'test-only-csrf' } }),
  );
  await page.route('**/api/auth/logout', (r) => r.fulfill({ status: 204 }));
  for (const path of ['/registrar', '/login']) {
    await page.goto(path);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect(
      page.locator('style,link[rel="stylesheet"],[style]'),
    ).toHaveCount(0);
  }
  await page.getByLabel('E-mail', { exact: true }).fill(user.email);
  await page
    .getByLabel('Senha', { exact: true })
    .fill('valid-test-password-123');
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await expect(page).toHaveURL('/dashboard');
  await expect(page.locator('[data-dashboard-shell]')).toHaveCSS(
    'background-color',
    'rgb(244, 246, 248)',
  );
  await page.getByRole('button', { name: 'Sair da conta' }).click();
  await expect(page).toHaveURL(/\/login/);
  await expect(page.locator('[data-dashboard-shell]')).toHaveCount(0);
  expect(
    await page.locator('h1').evaluate((el) => getComputedStyle(el).fontFamily),
  ).toMatch(/Times|serif/i);
});

test('cadastro mantém confirmação e envia somente contrato válido', async ({
  page,
}) => {
  await page.route('**/api/auth/session', (r) =>
    r.fulfill({ status: 401, json: { detail: 'Sessão ausente' } }),
  );
  let calls = 0;
  await page.route('**/api/auth/register', (r) => {
    calls++;
    expect(r.request().postDataJSON()).toEqual({
      name: 'Pessoa Nova',
      email: 'new@example.com',
      password: 'valid-test-password-123',
    });
    return r.fulfill({ status: 201, json: {} });
  });
  await page.goto('/registrar');
  await page.getByLabel('Nome', { exact: true }).fill('Pessoa Nova');
  await page.getByLabel('E-mail', { exact: true }).fill('new@example.com');
  await page
    .getByLabel('Senha', { exact: true })
    .fill('valid-test-password-123');
  await page
    .getByLabel('Confirmar senha', { exact: true })
    .fill('different-password');
  await page.getByRole('button', { name: 'Criar conta', exact: true }).click();
  await expect(page.getByText('As senhas não coincidem.')).toBeVisible();
  expect(calls).toBe(0);
  await page
    .getByLabel('Confirmar senha', { exact: true })
    .fill('valid-test-password-123');
  await page.getByRole('button', { name: 'Criar conta', exact: true }).click();
  await expect(
    page.getByText('Conta criada. Entre para continuar.'),
  ).toBeVisible();
  expect(calls).toBe(1);
});

test('login inválido mostra erro e apaga a senha', async ({ page }) => {
  await page.route('**/api/auth/session', (r) =>
    r.fulfill({ status: 401, json: { detail: 'Sessão ausente' } }),
  );
  await page.route('**/api/auth/login', (r) =>
    r.fulfill({ status: 401, json: { detail: 'Inválido' } }),
  );
  await page.goto('/login');
  await page.getByLabel('E-mail', { exact: true }).fill('user@example.com');
  await page
    .getByLabel('Senha', { exact: true })
    .fill('valid-test-password-123');
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await expect(page.getByText('E-mail ou senha inválidos.')).toBeVisible();
  await expect(page.getByLabel('Senha', { exact: true })).toHaveValue('');
});

test('rota privada redireciona ao login com destino interno', async ({
  page,
}) => {
  await page.route('**/api/auth/session', (r) =>
    r.fulfill({ status: 401, json: { detail: 'Sessão ausente' } }),
  );
  await page.goto('/dashboard/amostras');
  await expect(page).toHaveURL(/\/login\?next=/);
  await expect(
    page.getByRole('heading', { name: 'Entrar', exact: true }),
  ).toBeVisible();
});

test('dashboard preserva comparações, dados diários, detalhe e ausência de imagem fictícia', async ({
  page,
}) => {
  await page.goto('/dashboard');
  await expect(
    page.getByRole('table', { name: 'Comparação entre períodos' }),
  ).toBeVisible();
  await expect(
    page.getByRole('table', { name: 'Evolução diária das análises' }),
  ).toBeVisible();
  await page.getByRole('link', { name: /Ver detalhes da análise/ }).click();
  await expect(
    page.getByRole('heading', { name: 'Detalhe da análise' }),
  ).toBeVisible();
  await expect(page.locator('main')).toContainText(analysis.id);
  await expect(page.locator('main img')).toHaveCount(0);
  await expect(page.locator('main')).toContainText(
    'Justificativa não disponibilizada.',
  );
});

test('zero não inventa taxa medida e histórico vazio não mostra paginação', async ({
  page,
}) => {
  await page.route('**/api/metrics/comparison?*', (r) =>
    r.fulfill({
      json: comparisonFixture(
        r.request().url(),
        { approved: 0, attention: 0, review: 0 },
        { approved: 0, attention: 0, review: 0 },
      ),
    }),
  );
  await page.route('**/api/analyses?*', (r) =>
    r.fulfill({ json: { items: [], total: 0, as_of: analysis.timestamp } }),
  );
  await page.goto('/dashboard');
  await expect(
    page.getByText(
      'Ainda não há dados para comparar nos dois períodos selecionados.',
    ),
  ).toBeVisible();
  await expect(
    page
      .getByText('Taxa de aprovação', { exact: true })
      .locator('xpath=following-sibling::dd[1]'),
  ).toHaveText('—');
  await page.goto('/dashboard/historico');
  await expect(
    page.getByText(/Nenhuma análise neste período ou página/),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Próxima', exact: true }),
  ).toHaveCount(0);
});

test('filtro invertido não consulta e atalhos mantêm classe e URL', async ({
  page,
}) => {
  let calls = 0;
  await page.route('**/api/analyses?*', (r) => {
    calls++;
    return r.fulfill({
      json: { items: [analysis], total: 1, as_of: analysis.timestamp },
    });
  });
  await page.goto('/dashboard/historico?classification=REVISAR');
  await expect(
    page.getByRole('table', { name: 'Histórico de análises' }),
  ).toBeVisible();
  const before = calls;
  await page.getByLabel('Data inicial', { exact: true }).fill('2026-10-20');
  await page.getByLabel('Data final (inclusive)').fill('2026-10-01');
  await page.getByRole('button', { name: 'Aplicar filtros' }).click();
  await expect(
    page.getByText('Escolha um período válido de até 366 dias.'),
  ).toBeVisible();
  expect(calls).toBe(before);
  await page.getByRole('button', { name: '7 dias', exact: true }).click();
  expect(new URL(page.url()).searchParams.get('classification')).toBe(
    'REVISAR',
  );
  const params = new URL(page.url()).searchParams;
  expect(
    Date.parse(params.get('end')!) - Date.parse(params.get('start')!),
  ).toBe(7 * 86400000);
});

test('erro da API não aparece como histórico vazio', async ({ page }) => {
  await page.route('**/api/analyses?*', (r) =>
    r.fulfill({ status: 403, json: { detail: 'Sem acesso' } }),
  );
  await page.goto('/dashboard/historico');
  await expect(
    page.getByText(/Não foi possível consultar os dados/),
  ).toBeVisible();
  await expect(
    page.getByText(/Nenhuma análise neste período ou página/),
  ).toHaveCount(0);
});

test('expiração 401 retira o conteúdo privado', async ({ page }) => {
  await page.goto('/dashboard/historico');
  await expect(
    page.getByRole('table', { name: 'Histórico de análises' }),
  ).toBeVisible();
  await page.route('**/api/analyses?*', (r) =>
    r.fulfill({ status: 401, json: { detail: 'Expirada' } }),
  );
  await page.getByRole('button', { name: 'Atualizar consultas' }).click();
  await expect(page).toHaveURL(/\/login/);
  await expect(
    page.getByRole('table', { name: 'Histórico de análises' }),
  ).toHaveCount(0);
});

test('logout falho oculta dados sem afirmar revogação', async ({ page }) => {
  await page.route('**/api/auth/logout', (r) =>
    r.fulfill({ status: 503, json: { detail: 'indisponível' } }),
  );
  await page.goto('/dashboard');
  await expect(
    page.getByRole('table', { name: 'Histórico de análises' }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Sair da conta' }).click();
  await expect(
    page.getByText(/não foi possível confirmar o encerramento/),
  ).toBeVisible();
  await expect(
    page.getByRole('table', { name: 'Histórico de análises' }),
  ).toHaveCount(0);
});

test('pareamento usa nonce, código temporário e CSRF, e conserva estados', async ({
  page,
}) => {
  const now = '2026-10-20T15:00:00Z';
  let session: Record<string, unknown> | null = null;
  await page.route('**/api/inspections/config', (r) =>
    r.fulfill({ json: { enabled: true, ownership: 'inspection-session' } }),
  );
  await page.route('**/api/inspections/devices', (r) =>
    r.fulfill({ json: [{ id: device, name: 'PC de testes' }] }),
  );
  await page.route('**/api/inspections/current', (r) =>
    r.fulfill({ json: session ? [session] : [] }),
  );
  await page.route('**/api/inspections', (r) => {
    const body = r.request().postDataJSON();
    expect(body.device_id).toBe(device);
    expect(body.pairing_code).toMatch(/^[0-9a-f]{32}$/);
    expect(body.user_id).toBeUndefined();
    expect(r.request().headers()['x-csrf-token']).toBe('test-only-csrf');
    session = {
      id: analysis.id,
      user_id: user.id,
      device_id: device,
      operator_name: user.name,
      state: 'pending',
      created_at: now,
      pairing_expires_at: '2026-10-20T15:05:00Z',
      started_at: null,
      authorization_expires_at: null,
      closed_at: null,
      observed_at: now,
    };
    return r.fulfill({ status: 201, json: session });
  });
  await page.goto('/dashboard/inspecoes');
  await expect(
    page.getByRole('button', { name: 'Iniciar inspeção' }),
  ).toBeDisabled();
  await page.getByLabel('Equipamento autorizado').selectOption(device);
  await page.getByRole('button', { name: 'Iniciar inspeção' }).click();
  await expect(
    page.getByLabel('Código temporário de pareamento'),
  ).toBeVisible();
  await expect(page.getByText('Estado: Aguardando pareamento')).toBeVisible();
});

test('sem equipamento confirmado mostra orientação correta', async ({
  page,
}) => {
  await page.route('**/api/inspections/config', (r) =>
    r.fulfill({ json: { enabled: true, ownership: 'inspection-session' } }),
  );
  await page.route('**/api/inspections/devices', (r) =>
    r.fulfill({ json: [] }),
  );
  await page.route('**/api/inspections/current', (r) =>
    r.fulfill({ json: [] }),
  );
  await page.goto('/dashboard/inspecoes');
  await expect(page.getByText(/Nenhum equipamento foi liberado/)).toBeVisible();
});

test('amostras enviam arquivo com CSRF e mostram fila, detecção e máscara sem categoria inventada', async ({
  page,
}, info) => {
  let current: Record<string, unknown> | null = null;
  let nonce = '';
  await page.route('**/api/samples?*', (r) => {
    if (r.request().method() === 'POST') {
      expect(r.request().headers()['x-csrf-token']).toBe('test-only-csrf');
      expect(r.request().headers()['content-type']).toBe(
        'application/octet-stream',
      );
      const id = new URL(r.request().url()).searchParams.get('request_id')!;
      if (nonce) expect(id).toBe(nonce);
      nonce = id;
      current = { ...sample };
      return r.fulfill({ status: 201, json: current });
    }
    return r.fulfill({
      json: { items: current ? [current] : [], total: current ? 1 : 0 },
    });
  });
  await page.route(`**/api/samples/${analysis.id}/queue`, (r) => {
    expect(r.request().postDataJSON()).toEqual({ device_id: device });
    current = { ...sample, state: 'queued', device_id: device };
    return r.fulfill({ json: current });
  });
  await page.goto('/dashboard/amostras');
  await page.getByLabel('Selecionar imagem de amostra').setInputFiles({
    name: 'sample-test.png',
    mimeType: 'image/png',
    buffer: png,
  });
  await page
    .getByRole('button', { name: 'Enviar imagem', exact: true })
    .click();
  await expect(
    page.getByText('Imagem recebida', { exact: true }),
  ).toBeVisible();
  await page.getByLabel('Equipamento autorizado').selectOption(device);
  await page.getByRole('button', { name: 'Enviar para análise local' }).click();
  await expect(
    page.getByText('Aguardando análise', { exact: true }),
  ).toBeVisible();
  current = {
    ...sample,
    state: 'awaiting_review',
    mask_url: `/api/samples/${analysis.id}/mask`,
    detection: {
      status: 'detected',
      label: 'orange',
      score: 0.9,
      box: [10, 10, 40, 30],
      count: 1,
      model: 'synthetic-test-only',
      inference_ms: 20,
    },
  };
  await page.getByRole('button', { name: 'Atualizar amostras' }).click();
  await expect(page.getByText('Modelo sugere laranja')).toBeVisible();
  await expect(
    page.getByText('Ainda não validada', { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole('img', { name: 'Máscara experimental: sample-test.png' }),
  ).toBeVisible();
  await expect(page.locator('[data-dashboard-shell]')).toBeVisible();
  await page.screenshot({
    path: info.outputPath('amostras-personalizadas.png'),
    fullPage: true,
  });
});

test('sem migration ou erro da galeria não inventa ausência de fotos', async ({
  page,
}) => {
  await page.route('**/api/samples/config', (r) =>
    r.fulfill({
      json: { enabled: false, processing: 'device', max_upload_bytes: 5242880 },
    }),
  );
  await page.goto('/dashboard/amostras');
  await expect(page.getByText(/A galeria ainda não foi ativada/)).toBeVisible();
  await expect(page.getByText(/Você ainda não enviou amostras/)).toHaveCount(0);
});

test('páginas públicas e área logada mantêm acessibilidade automática', async ({
  page,
}) => {
  for (const path of [
    '/projeto',
    '/dashboard',
    '/dashboard/perfil',
    '/dashboard/amostras',
  ]) {
    await page.goto(path);
    await expect(page.locator('h1')).toBeVisible();
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  }
});
