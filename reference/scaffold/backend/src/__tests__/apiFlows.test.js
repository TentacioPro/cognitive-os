'use strict';

const request = require('supertest');
const { createApp } = require('../index');
const auditLogModule = require('../middleware/auditLog');

function owner(app) {
  return {
    post: (path) => request(app).post(path).set('x-actor-role', 'owner'),
    get: (path) => request(app).get(path).set('x-actor-role', 'owner'),
  };
}

describe('Complete API flows — /specs/api.spec.md', () => {
  beforeEach(() => auditLogModule.clearForTests());

  test('owner stages a journal entry and receives an id/request_id', async () => {
    const app = createApp();
    const response = await owner(app).post('/api/journal').send({
      content: 'Walked for 30 minutes',
      domain: 'health',
      value: 30,
      unit: 'minutes',
      energy: 8,
    });
    expect(response.status).toBe(202);
    expect(response.body.status).toBe('staged');
    expect(response.body.id).toMatch(/^journal_/);
    expect(response.body.request_id).toBeTruthy();
  });

  test('owner confirms a staged journal entry and it appears in committed reads', async () => {
    const app = createApp();
    const staged = await owner(app).post('/api/journal').send({ content: 'Read 20 pages' });
    const confirmed = await owner(app).post(`/api/journal/${staged.body.id}/confirm`).send({});
    expect(confirmed.status).toBe(200);
    expect(confirmed.body.status).toBe('committed');

    const entries = await owner(app).get('/api/journal');
    expect(entries.status).toBe(200);
    expect(entries.body.entries).toHaveLength(1);
    expect(entries.body.entries[0].status).toBe('committed');
  });

  test('non-owner cannot confirm staged data', async () => {
    const app = createApp();
    const staged = await request(app)
      .post('/api/journal')
      .set('x-actor-role', 'agent:staged_write')
      .send({ content: 'Agent capture' });
    expect(staged.status).toBe(202);
    const confirmed = await request(app)
      .post(`/api/journal/${staged.body.id}/confirm`)
      .set('x-actor-role', 'agent:staged_write')
      .send({});
    expect(confirmed.status).toBe(403);
  });

  test('owner invokes a registered agent and unknown agents are rejected', async () => {
    const app = createApp();
    const known = await owner(app).post('/api/agents/journal-capture/invoke').send({ input: 'hello' });
    expect(known.status).toBe(200);
    expect(known.body.agent).toBe('journal-capture');
    expect(known.body.request_id).toBeTruthy();

    const unknown = await owner(app).post('/api/agents/nope/invoke').send({ input: 'hello' });
    expect(unknown.status).toBe(404);
  });

  test('owner manages roles and non-owners are denied', async () => {
    const app = createApp();
    const granted = await owner(app).post('/api/roles').send({ subject: 'agent:test', role: 'agent:read_only' });
    expect(granted.status).toBe(201);
    expect(granted.body.role).toBe('agent:read_only');

    const denied = await request(app)
      .post('/api/roles')
      .set('x-actor-role', 'agent:read_only')
      .send({ subject: 'agent:other', role: 'owner' });
    expect(denied.status).toBe(403);
  });

  test('domains and audit reads have stable envelopes and audit entries are timestamped', async () => {
    const app = createApp();
    const domains = await owner(app).get('/api/domains');
    expect(domains.status).toBe(200);
    expect(domains.body.domains.map((domain) => domain.name)).toContain('health');
    expect(domains.body.request_id).toBeTruthy();

    const audit = await owner(app).get('/api/audit');
    expect(audit.status).toBe(200);
    expect(audit.body.entries.length).toBeGreaterThan(0);
    expect(audit.body.entries.every((entry) => entry.timestamp && entry.request_id)).toBe(true);
  });
});


test('journal entries survive a new app instance on the same SQLite file', async () => {
  const fs = require('fs');
  const os = require('os');
  const path = require('path');
  const dbPath = path.join(os.tmpdir(), `cognitive-os-journal-${Date.now()}.sqlite`);
  process.env.COGNITIVE_OS_DB = dbPath;
  try {
    const firstApp = createApp();
    const created = await owner(firstApp).post('/api/journal').send({ content: 'Durable entry' });
    const secondApp = createApp();
    const entries = await owner(secondApp).get('/api/journal');
    expect(entries.body.entries.some((entry) => entry.id === created.body.id)).toBe(true);
  } finally {
    delete process.env.COGNITIVE_OS_DB;
    if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);
  }
});
