# Spec: Audit Logging

## Purpose
Two audiences need this, for different reasons: **you**, so you can see what every agent actually
did over time as the system matures and gains more autonomy; and **the system itself**, so a
disputed or wrong write can be traced back to exactly what happened and why.

## What gets logged (every entry, no exceptions)

```json
{
  "timestamp": "ISO-8601",
  "actor": "owner | agent:<name>",
  "action": "read | write_staged | commit | reject | role_change",
  "resource": "node type + id, or route",
  "result": "success | denied | error",
  "denial_reason": "present only if result = denied",
  "request_id": "correlates to the agent-service trace in Opik, if applicable"
}
```

## Hard rules

1. **Logging happens before the action, not after.** A denied request is still logged — this is
   how you'd notice an agent repeatedly trying something it shouldn't.
2. **Audit logs are append-only.** No route exists to edit or delete an entry, including for
   `owner` — corrections happen by writing a new entry that references the old one, never by
   mutating history. This mirrors the plan doc's "never mutate history in place" schema rule.
3. **Audit logs are separate storage from the graph itself**, so a bug or rollback in the data
   layer can't take the audit trail down with it.
4. **You can always answer "what did every agent do this week"** with one query — this is the
   actual point of the maturity story: as agents get more autonomy over time, this is the thing
   that lets you keep trusting that autonomy.

## Implementation
`backend/src/middleware/auditLog.js` wraps every route. `backend/src/__tests__/auditLog.test.js`
asserts: denied requests are logged, entries are immutable (no update/delete route exists), and
every write carries a `request_id` that would correlate to an agent-service trace.
