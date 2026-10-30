import { test, expect } from './fixtures';

// Pre-visit B — PrevisitView (auth via useAuth, patientId = session user).
// Session mocked through /v1/auth/me; BE not started by webServer so API is mocked.
const ME = { id: 'soap_user', username: 'soap_user', role: 'user', is_active: true, is_verified: true };

function mockSession(page: any) {
  return page.route('**/v1/auth/me', async (route: any) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(ME) });
  });
}

function mockGlucoseGet(page: any) {
  return page.route('**/v1/glucose/*', async (route: any) => {
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({
        user_id: ME.id,
        logs: [{ id: 1, user_id: ME.id, value_mgdl: 130, measured_at: '2026-09-06T10:00:00', context: 'fasting', notes: 'banh ngot', classification: 'high' }],
        stats: { user_id: ME.id, total_logs: 1, avg_mgdl: 130, last_7_days_avg: 130, streak_days: 1, logs_per_week: 1, classification_counts: { high: 1 } },
        should_escalate: false,
        anomaly_ids: [1],
      }),
    });
  });
}

function mockSoapJson(page: any, soap: any, followup?: any) {
  return page.route('**/v1/soap/generate', async (route: any) => {
    if (route.request().url().includes('/markdown')) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({
        user_id: ME.id,
        generated_at: new Date().toISOString(),
        period: '14 ngày',
        soap,
        followup,
        stats: { user_id: ME.id, total_logs: 1, avg_mgdl: 130, last_7_days_avg: 130, streak_days: 1, logs_per_week: 1, classification_counts: { high: 1 } },
      }),
    });
  });
}

test.describe('Pre-visit B — SOAP Generation', () => {
  test('shows empty state when no SOAP yet', async ({ page }) => {
    await mockSession(page);
    await page.goto('/previsit');
    await expect(page.getByText(/Hãy ghi chỉ số ở Sổ đường huyết/)).toBeVisible();
  });

  test('generate SOAP JSON shows sections and empty-plan placeholder', async ({ page }) => {
    await mockSession(page);
    await mockGlucoseGet(page);
    await mockSoapJson(page, {
      subjective: 'Người bệnh ghi nhận ăn ngọt [Xem log #1]',
      objective: 'Trung bình 130 mg/dL [Xem log #1]',
      assessment: 'Chưa có xét nghiệm HbA1c; không thể kết luận đạt hay chưa đạt mục tiêu [Xem log #1]',
      plan: '',
    }, {
      period_start: '2026-09-05', period_end: '2026-09-07',
      missing_dates: ['2026-09-07'], recorded_days: 2,
      trend_projection: { direction: 'insufficient_data', basis_log_ids: [1], limitation: 'Không suy HbA1c hoặc thay thế đánh giá bác sĩ.' },
    });

    await page.goto('/previsit');
    await expect(page.getByTestId('soap-json-btn')).toBeVisible();
    await page.getByRole('button', { name: /Tạo bản tóm tắt/ }).click();
    await expect(page.getByText('S — Điều bạn chia sẻ')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('O — Chỉ số đã ghi')).toBeVisible();
    await expect(page.getByText('A — Nhận định tham khảo')).toBeVisible();
    await expect(page.getByText('Dành cho bác sĩ chỉ định')).toBeVisible();
    await expect(page.getByTestId('log-link').first()).toBeVisible();
    await expect(page.locator('a[href*="/tracker?highlight="]').first()).toBeVisible();
    await expect(page.getByText(/1 ngày trong kỳ/)).toBeVisible();
    await expect(page.getByText(/Không suy HbA1c hoặc thay thế đánh giá bác sĩ/)).toBeVisible();
  });

  test('generate markdown and download', async ({ page }) => {
    await mockSession(page);
    await mockGlucoseGet(page);
    const md = '# SOAP — soap_user\n\n## S\nTest';
    await page.route('**/v1/soap/generate/markdown', async (route: any) => {
      await route.fulfill({ status: 200, contentType: 'text/plain', body: md });
    });

    await page.goto('/previsit');
    await page.getByRole('button', { name: /Tạo bản để tải về/ }).click();
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: /Tải bản tóm tắt/ }).click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/SOAP_/);
  });

  test('handles API error gracefully', async ({ page }) => {
    await mockSession(page);
    await mockGlucoseGet(page);
    await page.route('**/v1/soap/generate', async (route: any) => {
      if (route.request().url().includes('/markdown')) {
        await route.continue();
        return;
      }
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Internal' }) });
    });

    await page.goto('/previsit');
    await page.getByRole('button', { name: /Tạo bản tóm tắt/ }).click();
    await expect(page.getByText(/Chưa tạo được bản tóm tắt/)).toBeVisible({ timeout: 5000 });
  });
});
