# Thiết kế giọng nói và luồng nhắc chỉ số hằng ngày

## So sánh provider cho demo local

| Direction | Default (ships) | Optional (same interface) | Future (VinGroup enterprise) |
|---|---|---|---|
| STT | Mock xác định cho CI; runtime chỉ bật STT thật khi đặt `VOICE_STT_PROVIDER=whisper` | Whisper đa ngôn ngữ chạy local qua Transformers và ffmpeg; model mặc định `openai/whisper-tiny` | ViVoice STT hoặc provider tiếng Việt đã được duyệt |
| TTS | **Server Piper vi (default, `VOICE_TTS_PROVIDER=piper`)** — lazy per-region download, fail-open to browser | `kokoro` env seam (voicepacks speaker-named, needs manual wire — NOT recommended, over budget) | ViVoice TTS / VieNeu / ZeroTTS |

Swap engines without touching dialog brain: `src/voice/providers.py`
(`transcribe(audio_bytes)->text`, `speak(text,voice_region)->bytes|None`).
Seam: `VOICE_TTS_PROVIDER=piper|kokoro|none` (default `piper`).
STT seam: `VOICE_STT_PROVIDER=mock|whisper` (mặc định `mock`). Whisper dùng
Transformers đã có trong môi trường và cần `ffmpeg` trên `PATH`; model được tải
vào cache local, không commit vào repo. CI giữ mock để không tải model hoặc gọi mạng.

## Thử nghiệm TTS trên server ngày 26/09/2026
- **Piper-vi (WINNER, wired)**: 3 official voices, `rhasspy/piper-voices`
  (espeak voice `vi`; `piper-tts` wheel embeds espeak-ng, no system install):
  `Bac → vi_VN-vais1000-medium` (female, ~64MB),
  `Trung → vi_VN-vivos-x_low` (female, ~32MB),
  `Nam → speaches-ai/piper-vi_VN-25hours_single-low` (`model.onnx`, ~63MB).
  Speakers differ (not certified region accents); certified Bac/Nam accents →
  community bucket `bonelag/voice` (40 VI models, espeak `vi`/`vi-vn-x-south`).
  Models download lazily per region into `metadata/voice_models/` (gitignored).
- **Kokoro-VN (NOT wired to inference — over budget)**: real
  (`contextboxai/Kokoro-Vietnamese`: `kokoro_vi.onnx` + voicepacks
  `diem_trinh/mai_linh/hung_thinh/...` + `vig2p` G2P, no espeak-ng) BUT base
  82M fp32 ~326MB / fp16 ~163MB (+ voicepack + `onnxruntime` +
  `kokoro-vietnamese` + `vig2p` chain) exceeds the 60-120MB budget, and
  voicepacks are speaker-named (no Bac/Trung/Nam mapping). Kept as
  `VOICE_TTS_PROVIDER=kokoro` seam (`KOKORO_REGION_VOICES` + fail-open
  `KokoroProvider.speak()->None`); inference wire lands only if user picks it.
- Unknown `voice_region` → `Bac` fallback (`_norm_region`).

## Nghe thử A/B
```powershell
# 1) login (session cookie, demo account)
$u = @{username='demo_patient_01';password='Demo@123'} | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/v1/auth/login-json -Method Post -Body $u -ContentType 'application/json' -SessionVariable s
# A) confirmation sentence, Piper Bac
$b = @{text='Bác vừa nói 126 lúc đói, đúng không?';voice_region='Bac'} | ConvertTo-Json
$r = Invoke-RestMethod http://localhost:8000/v1/voice/speak -Method Post -Body $b -ContentType 'application/json' -WebSession $s
[IO.File]::WriteAllBytes("$env:TEMP\tts_piper_bac.wav",[Convert]::FromBase64String($r.audio_base64))
# B) short answer, Piper Nam
$b = @{text='Chỉ số của bác ổn định. Bác nhớ đo lại sau ăn 2 giờ nhé.';voice_region='Nam'} | ConvertTo-Json
$r = Invoke-RestMethod http://localhost:8000/v1/voice/speak -Method Post -Body $b -ContentType 'application/json' -WebSession $s
[IO.File]::WriteAllBytes("$env:TEMP\tts_piper_nam.wav",[Convert]::FromBase64String($r.audio_base64))
```
To switch default after listening: `VOICE_TTS_PROVIDER=kokoro`
(opt-in only) or `none` (browser-only); no code change needed.

