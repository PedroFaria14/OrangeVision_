import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const members = [
  {
    name: 'Felipe Kenzo',
    initials: 'FK',
    profession: 'Estagiário em Projetos Automotivos na Flex',
    roles: 'Software • Documentação',
  },
  {
    name: 'Kauan Fernandes',
    initials: 'KF',
    profession: 'Técnico de Redes na Global Hitss',
    roles: 'Redes • Infraestrutura • Integração',
  },
  {
    name: 'Marcelo Capeletto',
    initials: 'MC',
    profession: 'Estagiário em Garantia de Qualidade na EssilorLuxottica',
    roles: 'Qualidade • Testes • Documentação',
  },
  {
    name: 'Pedro Faria',
    initials: 'PF',
    profession: 'Estagiário em Desenvolvimento Blockchain no CPQD',
    roles: 'Software • Backend • Integração',
  },
  {
    name: 'Glauber Sandi Martins',
    initials: 'GS',
    profession: 'Product Development Specialist',
    roles:
      'Desenvolvimento de Produto • Industrialização • Gestão de Projetos • Integração',
  },
  {
    name: 'João Assis',
    initials: 'JA',
    profession: 'Técnico de Soluções Digitais Sr na Bosch',
    roles: 'IoT • Sistemas Embarcados • Conectividade • Integração',
  },
] as const;

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

test('equipe pública apresenta seis perfis completos sem consultar dados privados', async ({
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
  await page.goto('/equipe');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Equipe');
  await expect(
    page.getByRole('heading', {
      name: 'Quem faz o OrangeVision acontecer',
    }),
  ).toBeVisible();
  const team = page.getByRole('region', {
    name: 'Integrantes da equipe OrangeVision',
  });
  await expect(team.getByRole('article')).toHaveCount(6);
  for (const member of members) {
    const card = team.getByRole('article', { name: member.name, exact: true });
    await expect(
      card.getByRole('heading', { name: member.name }),
    ).toBeVisible();
    await expect(card).toContainText(member.profession);
    await expect(card).toContainText(member.roles);
    await expect(card).toContainText(
      '3º ano de Engenharia da Computação na USF',
    );
    await expect(card).toContainText('Atuação no OrangeVision');
  }
  await expect(team.getByRole('article', { name: 'João Assis' })).toContainText(
    'Técnico em Mecatrônica',
  );
  await expect(
    team.getByRole('article', { name: 'Kauan Fernandes' }),
  ).toContainText('BGP, OSPF e serviços MPLS');
  expect(privateRequests).toEqual([]);
});

for (const width of [320, 768, 1024, 1440]) {
  test(`equipe com retratos ou iniciais, acessível e sem overflow em ${width}px`, async ({
    page,
  }, testInfo) => {
    const errors: string[] = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/equipe');
    await expect(page.getByRole('article')).toHaveCount(6);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();

    for (const member of members) {
      const card = page.getByRole('article', {
        name: member.name,
        exact: true,
      });
      const photo = card.locator('img');
      if ((await photo.count()) > 0) {
        await photo.scrollIntoViewIfNeeded();
        await expect
          .poll(() =>
            photo.evaluate((image) => (image as HTMLImageElement).naturalWidth),
          )
          .toBeGreaterThan(0);
      } else {
        await expect(
          card.getByText(member.initials, { exact: true }),
        ).toBeVisible();
        await expect(card.getByText('Sem foto', { exact: true })).toBeVisible();
      }
    }
    await expect(page.getByRole('contentinfo')).toHaveCount(1);
    const result = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    expect(result.violations).toEqual([]);
    expect(errors).toEqual([]);
    await page.screenshot({
      path: testInfo.outputPath(`equipe-${width}.png`),
      fullPage: true,
    });
    await page.getByRole('article', { name: 'Felipe Kenzo' }).screenshot({
      path: testInfo.outputPath(`perfil-${width}.png`),
    });
  });
}
