import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: '**/mobile-web.spec.js',
  timeout: 30_000,
  fullyParallel: false,
  reporter: [['line'], ['html', { outputFolder: 'playwright-mobile-report', open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:4174',
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
      command: 'python3 -m http.server 4174 --directory ../mobile/dist',
      cwd: '.',
      url: 'http://127.0.0.1:4174',
      reuseExistingServer: true,
      timeout: 30_000,
    },
  ],
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
