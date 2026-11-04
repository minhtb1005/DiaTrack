import { test, expect } from '@playwright/test';
import { execFileSync } from 'child_process';
import path from 'path';

const api = `http://127.0.0.1:${process.env.TRIAGE_E2E_API_PORT || 8108}`;
const runDir = process.env.TRIAGE_E2E_DB_DIR!;
const python = path.resolve(__dirname, '../../.venv/Scripts/python.exe');
const inspector = path.resolve(__dirname, '../../tests/triage_e2e_inspect.py');
const finalMessage = 'Vui lòng liên hệ cơ sở y tế để được khám sớm.';

function inspect(caseId: string) {
  return JSON.parse(execFileSync(python, [inspector, runDir, caseId], { encoding: 'utf8' }));
}

test('real patient UI, verified nurse UI, API and isolated SQLite', async ({ browser }) => {
  const patient = await browser.newContext();
  const nurse = await browser.newContext();
  const patientPage = await patient.newPage();
  const nursePage = await nurse.newPage();
  try {
    const username = `triage_${Date.now()}`;
    await patientPage.goto('/register');
    await patientPage.getByLabel('Tên đăng nhập').fill(username);
    await patientPage.locator('#account-password').fill('Patient@12345');
    await patientPage.getByLabel('Loại đái tháo đường theo hồ sơ của bạn').selectOption('type2');
    await patientPage.getByRole('button', { name: 'Tạo tài khoản' }).click();
    await expect(patientPage).toHaveURL(/onboarding\/voice/);
    await patientPage.goto('/tracker');
    await patientPage.getByRole('heading', { name: 'Phân luồng triệu chứng' }).locator('..').getByRole('button', { name: 'Mở' }).click();
    await patientPage.getByRole('spinbutton', { name: 'Đường huyết gần nhất mg/dL' }).fill('180');
    await patientPage.getByRole('textbox', { name: 'Triệu chứng bắt đầu từ khi nào' }).fill('hôm qua');
    await patientPage.getByRole('textbox', { name: 'Triệu chứng và thời gian muốn khám' }).fill('tê chân, mắt mờ');
    const submitted = patientPage.waitForResponse(r => r.url() === `${api}/v1/triage` && r.request().method() === 'POST');
    await patientPage.getByRole('textbox', { name: 'Triệu chứng và thời gian muốn khám' }).press('Enter');
    const response = await submitted;
    expect(response.status()).toBe(200);
    expect(response.request().postDataJSON()).toMatchObject({ structured: true, latest_glucose_mgdl: 180 });
    const created = await response.json();
    expect(created.case_id).toBeTruthy();
    expect(created.proposed_priority).toBe('soon');
    expect(created.recommended_doctors).toEqual([]);
    await expect(patientPage.getByText('Đã gửi thông tin cho điều dưỡng duyệt. Chưa có hướng xử trí được phê duyệt.')).toBeVisible();
    await expect(patientPage.getByText(finalMessage)).toHaveCount(0);
    const caseId = created.case_id as string;
    const pending = inspect(caseId);
    expect(pending.case.status).toBe('pending');
    expect(pending.case.requester_id).toBeTruthy();
    expect(pending.case.message).toBe('tê chân, mắt mờ');
    expect(pending.case.final_message).toBeNull();
    expect(pending.audit).toEqual([]);

    const wrong = await patient.request.post(`${api}/v1/triage/reviews/${caseId}/decide`, {
      data: { decision: 'approved', message: finalMessage },
    });
    expect(wrong.status()).toBe(403);
    const wrongQueue = await patient.request.get(`${api}/v1/triage/reviews/pending`);
    expect(wrongQueue.status()).toBe(403);

    // The emergency path must bypass the pending queue and alert before nurse action.
    await patientPage.getByRole('textbox', { name: 'Triệu chứng và thời gian muốn khám' }).fill('méo miệng, yếu nửa người');
    const emergency = patientPage.waitForResponse(r => r.url() === `${api}/v1/triage` && r.request().method() === 'POST');
    await patientPage.getByRole('textbox', { name: 'Triệu chứng và thời gian muốn khám' }).press('Enter');
    const emergencyResponse = await emergency;
    expect(emergencyResponse.status()).toBe(200);
    const red = await emergencyResponse.json();
    expect(red.emergency).toBe(true);
    expect(red.case_id).toBeNull();
    expect(red.message).toContain('115');
    await expect(patientPage.getByText(/CẢNH BÁO CẤP CỨU: Gọi 115/)).toBeVisible();
    expect(inspect(caseId).case.status).toBe('pending');

    await nursePage.goto('/login');
    await nursePage.getByLabel('Tên đăng nhập').fill('triage_nurse');
    await nursePage.locator('#account-password').fill('Nurse@12345');
    await nursePage.getByRole('button', { name: 'Đăng nhập' }).click();
    await expect(nursePage).toHaveURL(/tracker/);
    await nursePage.goto('/expert/triage');
    await expect(nursePage.getByText('Ca phân luồng chờ duyệt')).toBeVisible();
    const initialAudit = await nurse.request.get(`${api}/v1/triage/audit/report`);
    expect(initialAudit.status()).toBe(200);
    expect(JSON.stringify(await initialAudit.json())).not.toContain('requester_id');
    await expect(nursePage.getByRole('region', { name: 'Báo cáo kiểm toán' })).toContainText('chưa có dữ liệu');
    await expect(nursePage.getByText('tê chân, mắt mờ')).toBeVisible();
    const reviewer = inspect(caseId).reviewer;
    expect(reviewer.role).toBe('nurse');
    expect(reviewer.is_verified).toBe(1);
    await nursePage.getByRole('button', { name: 'Xem và duyệt' }).first().click();
    const handoff = nursePage.getByRole('region', { name: 'Phiếu bàn giao' });
    await expect(handoff).toContainText('Triệu chứng: tê chân, mắt mờ');
    await expect(handoff).toContainText('Đường huyết: 180 mg/dL');
    await expect(handoff).toContainText('Khởi phát: hôm qua');
    await expect(handoff).toContainText('Dữ kiện thiếu: Không có');
    await expect(handoff).toContainText('không phải chẩn đoán');
    await expect(handoff.getByRole('link')).toHaveCount(2);
    await expect(handoff.getByRole('link').first()).toHaveAttribute('href', /project_requirements\.json$/);
    await nursePage.getByRole('combobox', { name: 'Mức ưu tiên cuối' }).selectOption('routine');
    await nursePage.getByRole('textbox', { name: 'Thông báo cho bệnh nhân' }).fill(finalMessage);
    await nursePage.getByRole('textbox', { name: 'Ghi chú kiểm toán' }).fill('Đã đối chiếu dữ kiện thử.');
    const decided = nursePage.waitForResponse(r => r.url() === `${api}/v1/triage/reviews/${caseId}/decide` && r.request().method() === 'POST');
    await nursePage.getByRole('button', { name: 'Sửa và duyệt' }).click();
    expect((await decided).status()).toBe(200);
    const stored = inspect(caseId);
    expect(stored.case.status).toBe('revised');
    expect(stored.case.reviewer_id).toBe(reviewer.id);
    expect(stored.case.final_priority).toBe('routine');
    expect(stored.case.final_message).toBe(finalMessage);
    expect(Date.parse(stored.case.reviewed_at)).toBeGreaterThanOrEqual(Date.parse(stored.case.created_at));
    expect(stored.audit).toHaveLength(1);
    expect(stored.audit[0]).toMatchObject({ actor_id: reviewer.id, action: 'revised',
      previous_priority: pending.case.proposed_priority, final_priority: 'routine',
      previous_message: 'tê chân, mắt mờ', final_message: finalMessage });
    expect(stored.audit[0].created_at).toBe(stored.case.reviewed_at);
    await expect(nursePage.getByRole('region', { name: 'Báo cáo kiểm toán' })).toContainText('1/1 ca khác đề xuất (100.0%)');
    await expect(nursePage.getByRole('region', { name: 'Báo cáo kiểm toán' })).toContainText('Gold red-flag v1: 0/');
    expect((await patient.request.get(`${api}/v1/triage/audit/report`)).status()).toBe(403);
    await patientPage.reload();
    await patientPage.getByRole('heading', { name: 'Phân luồng triệu chứng' }).locator('..').getByRole('button', { name: 'Mở' }).click();
    await expect(patientPage.getByText(finalMessage)).toBeVisible({ timeout: 15_000 });
  } finally {
    await patient.close();
    await nurse.close();
  }
});
