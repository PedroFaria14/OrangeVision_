import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const id = '00000000-0000-4000-8000-000000000011';
const analysis = '00000000-0000-4000-8000-000000000099';
const local = {
  id: '00000000-0000-4000-8000-000000000021',
  origin: 'local',
  state: 'completed',
  classification: 'APROVADA',
  reason: 'Resultado local sintético.',
  criteria_version: 'fixture-calibration-v1',
  model_version: 'opencv-v1',
  created_at: '2026-11-06T12:00:00Z',
};
const gemini = {
  ...local,
  id: '00000000-0000-4000-8000-000000000022',
  origin: 'gemini',
  classification: 'ATENCAO',
  reason: 'Alterações visuais sintéticas; confirmar.',
  criteria_version: 'orange-surface-v1',
  model_version: 'fixture-model',
};
const job = {
  id: '00000000-0000-4000-8000-000000000023',
  state: 'running',
  attempts: 1,
  error_code: null,
  updated_at: '2026-11-06T12:00:00Z',
};
const sample = {
  id,
  filename: 'captura-sintetica.jpg',
  width: 80,
  height: 60,
  state: 'completed',
  device_id: '00000000-0000-4000-8000-000000000012',
  metrics: null,
  classification: 'APROVADA',
  reason: local.reason,
  calibration_version: 'fixture-calibration-v1',
  algorithm_version: 'opencv-v1',
  image_url: `/api/samples/${id}/image`,
  mask_url: null,
  created_at: local.created_at,
  updated_at: local.created_at,
  started_at: local.created_at,
  finished_at: local.created_at,
  claim_expires_at: null,
  source_inspection_id: '00000000-0000-4000-8000-000000000013',
  captured_at: local.created_at,
  analysis_id: analysis,
  evaluations: [local],
  gemini_job: job,
  decision: null,
  comparison: 'pending',
};
const png = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a1ioAAAAASUVORK5CYII=',
  'base64',
);

test.beforeEach(async ({ page }) => {
  await page.route('**/api/**', (r) =>
    r.fulfill({ status: 404, json: { detail: 'fixture' } }),
  );
  await page.route('**/api/auth/session', (r) =>
    r.fulfill({
      json: {
        user: {
          id: '00000000-0000-4000-8000-000000000001',
          name: 'Pessoa Teste',
          email: 'fixture@example.test',
        },
        csrf_token: 'synthetic-csrf',
      },
    }),
  );
  await page.route('**/api/inspections/config', (r) =>
    r.fulfill({ json: { enabled: true, ownership: 'inspection-session' } }),
  );
  await page.route('**/api/samples/config', (r) =>
    r.fulfill({
      json: {
        enabled: true,
        dashboard_enabled: true,
        dashboard_status: 'enabled',
        evaluations_enabled: true,
        gemini_enabled: true,
        processing: 'device',
        max_upload_bytes: 5242880,
      },
    }),
  );
  await page.route('**/api/samples/executors', (r) =>
    r.fulfill({ json: [{ id: sample.device_id, name: 'Bancada teste' }] }),
  );
  await page.route(`**/api/samples/${id}/image`, (r) =>
    r.fulfill({ contentType: 'image/png', body: png }),
  );
  await page.route('**/api/samples?*', (r) =>
    r.fulfill({ json: { items: [sample], total: 1 } }),
  );
});

