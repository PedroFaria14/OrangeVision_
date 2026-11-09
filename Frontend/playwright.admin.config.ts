import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/admin/browser',
  workers: 1,
  timeout: 30000,
  outputDir: './test-results/admin',
  use: {
    baseURL: 'http://127.0.0.1:4178',
    browserName: 'chromium',
    reducedMotion: 'reduce',
  },
  webServer: {
    command: 'corepack yarn preview --port 4178 --strictPort',
    url: 'http://127.0.0.1:4178/admin/prisma',
    reuseExistingServer: false,
  },
});
