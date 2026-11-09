import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const id = '00000000-0000-4000-8000-000000000011';
const device = '00000000-0000-4000-8000-000000000012';
const png = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a1ioAAAAASUVORK5CYII=',
  'base64',
);
const sample = {
  id,
  filename: 'amostra-sintetica-teste.png',
  width: 80,
  height: 60,
  state: 'received',
  device_id: null,
  metrics: null,
  classification: null,
  reason: null,
  calibration_version: null,
  algorithm_version: null,
  image_url: `/api/samples/${id}/image`,
  mask_url: null,
  created_at: '2026-10-23T12:00:00Z',
  updated_at: '2026-10-23T12:00:00Z',
  started_at: null,
  finished_at: null,
  claim_expires_at: null,
};

test.beforeEach(async ({ page }) => {
  await page.route('**/api/auth/session', (r) =>
    r.fulfill({
      json: {
        user: {
          id: '00000000-0000-4000-8000-000000000001',
          name: 'Pessoa Teste',
          email: 'sample@example.com',
        },
        csrf_token: 'test-only-csrf',
      },
    }),
  );
  await page.route('**/api/inspections/config', (r) =>
    r.fulfill({ json: { enabled: false, ownership: 'device-access' } }),
  );
  await page.route('**/api/samples/config', (r) =>
    r.fulfill({
      json: { enabled: true, processing: 'device', max_upload_bytes: 5242880 },
    }),
  );
  await page.route('**/api/samples/executors', (r) =>
    r.fulfill({ json: [{ id: device, name: 'Equipamento de teste' }] }),
  );
  await page.route('**/api/samples/*/image', (r) =>
    r.fulfill({ body: png, contentType: 'image/png' }),
  );
  await page.route('**/api/samples/*/mask*', (r) =>
    r.fulfill({ body: png, contentType: 'image/png' }),
  );
});

test('fila mostra contato ausente e depois contato recente do executor', async ({
  page,
}) => {
  let recent = false;
  await page.route('**/api/samples/executors', (r) =>
    r.fulfill({
      json: [
        {
          id: device,
          name: 'Equipamento de teste',
          last_seen_at: recent ? '2026-10-23T12:00:00Z' : null,
          executor_state: recent ? 'ready' : null,
          executor_recent: recent,
          model_version: recent ? 'test-model' : null,
        },
      ],
    }),
  );
  await page.route('**/api/samples?*', (r) =>
    r.fulfill({
      json: {
        items: [{ ...sample, state: 'queued', device_id: device }],
        total: 1,
      },
    }),
  );
  await page.goto('/dashboard/amostras');
  await expect(page).toHaveTitle(/Amostras e imagens/);
  await expect(
    page.getByText(/Nenhum contato do executor foi registrado/).first(),
  ).toBeVisible();
  await page.getByLabel('Equipamento autorizado').click();
  await page.getByRole('option', { name: 'Equipamento de teste' }).click();
  await expect(
    page.getByText('Estado informado pelo executor: Não informado.', {
      exact: true,
    }),
  ).toBeVisible();
  recent = true;
  await page.getByRole('button', { name: 'Atualizar amostras' }).click();
  await expect(
    page.getByText(/Executor entrou em contato recentemente/),
  ).toBeVisible();
  await expect(
    page.getByText('Estado informado pelo executor: Pronto.', { exact: true }),
  ).toBeVisible();
});

test('detecção aparece separada da categoria de qualidade', async ({
  page,
}) => {
  await page.route('**/api/samples?*', (r) =>
    r.fulfill({
      json: {
        items: [
          {
            ...sample,
            state: 'awaiting_review',
            detection: {
              status: 'detected',
              label: 'orange',
              score: 0.9,
              box: [10, 10, 50, 40],
              count: 1,
              model: 'synthetic-test-detector',
              inference_ms: 10,
            },
          },
        ],
        total: 1,
      },
    }),
  );
  await page.goto('/dashboard/amostras');
  await expect(page.getByText(/Modelo sugere laranja/)).toBeVisible();
  await expect(page.getByText(/Ainda não validada/)).toBeVisible();
  await expect(page.getByText(/não é acurácia nem qualidade/)).toBeVisible();
  await expect(
    page.getByText(
      'Caixa da detecção (x, y, largura, altura): 10, 10, 50, 40 px.',
      { exact: true },
    ),
  ).toBeVisible();
  await expect(page.locator('svg[viewBox="0 0 80 60"] rect')).toHaveAttribute(
    'x',
    '10',
  );
  await expect(page.locator('main')).not.toContainText(
    'Aprovada (experimental)',
  );
});

