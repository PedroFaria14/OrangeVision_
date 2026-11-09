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

test('projeto mantém conteúdo consolidado e referência bibliográfica conferida', async ({
  page,
}) => {
  await page.goto('/projeto');
  const main = page.getByRole('main');
  await expect(main.getByRole('heading', { level: 1 })).toHaveText('O Projeto');
  for (const name of [
    'ODS 2 — Fome Zero e Agricultura Sustentável',
    'Escopo e limitações',
    'Da fruta para os dados',
  ]) {
    await expect(main.getByRole('heading', { name, exact: true })).toHaveCount(
      1,
    );
  }
  const references = main.getByRole('region', {
    name: 'Referências de contexto',
  });
  await expect(references).toContainText('Comportamento de citros no Amazonas');
  await expect(references).toContainText('2007. 31 p. (Documentos, 55)');
  await expect(references).toContainText('não valida o classificador');
  await expect(main).toContainText('setor primário');
  await expect(main).not.toContainText('Primeiro Setor');
  await expect(
    main.getByRole('region', { name: 'Escopo e limitações' }),
  ).toContainText('não realiza diagnóstico fitossanitário');
  await expect(
    main.getByRole('region', {
      name: 'Uma inspeção mais padronizada e rastreável',
    }),
  ).toContainText('apenas quando esses periféricos estiverem presentes');
});

for (const width of [320, 390, 768, 1440]) {
  test(`projeto com divisores decorativos responsivos e acessíveis em ${width}px`, async ({
    page,
  }, testInfo) => {
    const errors: string[] = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/projeto');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    const dividers = page.getByTestId('orangevision-divider');
    await expect(dividers).toHaveCount(9);
    for (const divider of await dividers.all()) {
      await expect(divider).toHaveAttribute('aria-hidden', 'true');
      await expect(divider).toContainText('OrangeVision');
      expect(
        await divider.evaluate((node) => node.scrollWidth <= node.clientWidth),
      ).toBeTruthy();
    }
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    const heading = page.getByRole('heading', { level: 1 });
    await expect(heading).toHaveCSS('text-align', 'center');
    const accessibility = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    expect(accessibility.violations).toEqual([]);
    expect(errors).toEqual([]);
    await page.screenshot({
      path: testInfo.outputPath(`projeto-${width}.png`),
      fullPage: true,
    });
    await dividers
      .first()
      .screenshot({ path: testInfo.outputPath(`divisor-${width}.png`) });
  });
}
