import { test, expect } from '@playwright/test';

const api = `http://127.0.0.1:${process.env.TRIAGE_E2E_API_PORT || 8108}`;

async function login(page: any, username: string, password: string) {
  await page.goto('/login');
  await page.getByLabel('Tên đăng nhập').fill(username);
  await page.locator('#account-password').fill(password);
  await page.getByRole('button', { name: 'Đăng nhập' }).click();
  await expect(page).toHaveURL(/tracker/);
}

test('doctor creates, approves and stops a plan; patient sees only approved history', async ({ browser }) => {
  const patient = await browser.newContext();
  const doctor = await browser.newContext();
  const otherDoctor = await browser.newContext();
  const patientPage = await patient.newPage();
  const doctorPage = await doctor.newPage();
  try {
    const username = `med_${Date.now()}`;
    await patientPage.goto('/register');
    await patientPage.getByLabel('Tên đăng nhập').fill(username);
    await patientPage.locator('#account-password').fill('Patient@12345');
    await patientPage.getByLabel('Loại đái tháo đường theo hồ sơ của bạn').selectOption('type2');
    await patientPage.getByRole('button', { name: 'Tạo tài khoản' }).click();
    await expect(patientPage).toHaveURL(/onboarding\/voice/);
    const me = await patient.request.get(`${api}/v1/auth/me`);
    const patientId = (await me.json()).id;

    await login(doctorPage, 'medication_doctor', 'Doctor@12345');
    await doctorPage.goto('/medications');
    await doctorPage.getByLabel('Mã bệnh nhân').fill(patientId);
    await doctorPage.getByLabel('Tên thuốc theo đơn').fill('Thuốc mô phỏng');
    await doctorPage.getByLabel('Liều và cách dùng theo đơn').fill('Theo đơn thử đã nhập');
    await doctorPage.getByLabel('Mã hoặc nguồn đơn thuốc').fill('TEST-ONLY-260');
    await doctorPage.getByLabel(/Giờ nhắc/).fill('00:00');
    const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' }).format(new Date());
    await doctorPage.getByLabel('Ngày bắt đầu').fill(today);
    await doctorPage.getByLabel('Ngày kết thúc').fill(today);
    await doctorPage.getByRole('button', { name: 'Lưu bản nháp' }).click();
    await expect(doctorPage.getByText('Bản nháp — chưa áp dụng')).toBeVisible();

    await patientPage.goto('/medications');
    await expect(patientPage.getByText('Thuốc mô phỏng')).toHaveCount(0);
    const doctorPlans = await doctor.request.get(`${api}/v1/medications/patients/${patientId}`);
    const draft = (await doctorPlans.json()).plans[0];
    const wrongLogin = await otherDoctor.request.post(`${api}/v1/auth/login-json`, { data: { username: 'other_medication_doctor', password: 'Doctor@12345' } });
    const wrongToken = (await wrongLogin.json()).access_token;
    expect((await otherDoctor.request.post(`${api}/v1/medications/plans/${draft.id}/approve`, { headers: { Authorization: `Bearer ${wrongToken}` } })).status()).toBe(403);

    await doctorPage.getByRole('button', { name: 'Duyệt lịch theo đơn' }).click();
    await expect(doctorPage.getByText('Bác sĩ đã duyệt', { exact: true })).toBeVisible();
    await patientPage.reload();
    await expect(patientPage.getByText('Thuốc mô phỏng')).toBeVisible();
    const approved = (await (await patient.request.get(`${api}/v1/medications/patients/${patientId}`)).json()).plans[0];
    expect(approved.events.map((event: any) => event.action)).toEqual(['created', 'approved']);
    expect((await patient.request.post(`${api}/v1/glucose`, { data: { user_id: patientId, value_mgdl: 180, measured_at: new Date().toISOString(), context: 'random' } })).status()).toBe(200);

    const adminLogin = await otherDoctor.request.post(`${api}/v1/auth/login-json`, { data: { username: 'live_admin', password: 'TestAdmin@123' } });
    const adminToken = (await adminLogin.json()).access_token;
    expect((await otherDoctor.request.post(`${api}/v1/medications/reminders/run`, { headers: { Authorization: `Bearer ${adminToken}` } })).status()).toBe(200);
    expect((await (await otherDoctor.request.post(`${api}/v1/medications/reminders/run`, { headers: { Authorization: `Bearer ${adminToken}` } })).json()).sent).toBe(0);
    await patientPage.goto('/my/reviews');
    await expect(patientPage.getByText(/Đến giờ xác nhận dùng thuốc/)).toBeVisible();
    await patientPage.goto('/medications');
    await patientPage.getByRole('button', { name: 'Bỏ liều' }).click();
    await expect(patientPage.getByText(/Hỏi bác sĩ\/dược sĩ, không tự uống bù/)).toBeVisible();
    const skipped = (await (await patient.request.get(`${api}/v1/medications/patients/${patientId}`)).json()).plans[0];
    expect(skipped.schedule[0].status).toBe('skipped');
    expect((await patient.request.post(`${api}/v1/medications/plans/${draft.id}/doses`, { data: { due_at: skipped.schedule[0].due_at, status: 'skipped' } })).status()).toBe(409);
    await doctorPage.getByRole('button', { name: 'Xem lịch bệnh nhân' }).click();
    await expect(doctorPage.getByText('Đã xác nhận dùng 0/1 liều đến hạn (0%)')).toBeVisible();
    await expect(doctorPage.getByText('Chuỗi bỏ liều dài nhất: 1.')).toBeVisible();
    await expect(doctorPage.getByText(/180 mg\/dL/)).toBeVisible();
    await expect(doctorPage.getByText(/không chứng minh hiệu quả thuốc/)).toBeVisible();

    await doctorPage.getByText('Dừng lịch theo quyết định bác sĩ').click();
    await doctorPage.getByLabel('Lý do dừng').fill('Đơn thử đã kết thúc');
    await doctorPage.getByRole('button', { name: 'Xác nhận dừng lịch' }).click();
    await expect(doctorPage.getByText('Lý do dừng: Đơn thử đã kết thúc')).toBeVisible();
    await patientPage.reload();
    await expect(patientPage.getByText('Bác sĩ đã dừng lịch này')).toBeVisible();
    const stopped = (await (await patient.request.get(`${api}/v1/medications/patients/${patientId}`)).json()).plans[0];
    expect(stopped.events.map((event: any) => event.action)).toEqual(['created', 'approved', 'stopped']);
  } finally {
    await patient.close(); await doctor.close(); await otherDoctor.close();
  }
});
