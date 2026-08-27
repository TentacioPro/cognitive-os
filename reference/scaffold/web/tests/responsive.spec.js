import { expect, test } from '@playwright/test';

const viewports = [
  { name: 'mobile', width: 375, height: 812 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1440, height: 900 },
];

for (const viewport of viewports) {
  test(`keeps the ${viewport.name} layout navigable and free of horizontal overflow`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto('/#/dashboard');
    await expect(page.getByRole('heading', { name: /Make your life/i })).toBeVisible();
    await expect(page.getByTestId('nav-capture')).toBeVisible();
    await expect(page.getByTestId('nav-review')).toBeVisible();
    await expect(page.getByTestId('nav-system')).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
    expect(overflow, `${viewport.name} page overflows horizontally`).toBe(true);
    await page.getByTestId('nav-capture').click();
    await expect(page.getByRole('heading', { name: 'What is present?' })).toBeVisible();
    await expect(page.getByLabel('Observation')).toBeEditable();
  });
}
