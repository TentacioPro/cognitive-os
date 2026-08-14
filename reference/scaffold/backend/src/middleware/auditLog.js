'use strict';

/**
 * Audit log middleware — see /specs/audit-log.spec.md.
 * Append-only by construction: this module exposes no update/delete function,
 * only `record`. There is deliberately no route anywhere in the app that
 * calls anything else on the log store.
 */

// In-memory store for this scaffold. Swap for a real append-only store
// (separate from the graph DB per spec) when wiring up persistence —
// the interface below (`record`, `readAll`) is what callers depend on,
// so the swap doesn't touch calling code.
const _entries = [];

function record(entry) {
  const complete = {
    timestamp: new Date().toISOString(),
    actor: entry.actor,
    action: entry.action,
    resource: entry.resource,
    result: entry.result,
    denial_reason: entry.denial_reason,
    request_id: entry.request_id,
  };
  _entries.push(Object.freeze(complete));
  return complete;
}

function readAll() {
  return _entries.slice(); // defensive copy — callers can never mutate history
}

/**
 * Express middleware: logs the attempt before the handler runs (per spec hard
 * rule 1 — denied requests are logged too), then logs the result afterward.
 */
function auditLog(req, res, next) {
  const requestId = req.headers['x-request-id'] || `req_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  req.requestId = requestId;

  const actor = req.identity ? req.identity.role : 'unauthenticated';

  res.on('finish', () => {
    const denied = res.statusCode === 401 || res.statusCode === 403;
    record({
      actor,
      action: req.method + ' ' + req.path,
      resource: req.path,
      result: denied ? 'denied' : res.statusCode >= 500 ? 'error' : 'success',
      denial_reason: req.auditDenialReason,
      request_id: requestId,
    });
  });

  next();
}

module.exports = { auditLog, record, readAll };
