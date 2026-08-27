'use strict';

const fs = require('fs');
const path = require('path');

/**
 * Timestamped append-only audit log for every API request. Production runs
 * persist one JSON object per line; tests set NODE_ENV=test and remain isolated.
 */

const _entries = [];
const auditPath = process.env.COGNITIVE_OS_AUDIT_LOG || path.join(__dirname, '..', '..', 'data', 'audit.jsonl');
const persistenceEnabled = process.env.NODE_ENV !== 'test' && process.env.COGNITIVE_OS_AUDIT_LOG !== 'off';

function loadExisting() {
  if (!persistenceEnabled || !fs.existsSync(auditPath)) return;
  for (const line of fs.readFileSync(auditPath, 'utf8').split('\n')) {
    if (!line.trim()) continue;
    try { _entries.push(Object.freeze(JSON.parse(line))); } catch { /* corruption is reported by backup tooling */ }
  }
}

loadExisting();

function record(entry) {
  const complete = Object.freeze({
    timestamp: entry.timestamp || new Date().toISOString(),
    actor: entry.actor || 'unknown',
    action: entry.action,
    resource: entry.resource,
    result: entry.result,
    denial_reason: entry.denial_reason,
    request_id: entry.request_id,
  });
  _entries.push(complete);
  if (persistenceEnabled) {
    fs.mkdirSync(path.dirname(auditPath), { recursive: true });
    fs.appendFileSync(auditPath, `${JSON.stringify(complete)}\n`, 'utf8');
  }
  return complete;
}

function readAll() {
  return _entries.slice();
}

function clearForTests() {
  _entries.length = 0;
}

function auditLog(req, res, next) {
  const requestId = req.headers['x-request-id'] || `req_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  req.requestId = requestId;
  const actor = req.identity ? req.identity.role : 'unauthenticated';

  record({ actor, action: `${req.method} ${req.path}:attempt`, resource: req.path, result: 'started', request_id: requestId });

  res.on('finish', () => {
    const denied = res.statusCode === 401 || res.statusCode === 403;
    record({
      actor,
      action: `${req.method} ${req.path}`,
      resource: req.path,
      result: denied ? 'denied' : res.statusCode >= 500 ? 'error' : 'success',
      denial_reason: req.auditDenialReason,
      request_id: requestId,
    });
  });

  next();
}

module.exports = { auditLog, record, readAll, clearForTests };
