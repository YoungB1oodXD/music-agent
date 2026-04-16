import { test, expect } from '@playwright/test';

const BACKEND_URL = 'http://localhost:8000';
const TEST_USER = `e2e_${Date.now()}`;
const TEST_PASSWORD = 'testpassword123';

test.describe('Mustify E2E Tests', () => {

  test('registration and login flow', async ({ page }) => {
    await page.goto('/login');

    await page.getByRole('button', { name: /立即注册/i }).click();
    await page.getByPlaceholder('your_username').fill(TEST_USER);
    await page.getByPlaceholder(/\.\.\.\.\.\.\.\./i).fill(TEST_PASSWORD);

    await page.getByRole('button', { name: /注册/i }).click();

    await page.waitForURL('http://localhost:3000/');
    await expect(page).toHaveURL('http://localhost:3000/');
  });

  test('login with existing user', async ({ page }) => {
    await page.goto('/login');

    await page.getByPlaceholder('your_username').fill(TEST_USER);
    await page.getByPlaceholder(/\.\.\.\.\.\.\.\./i).fill(TEST_PASSWORD);

    await page.getByRole('button', { name: /立即登录/i }).click();

    await page.waitForURL('http://localhost:3000/');
    await expect(page).toHaveURL('http://localhost:3000/');
  });

  test('chat interaction - send message and receive recommendations', async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('your_username').fill(TEST_USER);
    await page.getByPlaceholder(/\.\.\.\.\.\.\.\./i).fill(TEST_PASSWORD);
    await page.getByRole('button', { name: /立即登录/i }).click();
    await page.waitForURL('http://localhost:3000/');

    const input = page.locator('input[placeholder*="心情"]');
    await input.fill('我想听点放松的爵士乐');
    await input.press('Enter');

    await page.waitForTimeout(3000);

    const recommendations = page.locator('[class*="rounded-2xl"]').filter({ hasText: /爵士|Jazz/i });
    await expect(recommendations.first()).toBeVisible();
  });

  test('history page - sessions are loaded from API', async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('your_username').fill(TEST_USER);
    await page.getByPlaceholder(/\.\.\.\.\.\.\.\./i).fill(TEST_PASSWORD);
    await page.getByRole('button', { name: /立即登录/i }).click();
    await page.waitForURL('http://localhost:3000/');

    await page.getByRole('button', { name: /历史记录/i }).click();
    await expect(page).toHaveURL(/\/history/);

    const sessionCards = page.locator('[class*="bg-white"]').filter({ hasText: /对话|会话/i });
    await expect(sessionCards.first()).toBeVisible();
  });

});