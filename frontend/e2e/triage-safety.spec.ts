import { test, expect } from './fixtures';

test('triage shows exact scope refusal and emergency action', async ({ page }) => {
  await page.route('**/v1/auth/me', route => route.fulfill({ json: {
    id: 'triage_user', username: 'triage_user', role: 'user', diabetes_type: 'type2', is_active: true,
  }}));
  await page.route('**/v1/glucose/*', route => route.fulfill({ json: {
    user_id: 'triage_user', logs: [], stats: { total_logs: 0, classification_counts: {} },
    should_escalate: false, anomaly_ids: [],
  }}));
  await page.route('**/v1/triage', async route => {
    const message = (await route.request().postDataJSON()).message;
    await route.fulfill({ json: message.includes('huyết áp')
      ? { emergency: false, message: 'Hệ thống chỉ hỗ trợ theo dõi đái tháo đường. Nội dung này nằm ngoài phạm vi an toàn của hệ thống, vui lòng hỏi bác sĩ ở lần khám tới.', recommended_doctors: [] }
      : { emergency: true, message: 'Gọi 115 ngay lập tức hoặc đến cơ sở y tế gần nhất.', recommended_doctors: [] },
    });
  });
  await page.goto('/tracker');
  await page.getByRole('button', { name: 'Mở' }).last().click();
  const input = page.getByRole('textbox', { name: 'Triệu chứng và thời gian muốn khám' });
  await input.fill('hỏi về huyết áp');
  await input.press('Enter');
  await expect(page.getByText('Hệ thống chỉ hỗ trợ theo dõi đái tháo đường. Nội dung này nằm ngoài phạm vi an toàn của hệ thống, vui lòng hỏi bác sĩ ở lần khám tới.')).toBeVisible();
  await input.fill('méo miệng');
  await input.press('Enter');
  await expect(page.getByRole('link', { name: 'Gọi 115' }).last()).toBeVisible();
});
