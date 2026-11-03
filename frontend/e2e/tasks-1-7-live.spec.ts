import { test, expect } from './fixtures';
import { execFileSync } from 'node:child_process';
import path from 'node:path';

const api = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8101';

async function signInPatient(page: any) {
  const username = `live_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  const password = 'Test@123';
  const registered = await page.request.post(`${api}/v1/auth/register`, {
    data: { username, password, diabetes_type: 'type2' },
  });
  expect(registered.status()).toBe(201);
  const patient = await registered.json();
  await signInThroughUi(page, username, password);
  const login = await page.request.post(`${api}/v1/auth/login-json`, { data: { username, password } });
  expect(login.ok()).toBeTruthy();
  return { ...patient, token: (await login.json()).access_token };
}

async function signInThroughUi(page: any, username: string, password: string) {
  await page.goto('/login');
  await page.getByLabel('Tên đăng nhập').fill(username);
  await page.locator('#account-password').fill(password);
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await page.waitForURL('**/tracker');
}

test('patient tracker saves a reading through the real API and reloads it', async ({ page }) => {
  const patient = await signInPatient(page);
  await page.goto('/tracker');
  await expect(page.getByRole('heading', { name: 'Nhật ký đường huyết' })).toBeVisible();
  await page.getByLabel('Giá trị (mg/dL)').fill('110');
  await page.getByTestId('tracker-save').click();
  await expect(page.getByRole('status')).toContainText('không xác nhận chỉ số đạt mục tiêu cá nhân', { timeout: 15000 });
  await page.reload();
  await expect(page.locator('[id^="log-"]').filter({ hasText: '110 mg/dL' })).toBeVisible();
  await page.getByLabel('Lần đo tiếp theo').fill('2026-01-01T07:00');
  await page.getByLabel('Lần tái khám tiếp theo').fill('2026-01-02T07:00');
  await page.getByRole('button', { name: 'Lưu lịch nhắc' }).click();
  await page.reload();
  await expect(page.getByText('Đã tới lịch đo đường huyết.', { exact: false })).toBeVisible();
  await expect(page.getByText('Đã tới lịch tái khám.', { exact: false })).toBeVisible();
  const listed = await page.request.get(`${api}/v1/glucose/${patient.id}`);
  expect(listed.ok()).toBeTruthy();
  expect((await listed.json()).logs.some((row: any) => row.value_mgdl === 110)).toBeTruthy();
  await page.goto('/previsit');
  await page.getByTestId('soap-json-btn').click();
  await expect(page.getByRole('heading', { name: 'Ngày chưa có bản ghi' })).toBeVisible({ timeout: 30000 });
  await expect(page.getByText('Dành cho bác sĩ chỉ định')).toBeVisible();
});

test('previsit report preserves a fixed missing day and matches JSON, Markdown, and SQLite', async ({ page }) => {
  const patient = await signInPatient(page);
  const fixedReadings = [
    [100, '2026-10-30T07:00:00+07:00'],
    [110, '2026-11-01T07:00:00+07:00'],
    [120, '2026-11-02T07:00:00+07:00'],
    [130, '2026-11-03T07:00:00+07:00'],
  ] as const;
  const savedIds: number[] = [];
  for (const [value, measured_at] of fixedReadings) {
    const saved = await page.request.post(`${api}/v1/glucose`, {
      headers: { Authorization: `Bearer ${patient.token}` },
      data: { user_id: patient.id, value_mgdl: value, measured_at, context: 'fasting' },
    });
    expect(saved.ok()).toBeTruthy();
    savedIds.push((await saved.json()).id);
  }

  await page.goto('/previsit');
  await page.getByLabel('Khoảng thời gian').selectOption('7');
  const jsonResponse = page.waitForResponse(r => r.url().endsWith('/v1/soap/generate') && r.request().method() === 'POST');
  await page.getByTestId('soap-json-btn').click();
  const jsonHttp = await jsonResponse;
  expect(jsonHttp.ok()).toBeTruthy();
  const report = await jsonHttp.json();
  expect(report.followup.period_start).toBe('2026-10-28');
  expect(report.followup.period_end).toBe('2026-11-03');
  expect(report.followup.missing_dates).toContain('2026-10-31');
  expect(report.followup.recorded_days).toBe(4);
  expect(report.followup.trend_projection.direction).toBe('up');
  expect(report.followup.trend_projection.basis_log_ids).toEqual(savedIds.slice(1));
  expect(report.soap.plan).toBe('');
  expect(report.soap.assessment).toContain('chưa có kết quả xét nghiệm HbA1c');
  expect(report.soap.assessment).toContain('không thể kết luận đạt hay chưa đạt mục tiêu HbA1c');
  expect(report.soap.assessment).not.toMatch(/HbA1c\s*(?:=|:|là)?\s*\d/i);
  expect(report.soap.assessment).not.toMatch(/(?:đã|được|cho thấy)\s+đạt[^.]*mục tiêu/i);

  const followup = page.getByTestId('followup-report');
  await expect(followup).toContainText('2026-10-31');
  await expect(followup).toContainText('Tăng');
  for (const id of savedIds.slice(1)) await expect(followup.getByRole('link', { name: `Xem log #${id}` })).toBeVisible();
  const plan = page.getByTestId('soap-plan');
  await expect(plan).toContainText('Dành cho bác sĩ chỉ định');
  await expect(plan).not.toContainText(/Điều trị|Kê|Uống|liều/i);

  const markdownResponse = page.waitForResponse(r => r.url().endsWith('/v1/soap/generate/markdown') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Tạo bản để tải về' }).click();
  const markdownHttp = await markdownResponse;
  expect(markdownHttp.ok()).toBeTruthy();
  const markdown = await markdownHttp.text();
  await expect(page.getByTestId('soap-markdown')).toHaveText(markdown);
  expect(markdown).toContain('2026-10-31');
  expect(markdown).toContain('## P — Plan (Kế hoạch)\n\n');
  for (const id of savedIds.slice(1)) expect(markdown).toContain(`[Xem log #${id}]`);
  expect(markdown).not.toMatch(/HbA1c\s*(?:=|:|là)?\s*\d/i);

  const runDir = process.env.TRIAGE_E2E_DB_DIR!;
  const root = path.resolve(__dirname, '../..');
  const dbRows = JSON.parse(execFileSync(path.join(root, '.venv/Scripts/python.exe'), ['-c',
    `import sqlite3,json,sys\nwith sqlite3.connect(sys.argv[1]) as c:\n c.row_factory=sqlite3.Row\n rows=c.execute("SELECT id,value_mgdl,measured_at FROM glucose_logs WHERE user_id=? ORDER BY measured_at",(sys.argv[2],)).fetchall()\n print(json.dumps([dict(r) for r in rows]))`,
    path.join(runDir, 'glucose.db'), patient.id], { encoding: 'utf8' }));
  expect(dbRows.map((row: any) => [row.id, row.value_mgdl, row.measured_at])).toEqual(
    savedIds.map((id, index) => [id, fixedReadings[index][0], fixedReadings[index][1]]));
  expect(dbRows.some((row: any) => String(row.measured_at).startsWith('2026-10-31'))).toBe(false);
  await page.screenshot({ path: path.join(runDir, 'task-5-previsit.png'), fullPage: true });
});

