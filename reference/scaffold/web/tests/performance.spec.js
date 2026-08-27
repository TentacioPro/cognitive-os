import { expect, test } from '@playwright/test';

test('dashboard stays within local performance budgets', async ({ page }) => {
  const started = Date.now();
  await page.goto('/#/dashboard');
  await expect(page.getByRole('heading', { name: /Make your life/i })).toBeVisible();
  const elapsedMs = Date.now() - started;
  const metrics = await page.evaluate(() => {
    const navigation = performance.getEntriesByType('navigation')[0];
    const resources = performance.getEntriesByType('resource');
    const scriptBytes = resources.filter((resource) => resource.name.endsWith('.js')).reduce((sum, resource) => sum + (resource.transferSize || 0), 0);
    const longTasks = performance.getEntriesByType('longtask');
    return { domContentLoaded: navigation?.domContentLoadedEventEnd || 0, loadEvent: navigation?.loadEventEnd || 0, scriptBytes, longTasks: longTasks.length };
  });
  expect(elapsedMs).toBeLessThan(2_000);
  expect(metrics.scriptBytes).toBeLessThan(500_000);
  expect(metrics.longTasks).toBeLessThan(3);
});
