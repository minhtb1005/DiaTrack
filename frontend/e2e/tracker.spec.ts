import { test, expect } from './fixtures';

// Guided UI (auth via useAuth, no User ID field): session mocked through /v1/auth/me.
// BE is not started by webServer, so API is mocked to match current UI contracts.
const ME = { id: 'e2e_user', username: 'e2e_user', role: 'user', is_active: true, is_verified: true };

// 44-byte header-only silent WAV; the Audio stub never decodes it.
const SILENT_WAV = 'UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=';

// Voice-mode loop stubs: getUserMedia + auto-stopping MediaRecorder + Audio whose
// play() resolves and fires onended immediately (so a turn completes deterministically).
function mockVoiceLoop(page: any) {
  return page.addInitScript(() => {
    const g = navigator as any;
    if (!g.mediaDevices) (g as any).mediaDevices = {};
    (g.mediaDevices as any).getUserMedia = async () => ({ getTracks: () => [] });
    (window as any).MediaRecorder = class {
      ondataavailable: any = null;
      onstop: any = null;
      stream: any;
      constructor(stream: any) { this.stream = stream; }
      start() { setTimeout(() => { if (this.ondataavailable) this.ondataavailable({ data: new Blob(['voice']) }); this.stop(); }, 30); }
      stop() { if (this.onstop) this.onstop(); }
    };
    (window as any).Audio = class {
      _onended: any = null;
      _onerror: any = null;
      src: string;
      constructor(src: string) { this.src = src; }
      set onended(fn: any) { this._onended = fn; }
      get onended() { return this._onended; }
      set onerror(fn: any) { this._onerror = fn; }
      get onerror() { return this._onerror; }
      play() { setTimeout(() => { if (this._onended) this._onended(); }, 0); return Promise.resolve(); }
    };
  });
}