test('tracker renders fixed-day real readings, DB-backed trend links, and local-only reminders', async ({ page }) => {
  const patient = await signInPatient(page);
  const savedIds: number[] = [];
  for (const [value, measured_at] of [[110, '2026-11-01T07:00:00+07:00'], [140, '2026-11-02T07:00:00+07:00']] as const) {
    const saved = await page.request.post(`${api}/v1/glucose`, {
      headers: { Authorization: `Bearer ${patient.token}` },
      data: { user_id: patient.id, value_mgdl: value, measured_at, context: 'fasting' },
    });
    expect(saved.ok()).toBeTruthy();
    savedIds.push((await saved.json()).id);
  }
  const writes: string[] = [];
  page.on('request', request => {
    if (request.method() !== 'GET') writes.push(request.url());
  });
  await page.goto('/tracker');
  await expect(page.getByText(/Tóm tắt xu hướng 14 ngày: 2 chỉ số, cao nhất 140 mg\/dL, thấp nhất 110 mg\/dL/)).toBeAttached();
  const listed = await page.request.get(`${api}/v1/glucose/${patient.id}`, { headers: { Authorization: `Bearer ${patient.token}` } });
  expect(listed.ok()).toBeTruthy();
  const dbIds = (await listed.json()).logs.map((row: any) => row.id);
  for (const id of savedIds) {
    expect(dbIds).toContain(id);
    await expect(page.getByRole('link', { name: `Bản ghi #${id}` })).toHaveAttribute('href', `#log-${id}`);
    await page.getByRole('link', { name: `Bản ghi #${id}` }).click();
    await expect(page.locator(`#log-${id}`)).toBeVisible();
  }
  await expect(page.getByText(/Lịch chỉ lưu trên thiết bị này.*backend không gửi thông báo/)).toBeVisible();
  await page.getByLabel('Lần đo tiếp theo').fill('2020-01-01T08:00');
  await page.getByLabel('Lần tái khám tiếp theo').fill('2020-01-02T08:00');
  await page.getByRole('button', { name: 'Lưu lịch nhắc' }).click();
  await expect(page.getByText(/Đã tới lịch đo đường huyết/)).toBeVisible();
  await page.reload();
  await expect(page.getByLabel('Lần đo tiếp theo')).toHaveValue('2020-01-01T08:00');
  await expect(page.getByText(/Đã tới lịch tái khám/)).toBeVisible();
  expect(writes).toEqual([]);
});

