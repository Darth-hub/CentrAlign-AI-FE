import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { validateDeploymentConfig } from './check-deploy-config.mjs';

const valid = { VITE_API_URL: 'https://api.example.com/api', VITE_OIDC_AUTHORITY: 'https://auth.example.com/realms/aria' };
test('allows a preview without backend configuration', () => assert.equal(validateDeploymentConfig({}).length, 2));
test('accepts complete HTTPS configuration', () => assert.deepEqual(validateDeploymentConfig(valid), []));
test('rejects partially configured deployments', () => assert.throws(() => validateDeploymentConfig({ VITE_API_URL: valid.VITE_API_URL }), /both/));
test('rejects loopback, HTTP, invalid and credential-bearing URLs without leaking values', () => {
  for (const value of ['https://localhost/api', 'https://test.localhost/api', 'https://127.0.0.2/api', 'https://[::1]/api', 'http://api.example.com', 'broken-url', 'https://user:private-value@api.example.com/api', 'https://api.example.com/?key=private-value']) {
    assert.throws(() => validateDeploymentConfig({ ...valid, VITE_API_URL: value }), error => !error.message.includes('private-value'));
  }
});
test('rejects secret variables even with a suffix', () => {
  for (const key of ['VITE_LLM_API_KEY', 'VITE_SECRET_VALUE', 'VITE_AUTH_TOKEN_EXTRA']) {
    assert.throws(() => validateDeploymentConfig({ ...valid, [key]: 'private-value' }), /Do not expose secrets/);
  }
});
test('CLI validates Vite env files rather than process.env alone', () => {
  const directory = mkdtempSync(join(tmpdir(), 'centralign-config-'));
  try {
    writeFileSync(join(directory, '.env.production'), 'VITE_LLM_API_KEY=synthetic-secret-for-test\n');
    const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('VITE_')));
    const result = spawnSync(process.execPath, [fileURLToPath(new URL('./check-deploy-config.mjs', import.meta.url))], { cwd: directory, env, encoding: 'utf8' });
    assert.equal(result.status, 1);
    assert.match(result.stderr, /VITE_LLM_API_KEY/);
    assert.ok(!result.stderr.includes('synthetic-secret-for-test'));
  } finally { rmSync(directory, { recursive: true, force: true }); }
});