test('upload e estados são separados da categoria e usam csrf sem dono arbitrário', async ({
  page,
}) => {
  let current: Record<string, unknown> | null = null;
  let requestId = '';
  await page.route('**/api/samples?*', async (route) => {
    if (route.request().method() === 'POST') {
      expect(route.request().headers()['x-csrf-token']).toBe('test-only-csrf');
      expect(route.request().headers()['content-type']).toBe(
        'application/octet-stream',
      );
      const url = new URL(route.request().url());
      expect(url.searchParams.has('user_id')).toBeFalsy();
      const incoming = url.searchParams.get('request_id')!;
      expect(incoming).toMatch(/^[0-9a-f-]{36}$/);
      if (requestId) expect(incoming).toBe(requestId);
      requestId = incoming;
      current = { ...sample };
      await route.fulfill({ status: 201, json: current });
    } else
      await route.fulfill({
        json: { items: current ? [current] : [], total: current ? 1 : 0 },
      });
  });
  await page.route(`**/api/samples/${id}/queue`, async (route) => {
    expect(route.request().headers()['x-csrf-token']).toBe('test-only-csrf');
    expect(route.request().postDataJSON()).toEqual({ device_id: device });
    current = { ...sample, state: 'queued', device_id: device };
    await route.fulfill({ json: current });
  });
  await page.goto('/dashboard/amostras');
  await expect(
    page.getByText(
      'Você ainda não enviou amostras. Escolha uma imagem para começar.',
    ),
  ).toBeVisible();
  await page.getByLabel('Selecionar imagem de amostra').setInputFiles({
    name: sample.filename,
    mimeType: 'image/png',
    buffer: png,
  });
  await page
    .getByRole('button', { name: 'Enviar imagem', exact: true })
    .click();
  await expect(
    page.getByText('Imagem recebida', { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText('Ainda não validada', { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole('combobox', { name: 'Equipamento autorizado' }),
  ).toContainText('Equipamento de teste');
  await page.getByRole('combobox', { name: 'Equipamento autorizado' }).click();
  await page.getByRole('option', { name: 'Selecione um equipamento' }).click();
  await expect(
    page.getByRole('button', { name: 'Enviar para análise local' }),
  ).toBeDisabled();
  await page.getByRole('combobox', { name: 'Equipamento autorizado' }).click();
  await page.getByRole('option', { name: 'Equipamento de teste' }).click();
  await page.getByRole('button', { name: 'Enviar para análise local' }).click();
  await expect(
    page.getByText('Aguardando análise', { exact: true }),
  ).toBeVisible();
  current = {
    ...sample,
    state: 'processing',
    device_id: device,
    claim_expires_at: '2026-10-23T12:05:00Z',
  };
  await page.getByRole('button', { name: 'Atualizar amostras' }).click();
  await expect(page.getByText('Em análise', { exact: true })).toBeVisible();
  current = {
    ...sample,
    state: 'awaiting_review',
    reason: 'Categoria aguarda validação.',
    metrics: {
      orange_color_ratio: null,
      abnormal_region_ratio: null,
      circularity: 0.8,
      asymmetry: 0.02,
      visual_score: null,
    },
    mask_url: `/api/samples/${id}/mask`,
  };
  await page.getByRole('button', { name: 'Atualizar amostras' }).click();
  await expect(
    page.getByText('Aguardando avaliação', { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('img', { name: `Máscara experimental: ${sample.filename}` }),
  ).toBeVisible();
  await expect(page.locator('main')).not.toContainText(
    'Aprovada (experimental)',
  );
});

for (const width of [390, 1366]) {
  test(`galeria privada responsiva e acessível em ${width}px`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height: 844 });
    await page.route('**/api/samples?*', (r) =>
      r.fulfill({
        json: {
          items: [
            {
              ...sample,
              state: 'not_evaluable',
              reason: 'Confira o enquadramento da amostra.',
            },
          ],
          total: 1,
        },
      }),
    );
    await page.goto('/dashboard/amostras');
    await expect(
      page.getByText('Não foi possível avaliar', { exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
    await page.screenshot({
      path: testInfo.outputPath('amostras-fixture.png'),
      fullPage: true,
    });
  });
}

test('sem migration não consulta lista nem apresenta falso vazio', async ({
  page,
}) => {
  let calls = 0;
  await page.route('**/api/samples/config', (r) =>
    r.fulfill({
      json: { enabled: false, processing: 'device', max_upload_bytes: 5242880 },
    }),
  );
  await page.route('**/api/samples?*', (r) => {
    calls++;
    return r.fulfill({ json: { items: [], total: 0 } });
  });
  await page.goto('/dashboard/amostras');
  await expect(page.getByText(/A galeria ainda não foi ativada/)).toBeVisible();
  expect(calls).toBe(0);
  await expect(
    page.getByText(
      'Você ainda não enviou amostras. Escolha uma imagem para começar.',
    ),
  ).toHaveCount(0);
});

test('falha de consulta não aparece como galeria vazia', async ({ page }) => {
  await page.route('**/api/samples?*', (r) =>
    r.fulfill({ status: 503, json: { detail: 'indisponível' } }),
  );
  await page.goto('/dashboard/amostras');
  await expect(
    page.getByText(/Não foi possível atualizar a galeria/),
  ).toBeVisible();
  await expect(
    page.getByText(
      'Você ainda não enviou amostras. Escolha uma imagem para começar.',
    ),
  ).toHaveCount(0);
});

test('paginação das amostras usa offset do servidor e expõe navegação nomeada', async ({
  page,
}) => {
  const items = Array.from({ length: 21 }, (_, index) => ({
    ...sample,
    id: `00000000-0000-4000-8000-${String(index + 50).padStart(12, '0')}`,
    filename: `amostra-teste-${index + 1}.png`,
  }));
  await page.route('**/api/samples?*', (route) => {
    const offset = Number(
      new URL(route.request().url()).searchParams.get('offset'),
    );
    return route.fulfill({
      json: { items: items.slice(offset, offset + 20), total: 21 },
    });
  });
  await page.goto('/dashboard/amostras');
  const pager = page.getByRole('navigation', {
    name: 'Paginação das amostras',
  });
  await expect(pager).toContainText('Página 1 · 21 amostras');
  await pager.getByRole('button', { name: 'Próxima', exact: true }).click();
  await expect(pager).toContainText('Página 2 · 21 amostras');
  await expect(
    page.getByRole('heading', { name: 'amostra-teste-21.png', exact: true }),
  ).toBeVisible();
  await expect(
    pager.getByRole('button', { name: 'Próxima', exact: true }),
  ).toBeDisabled();
});

test('captura concluída entra nos gráficos por comando idempotente com CSRF', async ({
  page,
}) => {
  let published = false;
  let writes = 0;
  const analysisId = '00000000-0000-4000-8000-000000000099';
  const completed = () => ({
    ...sample,
    state: 'completed',
    classification: 'APROVADA',
    source_inspection_id: '00000000-0000-4000-8000-000000000077',
    analysis_id: published ? analysisId : null,
  });
  await page.route('**/api/samples/config', (r) =>
    r.fulfill({
      json: {
        enabled: true,
        dashboard_enabled: true,
        processing: 'device',
        max_upload_bytes: 5242880,
      },
    }),
  );
  await page.route('**/api/samples?*', (r) =>
    r.fulfill({ json: { items: [completed()], total: 1 } }),
  );
  await page.route(`**/api/samples/${id}/analysis`, (r) => {
    expect(r.request().method()).toBe('POST');
    expect(r.request().headers()['x-csrf-token']).toBe('test-only-csrf');
    writes++;
    published = true;
    return r.fulfill({ json: completed() });
  });
  await page.goto('/dashboard/amostras');
  await expect(page.getByText(/Aprovada \(experimental\)/)).toBeVisible();
  await page
    .getByRole('button', { name: 'Incluir nos gráficos', exact: true })
    .click();
  await expect(
    page.getByText(/Incluída nos gráficos e no histórico/),
  ).toBeVisible();
  await expect(
    page.getByRole('link', { name: 'Ver análise', exact: true }),
  ).toHaveAttribute('href', `/dashboard/analises/${analysisId}`);
  await expect(
    page.getByRole('link', { name: 'Ver gráficos', exact: true }),
  ).toHaveAttribute('href', '/dashboard');
  await expect(
    page.getByRole('button', { name: 'Analisar novamente', exact: true }),
  ).toBeDisabled();
  await page.getByRole('button', { name: 'Atualizar amostras' }).click();
  expect(writes).toBe(1);
});

test('pendências e falhas explicam por que não entram nos gráficos', async ({
  page,
}) => {
  await page.route('**/api/samples?*', (r) =>
    r.fulfill({
      json: {
        items: [
          {
            ...sample,
            state: 'awaiting_review',
            reason: 'Categoria aguarda calibração.',
          },
          {
            ...sample,
            id: '00000000-0000-4000-8000-000000000098',
            state: 'not_evaluable',
            reason: 'O contorno encostou no limite da seleção.',
          },
        ],
        total: 2,
      },
    }),
  );
  await page.goto('/dashboard/amostras');
  await expect(
    page.getByText(/Ainda sem classificação de qualidade/),
  ).toBeVisible();
  await expect(
    page.getByText('O contorno encostou no limite da seleção.'),
  ).toBeVisible();
  await expect(
    page.getByText(
      /Sem classificação válida, esta captura não entra nos gráficos/,
    ),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Incluir nos gráficos' }),
  ).toHaveCount(0);
});

test('integração não ativada preserva a captura sem afirmar publicação', async ({
  page,
}) => {
  await page.route('**/api/samples/config', (r) =>
    r.fulfill({
      json: {
        enabled: true,
        dashboard_enabled: false,
        processing: 'device',
        max_upload_bytes: 5242880,
      },
    }),
  );
  await page.route('**/api/samples?*', (r) =>
    r.fulfill({
      json: {
        items: [
          {
            ...sample,
            state: 'completed',
            classification: 'ATENCAO',
            source_inspection_id: '00000000-0000-4000-8000-000000000077',
          },
        ],
        total: 1,
      },
    }),
  );
  await page.goto('/dashboard/amostras');
  await expect(
    page.getByText(/A integração com gráficos ainda não foi ativada/),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Incluir nos gráficos' }),
  ).toBeDisabled();
  await expect(
    page.getByRole('link', { name: 'Ver gráficos', exact: true }),
  ).toHaveCount(0);
});
