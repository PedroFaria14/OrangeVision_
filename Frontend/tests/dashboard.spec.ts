import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { comparisonFixture } from './fixtures/comparison';

const user = {
  id: '00000000-0000-4000-8000-000000000001',
  name: 'Pessoa Teste',
  email: 'person@example.com',
};
const analysis = {
  id: '00000000-0000-4000-8000-000000000002',
  device_id: '00000000-0000-4000-8000-000000000003',
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

function analysisAt(index: number) {
  return {
    ...analysis,
    id: `00000000-0000-4000-8000-${String(index + 100).padStart(12, '0')}`,
  };
}

test('cards e tooltip usam percentuais do recorte completo, não das linhas visíveis', async ({
  page,
}) => {
  await page.route('**/api/metrics/comparison?*', (route) =>
    route.fulfill({
      json: comparisonFixture(route.request().url(), {
        approved: 30,
        attention: 10,
        review: 10,
      }),
    }),
  );
  await page.route('**/api/analyses?*', (route) =>
    route.fulfill({
      json: {
        items: Array.from({ length: 20 }, (_, index) => analysisAt(index)),
        total: 50,
        as_of: analysis.timestamp,
      },
    }),
  );
  await page.goto('/dashboard');
  for (const [label, share] of [
    ['Aprovadas', '60%'],
    ['Atenção', '20%'],
    ['Revisar', '20%'],
  ]) {
    await expect(
      page.getByRole('region', { name: `Indicador: ${label}`, exact: true }),
    ).toContainText(`${share} do total`);
  }
  await expect(
    page.getByText('Exibindo 1–5 de 50 análises.', { exact: true }),
  ).toBeVisible();
  const distribution = page.getByRole('table', {
    name: 'Distribuição por classificação',
    exact: true,
  });
  await expect(
    distribution.getByRole('rowheader', { name: 'Aprovada', exact: true }),
  ).toBeVisible();
  const chart = page.locator('section').filter({
    has: page.getByRole('heading', {
      name: 'Distribuição por classificação',
      exact: true,
    }),
  });
  await chart.locator('.recharts-bar-rectangle').first().hover();
  await expect(chart.getByText('30 · 60%', { exact: true })).toBeVisible();
  const distributionRegion = page.getByRole('region', {
    name: 'Distribuição por classificação com rolagem horizontal',
  });
  await distributionRegion.focus();
  await expect(distributionRegion).toBeFocused();
  await page.getByText('Consultar dados em tabela', { exact: true }).click();
  const daily = page.getByRole('region', {
    name: 'Evolução diária com rolagem',
  });
  await daily.focus();
  await expect(daily).toBeFocused();
  await expect(daily.getByRole('rowheader')).toHaveCount(1);
});

test('histórico mostra o intervalo real e mantém paginação acessível na última página', async ({
  page,
}) => {
  const items = Array.from({ length: 25 }, (_, index) => analysisAt(index));
  await page.route('**/api/analyses?*', (route) => {
    const offset = Number(
      new URL(route.request().url()).searchParams.get('offset'),
    );
    return route.fulfill({
      json: {
        items: items.slice(offset, offset + 20),
        total: 25,
        as_of: analysis.timestamp,
      },
    });
  });
  await page.goto('/dashboard/historico');
  await expect(
    page.getByText('Exibindo 1–20 de 25 análises.', { exact: true }),
  ).toBeVisible();
  const pager = page.getByRole('navigation', {
    name: 'Paginação do histórico',
  });
  await pager.getByRole('button', { name: 'Próxima', exact: true }).click();
  await expect(
    page.getByText('Exibindo 21–25 de 25 análises.', { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('table', { name: 'Histórico de análises' }).getByRole('row'),
  ).toHaveCount(6);
  await expect(
    pager.getByRole('button', { name: 'Próxima', exact: true }),
  ).toBeDisabled();
  await pager.getByRole('button', { name: 'Anterior', exact: true }).click();
  await expect(
    page.getByText('Exibindo 1–20 de 25 análises.', { exact: true }),
  ).toBeVisible();
});

test('detalhe explica nulos e organiza justificativa e sessão sem inventar score', async ({
  page,
}) => {
  const sessionId = '00000000-0000-4000-8000-000000000005';
  await page.setViewportSize({ width: 320, height: 844 });
  await page.route(`**/api/analyses/${analysis.id}`, (route) =>
    route.fulfill({
      json: {
        ...analysis,
        inspection_session_id: sessionId,
        metrics: { ...analysis.metrics, visual_score: null },
        classification_reason: 'Inspeção experimental rastreável.',
      },
    }),
  );
  await page.goto(`/dashboard/analises/${analysis.id}`);
  const metrics = page.getByRole('region', { name: 'Métricas da análise' });
  await expect(metrics).toContainText(
    'O traço (—) indica uma métrica não informada.',
  );
  await expect(
    metrics.getByText('Não informado', { exact: true }),
  ).toBeVisible();
  await expect(metrics.getByRole('progressbar')).toHaveCount(0);
  await expect(
    page.getByRole('region', { name: 'Rastreabilidade' }),
  ).toContainText(sessionId);
  await expect(
    page.getByRole('region', { name: 'Justificativa da classificação' }),
  ).toContainText(
    'Justificativa registrada: Inspeção experimental rastreável.',
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test('atalhos respeitam Brasília na virada do ano e preservam classe e navegação', async ({
  page,
}) => {
  await page.clock.setSystemTime(new Date('2027-01-01T02:00:00Z'));
  await page.goto('/dashboard/historico?classification=REVISAR');
  await page.getByRole('button', { name: 'Hoje', exact: true }).click();
  let url = new URL(page.url());
  expect(new Date(url.searchParams.get('start')!).toISOString()).toBe(
    '2026-12-31T03:00:00.000Z',
  );
  expect(new Date(url.searchParams.get('end')!).toISOString()).toBe(
    '2027-01-01T03:00:00.000Z',
  );
  expect(url.searchParams.get('classification')).toBe('REVISAR');
  await page.getByRole('button', { name: '7 dias', exact: true }).click();
  url = new URL(page.url());
  expect(new Date(url.searchParams.get('start')!).toISOString()).toBe(
    '2026-12-25T03:00:00.000Z',
  );
  await page.goBack();
  await expect(page.getByLabel('Data inicial')).toHaveValue('2026-12-31');
});

test('histórico vazio não mostra paginação e permite limpar filtros', async ({
  page,
}) => {
  await page.route('**/api/analyses?*', (route) =>
    route.fulfill({ json: { items: [], total: 0, as_of: analysis.timestamp } }),
  );
  await page.goto('/dashboard/historico?classification=REVISAR');
  await expect(page.getByText('0 registros no recorte')).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Próxima', exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole('button', { name: 'Limpar filtros', exact: true })
    .first()
    .click();
  expect(new URL(page.url()).searchParams.get('classification')).toBe('');
});

test('detalhe mostra justificativa sem negar a informação fornecida', async ({
  page,
}) => {
  await page.route(`**/api/analyses/${analysis.id}`, (route) =>
    route.fulfill({
      json: {
        ...analysis,
        classification_reason: 'Critério experimental documentado.',
      },
    }),
  );
  await page.goto(`/dashboard/analises/${analysis.id}`);
  await expect(
    page.getByText(
      'Justificativa registrada: Critério experimental documentado.',
    ),
  ).toBeVisible();
  await expect(
    page.getByText('A justificativa da classificação não foi disponibilizada.'),
  ).toHaveCount(0);
});

test.beforeEach(async ({ page }) => {
  await page.route('**/api/inspections/config', (route) =>
    route.fulfill({ json: { enabled: false, ownership: 'device-access' } }),
  );
  await page.clock.install({ time: new Date('2026-10-20T15:00:00Z') });
  await page.route('**/api/auth/session', (route) =>
    route.fulfill({ json: { user, csrf_token: 'test-only-csrf' } }),
  );
  await page.route('**/api/metrics/comparison?*', (route) =>
    route.fulfill({
      json: comparisonFixture(route.request().url()),
    }),
  );
  await page.route('**/api/metrics/timeseries?*', (route) =>
    route.fulfill({
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
  await page.route('**/api/analyses?*', (route) =>
    route.fulfill({
      json: { items: [analysis], total: 1, as_of: analysis.timestamp },
    }),
  );
  await page.route(`**/api/analyses/${analysis.id}`, (route) =>
    route.fulfill({ json: analysis }),
  );
});

for (const width of [320, 390, 768, 900, 1024, 1440]) {
  test(`dashboard com contrato de teste em ${width}px`, async ({
    page,
  }, testInfo) => {
    const errors: string[] = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/dashboard');
    await expect(
      page.getByRole('heading', { name: 'Distribuição por classificação' }),
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'Evolução das análises' }),
    ).toBeVisible();
    await expect(
      page.getByRole('table', { name: 'Histórico de análises' }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
    expect(errors).toEqual([]);
    if (width === 390 || width === 1440)
      await page.screenshot({
        path: testInfo.outputPath('dashboard-contract-test.png'),
        fullPage: true,
      });
  });
}

test('detalhe preserva métrica nula e não inventa imagem', async ({ page }) => {
  await page.goto(`/dashboard/analises/${analysis.id}`);
  await expect(page.getByText(`ID: ${analysis.id}`)).toBeVisible();
  await expect(
    page.getByText('Regiões anormais', { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('region', { name: 'Justificativa da classificação' }),
  ).toContainText('Justificativa não disponibilizada.');
  await expect(page.getByRole('alert')).toContainText(
    'regiões anormais não constituem diagnóstico de doença.',
  );
  await expect(page.locator('main img')).toHaveCount(0);
});

test('gráficos com valores altos e muitos dias mantêm tabela acessível no mobile', async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route('**/api/metrics/comparison?*', (route) =>
    route.fulfill({
      json: comparisonFixture(
        route.request().url(),
        { approved: 90000, attention: 0, review: 10000 },
        { approved: 0, attention: 0, review: 0 },
      ),
    }),
  );
  await page.route('**/api/metrics/timeseries?*', (route) =>
    route.fulfill({
      json: {
        items: Array.from({ length: 30 }, (_, index) => ({
          start: new Date(Date.UTC(2026, 8, 21 + index, 3)).toISOString(),
          approved: 3000,
          attention: 0,
          review: 300,
        })),
        coverage: 'observed-only',
        granularity: 'day',
        timezone: 'America/Sao_Paulo',
        as_of: analysis.timestamp,
      },
    }),
  );
  await page.goto('/dashboard');
  const distribution = page.getByRole('table', {
    name: 'Distribuição por classificação',
    exact: true,
  });
  await expect(
    distribution.getByRole('row').filter({ hasText: 'Aprovada' }),
  ).toContainText('90000');
  const disclosure = page.getByText('Consultar dados em tabela', {
    exact: true,
  });
  await disclosure.focus();
  await page.keyboard.press('Enter');
  const timeline = page.getByRole('table', {
    name: 'Evolução diária das análises',
  });
  await expect(timeline).toBeVisible();
  await expect(timeline.getByRole('row')).toHaveCount(31);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: testInfo.outputPath('graficos-valores-altos-fixture.png'),
    fullPage: true,
  });
});

test('logout em request pendente não mostra dados privados tardios', async ({
  page,
}) => {
  let authenticated = true;
  await page.route('**/api/auth/session', (route) =>
    route.fulfill({
      status: authenticated ? 200 : 401,
      json: authenticated
        ? { user, csrf_token: 'test-only-csrf' }
        : { detail: 'Expirada' },
    }),
  );
  await page.route('**/api/auth/logout', (route) => {
    expect(route.request().headers()['x-csrf-token']).toBe('test-only-csrf');
    authenticated = false;
    return route.fulfill({ status: 204 });
  });
  await page.route('**/api/analyses?*', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 700));
    await route
      .fulfill({
        json: { items: [analysis], total: 1, as_of: analysis.timestamp },
      })
      .catch(() => {});
  });
  await page.goto('/dashboard');
  await page
    .getByRole('button', { name: 'Sair da conta', exact: true })
    .click();
  await expect(page).toHaveURL(/\/login/);
  await expect(
    page.getByText(analysis.id.slice(0, 8), { exact: true }),
  ).toHaveCount(0);
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([]);
});

test('URL com data inválida é tratada sem quebrar a interface', async ({
  page,
}) => {
  await page.goto('/dashboard?start=invalida&end=outra');
  await expect(page.getByText(/Período da URL inválido/)).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Bem-vindo, Pessoa!', exact: true }),
  ).toBeVisible();
});

for (const width of [390, 1440]) {
  test(`total zero não vira taxa medida nem NaN em ${width}px`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height: 844 });
    await page.route('**/api/metrics/comparison?*', (route) =>
      route.fulfill({
        json: comparisonFixture(
          route.request().url(),
          { approved: 0, attention: 0, review: 0 },
          { approved: 0, attention: 0, review: 0 },
        ),
      }),
    );
    await page.route('**/api/metrics/timeseries?*', (route) =>
      route.fulfill({
        json: {
          items: [],
          coverage: 'observed-only',
          granularity: 'day',
          timezone: 'America/Sao_Paulo',
          as_of: analysis.timestamp,
        },
      }),
    );
    await page.route('**/api/analyses?*', (route) =>
      route.fulfill({
        json: { items: [], total: 0, as_of: analysis.timestamp },
      }),
    );
    await page.goto('/dashboard');
    await expect(
      page.getByText('Taxa de aprovação', { exact: true }).locator('..'),
    ).toContainText('—');
    await expect(page.getByText(/Nenhuma análise nesta página/)).toBeVisible();
    await expect(page.locator('main')).not.toContainText('NaN');
    await expect(
      page.getByText(
        'Ainda não há dados para comparar nos dois períodos selecionados.',
      ),
    ).toBeVisible();
    await expect(
      page.getByRole('table', { name: 'Comparação entre períodos' }),
    ).toHaveCount(0);
    await expect(
      page.getByRole('table', { name: 'Distribuição por classificação' }),
    ).toHaveCount(0);
    await expect(
      page.getByText('Participação indisponível', { exact: true }),
    ).toHaveCount(3);
    await expect(
      page.getByText(/Fim exclusivo · America\/Sao_Paulo/),
    ).toHaveCount(2);
    await expect(page.getByText(/Comparação calculada em/)).toBeVisible();
    await expect(
      page.getByText(
        'Nenhuma análise neste período. A distribuição aparecerá quando houver registros.',
      ),
    ).toBeVisible();
    await page.screenshot({
      path: testInfo.outputPath('dashboard-vazio-fixture.png'),
      fullPage: true,
    });
  });
}

test('payload incompatível não aparece como vazio e não recebe retry', async ({
  page,
}) => {
  let calls = 0;
  await page.route('**/api/metrics/comparison?*', (route) => {
    calls++;
    return route.fulfill({ json: { total: 'inválido' } });
  });
  await page.goto('/dashboard');
  await expect(
    page.getByText('Os dados recebidos são incompatíveis com esta versão.'),
  ).toBeVisible();
  expect(calls).toBe(1);
});

test('401 durante atualização expira sessão e retira conteúdo privado', async ({
  page,
}) => {
  await page.goto('/dashboard');
  await expect(
    page.getByRole('table', { name: 'Histórico de análises' }),
  ).toBeVisible();
  await page.route('**/api/metrics/comparison?*', (route) =>
    route.fulfill({ status: 401, json: { detail: 'Expirada' } }),
  );
  await page.getByRole('button', { name: 'Atualizar consultas' }).click();
  await expect(page).toHaveURL(/\/login/);
  await expect(
    page.getByRole('table', { name: 'Histórico de análises' }),
  ).toHaveCount(0);
});

test('falha no logout não afirma revogação e oculta conteúdo privado', async ({
  page,
}) => {
  await page.route('**/api/auth/logout', (route) =>
    route.fulfill({ status: 503, json: { detail: 'Indisponível' } }),
  );
  await page.goto('/dashboard');
  await page
    .getByRole('button', { name: 'Sair da conta', exact: true })
    .click();
  await expect(page.getByRole('alert')).toContainText(
    'não foi possível confirmar a revogação no servidor',
  );
  await expect(
    page.getByRole('table', { name: 'Histórico de análises' }),
  ).toHaveCount(0);
});

test('filtro com período invertido é barrado no frontend antes da consulta', async ({
  page,
}) => {
  let calls = 0;
  await page.route('**/api/analyses?*', (route) => {
    calls++;
    return route.fulfill({
      json: { items: [analysis], total: 1, as_of: analysis.timestamp },
    });
  });
  await page.goto('/dashboard');
  await expect(
    page.getByRole('table', { name: 'Histórico de análises' }),
  ).toBeVisible();
  const originalUrl = page.url();
  const initialCalls = calls;
  await page.getByLabel('Data inicial', { exact: false }).fill('2026-10-20');
  await page.getByLabel('Data final', { exact: false }).fill('2026-10-01');
  await page.getByRole('button', { name: 'Aplicar filtros' }).click();
  await expect(
    page.getByText('Escolha um período válido de até 366 dias.'),
  ).toBeVisible();
  expect(page.url()).toBe(originalUrl);
  expect(calls).toBe(initialCalls);
});

test('menu móvel permite navegar e mantém recursos de hardware opcionais', async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 850 });
  await page.goto('/dashboard');
  await expect(
    page.getByRole('heading', { name: 'Bem-vindo, Pessoa!' }),
  ).toBeVisible();
  await expect(
    page.getByRole('link', { name: 'Dispositivos', exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole('link', { name: 'Tempo Real', exact: true }),
  ).toHaveCount(0);
  await expect(page.getByRole('button', { name: /Capturar/ })).toHaveCount(0);
  await page.getByRole('button', { name: 'Abrir menu' }).click();
  await expect(
    page.getByRole('navigation', { name: 'Navegação do dashboard' }),
  ).toBeVisible();
  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(
    accessibility.violations.map((item) => ({
      id: item.id,
      nodes: item.nodes.map((node) => ({
        target: node.target,
        summary: node.failureSummary,
      })),
    })),
  ).toEqual([]);
  await page.getByRole('link', { name: 'Análises', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard\/historico/);
  await expect(
    page.getByRole('heading', { name: 'Análises', exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('navigation', { name: 'Navegação do dashboard' }),
  ).toBeHidden();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test('perfil exibe dados da sessão em consulta sem oferecer gravação fictícia', async ({
  page,
}) => {
  await page.goto('/dashboard/perfil');
  await expect(
    page.getByRole('heading', { name: 'Meu perfil', exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel('Nome completo', { exact: false })).toHaveValue(
    user.name,
  );
  await expect(page.getByLabel('E-mail', { exact: false })).toHaveValue(
    user.email,
  );
  await expect(
    page.getByLabel('Nome completo', { exact: false }),
  ).toHaveAttribute('readonly', '');
  await expect(
    page.getByRole('button', { name: /Salvar|Capturar|Alterar senha/ }),
  ).toHaveCount(0);
  await expect(
    page.getByText('Câmera e periféricos', { exact: true }),
  ).toHaveCount(0);
});

test('layout privado tem navegação própria e estado ativo', async ({
  page,
}) => {
  await page.goto('/dashboard/historico');
  await expect(
    page.getByRole('link', { name: 'Análises', exact: true }),
  ).toHaveAttribute('aria-current', 'page');
  await expect(
    page.getByRole('navigation', { name: 'Navegação principal' }),
  ).toHaveCount(0);
  await expect(
    page.getByRole('navigation', { name: 'Navegação do dashboard' }),
  ).toBeVisible();
});

test('perfil móvel também funciona sem overflow ou opcionais configurados', async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto('/dashboard/perfil');
  await expect(page.getByRole('heading', { name: 'Meu perfil' })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test('área autenticada passa nas verificações automáticas de acessibilidade', async ({
  page,
}) => {
  for (const route of [
    '/dashboard',
    '/dashboard/historico',
    `/dashboard/analises/${analysis.id}`,
    '/dashboard/perfil',
  ]) {
    await page.goto(route);
    await expect(page.locator('h1')).toBeVisible();
    if (route === '/dashboard' || route === '/dashboard/historico')
      await expect(
        page.getByRole('table', { name: 'Histórico de análises' }),
      ).toBeVisible();
    const result = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    expect(
      result.violations.map((item) => ({
        id: item.id,
        impact: item.impact,
        nodes: item.nodes.map((node) => ({
          target: node.target,
          html: node.html,
          summary: node.failureSummary,
        })),
      })),
    ).toEqual([]);
  }
});

test('dashboard compara períodos e estados com dados da conta identificada', async ({
  page,
}) => {
  await page.goto('/dashboard');
  await expect(
    page.getByRole('heading', { name: 'Bem-vindo, Pessoa!' }),
  ).toBeVisible();
  await expect(
    page.getByText('Acompanhe suas análises e os resultados da triagem.'),
  ).toBeVisible();
  const table = page.getByRole('table', { name: 'Comparação entre períodos' });
  await expect(table).toBeVisible();
  const approved = table.getByRole('row').filter({ hasText: /^Aprovadas/ });
  await expect(approved.getByRole('rowheader')).toHaveText('Aprovadas');
  await expect(approved.getByRole('cell').nth(0)).toHaveText('1');
  await expect(approved.getByRole('cell').nth(1)).toHaveText('2');
  await expect(approved.getByRole('cell').nth(2)).toHaveText('-1');
  await expect(approved.getByRole('cell').nth(3)).toHaveText('-50%');
  const other = table.getByRole('row').filter({ hasText: /^Não aprovadas/ });
  await expect(other.getByRole('cell').nth(0)).toHaveText('0');
  await expect(other.getByRole('cell').nth(1)).toHaveText('2');
  const rate = table.getByRole('row').filter({ hasText: /^Aprovação/ });
  await expect(rate.getByRole('cell').nth(2)).toHaveText('+50 p.p.');
  await expect(rate.getByRole('cell').nth(3)).toHaveText('Não se aplica');
  await expect(
    page.getByText(/Não aprovadas = Atenção \+ Revisar/),
  ).toBeVisible();
  await expect(page.getByRole('alert')).toContainText(
    'Período atual em andamento',
  );
});

test('comparação sem base anterior mantém variação percentual indisponível', async ({
  page,
}) => {
  await page.route('**/api/metrics/comparison?*', (route) =>
    route.fulfill({
      json: comparisonFixture(
        route.request().url(),
        { approved: 3, attention: 1, review: 1 },
        { approved: 0, attention: 0, review: 0 },
      ),
    }),
  );
  await page.goto('/dashboard');
  const table = page.getByRole('table', { name: 'Comparação entre períodos' });
  const total = table.getByRole('row').filter({ hasText: /^Total analisado/ });
  await expect(total.getByRole('cell').nth(0)).toHaveText('5');
  await expect(total.getByRole('cell').nth(2)).toHaveText('+5');
  await expect(total.getByRole('cell').nth(3)).toHaveText('Sem base anterior');
  await expect(page.locator('main')).not.toContainText('Infinity');
  await expect(page.locator('main')).not.toContainText('NaN');
});

test('filtros são enviados ao endpoint de comparação e mantêm agrupamento por conta', async ({
  page,
}) => {
  const requests: string[] = [];
  await page.route('**/api/metrics/comparison?*', (route) => {
    requests.push(route.request().url());
    return route.fulfill({ json: comparisonFixture(route.request().url()) });
  });
  await page.goto('/dashboard');
  await expect(
    page.getByRole('table', { name: 'Comparação entre períodos' }),
  ).toBeVisible();
  await page.getByLabel('Data inicial', { exact: false }).fill('2026-10-01');
  await page.getByLabel('Data final', { exact: false }).fill('2026-10-07');
  await page.getByRole('button', { name: 'Aplicar filtros' }).click();
  await expect
    .poll(() =>
      new URL(requests[requests.length - 1]).searchParams.get('start'),
    )
    .toContain('2026-10-01');
  expect(
    new URL(requests[requests.length - 1]).searchParams.get('end'),
  ).toContain('2026-10-08');
  expect(
    new URL(requests[requests.length - 1]).searchParams.has('user_id'),
  ).toBe(false);
});

test('visitando o início logado mantém a identidade e o acesso ao dashboard pessoal', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page.getByText('Conectado como')).toBeVisible();
  await page.getByRole('link', { name: 'Meu dashboard', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Bem-vindo, Pessoa!' }),
  ).toBeVisible();
  await expect(
    page.getByRole('table', { name: 'Comparação entre períodos' }),
  ).toBeVisible();
});

test('troca de conta descarta comparação tardia da pessoa anterior', async ({
  page,
}) => {
  const secondUser = {
    ...user,
    id: '00000000-0000-4000-8000-000000000004',
    name: 'Teste Dois',
    email: 'second@example.com',
  };
  let active: typeof user | null = user;
  let firstRequested = false;
  let finishOld: (() => void) | undefined;
  const oldFinished = new Promise<void>((resolve) => {
    finishOld = resolve;
  });
  await page.route('**/api/auth/session', (route) =>
    route.fulfill({
      status: active ? 200 : 401,
      json: active
        ? { user: active, csrf_token: 'test-only-csrf' }
        : { detail: 'Sem sessão' },
    }),
  );
  await page.route('**/api/auth/logout', (route) => {
    active = null;
    return route.fulfill({ status: 204 });
  });
  await page.route('**/api/auth/login', (route) => {
    active = secondUser;
    return route.fulfill({
      json: { user: secondUser, csrf_token: 'test-only-new-csrf' },
    });
  });
  await page.route('**/api/metrics/comparison?*', async (route) => {
    const account = active;
    if (!account) {
      await route.fulfill({ status: 401, json: { detail: 'Sem sessão' } });
      return;
    }
    if (account.id === user.id) {
      firstRequested = true;
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
    await route
      .fulfill({
        json: comparisonFixture(
          route.request().url(),
          {
            approved: account.id === user.id ? 777 : 8,
            attention: 0,
            review: 0,
          },
          { approved: 1, attention: 0, review: 0 },
        ),
      })
      .catch(() => {});
    if (account.id === user.id) finishOld?.();
  });
  await page.goto('/dashboard');
  await expect.poll(() => firstRequested).toBe(true);
  await page
    .getByRole('button', { name: 'Sair da conta', exact: true })
    .click();
  await expect(page).toHaveURL(/\/login/);
  await page.getByLabel('E-mail', { exact: false }).fill(secondUser.email);
  await page.getByLabel(/^Senha/).fill('uma frase bastante longa');
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Bem-vindo, Teste!' }),
  ).toBeVisible();
  await oldFinished;
  const approved = page
    .getByRole('table', { name: 'Comparação entre períodos' })
    .getByRole('row')
    .filter({ hasText: /^Aprovadas/ });
  await expect(approved.getByRole('cell').nth(0)).toHaveText('8');
  await expect(page.locator('main')).not.toContainText('777');
});

test('nome longo da conta não causa overflow na saudação personalizada', async ({
  page,
}) => {
  const name = 'A'.repeat(90);
  await page.route('**/api/auth/session', (route) =>
    route.fulfill({
      json: { user: { ...user, name }, csrf_token: 'test-only-csrf' },
    }),
  );
  for (const width of [375, 1024]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/dashboard');
    await expect(
      page.getByRole('heading', { name: `Bem-vindo, ${name}!`, exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
  }
});
