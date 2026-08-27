import { expect, test } from '@playwright/test';

for (const viewport of [
  { name: 'phone', width: 390, height: 844 },
  { name: 'tablet', width: 768, height: 1024 },
]) {
  test(`mobile export works at ${viewport.name} size`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto('/');
    await expect(page.getByText('Cognitive OS')).toBeVisible();
    await expect(page.getByText('Make your life legible.')).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Capture' })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
    expect(overflow).toBe(true);
    await page.getByRole('tab', { name: 'Capture' }).click();
    await expect(page.getByText('What is present?')).toBeVisible();
    await expect(page.getByLabel('Observation')).toBeEditable();
  });
}
