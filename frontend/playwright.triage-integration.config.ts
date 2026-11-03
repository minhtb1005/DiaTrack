import { defineConfig, devices } from '@playwright/test';
import path from 'path';

const root = path.resolve(__dirname, '..');
const apiPort = Number(process.env.TRIAGE_E2E_API_PORT || 8108);
const webPort = Number(process.env.TRIAGE_E2E_WEB_PORT || 3108);
const api = `http://127.0.0.1:${apiPort}`;
const web = `http://127.0.0.1:${webPort}`;
if (!process.env.TRIAGE_E2E_DB_DIR) throw new Error('TRIAGE_E2E_DB_DIR is required');

export default defineConfig({
  testDir: './e2e',
  testMatch: 'triage-review.integration.spec.ts',
  timeout: 90_000,
  expect: { timeout: 15_000 },
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: { ...devices['Desktop Chrome'], baseURL: web, trace: 'off' },
  webServer: process.env.TRIAGE_E2E_EXTERNAL_SERVERS === '1' ? [] : [
    {
      command: '.\\.venv\\Scripts\\python.exe tests\\triage_e2e_server.py',
      cwd: root, url: `${api}/openapi.json`, reuseExistingServer: process.env.TRIAGE_E2E_EXTERNAL_SERVERS === '1',
      timeout: 180_000,
      env: { TRIAGE_E2E_DB_DIR: process.env.TRIAGE_E2E_DB_DIR,
             TRIAGE_E2E_API_PORT: String(apiPort), FRONTEND_URL: web },
    },
    {
      command: `npm run dev -- -p ${webPort} -H 127.0.0.1`,
      cwd: __dirname, url: web, reuseExistingServer: process.env.TRIAGE_E2E_EXTERNAL_SERVERS === '1',
      timeout: 180_000,
      env: { NEXT_PUBLIC_API_URL: api },
    },
  ],
});
