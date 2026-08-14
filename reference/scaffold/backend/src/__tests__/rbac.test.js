'use strict';

const request = require('supertest');
const { createApp } = require('../index');

describe('RBAC — /specs/rbac.spec.md', () => {
  test('unauthenticated request is rejected', async () => {
    const app = createApp();
    const res = await request(app).post('/api/journal').send({ content: 'hi' });
    expect(res.status).toBe(401);
  });

  test('agent:read_only cannot write_staged (matrix rule)', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/api/journal')
      .set('x-actor-role', 'agent:read_only')
      .send({ content: 'hi' });
    expect(res.status).toBe(403);
    expect(res.body.reason).toMatch(/lacks 'write_staged'/);
  });

  test('agent:staged_write CAN write_staged', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/api/journal')
      .set('x-actor-role', 'agent:staged_write')
      .send({ content: 'hi' });
    expect(res.status).toBe(202);
  });

  test('owner can read audit log; agent:staged_write cannot (no self-escalation)', async () => {
    const app = createApp();
    const ownerRes = await request(app).get('/api/audit').set('x-actor-role', 'owner');
    expect(ownerRes.status).toBe(200);

    const agentRes = await request(app).get('/api/audit').set('x-actor-role', 'agent:staged_write');
    expect(agentRes.status).toBe(403);
  });

  test('no agent role can ever reach commit-level permission (spec hard rule 1)', () => {
    const { PERMISSIONS } = require('../middleware/rbac');
    for (const [role, actions] of Object.entries(PERMISSIONS)) {
      if (role === 'owner') continue;
      expect(actions).not.toContain('commit');
    }
  });
});
