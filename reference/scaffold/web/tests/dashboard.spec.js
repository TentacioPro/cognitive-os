import { expect, test } from '@playwright/test';

async function openApp(page) {
  await page.goto('/#/dashboard');
  await expect(page.getByRole('heading', { name: /Make your life/i })).toBeVisible();
  await expect(page.getByText('Local system online')).toBeVisible();
}

test.describe('Cognitive OS web UX', () => {
  test('loads the dashboard and exposes primary navigation', async ({ page }) => {
    await openApp(page);
    await expect(page.getByTestId('nav-capture')).toBeVisible();
    await expect(page.getByTestId('nav-review')).toBeVisible();
    await expect(page.getByTestId('nav-system')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Recent entries' })).toBeVisible();
  });

  test('navigates to capture, stages an observation, reviews it, and confirms it', async ({ page }) => {
    await openApp(page);
    await page.getByTestId('nav-capture').click();
    await expect(page.getByRole('heading', { name: 'What is present?' })).toBeVisible();
    const content = `Playwright capture ${Date.now()}`;
    await page.getByLabel('Observation').fill(content);
    await page.getByLabel('Value').fill('25');
    await page.getByLabel('Unit').fill('minutes');
    await page.getByLabel('Energy / 10').fill('7');
    await page.getByTestId('capture-submit').click();
    await expect(page.getByRole('heading', { name: 'See the pattern.' })).toBeVisible();
    const card = page.getByText(content).first();
    await expect(card).toBeVisible();
    const entryCard = card.locator('..');
    const confirmButton = entryCard.getByRole('button', { name: 'Confirm entry' });
    await expect(confirmButton).toBeVisible();
    await confirmButton.click();
    await expect(entryCard.getByText('committed')).toBeVisible();
  });

  test('system page shows the four-layer architecture and audit trace', async ({ page }) => {
    await openApp(page);
    await page.getByTestId('nav-system').click();
    await expect(page.getByRole('heading', { name: 'How it holds.' })).toBeVisible();
    for (const layer of ['Capture', 'Extract', 'Store', 'Review']) {
      await expect(page.getByRole('heading', { name: layer })).toBeVisible();
    }
    await expect(page.getByRole('heading', { name: 'Recent audit events' })).toBeVisible();
  });
});
