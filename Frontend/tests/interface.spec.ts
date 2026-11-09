import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// Contratos simulados SOMENTE nos testes. A aplicação não contém mocks/fallbacks.
for (const viewport of [
  { width: 1366, height: 768 },
  { width: 390, height: 844 },
]) {
  test(`revisão de páginas institucionais e autenticação ${viewport.width}x${viewport.height}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize(viewport);
    for (const path of [
      '/projeto',
      '/planejamento',
      '/desenvolvimento',
      '/resultados',
      '/equipe',
      '/referencias',
      '/login',
      '/registrar',
    ]) {
      await page.goto(path);
      await expect(page.locator('h1')).toBeVisible();
      await expect(
        page.getByText(/\[(DEFINIR|VALIDAR|CONFIRMAR|COMPLETAR|PENDENTE)\]/),
      ).toHaveCount(0);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBeTruthy();
      if (path === '/registrar') {
        const button = page.getByRole('button', {
          name: 'Criar conta',
          exact: true,
        });
        await button.scrollIntoViewIfNeeded();
        await expect(button).toBeInViewport();
      }
      await page.screenshot({
        path: testInfo.outputPath(`${path.slice(1)}.png`),
        fullPage: true,
      });
    }
  });
}

test.beforeEach(async ({ page }) => {
  await page.route('**/api/inspections/config', (route) =>
    route.fulfill({ json: { enabled: false, ownership: 'device-access' } }),
  );
  await page.route('**/api/auth/session', (route) =>
    route.fulfill({ status: 401, json: { detail: 'Sessão ausente' } }),
  );
});

for (const width of [320, 375, 390, 768, 900, 1024, 1440]) {
  test(`páginas públicas e formulário sem overflow em ${width}px`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    for (const path of [
      '/',
      '/projeto',
      '/planejamento',
      '/desenvolvimento',
      '/resultados',
      '/equipe',
      '/referencias',
      '/login',
      '/registrar',
    ]) {
      await page.goto(path);
      await expect(page.locator('h1')).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      ).toBeTruthy();
      if (
        (width === 375 || width === 1440) &&
        (path === '/login' || path === '/registrar')
      )
        await page.screenshot({
          path: testInfo.outputPath(`${path.slice(1)}-${width}.png`),
          fullPage: true,
        });
    }
  });
}

test('rota privada exige sessão e mantém destino interno', async ({ page }) => {
  await page.goto('/dashboard/historico');
  await expect(page).toHaveURL(/\/login\?next=/);
  await expect(
    page.getByRole('heading', { name: 'Entrar', exact: true }),
  ).toBeVisible();
});

test('cadastro valida confirmação sem enviar credenciais inválidas', async ({
  page,
}) => {
  let sent = 0;
  await page.route('**/api/auth/register', (route) => {
    sent++;
    return route.fulfill({ status: 201, json: { message: 'Criado' } });
  });
  await page.goto('/registrar');
  await page.getByLabel('Nome', { exact: false }).fill('Pessoa Teste');
  await page.getByLabel('E-mail', { exact: false }).fill('person@example.com');
  await page.getByLabel(/^Senha/).fill('uma frase bastante longa');
  await page
    .getByLabel('Confirmar senha', { exact: false })
    .fill('uma frase diferente');
  await page.getByRole('button', { name: 'Criar conta', exact: true }).click();
  await expect(page.getByText('As senhas não coincidem.')).toBeVisible();
  expect(sent).toBe(0);
});

test('login inválido apresenta erro genérico e limpa senha', async ({
  page,
}) => {
  await page.route('**/api/auth/login', (route) =>
    route.fulfill({ status: 401, json: { detail: 'Credenciais inválidas' } }),
  );
  await page.goto('/login');
  await page.getByLabel('E-mail', { exact: false }).fill('person@example.com');
  await page.getByLabel(/^Senha/).fill('uma frase bastante longa');
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText(
    'E-mail ou senha inválidos.',
  );
  await expect(page.getByLabel(/^Senha/)).toHaveValue('');
});

test('login aguarda a sessão e permite recuperar uma falha sem fingir que o usuário está anônimo', async ({
  page,
}) => {
  let release: () => void = () => {};
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let recovered = false;
  await page.route('**/api/auth/session', async (route) => {
    await gate;
    return route.fulfill({
      status: recovered ? 401 : 503,
      json: {
        detail: recovered ? 'Sessão ausente' : 'Temporariamente indisponível',
      },
    });
  });
  try {
    await page.goto('/login');
    await expect(
      page.getByText('Verificando sua sessão…', { exact: true }),
    ).toBeVisible();
    await expect(page.getByLabel('E-mail', { exact: false })).toHaveCount(0);
    release();
    await expect(
      page.getByText(/Não foi possível confirmar sua sessão/),
    ).toBeVisible();
    await expect(page.getByLabel('E-mail', { exact: false })).toHaveCount(0);
    recovered = true;
    await page
      .getByRole('button', { name: 'Tentar novamente', exact: true })
      .click();
    await expect(page.getByLabel('E-mail', { exact: false })).toBeVisible();
  } finally {
    release();
  }
});

test('cadastro bloqueia campos durante envio e limita senha e confirmação a 128 caracteres', async ({
  page,
}) => {
  let release: () => void = () => {};
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let calls = 0;
  await page.route('**/api/auth/register', async (route) => {
    calls++;
    const payload = route.request().postDataJSON();
    expect(payload.email).toBe('fixture@example.com');
    expect(payload.password).toBe('uma frase bastante longa');
    await gate;
    return route.fulfill({
      status: 201,
      json: { message: 'Cadastro concluído.' },
    });
  });
  try {
    await page.goto('/registrar');
    await page.getByLabel('Nome', { exact: false }).fill('Pessoa Teste');
    await page
      .getByLabel('E-mail', { exact: false })
      .fill('fixture@example.com');
    await page.getByLabel(/^Senha/).fill('uma frase bastante longa');
    await page
      .getByLabel('Confirmar senha', { exact: false })
      .fill('uma frase bastante longa');
    await expect(page.getByLabel(/^Senha/)).toHaveAttribute('maxlength', '128');
    await expect(
      page.getByLabel('Confirmar senha', { exact: false }),
    ).toHaveAttribute('maxlength', '128');
    await page
      .getByRole('button', { name: 'Criar conta', exact: true })
      .click();
    for (const name of ['name', 'email', 'password', 'confirmation']) {
      await expect(page.locator(`input[name="${name}"]`)).toBeDisabled();
    }
    await expect(
      page.getByRole('button', { name: 'Mostrar senha', exact: true }),
    ).toBeDisabled();
    await expect(
      page.getByRole('button', {
        name: 'Mostrar confirmação de senha',
        exact: true,
      }),
    ).toBeDisabled();
    expect(calls).toBe(1);
    release();
    await expect(page).toHaveURL(/\/login\?registered=1/);
    await expect(page.getByLabel('E-mail', { exact: false })).toBeEnabled();
    await expect(page.getByLabel(/^Senha/)).toHaveValue('');
  } finally {
    release();
  }
});

test('rota inexistente mostra 404 de interface', async ({ page }) => {
  await page.goto('/nao-existe');
  await expect(page.getByRole('alert')).toContainText('Página não encontrada.');
});

test('desenvolvimento descreve a arquitetura real sem consultar dados privados', async ({
  page,
}) => {
  let privateRequests = 0;
  await page.route(/\/api\/(metrics|analyses)(\/|\?|$)/, (route) => {
    privateRequests++;
    return route.fulfill({
      status: 403,
      json: { detail: 'Consulta privada não esperada.' },
    });
  });
  await page.goto('/desenvolvimento');
  const main = page.getByRole('main');
  for (const title of [
    'Arquitetura do OrangeVision',
    'Hardware e Componentes',
    'Visão Computacional',
    'Lógica de Classificação',
    'Software do OrangeVision',
    'Banco de Dados',
    'Integração do Sistema',
    'Referências Técnicas',
  ]) {
    await expect(
      main.getByRole('heading', { level: 2, name: title, exact: true }),
    ).toBeVisible();
  }
  // Navegação interna leva à seção certa.
  await main
    .getByRole('navigation', { name: 'Seções do desenvolvimento' })
    .getByRole('link', { name: 'Banco de dados' })
    .click();
  await expect(page).toHaveURL(/#banco$/);
  // As regras publicadas são as da calibração, sem atuadores físicos.
  await expect(
    main.getByText('12% ou mais da casca com manchas.'),
  ).toBeVisible();
  await expect(main.getByText(/LED verde|servo direcionado/)).toHaveCount(0);
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(
    result.violations.map((item) => ({
      id: item.id,
      targets: item.nodes.map((node) => node.target.join(' ')),
    })),
  ).toEqual([]);
  expect(privateRequests).toBe(0);
});

test('projeto mescla contexto, métricas, ODS e limites sem repetir os blocos', async ({
  page,
}) => {
  let privateRequests = 0;
  page.on('request', (request) => {
    if (/\/api\/(metrics|analyses)/.test(request.url())) privateRequests++;
  });
  await page.goto('/projeto');
  const main = page.getByRole('main');
  await expect(main.getByRole('heading', { level: 1 })).toHaveCount(1);
  for (const name of [
    'Tecnologia aplicada à citricultura',
    'Inspeção visual subjetiva e repetitiva',
    'Sistemas embarcados, visão e dados',
    'Laranja Pêra-Rio',
    'Da fruta para os dados',
    'ODS 2 — Fome Zero e Agricultura Sustentável',
    'Escopo e limitações',
    'Uma inspeção mais padronizada e rastreável',
  ]) {
    await expect(main.getByRole('heading', { name, exact: true })).toHaveCount(
      1,
    );
  }
  const metrics = main.getByRole('region', { name: 'Da fruta para os dados' });
  for (const name of [
    'Coloração',
    'Regiões anormais',
    'Forma e circularidade',
    'Assimetria',
  ]) {
    await expect(
      metrics.getByRole('heading', { name, exact: true }),
    ).toBeVisible();
  }
  await expect(
    main.getByRole('heading', { name: 'Meta 2.a', exact: true }),
  ).toBeVisible();
  await expect(
    main.getByText(/não realiza diagnóstico fitossanitário/),
  ).toBeVisible();
  await expect(main.getByText(/UUID/)).toBeVisible();
  await expect(
    main.getByText(/variedade utilizada depende da disponibilidade/),
  ).toBeVisible();
  await expect(
    main.getByRole('link', { name: 'Consultar documento da Embrapa (PDF)' }),
  ).toHaveAttribute(
    'href',
    'https://www.infoteca.cnptia.embrapa.br/bitstream/doc/681766/1/Doc55.pdf',
  );
  await expect(
    main.getByRole('link', {
      name: 'Consultar Fundecitrus — greening e psilídeo',
    }),
  ).toHaveAttribute(
    'href',
    'https://www.fundecitrus.com.br/pragas-e-doencas/greening-e-psilideo/',
  );
  await expect(
    main.getByRole('link', {
      name: 'Consultar ODS 2 e suas metas na ONU Brasil',
    }),
  ).toHaveAttribute('href', 'https://brasil.un.org/pt-br/sdgs/2');
  expect(privateRequests).toBe(0);
});

test('rodapé público tem faixa, marca e identificação acadêmica sem duplicação', async ({
  page,
}, testInfo) => {
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
    const footer = page.getByRole('contentinfo');
    await expect(footer).toHaveCount(1);
    await expect(
      footer.getByRole('link', { name: 'OrangeVision — início do site' }),
    ).toHaveCount(1);
    await expect(footer).toContainText('Engenharia • Tecnologia • Agronegócio');
    await expect(footer).toContainText(
      'Tecnologia aplicada a desafios reais do campo.',
    );
    await expect(footer).toContainText('Universidade São Francisco — USF');
    await expect(footer).toContainText('Projeto Acadêmico • 2026');
    await expect(footer).toContainText(
      'Resultados experimentais sujeitos à validação.',
    );
  }
  await page
    .getByRole('contentinfo')
    .screenshot({ path: testInfo.outputPath('rodape-publico-desktop.png') });
  for (const path of ['/login', '/registrar', '/admin/prisma']) {
    await page.goto(path);
    await expect(page.getByRole('contentinfo')).toHaveCount(0);
  }
});

test('projeto e referências passam em acessibilidade no desktop e no mobile', async ({
  page,
}, testInfo) => {
  for (const width of [390, 1366]) {
    await page.setViewportSize({ width, height: 844 });
    for (const path of ['/projeto', '/referencias']) {
      await page.goto(path);
      await expect(page.locator('h1')).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      const result = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .analyze();
      expect(
        result.violations.map((item) => ({
          id: item.id,
          nodes: item.nodes.map((node) => ({
            target: node.target,
            summary: node.failureSummary,
          })),
        })),
      ).toEqual([]);
      await page.getByRole('contentinfo').screenshot({
        path: testInfo.outputPath(`rodape-${width}-${path.slice(1)}.png`),
      });
      if (path === '/projeto') {
        await page.screenshot({
          path: testInfo.outputPath(`projeto-${width}.png`),
          fullPage: true,
        });
        await page
          .getByRole('link', {
            name: 'Consultar ODS 2 e suas metas na ONU Brasil',
          })
          .focus();
        await expect(
          page.getByRole('link', {
            name: 'Consultar ODS 2 e suas metas na ONU Brasil',
          }),
        ).toBeFocused();
      }
    }
  }
});

test('cadastro envia apenas campos do contrato e não autentica automaticamente', async ({
  page,
}) => {
  let submitted: Record<string, string> | undefined;
  await page.route('**/api/auth/register', (route) => {
    submitted = route.request().postDataJSON();
    return route.fulfill({
      status: 201,
      json: { message: 'Cadastro concluído. Entre para continuar.' },
    });
  });
  await page.goto('/registrar');
  await page.getByLabel('Nome', { exact: false }).fill('Pessoa Teste');
  await page.getByLabel('E-mail', { exact: false }).fill('person@example.com');
  await page.getByLabel(/^Senha/).fill('uma frase bastante longa');
  await page
    .getByLabel('Confirmar senha', { exact: false })
    .fill('uma frase bastante longa');
  await page.getByRole('button', { name: 'Criar conta', exact: true }).click();
  await expect(page).toHaveURL(/\/login\?registered=1/);
  await expect(page.getByRole('alert')).toContainText(
    'Conta criada. Entre para continuar.',
  );
  expect(submitted).toEqual({
    name: 'Pessoa Teste',
    email: 'person@example.com',
    password: 'uma frase bastante longa',
  });
});

test('envios concorrentes do formulário não duplicam a solicitação', async ({
  page,
}) => {
  let calls = 0;
  await page.route('**/api/auth/login', async (route) => {
    calls++;
    await new Promise((resolve) => setTimeout(resolve, 300));
    await route.fulfill({
      status: 401,
      json: { detail: 'Credenciais inválidas' },
    });
  });
  await page.goto('/login');
  await page.getByLabel('E-mail', { exact: false }).fill('person@example.com');
  await page.getByLabel(/^Senha/).fill('uma frase bastante longa');
  await page.locator('form').evaluate((form) => {
    form.requestSubmit();
    form.requestSubmit();
  });
  await expect(page.getByRole('alert')).toContainText(
    'E-mail ou senha inválidos.',
  );
  expect(calls).toBe(1);
});

test('login tem layout independente e alternância de senha acessível', async ({
  page,
}, testInfo) => {
  await page.goto('/login');
  await expect(
    page.getByRole('navigation', { name: 'Navegação principal' }),
  ).toHaveCount(0);
  const password = page.getByLabel(/^Senha/);
  await password.fill('uma frase bastante longa');
  await expect(password).toHaveAttribute('type', 'password');
  await page
    .getByRole('button', { name: 'Mostrar senha', exact: true })
    .click();
  await expect(password).toHaveAttribute('type', 'text');
  await page
    .getByRole('button', { name: 'Ocultar senha', exact: true })
    .click();
  await expect(password).toHaveAttribute('type', 'password');
  await password.fill('');
  await expect(
    page.getByRole('button', { name: 'Entrar', exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath('login-layout.png'),
    fullPage: true,
  });
});

test('autenticação passa nas verificações automáticas de acessibilidade', async ({
  page,
}) => {
  for (const route of ['/login', '/registrar']) {
    await page.goto(route);
    await expect(page.locator('h1')).toBeVisible();
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

test('página inicial tem menu lateral e navegação pública sem consultar métricas privadas', async ({
  page,
}, testInfo) => {
  let privateRequests = 0;
  page.on('request', (request) => {
    if (/\/api\/(metrics|analyses)/.test(request.url())) privateRequests++;
  });
  await page.goto('/');
  const nav = page.getByRole('navigation', { name: 'Navegação principal' });
  await expect(nav).toBeVisible();
  await expect(
    nav.getByRole('link', { name: 'Início', exact: true }),
  ).toHaveAttribute('aria-current', 'page');
  await expect(
    nav.getByRole('link', { name: 'Dashboard', exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath('inicio-sidebar.png'),
    fullPage: true,
  });
  await nav.getByRole('link', { name: 'O Projeto', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'O Projeto', exact: true }),
  ).toBeVisible();
  await expect(
    nav.getByRole('link', { name: 'O Projeto', exact: true }),
  ).toHaveAttribute('aria-current', 'page');
  expect(privateRequests).toBe(0);
});

test('menu público móvel abre, navega e mantém login opcional para ler o projeto', async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 850 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Abrir menu' }).click();
  const nav = page.getByRole('navigation', { name: 'Navegação principal' });
  await expect(nav).toBeVisible();
  await nav.getByRole('link', { name: 'O Projeto', exact: true }).click();
  await expect(page).toHaveURL(/\/projeto$/);
  await expect(nav).toBeHidden();
  await expect(page.getByRole('heading', { name: 'O Projeto' })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test('sidebar pública encaminha dashboard ao login quando não existe sessão', async ({
  page,
}) => {
  await page.goto('/');
  await page
    .getByRole('navigation', { name: 'Navegação principal' })
    .getByRole('link', { name: 'Dashboard', exact: true })
    .click();
  await expect(page).toHaveURL(/\/login\?next=/);
});

test('página institucional com sidebar passa nas verificações de acessibilidade', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page.locator('h1')).toBeVisible();
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(
    result.violations.map((item) => ({
      id: item.id,
      nodes: item.nodes.map((node) => ({
        target: node.target,
        summary: node.failureSummary,
      })),
    })),
  ).toEqual([]);
});

test('mudar de mobile para desktop com menu aberto não bloqueia o conteúdo público', async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 850 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Abrir menu' }).click();
  await expect(
    page.getByRole('navigation', { name: 'Navegação principal' }),
  ).toBeVisible();
  await page.setViewportSize({ width: 1280, height: 900 });
  await expect(page.getByRole('main')).toBeVisible();
  await page
    .getByRole('navigation', { name: 'Navegação principal' })
    .getByRole('link', { name: 'O Projeto', exact: true })
    .click();
  await expect(
    page.getByRole('heading', { name: 'O Projeto', exact: true }),
  ).toBeVisible();
});
