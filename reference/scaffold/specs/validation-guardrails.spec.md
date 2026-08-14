# Spec: Validation & Anti-Hallucination Guardrails

## Two different things, both required

**Validation** = is this input well-formed (schema, types, required fields)? Runs in `backend/` on
every request, before it reaches the agent service at all.

**Guardrails** = even if an agent's output is well-formed, is it *making claims it can't support*?
This is the anti-hallucination check from the plan doc, and it runs in `agent-service/`, on every
agent output before it's allowed to be staged.

## Guardrail checks (in order, all must pass)

1. **Quantified-claim check**: does the output contain a specific number (percentage, count, dollar
   amount) not present in, or derivable from, the source data it was given? If yes → flag, don't
   auto-reject — surface it to you the way the Maaxly "Current Status" inconsistency was surfaced,
   as a specific, named discrepancy, not a vague warning.
2. **Provenance-downgrade check**: does the output cite something at a higher provenance level than
   its actual source supports (e.g. presenting an `ai_generated_unverified` claim as
   `verified_artifact`)? Reject, don't flag — this one is a hard stop.
3. **Cross-document consistency check**: if this claim also appears in another document already in
   the graph, is it *independently* sourced, or just repeated? Repetition from the same origin does
   not raise confidence — see plan doc Section 7 on the resume/bio duplication.
4. **Resume/external-output check**: anything destined for the resume/cover-letter agent runs an
   additional pass — provenance must be `user_attested` or `verified_artifact`, no exceptions, per
   `provenance.spec.md` rule 3.

## Hard rules

- Guardrail failures are logged to the audit trail (`action: reject`), same as an RBAC denial.
- A guardrail check that can't make a confident call **fails toward flagging for your review, not
  toward silent pass-through.** Silence is how the original problem happened.

## Implementation
`agent-service/app/agent_layer/guardrails.py`. `agent-service/tests/test_guardrails.py` covers all
four checks, including a regression test built directly from the real Maaxly "MVP Complete" vs.
GCP-research-doc contradiction found in this conversation — that's now a permanent test case.
