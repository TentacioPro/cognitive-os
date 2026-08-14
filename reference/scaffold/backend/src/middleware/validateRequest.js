'use strict';

/**
 * Schema validation — the "is this well-formed" half of validation-guardrails.spec.md.
 * The other half (is this a supportable claim) lives in agent-service's guardrails.py,
 * since that check needs the actual agent output, not just the request shape.
 */

function validateBody(schema) {
  return function validateRequestMiddleware(req, res, next) {
    const errors = [];
    for (const [field, rule] of Object.entries(schema)) {
      const value = req.body ? req.body[field] : undefined;
      if (rule.required && (value === undefined || value === null || value === '')) {
        errors.push(`missing required field: ${field}`);
        continue;
      }
      if (value !== undefined && rule.type && typeof value !== rule.type) {
        errors.push(`field '${field}' expected ${rule.type}, got ${typeof value}`);
      }
    }
    if (errors.length > 0) {
      req.auditDenialReason = `validation failed: ${errors.join('; ')}`;
      return res.status(400).json({ error: 'invalid request', details: errors });
    }
    next();
  };
}

module.exports = { validateBody };