test('tracker displays real API safety classifications at every boundary', async ({ page }) => {
  const patient = await signInPatient(page);
  await page.goto('/tracker');
  for (const [value, classification] of [
    [69, 'low'], [70, 'no_alert'], [250, 'no_alert'],
    [251, 'alert_high'], [299, 'alert_high'], [300, 'critical'],
  ] as const) {
    await page.getByLabel('Giá trị (mg/dL)').fill(String(value));
    const saved = page.waitForResponse(response => response.url().endsWith('/v1/glucose') && response.request().method() === 'POST');
    await page.getByTestId('tracker-save').click();
    expect((await saved).ok()).toBeTruthy();
    await page.reload();
    await expect(page.locator('[id^="log-"]').filter({ hasText: `${value} mg/dL` })).toBeVisible({ timeout: 15000 });
    const message = page.getByRole('status');
    if (value === 69 || value === 300) {
      await expect(page.getByTestId('critical-banner')).toBeVisible();
      await expect(message).toContainText('liên hệ cơ sở y tế ngay');
    } else {
      await expect(page.getByTestId('critical-banner')).toHaveCount(0);
      await expect(message).not.toContainText('liên hệ cơ sở y tế ngay');
    }
    if (value === 251 || value === 299) await expect(message).toContainText('liên hệ bác sĩ');
    await expect(message).not.toContainText(/(?<!không )tự đổi liều (thuốc|insulin)/i);
  }
  const listed = await page.request.get(`${api}/v1/glucose/${patient.id}`);
  expect(listed.ok()).toBeTruthy();
  const rows = (await listed.json()).logs;
  for (const [value, classification] of [
    [69, 'low'], [70, 'no_alert'], [250, 'no_alert'],
    [251, 'alert_high'], [299, 'alert_high'], [300, 'critical'],
  ] as const) {
    const row = rows.find((item: any) => item.value_mgdl === value);
    expect(row?.classification).toBe(classification);
    expect(row?.message).toBeTruthy();
    expect(row?.message).not.toMatch(/(?<!không )tự đổi liều (thuốc|insulin)/i);
  }
});

test('triage UI sends structured data and shows a real red flag immediately', async ({ page }) => {
  await signInPatient(page);
  await page.goto('/tracker');
  await page.getByRole('button', { name: 'Mở' }).last().click();
  await page.getByRole('spinbutton', { name: 'Đường huyết gần nhất mg/dL' }).fill('300');
  await page.getByRole('textbox', { name: 'Triệu chứng bắt đầu từ khi nào' }).fill('hôm nay');
  const input = page.getByRole('textbox', { name: 'Triệu chứng và thời gian muốn khám' });
  await input.fill('đau ngực, méo miệng');
  const response = page.waitForResponse(r => r.url().endsWith('/v1/triage') && r.request().method() === 'POST');
  await input.press('Enter');
  const result = await response;
  expect(result.ok()).toBeTruthy();
  expect(result.request().postDataJSON().structured).toBe(true);
  expect((await result.json()).emergency).toBe(true);
  await expect(page.getByText(/115/).last()).toBeVisible();
});

