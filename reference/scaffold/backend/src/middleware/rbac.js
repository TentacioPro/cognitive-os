'use strict';

/**
 * RBAC middleware — see /specs/rbac.spec.md for the full contract.
 * Permission matrix is DATA, not branching logic, so adding a role/action
 * is a data change, not a code change (spec hard rule).
 */

const PERMISSIONS = {
  owner: [
    'read', 'write_staged', 'commit', 'modify_schema',
    'read_audit', 'grant_role',
  ],
  'agent:read_only': ['read'],
  'agent:staged_write': ['read', 'write_staged'],
};

const ROLE_ESCALATION_ACTIONS = new Set(['grant_role']);

/**
 * @param {string} requiredAction - one of the actions in PERMISSIONS
 * @returns {import('express').RequestHandler}
 */
function requirePermission(requiredAction) {
  return function rbacMiddleware(req, res, next) {
    const identity = req.identity; // set by an upstream `authenticate` middleware
    if (!identity || !identity.role) {
      return res.status(401).json({ error: 'no authenticated identity on request' });
    }

    // Hard rule: no role can escalate itself. Only `owner` may grant/revoke roles,
    // and self-granting is rejected even if the actor is somehow already `owner`-adjacent.
    if (ROLE_ESCALATION_ACTIONS.has(requiredAction) && identity.role !== 'owner') {
      req.auditDenialReason = 'role escalation attempt by non-owner identity';
      return res.status(403).json({ error: 'forbidden', reason: req.auditDenialReason });
    }

    const allowed = PERMISSIONS[identity.role] || [];
    if (!allowed.includes(requiredAction)) {
      req.auditDenialReason = `role '${identity.role}' lacks '${requiredAction}'`;
      return res.status(403).json({ error: 'forbidden', reason: req.auditDenialReason });
    }

    next();
  };
}

module.exports = { requirePermission, PERMISSIONS };
