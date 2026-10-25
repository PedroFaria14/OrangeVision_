import assert from 'node:assert/strict';
import { once } from 'node:events';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import {
  createServer as createHttpServer,
  request as httpRequest,
} from 'node:http';
import { join } from 'node:path';
import test from 'node:test';
import { chromium } from 'playwright-core';
import { createServer } from 'vite';
import { createDevApiProxy } from '../dev-api-proxy.ts';

test('proxy local: cookie de produção, origem, CSRF e isolamento de cookies', async () => {
  const base = join(process.cwd(), 'test-results', 'proxy-check');
  await mkdir(base, { recursive: true });
  const root = await mkdtemp(join(base, 'case-'));
  await writeFile(
    join(root, 'index.html'),
    '<html><head><title>Proxy fixture</title></head><body>Teste local</body></html>',
  );
  let upstreamOrigin = '';
  const requests: {
    origin?: string;
    cookie?: string;
    csrf?: string;
    url?: string;
  }[] = [];
  const upstream = createHttpServer((req, res) => {
    requests.push({
      origin: req.headers.origin,
      cookie: req.headers.cookie,
      csrf: String(req.headers['x-csrf-token'] || ''),
      url: req.url,
    });
    res.setHeader('Content-Type', 'application/json');
    if (req.method === 'POST' && req.headers.origin !== upstreamOrigin) {
      res.writeHead(403);
      res.end('{}');
      return;
    }
    if (req.url === '/api/auth/login') {
      res.setHeader('Set-Cookie', [
        'orangevision_session=synthetic-session; Domain=api.example.test; Path=/api; HttpOnly; Secure; SameSite=Lax; Max-Age=3600',
        'unrelated_remote=never-copy; Path=/; Secure',
      ]);
      res.end(JSON.stringify({ csrf_token: 'synthetic-csrf' }));
      return;
    }
    if (req.url === '/api/auth/logout') {
      res.setHeader(
        'Set-Cookie',
        'orangevision_session=; Domain=api.example.test; Path=/api; HttpOnly; Secure; SameSite=Lax; Max-Age=0',
      );
      res.writeHead(204);
      res.end();
      return;
    }
    if (
      req.url === '/api/auth/session' &&
      !req.headers.cookie?.includes('orangevision_session=synthetic-session')
    ) {
      res.writeHead(401);
      res.end('{}');
      return;
    }
    res.end(JSON.stringify({ ok: true }));
  });
  upstream.listen(0, '127.0.0.1');
  await once(upstream, 'listening');
  const address = upstream.address();
  assert(address && typeof address !== 'string');
  upstreamOrigin = `http://127.0.0.1:${address.port}`;
  const reservation = createHttpServer();
  reservation.listen(0, '127.0.0.1');
  await once(reservation, 'listening');
  const free = reservation.address();
  assert(free && typeof free !== 'string');
  await new Promise<void>((resolve) => reservation.close(() => resolve()));
  const api = createDevApiProxy(upstreamOrigin);
  assert.equal(api.proxy.secure, true);
  assert.throws(() => createDevApiProxy('http://external.example'));
  assert.throws(() => createDevApiProxy('https://user:secret@example.com'));
  assert.throws(() => createDevApiProxy('https://example.com/api'));
  const vite = await createServer({
    configFile: false,
    root,
    logLevel: 'silent',
    plugins: [api.plugin],
    optimizeDeps: { noDiscovery: true },
    server: {
      host: '127.0.0.1',
      port: free.port,
      strictPort: true,
      proxy: { '/api': api.proxy },
    },
  });
  let browser: Awaited<ReturnType<typeof chromium.launch>> | undefined;
  try {
    await vite.listen();
    const front = `http://127.0.0.1:${free.port}`;
    const before = requests.length;
    for (const headers of [{ Origin: 'https://evil.example' }, {}]) {
      const response = await fetch(front + '/api/auth/login', {
        method: 'POST',
        headers,
        body: '{}',
      });
      assert.equal(response.status, 403);
      await response.text();
    }
    assert.equal(requests.length, before);
    const hostileHost = await new Promise<number | undefined>(
      (resolve, reject) => {
        const request = httpRequest(
          front + '/api/auth/login',
          { method: 'POST', headers: { Host: 'evil.example', Origin: front } },
          (response) => {
            response.resume();
            response.on('end', () => resolve(response.statusCode));
          },
        );
        request.on('error', reject);
        request.end('{}');
      },
    );
    assert.equal(hostileHost, 403);
    assert.equal(requests.length, before);
    const transport = await fetch(front + '/api/echo?value=test', {
      method: 'POST',
      headers: {
        Origin: front,
        Cookie:
          'unrelated_local=do-not-leak; orangevision_session=synthetic-session',
        'X-CSRF-Token': 'synthetic-csrf',
      },
      body: '{}',
    });
    assert.equal(transport.status, 200);
    await transport.text();
    assert.equal(requests.at(-1)?.origin, upstreamOrigin);
    assert.equal(
      requests.at(-1)?.cookie,
      'orangevision_session=synthetic-session',
    );
    assert.equal(requests.at(-1)?.csrf, 'synthetic-csrf');
    assert.equal(requests.at(-1)?.url, '/api/echo?value=test');
    browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto(front);
    assert.equal(
      await page.evaluate(
        async () =>
          (
            await fetch('/api/auth/login', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: '{}',
            })
          ).status,
      ),
      200,
    );
    const cookies = await context.cookies(front + '/api/auth/session');
    const session = cookies.find(
      (cookie) => cookie.name === 'orangevision_session',
    );
    assert(session);
    assert.equal(session.httpOnly, true);
    assert.equal(session.sameSite, 'Lax');
    assert.equal(session.secure, false);
    assert.equal(session.path, '/api');
    assert(!cookies.some((cookie) => cookie.name === 'unrelated_remote'));
    assert(
      !(await page.evaluate(() => document.cookie)).includes(
        'orangevision_session',
      ),
    );
    assert.equal(
      await page.evaluate(
        async () => (await fetch('/api/auth/session')).status,
      ),
      200,
    );
    assert.equal(
      await page.evaluate(
        async () =>
          (
            await fetch('/api/auth/logout', {
              method: 'POST',
              headers: { 'X-CSRF-Token': 'synthetic-csrf' },
            })
          ).status,
      ),
      204,
    );
    assert.equal(
      await page.evaluate(
        async () => (await fetch('/api/auth/session')).status,
      ),
      401,
    );
    await context.close();
  } finally {
    await browser?.close();
    await vite.close();
    upstream.closeAllConnections();
    await new Promise<void>((resolve) => upstream.close(() => resolve()));
    await rm(root, { recursive: true, force: true });
  }
});
