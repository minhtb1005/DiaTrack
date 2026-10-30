import { test, expect } from '@playwright/test';

test('registration asks for a self-reported diabetes type', async ({ page }) => {
  await page.goto('/register');
  await expect(page.getByLabel('Loại đái tháo đường theo hồ sơ của bạn')).toBeVisible();
  await expect(page.getByText('Đây là thông tin bạn tự khai báo, không phải chẩn đoán.')).toBeVisible();
  await expect(page.getByLabel('Loại đái tháo đường theo hồ sơ của bạn')).toHaveValue('unknown');
  await page.getByLabel('Loại đái tháo đường theo hồ sơ của bạn').selectOption('type2');
  await expect(page.getByLabel('Loại đái tháo đường theo hồ sơ của bạn')).toHaveValue('type2');
});

test('existing patient can update type in settings', async ({ page }) => {
  await page.addInitScript(() => {
    let saved = 'unknown';
    const originalFetch = window.fetch.bind(window);
    window.fetch = (input, init) => {
      const url = String(input);
      if (url.endsWith('/v1/auth/me/diabetes-type')) saved = JSON.parse(String(init?.body)).diabetes_type;
      if (url.endsWith('/v1/auth/me') || url.endsWith('/v1/auth/me/diabetes-type')) {
        return Promise.resolve(new Response(JSON.stringify({ id: 'u', username: 'u', role: 'user', diabetes_type: saved, is_active: true, is_verified: true }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (url.endsWith('/v1/auth/refresh')) {
        return Promise.resolve(new Response(JSON.stringify({ user: { id: 'u', username: 'u', role: 'user', diabetes_type: saved, is_active: true, is_verified: true } }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      return originalFetch(input, init);
    };
  });
  await page.goto('/settings');
  const selector = page.getByLabel('Chọn loại theo hồ sơ bác sĩ');
  await expect(selector).toHaveValue('unknown');
  await selector.selectOption('type2');
  await expect(page.getByRole('status')).toContainText('Đã lưu');
  await expect(selector).toHaveValue('type2');
});
