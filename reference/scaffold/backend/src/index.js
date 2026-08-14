'use strict';

const express = require('express');
const { requirePermission } = require('./middleware/rbac');
const { auditLog, readAll } = require('./middleware/auditLog');
const { validateBody } = require('./middleware/validateRequest');

/**
 * Minimal auth stub for this scaffold: reads identity off a header instead of
 * verifying a real JWT. Replace with real auth before this leaves localhost —
 * tracked as a TODO, not hidden.
 */
function authenticate(req, res, next) {
  const role = req.headers['x-actor-role'];
  if (role) {
    req.identity = { role };
  }
  next();
}

function createApp() {
  const app = express();
  app.use(express.json());
  app.use(authenticate);
  app.use(auditLog); // logs every request, including ones RBAC will deny below

  app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', request_id: req.requestId });
  });

  app.post(
    '/api/journal',
    requirePermission('write_staged'),
    validateBody({ content: { required: true, type: 'string' } }),
    (req, res) => {
      // TODO: proxy to agent-service journal-capture agent (see specs/agent-layer.spec.md)
      res.status(202).json({ status: 'staged', request_id: req.requestId });
    }
  );

  app.get('/api/audit', requirePermission('read_audit'), (req, res) => {
    res.json({ entries: readAll(), request_id: req.requestId });
  });

  return app;
}

if (require.main === module) {
  const app = createApp();
  const port = process.env.PORT || 3000;
  app.listen(port, () => console.log(`backend listening on ${port}`));
}

module.exports = { createApp };