for (const message of [
  'vã mồ hôi, lơ mơ', 'va mo hoi, lo mo',
  'thở nhanh, hơi thở mùi xeton', 'tho nhanh, hoi tho mui xeton',
  'bàn chân sưng đỏ, chảy mủ', 'ban chan sung do, chay mu',
  'đau ngực, méo miệng', 'dau nguc, meo mieng',
]) {
  test(`real triage UI red flag: ${message}`, async ({ page }) => {
    await signInPatient(page);
    await page.goto('/tracker');
    await page.getByRole('button', { name: 'Mở' }).last().click();
    const input = page.getByRole('textbox', { name: 'Triệu chứng và thời gian muốn khám' });
    await input.fill(message);
    const response = page.waitForResponse(r => r.url().endsWith('/v1/triage') && r.request().method() === 'POST');
    await input.press('Enter');
    const http = await response;
    expect(http.ok()).toBeTruthy();
    const result = await http.json();
    expect(result.emergency).toBe(true);
    expect(result.message).toContain('115');
    expect(result.recommended_doctors).toEqual([]);
    await expect(page.getByText(/115/).last()).toBeVisible();
  });
}

test('real triage UI shows the fixed out-of-scope refusal', async ({ page }) => {
  await signInPatient(page);
  await page.goto('/tracker');
  await page.getByRole('button', { name: 'Mở' }).last().click();
  const input = page.getByRole('textbox', { name: 'Triệu chứng và thời gian muốn khám' });
  await input.fill('hỏi về huyết áp');
  const response = page.waitForResponse(r => r.url().endsWith('/v1/triage') && r.request().method() === 'POST');
  await input.press('Enter');
  const http = await response;
  expect(http.ok()).toBeTruthy();
  const refused = await http.json();
  expect(refused.emergency).toBe(false);
  expect(refused.message).toBe('Hệ thống chỉ hỗ trợ theo dõi đái tháo đường. Nội dung này nằm ngoài phạm vi an toàn của hệ thống, vui lòng hỏi bác sĩ ở lần khám tới.');
  expect(refused.recommended_doctors).toEqual([]);
  expect(refused.message).not.toMatch(/chẩn đoán|bạn bị|bạn mắc/i);
  await expect(page.getByText(refused.message).last()).toBeVisible();
});

test('triage normal case is not a red flag and withholds scheduling before review', async ({ page }) => {
  await signInPatient(page);
  await page.goto('/tracker');
  await page.getByRole('button', { name: 'Mở' }).last().click();
  await page.getByRole('spinbutton', { name: 'Đường huyết gần nhất mg/dL' }).fill('180');
  await page.getByRole('textbox', { name: 'Triệu chứng bắt đầu từ khi nào' }).fill('hôm qua');
  const input = page.getByRole('textbox', { name: 'Triệu chứng và thời gian muốn khám' });
  await input.fill('khát nhiều');
  const response = page.waitForResponse(r => r.url().endsWith('/v1/triage') && r.request().method() === 'POST');
  await input.press('Enter');
  const http = await response;
  expect(http.ok()).toBeTruthy();
  const result = await http.json();
  expect(result.emergency).toBe(false);
  expect(result.red_flag_type).toBeNull();
  expect(result.review_status).toBe('pending_clinician_review');
  expect(result.recommended_doctors).toEqual([]);
  expect(result.message).not.toContain('115');
  await expect(page.getByText(result.message).last()).toBeVisible();
});

test('triage red flag takes priority over out-of-scope refusal', async ({ page }) => {
  await signInPatient(page);
  await page.goto('/tracker');
  await page.getByRole('button', { name: 'Mở' }).last().click();
  const input = page.getByRole('textbox', { name: 'Triệu chứng và thời gian muốn khám' });
  await input.fill('đau ngực, méo miệng và hỏi về huyết áp');
  const response = page.waitForResponse(r => r.url().endsWith('/v1/triage') && r.request().method() === 'POST');
  await input.press('Enter');
  const result = await response;
  expect(result.ok()).toBeTruthy();
  const body = await result.json();
  expect(body.emergency).toBe(true);
  expect(body.message).toContain('115');
  expect(body.message).not.toContain('nằm ngoài phạm vi');
  expect(body.recommended_doctors).toEqual([]);
});