function dayIso(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T07:00:00`;
}

function mockSession(page: any) {
  return page.route('**/v1/auth/me', async (route: any) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(ME) });
  });
}

function mockGlucoseGet(page: any, logs: any[]) {
  return page.route('**/v1/glucose/*', async (route: any) => {
    if (route.request().method() !== 'GET') {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: ME.id,
        logs,
        stats: { user_id: ME.id, total_logs: logs.length, avg_mgdl: 130, last_7_days_avg: 130, streak_days: 1, logs_per_week: 0.5, classification_counts: { no_alert: logs.length } },
        should_escalate: false,
        anomaly_ids: [],
      }),
    });
  });
}

function mockGlucosePost(page: any, resp: any) {
  return page.route('**/v1/glucose', async (route: any) => {
    if (route.request().method() !== 'POST') {
      await route.continue();
      return;
    }
    const body = await route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 1, user_id: ME.id, value_mgdl: body.value_mgdl, measured_at: dayIso(),
        context: body.context, notes: body.notes, classification: 'no_alert', message: 'Chưa có cảnh báo; hỏi bác sĩ về mục tiêu cá nhân.',
        ...resp,
      }),
    });
  });
}

test.describe('Tracker A — Guided UI', () => {
  test('multiple days appear in chart summary and original log links', async ({ page }) => {
    await mockSession(page);
    await mockGlucoseGet(page, [
      { id: 2, user_id: ME.id, value_mgdl: 120, measured_at: '2026-10-28T07:00:00', context: 'fasting', notes: null, classification: 'elevated' },
      { id: 1, user_id: ME.id, value_mgdl: 110, measured_at: '2026-10-27T07:00:00', context: 'fasting', notes: null, classification: 'normal' },
    ]);
    await page.goto('/tracker');
    await expect(page.getByText(/Tóm tắt xu hướng 14 ngày: 2 chỉ số/)).toBeAttached();
    await expect(page.locator('#log-1')).toContainText('110 mg/dL');
    await expect(page.locator('#log-2')).toContainText('120 mg/dL');
    await expect(page.locator('#log-1')).toContainText('Chưa có cảnh báo');
    await expect(page.locator('#log-2')).toContainText('Chưa có cảnh báo');
    await expect(page.getByText('Trong ngưỡng tham khảo')).toHaveCount(0);
  });

  test('legacy high label uses measured value for warning badge', async ({ page }) => {
    await mockSession(page);
    await mockGlucoseGet(page, [
      { id: 3, user_id: ME.id, value_mgdl: 280, measured_at: dayIso(), context: 'random', notes: null, classification: 'high' },
    ]);
    await page.goto('/tracker');
    await expect(page.locator('#log-3')).toContainText('Liên hệ bác sĩ');
    await expect(page.getByText('Cao', { exact: true })).toHaveCount(0);
  });

  test('submit safe log shows KPIs and history', async ({ page }) => {
    await mockSession(page);
    await mockGlucosePost(page, { anomaly: { type: 'none', reason: '' }, follow_up_questions: [] });
    await mockGlucoseGet(page, [
      { id: 1, user_id: ME.id, value_mgdl: 130, measured_at: dayIso(), context: 'fasting', notes: null, classification: 'no_alert' },
    ]);

    await page.goto('/tracker');
    await page.locator('input[type="number"]').first().fill('130');
    await page.locator('select').first().selectOption('fasting');
    await page.getByRole('button', { name: /Lưu chỉ số/ }).click();
    await expect(page.getByText('Chưa có cảnh báo; hỏi bác sĩ về mục tiêu cá nhân.')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/Số lần ghi/)).toBeVisible();
  });

  test('critical submit shows red banner and locks chat', async ({ page }) => {
    await mockSession(page);
    await mockGlucosePost(page, {
      classification: 'critical',
      anomaly: { type: 'spike', direction: 'high', reason: 'spike test' },
      follow_up_questions: ['q1?'],
    });
    await mockGlucoseGet(page, []);

    await page.goto('/tracker');
    await page.locator('input[type="number"]').first().fill('300');
    await page.getByRole('button', { name: /Lưu chỉ số/ }).click();
    await expect(page.getByText(/CẢNH BÁO: Đường huyết nguy hiểm/)).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId('critical-banner')).toBeVisible();
    await expect(page.getByTestId('tracker-save')).toBeVisible();
    await expect(page.getByText(/Hỏi thêm ngữ cảnh/)).toBeHidden();
    await expect(page.getByRole('button', { name: /Giúp tôi hiểu biểu đồ/ })).toBeHidden();
  });

  test('spike above 250 below 300 shows warning without emergency lock', async ({ page }) => {
    await mockSession(page);
    await mockGlucosePost(page, {
      classification: 'alert_high',
      anomaly: { type: 'spike', direction: 'high', reason: 'Liên hệ bác sĩ để được hướng dẫn.' },
      follow_up_questions: ['q1?'],
    });
    await mockGlucoseGet(page, []);

    await page.goto('/tracker');
    await page.locator('input[type="number"]').first().fill('280');
    await page.getByRole('button', { name: /Lưu chỉ số/ }).click();
    await expect(page.getByTestId('critical-banner')).toBeHidden();
    await expect(page.getByText('Liên hệ bác sĩ để được hướng dẫn.')).toBeVisible();
    await expect(page.getByText(/Hỏi thêm ngữ cảnh/)).toBeVisible();
  });

  test('trend submit opens FQG chat and reply saves context', async ({ page }) => {
    await mockSession(page);
    await mockGlucosePost(page, {
      anomaly: { type: 'trend', direction: 'up', reason: 'cascade test' },
      follow_up_questions: ['Khẩu phần ăn gần đây thế nào?'],
    });
    await mockGlucoseGet(page, []);
    await page.route('**/v1/query', async (route: any) => {
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ answer: 'Ghi nhận ngữ cảnh, tiếp tục theo dõi.', contexts: [] }),
      });
    });
    await page.route('**/v1/glucose/followup', async (route: any) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ saved: true }) });
    });

    await page.goto('/tracker');
    await page.locator('input[type="number"]').first().fill('140');
    await page.getByRole('button', { name: /Lưu chỉ số/ }).click();
    await expect(page.getByText(/Cảnh báo chuỗi tăng/)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/Hỏi thêm ngữ cảnh/)).toBeVisible();
    await expect(page.getByTestId('fqg-input')).toBeVisible();
    await page.getByPlaceholder('vd: ăn 2 miếng bánh ngọt').fill('ăn 2 miếng bánh ngọt');
    await expect(page.getByTestId('fqg-send')).toBeVisible();
    await page.getByRole('button', { name: 'Gửi' }).click();
    await expect(page.getByText('Đã lưu ngữ cảnh.')).toBeVisible({ timeout: 5000 });
  });

  test('explain trend calls RAG and shows answer', async ({ page }) => {
    await mockSession(page);
    await mockGlucoseGet(page, [
      { id: 1, user_id: ME.id, value_mgdl: 130, measured_at: dayIso(), context: 'fasting', notes: null, classification: 'high' },
    ]);
    await page.route('**/v1/query', async (route: any) => {
      expect((await route.request().postDataJSON()).require_doctor_review).toBe(true);
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ answer: 'Xu hướng tăng nhẹ, khuyến nghị theo dõi WHO.', contexts: [{ source_id: 'WHO-HEARTS-D', file_name: 'WHO_HEARTS-D_2020.pdf', page_numbers: [12] }] }),
      });
    });

    await page.goto('/tracker');
    await expect(page.getByText(/Biểu đồ 14 ngày/)).toBeVisible();
    await expect(page.getByTestId('trend-explain')).toBeVisible();
    await page.getByRole('button', { name: /Giúp tôi hiểu biểu đồ/ }).click();
    await expect(page.getByText(/Xu hướng tăng nhẹ/)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('WHO_HEARTS-D_2020.pdf, trang 12')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Bản ghi #1' })).toHaveAttribute('href', '#log-1');
  });

  test('tracker hides draft while doctor review is pending', async ({ page }) => {
    await mockSession(page);
    await mockGlucoseGet(page, [
      { id: 1, user_id: ME.id, value_mgdl: 110, measured_at: dayIso(), context: 'fasting', notes: null, classification: 'elevated' },
    ]);
    await page.route('**/v1/query', async (route: any) => {
      expect((await route.request().postDataJSON()).require_doctor_review).toBe(true);
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        status: 'pending_review', answer: 'Bản nháp không được hiển thị', review_id: 'review-1', contexts: [],
      }) });
    });
    await page.goto('/tracker');
    await page.getByRole('button', { name: /Giúp tôi hiểu biểu đồ/ }).click();
    await expect(page.getByText(/Câu hỏi đang được chuyên gia xem lại/)).toBeVisible();
    await expect(page.getByText('Bản nháp không được hiển thị')).toBeHidden();
  });

  test('due reminders persist and appear when tracker opens', async ({ page }) => {
    await mockSession(page);
    await mockGlucoseGet(page, []);
    await page.goto('/tracker');
    await page.getByLabel('Lần đo tiếp theo').fill('2020-01-01T08:00');
    await page.getByLabel('Lần tái khám tiếp theo').fill('2020-01-02T08:00');
    await page.getByRole('button', { name: 'Lưu lịch nhắc' }).click();
    await expect(page.getByText(/Đã tới lịch đo đường huyết/)).toBeVisible();
    await expect(page.getByText(/Đã tới lịch tái khám/)).toBeVisible();
    await page.reload();
    await expect(page.getByLabel('Lần đo tiếp theo')).toHaveValue('2020-01-01T08:00');
    await expect(page.getByText(/Đã tới lịch tái khám/)).toBeVisible();
    await page.getByRole('button', { name: 'Xóa lịch nhắc trên thiết bị' }).click();
    await expect(page.getByText(/Đã tới lịch tái khám/)).toBeHidden();
    await page.reload();
    await expect(page.getByLabel('Lần đo tiếp theo')).toHaveValue('');
  });

  test('voice mic transcribes ambiguous then auto-sends via existing path', async ({ page }) => {
    await page.addInitScript(() => {
      const g = navigator as any;
      if (!g.mediaDevices) (g as any).mediaDevices = {};
      (g.mediaDevices as any).getUserMedia = async () => ({ getTracks: () => [] });
      (window as any).MediaRecorder = class {
        ondataavailable: any = null;
        onstop: any = null;
        stream: any;
        constructor(stream: any) { this.stream = stream; }
        start() {}
        stop() { if (this.onstop) this.onstop(); }
      };
    });
    await mockSession(page);
    await mockGlucosePost(page, {
      anomaly: { type: 'trend', direction: 'up', reason: 'cascade test' },
      follow_up_questions: ['Khẩu phần ăn gần đây thế nào?'],
    });
    await mockGlucoseGet(page, []);
    await page.route('**/v1/voice/transcribe', async (route: any) => {
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ text: 'ăn 2 miếng bánh ngọt', emergency: false, parse: { value: null, context: null, ambiguous: true, reason: 'no_number', confirm_text: '' } }),
      });
    });
    await page.route('**/v1/query', async (route: any) => {
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ answer: 'Trả lời voice rút gọn.', contexts: [] }),
      });
    });
    await page.route('**/v1/glucose/followup', async (route: any) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ saved: true }) });
    });
    await page.route('**/v1/voice/speak', async (route: any) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ audio_available: false, text: '' }) });
    });

    await page.goto('/tracker');
    await page.locator('input[type="number"]').first().fill('140');
    await page.getByRole('button', { name: /Lưu chỉ số/ }).click();
    await expect(page.getByText(/Hỏi thêm ngữ cảnh/)).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId('mic-btn')).toBeVisible();
    await page.getByTestId('mic-btn').click();
    await page.getByTestId('mic-btn').click();
    await expect(page.getByText('Trả lời voice rút gọn.')).toBeVisible({ timeout: 10000 });
    await expect(page.getByPlaceholder('vd: ăn 2 miếng bánh ngọt')).toBeVisible();
  });

  test('voice asks for missing measurement time before saving', async ({ page }) => {
    await page.addInitScript(() => {
      const g = navigator as any;
      if (!g.mediaDevices) g.mediaDevices = {};
      g.mediaDevices.getUserMedia = async () => ({ getTracks: () => [] });
      (window as any).MediaRecorder = class {
        onstop: any = null;
        start() {}
        stop() { this.onstop?.(); }
      };
    });
    await mockSession(page);
    await mockGlucoseGet(page, []);
    let transcriptCall = 0;
    let saved: any = null;
    await page.route('**/v1/voice/transcribe', async (route: any) => {
      transcriptCall++;
      const body = transcriptCall === 1
        ? { text: '110 lúc đói', emergency: false, parse: { value: 110, context: 'fasting', ambiguous: false, confirm_text: 'Bác vừa nói 110 lúc đói, đúng không?' }, measurement_time: null }
        : { text: 'lúc 7 giờ sáng', emergency: false, parse: { ambiguous: true }, measurement_time: '2026-10-30T07:00:00+07:00' };
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    });
    await page.route('**/v1/voice/speak', async (route: any) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ audio_available: false, text: '' }) });
    });
    await page.route('**/v1/glucose', async (route: any) => {
      if (route.request().method() === 'POST') {
        saved = route.request().postDataJSON();
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...saved, id: 1, anomaly: { type: 'none' }, follow_up_questions: [] }) });
      } else await route.continue();
    });
    await page.goto('/tracker#voice-entry');
    await expect(page.getByTestId('mic-btn')).toBeVisible();
    await page.getByTestId('mic-btn').click();
    await page.getByTestId('mic-btn').click();
    await expect(page.getByRole('button', { name: 'Nói giờ đo' })).toBeVisible();
    expect(saved).toBeNull();
    await page.getByRole('button', { name: 'Nói giờ đo' }).click();
    await page.getByTestId('mic-btn').click();
    await expect(page.getByRole('button', { name: 'Xác nhận đúng, lưu chỉ số' })).toBeVisible();
    await page.getByRole('button', { name: 'Xác nhận đúng, lưu chỉ số' }).click();
    await expect.poll(() => saved?.measured_at).toBe('2026-10-30T07:00:00+07:00');
  });

  test('voice STT failure shows sys message and no auto-send', async ({ page }) => {
    await page.addInitScript(() => {
      const g = navigator as any;
      if (!g.mediaDevices) (g as any).mediaDevices = {};
      (g.mediaDevices as any).getUserMedia = async () => ({ getTracks: () => [] });
      (window as any).MediaRecorder = class {
        ondataavailable: any = null;
        onstop: any = null;
        stream: any;
        constructor(stream: any) { this.stream = stream; }
        start() {}
        stop() { if (this.onstop) this.onstop(); }
      };
    });
    await mockSession(page);
    await mockGlucosePost(page, {
      anomaly: { type: 'trend', direction: 'up', reason: 'cascade test' },
      follow_up_questions: ['Khẩu phần ăn gần đây thế nào?'],
    });
    await mockGlucoseGet(page, []);
    await page.route('**/v1/voice/transcribe', async (route: any) => {
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'transcribe failed' }) });
    });
    let queryCalls = 0;
    await page.route('**/v1/query', async (route: any) => {
      queryCalls += 1;
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ answer: 'Không được gọi.', contexts: [] }),
      });
    });
    await page.route('**/v1/voice/speak', async (route: any) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ audio_available: false, text: '' }) });
    });

    await page.goto('/tracker');
    await page.locator('input[type="number"]').first().fill('140');
    await page.getByRole('button', { name: /Lưu chỉ số/ }).click();
    await expect(page.getByText(/Hỏi thêm ngữ cảnh/)).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId('mic-btn')).toBeVisible();
    await page.getByTestId('mic-btn').click();
    await page.getByTestId('mic-btn').click();
    await expect(page.getByText(/Không nghe rõ/)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Không được gọi.')).toBeHidden();
    expect(queryCalls).toBe(0);
  });

  test('voice mode auto-advances to turn 2 after TTS end, Stop halts further turns', async ({ page }) => {
    await mockVoiceLoop(page);
    await mockSession(page);
    await mockGlucosePost(page, {
      anomaly: { type: 'trend', direction: 'up', reason: 'cascade test' },
      follow_up_questions: ['Khẩu phần ăn gần đây thế nào?'],
    });
    await mockGlucoseGet(page, []);
    let transcribeCalls = 0;
    await page.route('**/v1/voice/transcribe', async (route: any) => {
      transcribeCalls += 1;
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ text: 'ăn 2 miếng bánh ngọt', emergency: false, parse: null }),
      });
    });
    await page.route('**/v1/query', async (route: any) => {
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ answer: 'Trả lời voice mode.', contexts: [] }),
      });
    });
    await page.route('**/v1/glucose/followup', async (route: any) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ saved: true }) });
    });
    await page.route('**/v1/voice/speak', async (route: any) => {
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ audio_available: true, mime: 'audio/wav', audio_base64: SILENT_WAV }),
      });
    });

    await page.goto('/tracker');
    await page.locator('input[type="number"]').first().fill('140');
    await page.getByRole('button', { name: /Lưu chỉ số/ }).click();
    await expect(page.getByText(/Hỏi thêm ngữ cảnh/)).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId('voice-mode-btn')).toBeVisible();
    await page.getByTestId('voice-mode-btn').click();
    // Turn 1: auto-stop -> transcribe -> send -> TTS ended -> gap -> turn 2 transcribe.
    await expect.poll(() => transcribeCalls, { timeout: 15000, intervals: [50] }).toBe(2);
    await page.getByTestId('voice-mode-btn').click(); // Stop
    await expect(page.getByText('Trả lời voice mode.').first()).toBeVisible();
    await page.waitForTimeout(1200);
    expect(transcribeCalls).toBe(2);
  });

  test('voice mode stops when STT fails', async ({ page }) => {
    await mockVoiceLoop(page);
    await mockSession(page);
    await mockGlucosePost(page, {
      anomaly: { type: 'trend', direction: 'up', reason: 'cascade test' },
      follow_up_questions: ['Khẩu phần ăn gần đây thế nào?'],
    });
    await mockGlucoseGet(page, []);
    let transcribeCalls = 0;
    await page.route('**/v1/voice/transcribe', async (route: any) => {
      transcribeCalls += 1;
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'transcribe failed' }) });
    });
    let queryCalls = 0;
    await page.route('**/v1/query', async (route: any) => {
      queryCalls += 1;
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ answer: 'Không được gọi.', contexts: [] }) });
    });
    await page.route('**/v1/voice/speak', async (route: any) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ audio_available: false, text: '' }) });
    });

    await page.goto('/tracker');
    await page.locator('input[type="number"]').first().fill('140');
    await page.getByRole('button', { name: /Lưu chỉ số/ }).click();
    await expect(page.getByText(/Hỏi thêm ngữ cảnh/)).toBeVisible({ timeout: 5000 });
    await page.getByTestId('voice-mode-btn').click();
    await expect(page.getByText(/Không nghe rõ/)).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('voice-mode-btn')).toHaveAttribute('aria-label', 'Bật chế độ nói liên tục');
    await page.waitForTimeout(800);
    expect(transcribeCalls).toBe(1);
    expect(queryCalls).toBe(0);
  });
});
