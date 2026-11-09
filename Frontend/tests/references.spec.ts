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

test('referencial relaciona as fontes às métricas sem prometer diagnóstico ou acurácia', async ({
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
  await page.goto('/referencias');
  const main = page.getByRole('main');
  await expect(main.getByRole('heading', { level: 1 })).toHaveText(
    'Referencial Teórico',
  );
  await expect(
    main.getByRole('region', { name: 'Laranja Pêra-Rio' }),
  ).toContainText('2007, p. 23');
  const applications = main.getByRole('region', {
    name: 'Aplicação no OrangeVision',
  });
  await expect(applications.getByRole('heading', { level: 3 })).toHaveText([
    'Coloração',
    'Regiões Anormais',
    'Forma',
    'Assimetria',
  ]);
  await expect(applications).toContainText('4πA / P²');
  await expect(applications).toContainText('espelho horizontal');
  const score = main.getByRole('region', {
    name: 'Score visual e classificação experimental',
  });
  await expect(score).toContainText('Σ(wᵢ × nᵢ) / Σwᵢ');
  await expect(score).toContainText('Score não é probabilidade nem acurácia');
  await expect(
    main.getByRole('region', { name: 'Limitação do sistema' }),
  ).toContainText('não realiza diagnóstico de greening');
  await expect(
    main.getByRole('region', { name: 'Artigos Científicos' }),
  ).toContainText('Seleção e fichamento pendentes');
  expect(privateRequests).toEqual([]);
});

test('bibliografia única usa a stack real e oferece links verificáveis', async ({
  page,
}) => {
  await page.goto('/referencias');
  const bibliography = page.getByRole('region', {
    name: 'Referências Bibliográficas e Técnicas',
  });
  await expect(bibliography.getByRole('heading', { level: 3 })).toHaveCount(11);
  for (const name of ['React', 'FastAPI', 'PostgreSQL', 'Neon', 'SQLite']) {
    await expect(
      bibliography.getByRole('heading', { name, exact: true }),
    ).toHaveCount(1);
  }
  await expect(page.getByRole('main')).not.toContainText('Streamlit');
  for (const [name, url] of [
    [
      'Consultar documento da Embrapa (PDF)',
      'https://www.infoteca.cnptia.embrapa.br/bitstream/doc/681766/1/Doc55.pdf',
    ],
    [
      'Consultar Fundecitrus — greening e psilídeo',
      'https://www.fundecitrus.com.br/pragas-e-doencas/greening-e-psilideo/',
    ],
    ['Consultar documentação do React', 'https://react.dev/learn'],
    [
      'Consultar ODS 2 e suas metas na ONU Brasil',
      'https://brasil.un.org/pt-br/sdgs/2',
    ],
    [
      'Contornos, área e perímetro',
      'https://docs.opencv.org/4.x/dd/d49/tutorial_py_contour_features.html',
    ],
  ] as const) {
    await expect(
      bibliography.getByRole('link', { name, exact: true }),
    ).toHaveAttribute('href', url);
  }
  const citation = page.getByRole('link', {
    name: 'Fonte: Embrapa — Comportamento de citros no Amazonas, p. 23',
  });
  await citation.focus();
  await citation.press('Enter');
  await expect(page).toHaveURL(/#reference-embrapa$/);
  await expect(page.locator('#reference-embrapa')).toBeFocused();
  await expect(page.locator('#reference-embrapa')).toBeInViewport();
});

for (const width of [320, 390, 768, 1440]) {
  test(`referencial acessível e sem overflow em ${width}px`, async ({
    page,
  }, testInfo) => {
    const errors: string[] = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/referencias');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    await expect(page.getByRole('contentinfo')).toHaveCount(1);
    const result = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    expect(result.violations).toEqual([]);
    expect(errors).toEqual([]);
    await page.screenshot({
      path: testInfo.outputPath(`referencial-${width}.png`),
      fullPage: true,
    });
    await page
      .getByRole('region', { name: 'Aplicação no OrangeVision' })
      .screenshot({
        path: testInfo.outputPath(`metricas-${width}.png`),
        style: 'header { visibility: hidden !important; }',
      });
  });
}
