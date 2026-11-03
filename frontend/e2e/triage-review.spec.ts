import { test, expect } from './fixtures';

test('nurse revises a pending triage case', async ({ page }) => {
  await page.route('**/v1/auth/me', route => route.fulfill({ json: {
    id: 'nurse-1', username: 'nurse', role: 'nurse', is_active: true, is_verified: true,
  }}));
  await page.route('**/v1/triage/reviews/pending', route => route.fulfill({ json: { cases: [{
    id: 'case-1', requester_id: 'patient-1', message: 'tê chân, mắt mờ', latest_glucose_mgdl: 180,
    symptom_onset: 'hôm qua', proposed_priority: 'soon', rationale: 'Cần xem xét.',
    source: 'docs/project_requirements.json#scope_rules', created_at: '2026-10-30T09:00:00Z',
  }] } }));
  let decision: any = null;
  await page.route('**/v1/triage/reviews/case-1/decide', async route => {
    decision = await route.request().postDataJSON();
    await route.fulfill({ json: { id: 'case-1', status: 'revised', final_priority: decision.priority } });
  });
  await page.goto('/expert/triage');
  await expect(page.getByText('Ca phân luồng chờ duyệt')).toBeVisible();
  await page.getByRole('button', { name: 'Xem và duyệt' }).click();
  await page.getByRole('combobox', { name: 'Mức ưu tiên cuối' }).selectOption('routine');
  await page.getByRole('textbox', { name: 'Thông báo cho bệnh nhân' }).fill('Vui lòng liên hệ cơ sở y tế để được tư vấn.');
  await page.getByRole('textbox', { name: 'Ghi chú kiểm toán' }).fill('Đã kiểm tra triệu chứng.');
  await page.getByRole('button', { name: 'Sửa và duyệt' }).click();
  await expect(page.getByText('Không có ca chờ duyệt.')).toBeVisible();
  expect(decision).toMatchObject({ decision: 'revised', priority: 'routine', notes: 'Đã kiểm tra triệu chứng.' });
});

test('patient sees reviewed message after pending status', async ({ page }) => {
  await page.route('**/v1/auth/me', route => route.fulfill({ json: {
    id: 'patient-1', username: 'patient', role: 'user', diabetes_type: 'type2', is_active: true,
  }}));
  await page.route('**/v1/glucose/*', route => route.fulfill({ json: {
    user_id: 'patient-1', logs: [], stats: { total_logs: 0, classification_counts: {} }, should_escalate: false, anomaly_ids: [],
  }}));
  await page.route('**/v1/triage', route => route.fulfill({ json: {
    emergency: false, case_id: 'case-1', review_status: 'pending_clinician_review',
    message: 'Đã gửi thông tin cho điều dưỡng duyệt. Chưa có hướng xử trí được phê duyệt.', recommended_doctors: [],
  }}));
  await page.route('**/v1/triage/reviews/case-1', route => route.fulfill({ json: {
    id: 'case-1', status: 'revised', priority: 'soon', message: 'Vui lòng liên hệ cơ sở y tế để được khám sớm.',
  }}));
  await page.goto('/tracker');
  await page.getByRole('button', { name: 'Mở' }).last().click();
  await page.getByRole('spinbutton', { name: 'Đường huyết gần nhất mg/dL' }).fill('180');
  await page.getByRole('textbox', { name: 'Triệu chứng bắt đầu từ khi nào' }).fill('hôm qua');
  await page.getByRole('textbox', { name: 'Triệu chứng và thời gian muốn khám' }).fill('tê chân, mắt mờ');
  await page.getByRole('textbox', { name: 'Triệu chứng và thời gian muốn khám' }).press('Enter');
  await expect(page.getByText('Đã gửi thông tin cho điều dưỡng duyệt. Chưa có hướng xử trí được phê duyệt.')).toBeVisible();
  await expect(page.getByText('Vui lòng liên hệ cơ sở y tế để được khám sớm.')).toBeVisible({ timeout: 12000 });
});
