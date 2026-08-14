NIGHT SHIFT invocation. You are headless; no human until morning. Read
docs/setup/autopilot-pack.md §1 (your standing contract) — its interrupt rules apply,
with one change: on interrupt, write blocked_on + push + EXIT (no human wait).

RATCHET RULES:
1. First: git pull --ff-only origin feat/ui-revamp-v4; read specs/tasks/NIGHT-QUEUE.md
   and all *.state.md. Determine the single next unblocked queue item.
2. Advance it as far as budget allows (≤70 turns). EVERY loop-step boundary: commit + push.
   Never leave uncommitted work — a rate-limit death must cost zero.
3. If the item completes: update state, self-review per §1, mark done in NIGHT-QUEUE.md,
   commit, push, and if turns remain, start the next item.
4. If ALL items are done or blocked: write specs/tasks/morning-report.md (state summary,
   metrics rollup, blockers, what you'd do next), create specs/tasks/NIGHT-DONE.flag,
   commit, push, exit.
5. NEVER overnight: touch main, run migrations, delete branches, weaken a test, edit .env.
   Anything requiring these → blocked_on + move on.
