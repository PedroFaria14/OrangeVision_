import assert from 'node:assert/strict';
import { once } from 'node:events';
import { createServer as httpServer } from 'node:http';
import test from 'node:test';
import { createServer } from 'vite';
import { createRenderStatusPlugin, probeApiHealth } from '../dev-api-status.ts';

test('health: identidade, HTTP 503, JSON inválido, redirect e timeout', async (t) => {
  let mode = 'healthy';
  let receivedCookie: string | undefined;
  let receivedAuthorization: string | undefined;
  const upstream = httpServer((req, res) => {
    receivedCookie = req.headers.cookie;
    receivedAuthorization = req.headers.authorization;
    assert.equal(req.url, '/health');
    if (mode === 'timeout') return;
    if (mode === 'redirect') {
      res.writeHead(302, { Location: '/must-not-follow' });
      res.end();
      return;
    }
    if (mode === '503') {
      res.writeHead(503);
      res.end('Private upstream error must not be exposed');
      return;
    }
    res.setHeader('Content-Type', 'application/json');
    res.end(
      mode === 'invalid'
        ? '<html>Not JSON</html>'
        : mode === 'large'
          ? 'x'.repeat(9000)
          : JSON.stringify({
              status: 'ok',
              service:
                mode === 'wrong-service' ? 'another-api' : 'orangevision-web',
            }),
    );
  });
  upstream.listen(0, '127.0.0.1');
  await once(upstream, 'listening');
  const address = upstream.address();
  assert(address && typeof address !== 'string');
  const origin = `http://127.0.0.1:${address.port}`;
  try {
    for (const [scenario, expected] of [
      ['healthy', 'available'],
      ['503', 'unavailable'],
      ['invalid', 'unexpected'],
      ['wrong-service', 'unexpected'],
      ['large', 'unexpected'],
      ['redirect', 'unavailable'],
      ['timeout', 'unreachable'],
    ]) {
      await t.test(scenario, async () => {
        mode = scenario;
        const result = await probeApiHealth(
          origin,
          scenario === 'timeout' ? 50 : 2000,
        );
        assert.equal(result.state, expected);
        assert.equal(
          result.httpStatus,
          scenario === '503'
            ? 503
            : scenario === 'redirect'
              ? 302
              : scenario === 'timeout'
                ? null
                : 200,
        );
        assert(Number.isFinite(Date.parse(result.checkedAt)));
        assert(result.durationMs >= 0);
        assert.equal(receivedCookie, undefined);
        assert.equal(receivedAuthorization, undefined);
        assert(!JSON.stringify(result).includes('Private upstream'));
      });
    }
    await assert.rejects(probeApiHealth('http://external.example'));
    await assert.rejects(probeApiHealth('https://user:secret@example.com'));
  } finally {
    upstream.closeAllConnections();
    await new Promise<void>((resolve) => upstream.close(() => resolve()));
  }
});

test('gateway: destino fixo, cache, requisições simultâneas e método GET', async () => {
  let calls = 0;
  const plugin = createRenderStatusPlugin(async () => {
    calls++;
    await new Promise((resolve) => setTimeout(resolve, 30));
    return {
      state: 'unavailable',
      checkedAt: new Date().toISOString(),
      durationMs: 10,
      httpStatus: 503,
    };
  });
  const reservation = httpServer();
  reservation.listen(0, '127.0.0.1');
  await once(reservation, 'listening');
  const address = reservation.address();
  assert(address && typeof address !== 'string');
  await new Promise<void>((resolve) => reservation.close(() => resolve()));
  const vite = await createServer({
    configFile: false,
    logLevel: 'silent',
    plugins: [plugin],
    optimizeDeps: { noDiscovery: true },
    server: { host: '127.0.0.1', port: address.port, strictPort: true },
  });
  try {
    await vite.listen();
    const url = `http://127.0.0.1:${address.port}/api/status/render`;
    const responses = await Promise.all([
      fetch(url),
      fetch(url + '?url=http://must-not-be-used.example'),
    ]);
    for (const response of responses) {
      assert.equal(response.status, 200);
      assert.equal(response.headers.get('cache-control'), 'no-store');
      assert.equal((await response.json()).httpStatus, 503);
      assert.equal(response.headers.get('set-cookie'), null);
    }
    assert.equal(calls, 1);
    await (await fetch(url)).text();
    assert.equal(calls, 1);
    assert.equal((await fetch(url, { method: 'POST' })).status, 405);
    assert.equal(calls, 1);
  } finally {
    await vite.close();
  }
});
