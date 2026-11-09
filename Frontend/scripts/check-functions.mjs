import assert from 'node:assert/strict';
import console from 'node:console';
import { mkdtemp, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import process from 'node:process';
import { fileURLToPath, pathToFileURL, URL } from 'node:url';
import ts from 'typescript';

const { Request, Response } = globalThis;
const root = fileURLToPath(new URL('..', import.meta.url));
// Dentro de node_modules: artefatos ignorados pelo Git e resolução normal dos pacotes.
const output = await mkdtemp(join(root, 'node_modules', '.functions-check-'));
const previousEnv = { ...process.env };
const previousFetch = globalThis.fetch;

try {
  const configFile = ts.readConfigFile(
    join(root, 'tsconfig.json'),
    ts.sys.readFile,
  );
  if (configFile.error)
    throw new Error(
      ts.flattenDiagnosticMessageText(configFile.error.messageText, '\n'),
    );
  const config = ts.parseJsonConfigFileContent(configFile.config, ts.sys, root);
  const files = ts.sys.readDirectory(
    root,
    ['.ts'],
    ['node_modules'],
    ['api/**/*.ts', 'server/**/*.ts'],
  );
  const program = ts.createProgram(files, {
    ...config.options,
    module: ts.ModuleKind.NodeNext,
    moduleResolution: ts.ModuleResolutionKind.NodeNext,
    types: ['node'],
    noEmit: false,
    noEmitOnError: true,
    allowImportingTsExtensions: false,
    rootDir: root,
    outDir: output,
  });
  const result = program.emit();
  const diagnostics = [
    ...config.errors,
    ...ts.getPreEmitDiagnostics(program),
    ...result.diagnostics,
  ];
  if (diagnostics.length || result.emitSkipped) {
    console.error(
      ts.formatDiagnosticsWithColorAndContext(diagnostics, {
        getCanonicalFileName: (name) => name,
        getCurrentDirectory: () => root,
        getNewLine: () => '\n',
      }),
    );
    throw new Error(
      'As funções não podem ser emitidas como JavaScript Node/ESM.',
    );
  }
  await writeFile(join(output, 'package.json'), '{"type":"module"}\n');

  async function checkImports(directory) {
    for (const file of await readdir(directory, { withFileTypes: true })) {
      const path = join(directory, file.name);
      if (file.isDirectory()) await checkImports(path);
      else if (file.name.endsWith('.js')) {
        assert.doesNotMatch(
          await readFile(path, 'utf8'),
          /\bfrom\s+['"]\.{1,2}\/[^'"]+\.tsx?['"]/,
          `Import TypeScript preservado no artefato ${file.name}`,
        );
      }
    }
  }
  await checkImports(output);

  Object.assign(process.env, {
    NEXTAUTH_URL: 'https://admin-functions.example.test',
    NEXTAUTH_SECRET: 'functions-check-only-'.repeat(4),
    GITHUB_CLIENT_ID: 'functions-check',
    GITHUB_CLIENT_SECRET: 'functions-check',
    ADMIN_GITHUB_ID: '12345',
    VERCEL: '1',
    RENDER_API_ORIGIN: '',
    API_PROXY_TARGET: '',
  });
  delete process.env.STUDIO_DATABASE_URL;
  // Nenhuma consulta ao GitHub, Render ou banco real durante a validação do build.
  globalThis.fetch = async () => {
    throw new Error('Acesso externo não permitido no teste de artefatos.');
  };

  const load = async (path) => {
    const module = await import(pathToFileURL(join(output, path)).href);
    assert.equal(typeof module.default?.fetch, 'function');
    return module.default;
  };
  const auth = await load('api/admin/auth.js');
  const studio = await load('api/admin/studio.js');
  const render = await load('api/status/render.js');
  const origin = process.env.NEXTAUTH_URL;

  for (const path of [
    '/api/admin/auth/session',
    '/api/admin/auth?__path=session',
  ]) {
    const response = await auth.fetch(new Request(`${origin}${path}`));
    assert.equal(response.status, 200);
    assert.match(response.headers.get('content-type'), /application\/json/);
    assert.equal((await response.json())?.user, undefined);
  }
  const providers = await auth.fetch(
    new Request(`${origin}/api/admin/auth/providers`),
  );
  assert.equal(providers.status, 200);
  assert.equal((await providers.json()).github.id, 'github');

  const wrongMethod = await studio.fetch(
    new Request(`${origin}/api/admin/studio`),
  );
  assert.equal(wrongMethod.status, 405);
  const anonymous = await studio.fetch(
    new Request(`${origin}/api/admin/studio`, {
      method: 'POST',
      headers: { Origin: origin, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        procedure: 'query',
        query: { sql: 'SELECT 1', parameters: [] },
      }),
    }),
  );
  assert.equal(anonymous.status, 401);

  const unconfigured = await render.fetch(
    new Request(`${origin}/api/status/render`),
  );
  assert.equal(unconfigured.status, 503);
  process.env.RENDER_API_ORIGIN = 'https://render-functions.example.test';
  globalThis.fetch = async (url) => {
    assert.equal(String(url), 'https://render-functions.example.test/health');
    return Response.json({ status: 'ok', service: 'orangevision-web' });
  };
  const healthy = await render.fetch(
    new Request(`${origin}/api/status/render`),
  );
  assert.equal(healthy.status, 200);
  assert.equal((await healthy.json()).state, 'available');
  process.env.NEXTAUTH_SECRET = '';
  assert.equal(
    (await auth.fetch(new Request(`${origin}/api/admin/auth/session`))).status,
    503,
  );

  console.log(
    'Funções Node/ESM: emissão, imports JavaScript e entrypoints validados sem loader TypeScript.',
  );
} finally {
  process.env = previousEnv;
  globalThis.fetch = previousFetch;
  await rm(output, { recursive: true, force: true });
}