for (const value of [69, 300]) {
  test(`triage glucose ${value} uses the emergency path without scheduling`, async ({ page }) => {
    await signInPatient(page);
    await page.goto('/tracker');
    await page.getByRole('button', { name: 'Mở' }).last().click();
    await page.getByRole('spinbutton', { name: 'Đường huyết gần nhất mg/dL' }).fill(String(value));
    await page.getByRole('textbox', { name: 'Triệu chứng bắt đầu từ khi nào' }).fill('hôm nay');
    const input = page.getByRole('textbox', { name: 'Triệu chứng và thời gian muốn khám' });
    await input.fill('khát nhiều');
    const response = page.waitForResponse(r => r.url().endsWith('/v1/triage') && r.request().method() === 'POST');
    await input.press('Enter');
    const http = await response;
    expect(http.ok()).toBeTruthy();
    expect(http.request().postDataJSON().latest_glucose_mgdl).toBe(value);
    const result = await http.json();
    expect(result.emergency).toBe(true);
    expect(result.proposed_priority).toBe('emergency');
    expect(result.message).toContain('115');
    expect(result.recommended_doctors).toEqual([]);
    await expect(page.getByText(/115/).last()).toBeVisible();
  });
}

test('structured triage asks for missing data and withholds routine advice pending review', async ({ page }) => {
  await signInPatient(page);
  await page.goto('/tracker');
  await page.getByRole('button', { name: 'Mở' }).last().click();
  const input = page.getByRole('textbox', { name: 'Triệu chứng và thời gian muốn khám' });
  await input.fill('tê chân, mắt mờ');
  const firstResponse = page.waitForResponse(r => r.url().endsWith('/v1/triage') && r.request().method() === 'POST');
  await input.press('Enter');
  const first = await firstResponse;
  expect(first.request().postDataJSON().structured).toBe(true);
  expect((await first.json()).followup_question).toContain('đường huyết');
  await expect(page.getByText(/đường huyết gần nhất/).last()).toBeVisible();
  await page.getByRole('spinbutton', { name: 'Đường huyết gần nhất mg/dL' }).fill('180');
  await page.getByRole('textbox', { name: 'Triệu chứng bắt đầu từ khi nào' }).fill('hôm qua');
  await input.fill('tê chân, mắt mờ');
  const finalResponse = page.waitForResponse(r => r.url().endsWith('/v1/triage') && r.request().method() === 'POST');
  await input.press('Enter');
  const final = await finalResponse;
  expect(final.request().postDataJSON().structured).toBe(true);
  const proposal = await final.json();
  expect(['routine', 'soon', 'emergency']).toContain(proposal.proposed_priority);
  expect(proposal.review_status).toBe('pending_clinician_review');
  expect(proposal.rationale).toContain('không phải chẩn đoán');
  expect(proposal.source).toContain('project_requirements.json');
  expect(proposal.recommended_doctors).toEqual([]);
  expect(proposal.message).not.toMatch(/đặt lịch|hướng xử trí đã|bạn nên/i);
  await expect(page.getByText(/chờ.*duyệt/i).last()).toBeVisible();
  await expect(page.getByText(/không phải chẩn đoán/i).last()).toBeVisible();
  await expect(page.getByText(/Nguồn:.*project_requirements\.json/i).last()).toBeVisible();
  await page.screenshot({ path: path.join(process.env.TRIAGE_E2E_DB_DIR!, 'task-6-structured.png'), fullPage: true });
});

