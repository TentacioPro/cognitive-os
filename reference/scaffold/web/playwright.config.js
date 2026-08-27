import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: ['**/dashboard.spec.js', '**/responsive.spec.js', '**/performance.spec.js'],
  timeout: 30_000,
  fullyParallel: false,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command: 'node src/index.js',
      cwd: '../backend',
      url: 'http://127.0.0.1:3000/api/health',
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      command: 'npm run dev -- --port 4173',
      cwd: '.',
      url: 'http://127.0.0.1:4173',
      reuseExistingServer: true,
      timeout: 30_000,
    },
  ],
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