test('local permanece visível enquanto Gemini demora e divergência não adota sozinha', async ({
  page,
}) => {
  let finished = false;
  let decisions = 0;
  const external: string[] = [];
  page.on('request', (request) => {
    if (request.url().includes('generativelanguage.googleapis.com'))
      external.push(request.url());
  });
  await page.route('**/api/samples?*', (r) =>
    r.fulfill({
      json: {
        items: [
          {
            ...sample,
            evaluations: finished ? [local, gemini] : [local],
            gemini_job: { ...job, state: finished ? 'completed' : 'running' },
            comparison: finished ? 'divergence' : 'pending',
          },
        ],
        total: 1,
      },
    }),
  );
  await page.route(`**/api/samples/${id}/decisions`, (r) => {
    decisions++;
    return r.fulfill({ status: 500 });
  });
  await page.goto('/dashboard/amostras');
  await expect(
    page
      .getByRole('region', { name: `Avaliação local de ${sample.filename}` })
      .getByText('Aprovada', { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('status').filter({ hasText: 'Gemini em processamento' }),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Avaliar novamente com Gemini' }),
  ).toBeDisabled();
  finished = true;
  await page.getByRole('button', { name: 'Atualizar amostras' }).click();
  await expect(page.getByText(/Avaliações divergentes/)).toBeVisible();
  await expect(
    page.getByText(
      /Uma segunda opinião não altera os gráficos sem confirmação/,
    ),
  ).toBeVisible();
  expect(decisions).toBe(0);
  expect(external).toEqual([]);
});

test('confirma Gemini e corrige com revisão sem criar segunda análise', async ({
  page,
}) => {
  let adopted: {
    revision: number;
    origin: string;
    classification: string;
    reason: string;
    created_at: string;
  } | null = null;
  const commands: Record<string, unknown>[] = [];
  const fixture = () => ({
    ...sample,
    evaluations: [local, gemini],
    gemini_job: { ...job, state: 'completed' },
    comparison: 'divergence',
    decision: adopted,
  });
  await page.route('**/api/samples?*', (r) =>
    r.fulfill({ json: { items: [fixture()], total: 1 } }),
  );
  await page.route(`**/api/samples/${id}/decisions`, (r) => {
    const body = r.request().postDataJSON();
    expect(r.request().headers()['x-csrf-token']).toBe('synthetic-csrf');
    expect(body.expected_revision).toBe(commands.length);
    commands.push(body);
    adopted = {
      revision: commands.length,
      origin: body.evaluation_id ? 'gemini' : 'human',
      classification: body.classification,
      reason: body.reason,
      created_at: local.created_at,
    };
    return r.fulfill({ json: fixture() });
  });
  await page.goto('/dashboard/amostras');
  await page.getByRole('button', { name: 'Adotar sugestão Gemini' }).click();
  await page
    .getByRole('dialog')
    .getByLabel('Justificativa da decisão')
    .fill('Confirmei os sinais visuais na foto.');
  await page
    .getByRole('button', { name: 'Confirmar decisão', exact: true })
    .click();
  await expect(
    page.getByText(/Resultado adotado: Atenção.*revisão 1/),
  ).toBeVisible();
  expect(commands[0].evaluation_id).toBe(gemini.id);
  await page
    .getByRole('button', { name: 'Corrigir resultado com justificativa' })
    .click();
  await page
    .getByRole('dialog')
    .getByRole('combobox', { name: 'Categoria adotada' })
    .click();
  await page.getByRole('option', { name: 'Revisar', exact: true }).click();
  await page
    .getByRole('dialog')
    .getByLabel('Justificativa da decisão')
    .fill('Após conferir, a captura precisa de revisão.');
  await page
    .getByRole('button', { name: 'Confirmar decisão', exact: true })
    .click();
  await expect(
    page.getByText(/Resultado adotado: Revisar.*revisão 2/),
  ).toBeVisible();
  expect(commands[1].evaluation_id).toBeNull();
  await expect(
    page.getByRole('link', { name: 'Ver análise', exact: true }),
  ).toHaveAttribute('href', `/dashboard/analises/${analysis}`);
});

test('validação rápida no site publica uma decisão por captura', async ({
  page,
}) => {
  let adopted: Record<string, unknown> | null = null;
  const commands: Record<string, unknown>[] = [];
  const fixture = () => ({
    ...sample,
    state: 'awaiting_review',
    classification: null,
    analysis_id: adopted ? analysis : null,
    evaluations: [{ ...gemini }],
    gemini_job: { ...job, state: 'completed' },
    comparison: 'inconclusive',
    decision: adopted,
  });
  await page.route('**/api/samples?*', (r) =>
    r.fulfill({ json: { items: [fixture()], total: 1 } }),
  );
  await page.route(`**/api/samples/${id}/decisions`, (r) => {
    const body = r.request().postDataJSON();
    commands.push(body);
    adopted = {
      revision: 1,
      origin: body.evaluation_id ? 'gemini' : 'human',
      classification: body.classification,
      reason: body.reason,
      created_at: local.created_at,
    };
    return r.fulfill({ json: fixture() });
  });
  await page.goto('/dashboard/amostras');
  await expect(page.getByText('Aguardando sua validação')).toBeVisible();
  await page
    .getByRole('button', { name: 'Validar como Aprovada', exact: true })
    .click();
  await expect(
    page.getByText(/Resultado adotado: Aprovada.*revisão 1/),
  ).toBeVisible();
  expect(commands).toHaveLength(1);
  expect(commands[0].evaluation_id).toBeNull();
  expect(commands[0].expected_revision).toBe(0);
  expect(String(commands[0].reason).length).toBeGreaterThanOrEqual(5);
  await expect(page.getByText('Aguardando sua validação')).toHaveCount(0);
  await expect(
    page.getByRole('button', { name: 'Validar como Aprovada', exact: true }),
  ).toHaveCount(0);
});

test('validação rápida igual à sugestão Gemini confirma a avaliação', async ({
  page,
}) => {
  const commands: Record<string, unknown>[] = [];
  await page.route('**/api/samples?*', (r) =>
    r.fulfill({
      json: {
        items: [{ ...sample, analysis_id: null, evaluations: [gemini] }],
        total: 1,
      },
    }),
  );
  await page.route(`**/api/samples/${id}/decisions`, (r) => {
    commands.push(r.request().postDataJSON());
    return r.fulfill({ status: 409 });
  });
  await page.goto('/dashboard/amostras');
  await page
    .getByRole('button', { name: 'Validar como Atenção', exact: true })
    .click();
  await expect.poll(() => commands.length).toBe(1);
  expect(commands[0].evaluation_id).toBe(gemini.id);
  expect(commands[0].classification).toBe('ATENCAO');
});

test('resposta perdida reutiliza comando Gemini em vez de solicitar outra avaliação', async ({
  page,
}) => {
  const commands: unknown[] = [];
  await page.route('**/api/samples?*', (r) =>
    r.fulfill({ json: { items: [{ ...sample, gemini_job: null }], total: 1 } }),
  );
  await page.route(`**/api/samples/${id}/evaluations/gemini`, (r) => {
    commands.push(r.request().postDataJSON());
    return commands.length === 1
      ? r.abort('failed')
      : r.fulfill({
          status: 202,
          json: { ...sample, gemini_job: { ...job, state: 'queued' } },
        });
  });
  await page.goto('/dashboard/amostras');
  await page
    .getByRole('button', { name: 'Solicitar Gemini', exact: true })
    .click();
  await page.getByRole('button', { name: 'Confirmar o mesmo comando' }).click();
  await expect(
    page.getByRole('button', { name: 'Confirmar o mesmo comando' }),
  ).toHaveCount(0);
  expect(commands).toHaveLength(2);
  expect(commands[0]).toEqual(commands[1]);
});

test('duas avaliações são acessíveis sem overflow no celular e desktop', async ({
  page,
}) => {
  await page.route('**/api/samples?*', (r) =>
    r.fulfill({
      json: {
        items: [
          {
            ...sample,
            evaluations: [local, gemini],
            comparison: 'divergence',
            gemini_job: { ...job, state: 'completed' },
          },
        ],
        total: 1,
      },
    }),
  );
  for (const width of [320, 390, 1366]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/dashboard/amostras');
    await expect(
      page.getByRole('heading', { name: 'Segunda opinião · Gemini' }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  }
});