### Enabling Piper (server TTS)
1. `pip install piper-tts` (optional, NOT in requirements.txt).
2. First `/v1/voice/speak` call auto-downloads the region voice;
   missing dep/model returns `None` → fail-open text-only (+ browser fallback).

### Bật Whisper local cho STT

1. Cài nhóm dependency local bằng `pip install -e ".[local]"`, cài `ffmpeg`
   và bảo đảm lệnh có trên `PATH`.
2. Đặt `VOICE_STT_PROVIDER=whisper`; có thể đổi model bằng `VOICE_STT_MODEL`.
3. Lần khởi tạo đầu tải model từ Hugging Face. Audio được giải mã trong bộ nhớ
   qua pipe ffmpeg rồi mới đưa vào pipeline; endpoint không ghi file tạm.
4. `whisper-tiny` chỉ chứng minh đường tích hợp. Kiểm thử 04/11/2026 trả transcript
   không rỗng nhưng nhận sai câu chứa giá trị 142, nên chưa đạt gate độ chính xác
   lâm sàng và không được tự lưu chỉ số nếu người dùng chưa xác nhận.

## Nhân vật giọng nói được duyệt ngày 27/09/2026
- 3 personas, name + voice + avatar only (no per-persona dialog, no medical authority):
  `Cô Lan` (Bắc, DEFAULT) / `Cô Hương` (Trung) / `Chú Sáu` (Nam).
- Split-brain rule (D1): frontend `lib/personas.ts` is display-only
  `{id, region, name, avatarSvg, greeting}`; backend is voice-truth
  (`PERSONA_REGIONS` + `VOICE_RATE` in `providers.py`, `selected_persona`
  canonical in `prefs.py`). `/v1/voice/speak` resolves persona → region
  server-side; client-sent `voice_region` is ignored when persona is present.
- Slower speech (D3): single `VOICE_RATE=1.2` passed as Piper `length_scale`
  (no per-persona rates). Avatars are inline SVG strings (D4, no files).
- Picker (D2): post-register `/onboarding/voice` (session exists via
  auto-login) — 3 cards + Nghe thử (reuses `playServerAudio`) + Chọn/Bỏ qua
  → `POST /voice/prefs {selected_persona}` → `/`. Same picker reused in
  Settings voice section (`/settings`). Skip → `lan` (Bac).
- Prefs (D5): `selected_persona` canonical + allowlist (`norm_persona`,
  unknown/empty → `lan`); `set()` syncs `tts_voice_region`; skip → Bac.
- Tests (D6): `VOICE_TTS_PROVIDER=none` + `available=False` force-mock
  (`tests/test_voice_persona.py`); no real-audio e2e.

## Yêu cầu an toàn bắt buộc
- Numbers from speech MUST confirm before save: TTS reads back
  ("Bác vừa nói 126 lúc đói, đúng không?") → big buttons **"Đúng, lưu" /
  "Nói lại"** (≥44px) → existing `POST /v1/glucose` (panic/red-flag run).
- `check_red_flag` runs on the STT transcript BEFORE confirm/save.
- `vn_parse` is no-guess: ambiguous → re-speak, never average/guess.
- Transcript-only: audio được xử lý trong bộ nhớ, không persisted/logged.
- Mọi key chỉ nằm ở server. `tests/test_voice_api.py::test_frontend_has_no_server_keys` kiểm tra frontend không chứa key của provider.

## Nhắc chỉ số còn thiếu hằng ngày
- Required slots per patient: `GET/POST /v1/voice/prefs`
  (default `[fasting, post_meal_2h]`, sidecar `metadata/voice_prefs.json`).
- `GET /v1/voice/daily-check` is stateless read-only (today in
  Asia/Ho_Chi_Minh → missing slots + greeting).
- Frontend nags max 1/day: `localStorage voice_daily_<user>_<YYYY-MM-DD>`.
- Manual form always visible under the voice prompt ("Tự điền" anchor).
- Photo of meter deferred to phase 2 (Nura OCR-defer stands).
