'use strict';

const request = require('supertest');
const { createApp } = require('../index');

describe('Request validation — /specs/api.spec.md, validation half of validation-guardrails.spec.md', () => {
  test('missing required field is rejected with a clear reason', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/api/journal')
      .set('x-actor-role', 'agent:staged_write')
      .send({});
    expect(res.status).toBe(400);
    expect(res.body.details[0]).toMatch(/missing required field: content/);
  });

  test('wrong type is rejected', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/api/journal')
      .set('x-actor-role', 'agent:staged_write')
      .send({ content: 12345 });
    expect(res.status).toBe(400);
  });

  test('validation runs before the handler — RBAC-denied requests never reach it (order matters)', async () => {
    const app = createApp();
    // agent:read_only is denied by RBAC regardless of body validity — should get 403, not 400
    const res = await request(app)
      .post('/api/journal')
      .set('x-actor-role', 'agent:read_only')
      .send({}); // invalid body, but RBAC should reject first
    expect(res.status).toBe(403);
  });
});
