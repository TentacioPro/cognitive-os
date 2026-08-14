# Spec: Provenance

## Purpose
This is the direct fix for the failure mode that motivated this whole project: a year of
AI-elaborated content quietly drifting from "notes about real work" into "confident prose
about work," with no marker showing where the line was crossed. See plan doc Section 4.5.

## The five levels (canonical list — matches the plan doc exactly)

```python
class Provenance(str, Enum):
    USER_ATTESTED = "user_attested"                 # you said it, in your own words
    VERIFIED_ARTIFACT = "verified_artifact"          # backed by a checkable primary source
    STRUCTURALLY_EVIDENCED = "structurally_evidenced" # AI-generated but backed by concrete structure
    AI_GENERATED_UNVERIFIED = "ai_generated_unverified" # LLM elaboration, unchecked
    INFERENCE = "inference"                          # the system's own pattern-noticing
```

## Hard rules

1. **Every node has exactly one provenance level. No node ships without one** — there is no
   "unset" default; the data layer rejects a write that omits it.
2. **Provenance only moves toward more trusted, and only through an explicit verification step**,
   never automatically and never backward-compatibly assumed. `ai_generated_unverified` →
   `verified_artifact` requires a logged verification action (e.g. "checked against commit
   `abc123`"), not just time passing.
3. **The resume/cover-letter agent (and anything else representing you externally) queries only
   `user_attested` and `verified_artifact` nodes.** `structurally_evidenced` is not enough on its
   own for anything that leaves the system and reaches a third party — it's a research lead, not a
   claim.
4. **`inference` nodes always carry a `derived_from` pointer** to the node(s) they were inferred
   from, so any inference is traceable back to its actual evidence.

## Implementation
`agent-service/app/data_layer/provenance.py` defines the enum and the write-time validator.
`agent-service/tests/test_provenance.py` covers: rejecting an unset provenance, rejecting a
backward provenance transition, and rejecting a resume-agent query that includes anything below
`verified_artifact`.