test('verified doctor sees real patient readings while patients cannot open the dashboard', async ({ page }) => {
  const first = await signInPatient(page);
  const second = await signInPatient(page);
  for (const [patient, value] of [[first, 280], [second, 300]] as const) {
    const saved = await page.request.post(`${api}/v1/glucose`, {
      headers: { Authorization: `Bearer ${patient.token}` },
      data: { user_id: patient.id, value_mgdl: value, context: 'fasting' },
    });
    expect(saved.ok()).toBeTruthy();
  }
  await page.goto('/expert/patients');
  await expect(page.getByText('403 — Chỉ bác sĩ mới xem được hàng đợi bệnh nhân.')).toBeVisible();
  const adminLogin = await page.request.post(`${api}/v1/auth/login-json`, {
    data: { username: 'live_admin', password: 'TestAdmin@123' },
  });
  expect(adminLogin.ok()).toBeTruthy();
  const adminToken = (await adminLogin.json()).access_token;
  const username = `live_doc_${Date.now()}`;
  const password = 'Doc@123';
  const created = await page.request.post(`${api}/v1/auth/register`, {
    headers: { Authorization: `Bearer ${adminToken}` },
    data: { username, password, role: 'doctor' },
  });
  expect(created.status()).toBe(201);
  await signInThroughUi(page, username, password);
  await page.goto('/expert/patients');
  await expect(page.getByTestId('queue-row').filter({ hasText: first.username })).toContainText('Cần theo dõi');
  await expect(page.getByTestId('queue-row').filter({ hasText: second.username })).toContainText('Cần hỗ trợ ngay');
});


