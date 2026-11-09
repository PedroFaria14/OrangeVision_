import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('**/api/auth/session', (route) =>
    route.fulfill({ status: 401, json: { detail: 'Sessão ausente' } }),
  );
  await page.route('**/api/inspections/config', (route) =>
    route.fulfill({ json: { enabled: false, ownership: 'device-access' } }),
  );
  await page.route('**/api/status/render', (route) =>
    route.fulfill({
      json: {
        state: 'available',
        checkedAt: '2026-11-05T12:00:00Z',
        durationMs: 100,
        httpStatus: 200,
      },
    }),
  );
});

test('planejamento público apresenta 5W2H, sete etapas e entregas previstas', async ({
  page,
}) => {
  const privateRequests: string[] = [];
  page.on('request', (request) => {
    if (
      /\/api\/(metrics|analyses|samples|device)(?:[/?]|$)/.test(request.url())
    ) {
      privateRequests.push(request.url());
    }
  });
  await page.goto('/planejamento');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(
    'Planejamento',
  );
  await expect(
    page.getByRole('heading', { name: 'Da ideia à implementação' }),
  ).toBeVisible();

  const questions = page.getByRole('region', { name: '5W2H do OrangeVision' });
  await expect(questions.getByRole('article')).toHaveCount(7);
  for (const name of [
    'O quê?',
    'Por quê?',
    'Onde?',
    'Quando?',
    'Quem?',
    'Como?',
    'Quanto?',
  ]) {
    await expect(
      questions.getByRole('heading', { name, exact: true }),
    ).toBeVisible();
  }
  await expect(
    questions.getByRole('article', { name: 'Quanto?' }),
  ).toContainText('O orçamento ainda não foi definido.');

  const stages = page.getByRole('region', {
    name: 'Etapas do Projeto',
    exact: true,
  });
  await expect(stages.getByRole('listitem')).toHaveCount(7);
  await expect(stages).toContainText('LEDs, buzzer e servo são opcionais');
  const deliverables = page.getByRole('region', {
    name: 'Entregas do Projeto',
    exact: true,
  });
  await expect(deliverables.getByRole('article')).toHaveCount(6);
  await expect(deliverables).toContainText('Entrega final prevista');
  await expect(deliverables).toContainText(
    'As evidências serão registradas após os testes reais.',
  );
  await expect(deliverables.getByRole('alert')).toContainText(
    'calibração validada',
  );
  expect(privateRequests).toEqual([]);
});

test('cronograma conserva os períodos fornecidos sem afirmar conclusão', async ({
  page,
}) => {
  await page.goto('/planejamento');
  const table = page.getByRole('table', {
    name: 'Períodos previstos para cada etapa · 2026',
  });
  await expect(table.getByRole('columnheader')).toHaveText([
    'Etapa',
    'Atividade',
    'Setembro',
    'Outubro',
    'Novembro',
  ]);
  await expect(table.getByRole('row')).toHaveCount(8);
  for (const [title, expected] of [
    ['Pesquisa e Definição', ['01', 'Previsto', '—', '—']],
    ['Montagem do Hardware', ['03', 'Previsto', 'Previsto', '—']],
    ['Software e Dados', ['05', '—', 'Previsto', '—']],
    ['Integração e Testes', ['06', '—', 'Previsto', 'Previsto']],
    ['Validação e Resultados', ['07', '—', '—', 'Previsto']],
  ] as const) {
    const row = table.getByRole('row').filter({
      has: page.getByRole('rowheader', { name: title, exact: true }),
    });
    await expect(row.getByRole('cell')).toHaveText([...expected]);
  }
  await expect(
    page.getByRole('region', { name: 'Cronograma do Projeto', exact: true }),
  ).toContainText('não indica conclusão');
});

for (const width of [320, 768, 1440]) {
  test(`planejamento e rodapé acessíveis e sem overflow em ${width}px`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/planejamento');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();

    const schedule = page.getByRole('region', {
      name: 'Cronograma previsto de setembro a novembro de 2026',
    });
    await schedule.focus();
    await expect(schedule).toBeFocused();
    if (width === 320) {
      expect(
        await schedule.evaluate((node) => node.scrollWidth > node.clientWidth),
      ).toBeTruthy();
      await schedule.press('ArrowRight');
      await expect
        .poll(() => schedule.evaluate((node) => node.scrollLeft))
        .toBeGreaterThan(0);
    }
    const footer = page.getByRole('contentinfo');
    await expect(footer).toHaveCount(1);
    await expect(footer).toContainText('Engenharia • Tecnologia • Agronegócio');
    await expect(footer).toContainText(
      'Tecnologia aplicada a desafios reais do campo.',
    );
    await expect(footer).toContainText('Universidade São Francisco — USF');
    await expect(footer).toContainText('Projeto Acadêmico • 2026');

    const result = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    expect(result.violations).toEqual([]);
    await page.screenshot({
      path: testInfo.outputPath(`planejamento-${width}.png`),
      fullPage: true,
    });
    await footer.screenshot({
      path: testInfo.outputPath(`rodape-${width}.png`),
    });
    if (width === 1440) {
      await page
        .getByRole('region', { name: '5W2H do OrangeVision' })
        .screenshot({
          path: testInfo.outputPath('5w2h-desktop.png'),
          style: 'header { visibility: hidden !important; }',
        });
    }
  });
}
