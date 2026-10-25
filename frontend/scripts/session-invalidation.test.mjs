import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const source = readFileSync(new URL('../src/sessionInvalidation.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText;
const { createSessionInvalidator } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);

test('concurrent 401 responses clear the session and notify once', async () => {
  let clears = 0, notifications = 0;
  const invalidate = createSessionInvalidator(async () => { clears++; }, () => { notifications++; });
  await Promise.all([invalidate(), invalidate(), invalidate(), invalidate()]);
  assert.equal(clears, 1);
  assert.equal(notifications, 1);
  await invalidate();
  assert.equal(notifications, 1);
});
test('storage failure still returns the UI to sign-in', async () => {
  let notifications = 0;
  const invalidate = createSessionInvalidator(async () => { throw new Error('storage unavailable'); }, () => { notifications++; });
  await invalidate();
  assert.equal(notifications, 1);
});
test('does not notify before local clearing finishes', async () => {
  let release;
  const order = [];
  const invalidate = createSessionInvalidator(() => new Promise(resolve => { release = resolve; }), () => order.push('signed out'));
  const pending = invalidate();
  await Promise.resolve();
  assert.deepEqual(order, []);
  release();
  await pending;
  assert.deepEqual(order, ['signed out']);
});