test('real RAG review stays private until verified doctor approves or revises and patient reloads', async ({ page, browser }) => {
  test.setTimeout(300_000);
  test.skip(process.env.TRIAGE_E2E_LIVE_RAG !== '1', 'Requires explicit live NVIDIA RAG and isolated DB stores');
  const runDir = process.env.TRIAGE_E2E_DB_DIR!;
  expect(runDir).toBeTruthy();
  const root = path.resolve(__dirname, '../..');
  const readDb = (id: string) => JSON.parse(execFileSync(path.join(root, '.venv/Scripts/python.exe'), ['-c',
    `import sqlite3,json,sys
with sqlite3.connect(sys.argv[1]) as c:
 c.row_factory=sqlite3.Row
 r=c.execute("SELECT * FROM review_requests WHERE id=?",(sys.argv[2],)).fetchone()
 h=c.execute("SELECT answer,status FROM query_history WHERE review_id=?",(sys.argv[2],)).fetchone()
 print(json.dumps({"review":dict(r),"history":dict(h)}))`,
    path.join(runDir, 'auth.db'), id], { encoding: 'utf8' }));
  const patient = await signInPatient(page);
  for (const value of [110, 140]) {
    const saved = await page.request.post(`${api}/v1/glucose`, { data: { user_id: patient.id, value_mgdl: value, context: 'fasting' } });
    expect(saved.ok()).toBeTruthy();
  }
  const doctorContext = await browser.newContext();
  const otherContext = await browser.newContext();
  try {
    const doctor = await doctorContext.newPage();
    const other = await otherContext.newPage();
    const otherPatient = await signInPatient(other);
    const admin = await doctor.request.post(`${api}/v1/auth/login-json`, { data: { username: 'live_admin', password: 'TestAdmin@123' } });
    expect(admin.ok()).toBeTruthy();
    const adminHeaders = { Authorization: `Bearer ${(await admin.json()).access_token}` };
    const username = `review_doc_${Date.now()}`;
    const registered = await doctor.request.post(`${api}/v1/auth/register`, { headers: adminHeaders, data: { username, password: 'Doc@123', role: 'doctor' } });
    expect(registered.status()).toBe(201);
    const docUser = await registered.json();
    expect(docUser.is_verified).toBeTruthy();
    const wrongName = `review_pharm_${Date.now()}`;
    expect((await doctor.request.post(`${api}/v1/auth/register`, { headers: adminHeaders, data: { username: wrongName, password: 'Doc@123', role: 'pharmacist' } })).status()).toBe(201);
    const wrongLogin = await doctor.request.post(`${api}/v1/auth/login-json`, { data: { username: wrongName, password: 'Doc@123' } });
    const wrongToken = (await wrongLogin.json()).access_token;
    await signInThroughUi(doctor, username, 'Doc@123');
    for (const decision of ['revised', 'approved']) {
      await page.goto('/tracker');
      const query = page.waitForResponse(r => r.url().endsWith('/v1/query') && r.request().method() === 'POST', { timeout: 180_000 });
      await page.getByTestId('trend-explain').click();
      const response = await query;
      expect(response.status(), await response.text()).toBe(200);
      expect(response.request().postDataJSON().require_doctor_review).toBe(true);
      const pending = await response.json();
      expect(pending.status).toBe('pending_review');
      expect(pending.evaluation).toBeNull();
      const id = pending.review_id;
      const before = readDb(id);
      const draft = before.review.draft_answer;
      expect(draft.length).toBeGreaterThan(0);
      expect(before.review.status).toBe('pending');
      expect(before.review.requester_id).toBe(patient.id);
      expect(before.history.status).toBe('pending_review');
      expect(pending.answer).not.toBe(draft);
      expect(JSON.stringify(pending)).not.toContain(draft);
      for (const url of ['/v1/reviews', '/v1/reviews/me', `/v1/reviews/${id}`, '/v1/query/history']) {
        const result = await page.request.get(`${api}${url}`);
        expect(result.status()).toBe(200);
        expect(await result.text()).not.toContain(draft);
      }
      await page.goto('/my/reviews');
      await expect(page.getByTestId(`review-${id}`)).toContainText('Đang chờ bác sĩ duyệt');
      await expect(page.getByTestId(`review-${id}`)).not.toContainText(draft);
      expect((await other.request.get(`${api}/v1/reviews/${id}`)).status()).toBe(403);
      for (const token of [patient.token, otherPatient.token, wrongToken]) {
        for (const endpoint of ['decide', 'decision?decision=approved']) {
          const denied = await other.request.post(`${api}/v1/reviews/${id}/${endpoint}`, { headers: { Authorization: `Bearer ${token}` }, data: { decision: 'approved' } });
          expect(denied.status()).toBe(403);
        }
      }
      expect(readDb(id).review.status).toBe('pending');
      await doctor.goto('/expert/queue');
      await doctor.getByTestId(`review-${id}`).click();
      await expect(doctor.getByLabel('Final answer (chỉnh sửa nếu revised)')).toHaveValue(draft);
      const final = decision === 'approved' ? draft : 'DEMO KIỂM THỬ — tài khoản bác sĩ mô phỏng. ' + 'Các số đo được ghi nhận để trao đổi trong lần khám; mục tiêu cá nhân cần được bác sĩ xác định. '.repeat(4) + 'Không tự đổi liều thuốc. KẾT THÚC NỘI DUNG ĐÃ SỬA.';
      if (decision === 'revised') await doctor.getByLabel('Final answer (chỉnh sửa nếu revised)').fill(final);
      await doctor.getByLabel('Expert notes').fill('Duyệt mô phỏng dữ liệu tổng hợp để kiểm thử workflow, không xác nhận y khoa.');
      await doctor.screenshot({ path: path.join(runDir, `doctor-${decision}.png`), fullPage: true });
      const saved = doctor.waitForResponse(r => r.url().endsWith(`/v1/reviews/${id}/decide`) && r.request().method() === 'POST');
      await doctor.getByRole('button', { name: decision === 'approved' ? 'Duyệt (approved)' : 'Duyệt có sửa (revised)', exact: true }).click();
      expect((await saved).status()).toBe(200);
      await expect(doctor.getByTestId(`review-${id}`)).toHaveCount(0);
      await page.reload();
      await expect(page.getByTestId(`review-${id}`)).toContainText(final);
      await page.screenshot({ path: path.join(runDir, `patient-${decision}.png`), fullPage: true });
      const after = readDb(id);
      expect(after.review.status).toBe(decision);
      expect(after.review.final_answer).toBe(final);
      expect(after.review.assigned_expert_id).toBe(docUser.id);
      expect(after.review.reviewed_at).toBeTruthy();
      expect(after.history.answer).toBe(final);
      expect(after.history.status).toBe('approved');
      const published = await page.request.get(`${api}/v1/reviews/${id}`);
      expect((await published.json()).final_answer).toBe(final);
      expect((await other.request.get(`${api}/v1/reviews/${id}`)).status()).toBe(403);
    }
  } finally {
    await doctorContext.close();
    await otherContext.close();
  }
});
