import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/browser',
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  use: { baseURL: 'http://127.0.0.1:3001', headless: true },
  webServer: {
    command: 'npm run start',
    url: 'http://127.0.0.1:3001/login',
    reuseExistingServer: false,
    timeout: 60000,
  },
});
