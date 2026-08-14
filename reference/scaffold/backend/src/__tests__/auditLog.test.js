'use strict';

const request = require('supertest');
const { createApp } = require('../index');
const auditLogModule = require('../middleware/auditLog');

describe('Audit log — /specs/audit-log.spec.md', () => {
  test('a denied (403) request is still logged, with a reason', async () => {
    const app = createApp();
    await request(app)
      .post('/api/journal')
      .set('x-actor-role', 'agent:read_only')
      .send({ content: 'hi' });

    const entries = auditLogModule.readAll();
    const denied = entries.find((e) => e.result === 'denied');
    expect(denied).toBeDefined();
    expect(denied.denial_reason).toMatch(/lacks 'write_staged'/);
  });

  test('every entry carries a request_id', async () => {
    const app = createApp();
    await request(app).get('/api/health');
    const entries = auditLogModule.readAll();
    expect(entries.every((e) => !!e.request_id)).toBe(true);
  });

  test('log module exposes no update or delete function (append-only, spec hard rule 2)', () => {
    expect(auditLogModule.update).toBeUndefined();
    expect(auditLogModule.delete).toBeUndefined();
    expect(auditLogModule.remove).toBeUndefined();
  });

  test('readAll returns a defensive copy — callers cannot mutate history', async () => {
    const app = createApp();
    await request(app).get('/api/health');
    const entries = auditLogModule.readAll();
    const originalLength = entries.length;
    entries.push({ fake: 'entry' });
    expect(auditLogModule.readAll().length).toBe(originalLength);
  });
});
