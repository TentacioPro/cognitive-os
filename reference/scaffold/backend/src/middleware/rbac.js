'use strict';

/**
 * Permission matrix for the API gateway. Permissions remain data so every
 * route uses the same authorization behavior and no agent role can self-escalate.
 */

const PERMISSIONS = {
  owner: [
    'read', 'write_staged', 'commit', 'modify_schema',
    'read_audit', 'grant_role', 'agent:invoke',
  ],
  'agent:read_only': ['read'],
  'agent:staged_write': ['read', 'write_staged'],
  'agent:service': ['read', 'write_staged', 'agent:invoke'],
};

const ROLE_ESCALATION_ACTIONS = new Set(['grant_role']);

function requirePermission(requiredAction) {
  return function rbacMiddleware(req, res, next) {
    const identity = req.identity;
    if (!identity || !identity.role) {
      req.auditDenialReason = 'no authenticated identity on request';
      return res.status(401).json({ error: 'no authenticated identity on request', request_id: req.requestId });
    }

    if (ROLE_ESCALATION_ACTIONS.has(requiredAction) && identity.role !== 'owner') {
      req.auditDenialReason = 'role escalation attempt by non-owner identity';
      return res.status(403).json({ error: 'forbidden', reason: req.auditDenialReason, request_id: req.requestId });
    }

    const allowed = PERMISSIONS[identity.role] || [];
    if (!allowed.includes(requiredAction)) {
      req.auditDenialReason = `role '${identity.role}' lacks '${requiredAction}'`;
      return res.status(403).json({ error: 'forbidden', reason: req.auditDenialReason, request_id: req.requestId });
    }

    next();
  };
}

module.exports = { requirePermission, PERMISSIONS };
