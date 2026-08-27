'use strict';

const express = require('express');
const { requirePermission } = require('./middleware/rbac');
const { auditLog, readAll } = require('./middleware/auditLog');
const { validateBody } = require('./middleware/validateRequest');
const { JournalStore } = require('./storage');

const KNOWN_AGENTS = new Set([
  'journal-capture',
  'notebook-ingest',
  'metacognitive-review',
  'ikigai',
  'narrative-fidelity',
  'resume-cover-letter',
]);

const DOMAINS = [
  { name: 'health', icon: 'heart-pulse', color: '#16a34a', active: true },
  { name: 'work', icon: 'briefcase', color: '#2563eb', active: true },
  { name: 'relationships', icon: 'users', color: '#db2777', active: true },
  { name: 'learning', icon: 'book-open', color: '#9333ea', active: true },
];

function authenticate(req, res, next) {
  const role = req.headers['x-actor-role'];
  if (role) req.identity = { role };
  next();
}

function nowIso() {
  return new Date().toISOString();
}

async function invokeAgentService(agentName, payload) {
  const serviceUrl = process.env.AGENT_SERVICE_URL;
  if (serviceUrl) {
    const normalizedServiceUrl = serviceUrl.endsWith('/') ? serviceUrl.slice(0, -1) : serviceUrl;
    const response = await fetch(`${normalizedServiceUrl}/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...payload, agent: agentName, actor_role: payload.actor_role || 'owner' }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(body.detail || body.error || 'agent-service rejected invocation');
      error.statusCode = response.status;
      throw error;
    }
    return { ...body, proxied: true };
  }
  return {
    agent: agentName,
    status: 'accepted',
    guardrail_outcome: 'pass',
    output: { input: payload.input === undefined ? null : payload.input, mode: 'local-fallback' },
    proxied: false,
  };
}

function createApp() {
  const app = express();
  app.use((req, res, next) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, x-actor-role, x-request-id');
    res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
    if (req.method === 'OPTIONS') return res.status(204).end();
    return next();
  });
  const journalStore = new JournalStore(process.env.COGNITIVE_OS_DB || ':memory:');
  const roles = new Map();

  app.use(express.json());
  app.use(authenticate);
  app.use(auditLog);

  app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', timestamp: nowIso(), request_id: req.requestId });
  });

  app.post(
    '/api/journal',
    requirePermission('write_staged'),
    validateBody({ content: { required: true, type: 'string' } }),
    (req, res) => {
      const id = `journal_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      const entry = {
        id,
        content: req.body.content.trim(),
        domain: req.body.domain || 'uncategorized',
        value: req.body.value === undefined ? null : req.body.value,
        unit: req.body.unit || null,
        sentiment: req.body.sentiment === undefined ? null : req.body.sentiment,
        energy: req.body.energy === undefined ? null : req.body.energy,
        timestamp: req.body.timestamp || nowIso(),
        created_at: nowIso(),
        source: req.body.source || 'manual',
        status: 'staged',
      };
      journalStore.create(entry);
      res.status(202).json({ status: 'staged', id, entry, request_id: req.requestId });
    },
  );

  app.get('/api/journal', requirePermission('read'), (req, res) => {
    res.json({ entries: journalStore.list(), request_id: req.requestId });
  });

  app.post(
    '/api/journal/:id/confirm',
    requirePermission('commit'),
    (req, res) => {
      const committed = journalStore.commit(req.params.id, nowIso());
      if (!committed) return res.status(404).json({ error: 'staged journal entry not found', request_id: req.requestId });
      return res.status(200).json({ status: 'committed', entry: committed, request_id: req.requestId });
    },
  );

  app.post('/api/agents/:name/invoke', requirePermission('agent:invoke'), async (req, res, next) => {
    if (!KNOWN_AGENTS.has(req.params.name)) {
      return res.status(404).json({ error: 'agent not registered', request_id: req.requestId });
    }
    try {
      const result = await invokeAgentService(req.params.name, { ...req.body, actor_role: req.identity.role });
      return res.json({ ...result, request_id: req.requestId });
    } catch (error) {
      error.statusCode = error.statusCode || 502;
      return next(error);
    }
  });

  app.get('/api/audit', requirePermission('read_audit'), (req, res) => {
    res.json({ entries: readAll(), request_id: req.requestId });
  });

  app.get('/api/domains', requirePermission('read'), (req, res) => {
    res.json({ domains: DOMAINS.map((domain) => ({ ...domain })), request_id: req.requestId });
  });

  app.post(
    '/api/roles',
    requirePermission('grant_role'),
    validateBody({
      subject: { required: true, type: 'string' },
      role: { required: true, type: 'string' },
    }),
    (req, res) => {
      const allowedRoles = new Set(['owner', 'agent:read_only', 'agent:staged_write', 'agent:service']);
      if (!allowedRoles.has(req.body.role)) {
        req.auditDenialReason = `unknown role '${req.body.role}'`;
        return res.status(400).json({ error: 'invalid role', request_id: req.requestId });
      }
      roles.set(req.body.subject, req.body.role);
      return res.status(201).json({ subject: req.body.subject, role: req.body.role, request_id: req.requestId });
    },
  );

  app.use((error, req, res, _next) => {
    const statusCode = error.statusCode || 500;
    req.auditDenialReason = error.message;
    return res.status(statusCode).json({ error: error.message, request_id: req.requestId });
  });

  return app;
}

if (require.main === module) {
  const app = createApp();
  const port = process.env.PORT || 3000;
  app.listen(port, () => console.log(`backend listening on ${port}`));
}

module.exports = { createApp };
