# Spec: Data Layer

## Components
- **Kùzu** — the knowledge graph (all node types from the plan doc: `Habit`, `DormantSkill`,
  `HealthTreatment`, `LifeChapter`, `CareerSkill`, `FinancialGoal`, `ValueOrPrinciple`,
  `ReadingItem`, `Document`, `Prompt`, plus a `StagingItem` type that everything passes through
  first per the confirmation-flow and RBAC specs).
- **LanceDB** — vector store for semantic retrieval over the same content.
- **Staging area** — a distinct table/namespace, not just a status flag on graph nodes, so an
  agent literally cannot write to the committed graph even by mistake — the write target is
  different.

## Hard rules

1. **Every write carries `schema_version` and `provenance`.** Both are required fields at the
   storage layer, not just convention — a write missing either is rejected before it reaches Kùzu.
2. **Migrations are scripts, never manual edits.** `data_layer/migrations/` holds one file per
   schema change, applied in order, each one reversible.
3. **Dedup runs before commit, not after**: exact hash match first (cheap), then semantic
   similarity (~0.90–0.95 cosine threshold) against nearby LanceDB vectors. A near-duplicate is
   surfaced to you at confirmation time ("this looks like it might be the same as X from March"),
   not silently merged or silently duplicated.
4. **Reads are scoped by the requesting identity's RBAC role**, enforced at the data-layer level
   too, not only at the gateway — defense in depth, per `rbac.spec.md`.

## Implementation status
`agent-service/app/data_layer/provenance.py` and `dedup.py` are implemented and tested this pass.
`graph_store.py` and `vector_store.py` are stubbed with the intended interface and a `NotImplementedError`
— wiring in actual Kùzu/LanceDB is the next concrete build step, tracked as a TODO with a failing
test (`test_graph_store.py::test_write_requires_kuzu_connection`) so it can't be silently skipped.
