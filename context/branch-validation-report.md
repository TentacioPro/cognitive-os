# Branch Validation Report — All Repos, All Branches

*Every branch below was cloned, checked out, and inspected in this session. Test suites were
executed where the environment allowed; where they couldn't run, the reason is stated instead of
guessed. All claims here are `verified_artifact` (checked against the actual repos today) unless
marked otherwise.*

Date: 2026-07-19 · Repos: `TentacioPro/CiggTrack`, `TentacioPro/maaxly`, `TentacioPro/polymath-os-android`

---

## 1. CiggTrack — 1 branch

### `master` (only branch; 3 commits, tip `4ea335a "APK"`)
- Real Flutter app, not a mock: `lib/` has `models/` (`cigarette_log.dart`, `app_settings.dart`,
  `app_theme.dart`), `services/` (`smoking_data_service.dart`, `app_settings_service.dart`),
  `providers/`, three screens (home / stats / settings) + theme. Design HTML mocks in `design/`.
- A built `app-release.apk` (+sha1) is committed — accounts for most of the repo's 48MB.
- **Tests: 1 file, and it's stale boilerplate.** `test/widget_test.dart` is Flutter's default
  "counter increments" smoke test — it asserts a counter app that this app is not. Could not
  execute (no Flutter SDK in this container), but by inspection it would fail or test nothing real.
- **Reuse value**: the data model (`cigarette_log`, per-day/week aggregation in
  `smoking_data_service`) is the direct ancestor of the `Habit` node type and the journal-capture
  agent's smoking-tracking behavior. Port the *model semantics*, not the Flutter code.

**Verdict**: single-branch, coherent, small. Mine for schema; do not extend as an app.

---

## 2. maaxly — 4 branches ⚠️ main is NOT the latest

Ahead/behind counts vs `main` (main-unique / branch-unique):

| Branch | vs main | Tip |
|---|---|---|
| `main` | — | `159dfcb` "Followup plan… deployment branch created" |
| `gcp-deploy-300` | 1 / **9** | env files deleted from branch |
| `backup/gcp-deploy-300-before-reset` | 1 / **16** | "HELLLL FIX… compose files" |
| `gcp-deploy-nov15` | 1 / **26** | "ci: trigger build november 21" |

- **All three deploy branches are ahead of `main`.** `main` has exactly 1 commit none of them have.
  Checked containment with `merge-base --is-ancestor`: **none of the three is an ancestor of
  another** — they share the early deploy commits then genuinely diverge (mostly around env-file
  deletion, compose-file fixes, and CI workflow rewrites).
- **`gcp-deploy-nov15` is the true latest state of Maaxly** (26 unique commits): working GCP deploy
  pipeline, nginx/DuckDNS routing fix (80/443→8080/8443), GitHub Actions with SSH-key handling,
  secrets stripped from the repo and gitignored, docs reorganized (`docs/` incl. issue tracker and
  GCloud storage map), and — directly relevant to Task 10 — **`scripts/backup/backup.sh`**, a real
  data-backup script.
- **Test infrastructure on `main` is broken.** 4 test files exist (`profile-visibility`,
  `messaging-utils` ×2, `ConversationOverlay`); ran `npx jest`: **all 3 suites fail on
  SyntaxError** — Jest has no Babel/ESM/JSX transform configured. These tests have plausibly never
  run green anywhere. Failure is configuration, not logic — but it means "maaxly has tests" is
  currently a false comfort.
- Stack per `main`: Vite + React frontend, Node/Express `server/` with Mongo models, Redis, and a
  `server/kafka/` producer/consumer pair, `docker-compose.kafka.yml`. (Noteworthy: Kafka exists
  *here*, in the LinkedIn-clone SaaS — this is likely where the Qwen exocortex doc's Kafka idea
  leaked in from. It stays rejected for the Cognitive OS; fine for Maaxly itself.)

**Verdict**: treat **`gcp-deploy-nov15` as maaxly's canonical branch** for any reuse (deploy
scripts, backup script, nginx/CI patterns). The three deploy branches should eventually be
reconciled into `main` — but that's Maaxly repo hygiene, not on the Cognitive OS critical path.
This is a second, sharper instance of the "which version is real" lesson: last session it was a
doc contradiction; this session it's `main` being 26 commits stale.

---

## 3. polymath-os-android — 3 branches ✅ cleanest possible topology

| Branch | vs main | Containment |
|---|---|---|
| `main` | — (0 unique commits) | |
| `feat/ui-revamp-v3` | 0 / 12 | **strict ancestor of v4** (verified) |
| `feat/ui-revamp-v4` | 0 / 33 | contains all of v3 + 21 more commits |

- **`main` has ZERO commits that v4 lacks → merging v4 is a conflict-free fast-forward.** v3 is
  fully contained in v4 and can be deleted after. Task 01 collapses from "merge two feature
  branches" to one `git merge --ff-only` plus branch cleanup.

### What was validated on `feat/ui-revamp-v4` (the build base)

**Backend (FastAPI + Mongo/motor)** — the corrected plan's claims held up, with precision added:
- `auth.py`: JWT access+refresh with rotation, Argon2id hashing, device/session tracking, account
  lockout (threshold + duration via env). Real and substantive.
- `crypto.py`: AES-256-GCM field-level encryption with per-value nonce, PBKDF2 key derivation. Real.
- Audit logging: real (`log_audit_event` → `db.audit_logs`, invoked on register/login/etc.) **but
  it lives inline in a monolithic `server.py`, Mongo-backed.** "Extend the existing audit logging"
  (Task 04) therefore means *extracting it into a module* and aligning to `audit-log.spec.md`'s
  schema — slightly more work than the plan implied, same direction.
- Backend tests: `tests/test_smoke_backend.py`, **22 tests — all are live-server integration
  tests.** Ran them: all 22 fail here with `ConnectError` (no running server + Mongo in this
  container). **Environmental, not proof of broken code** — but it also means the backend has *no
  unit-level suite*; new Python modules (RBAC/guardrails ports) must bring their own unit tests.

**Frontend (Expo/React Native)** — `frontend/`, 9 Jest suites. Ran them:
- **250 tests: 243 pass, 7 fail.** All 7 failures are theme-identity assertions (e.g. "void theme
  should have dark surface") stale after the v4 design change — tests asserting pre-revamp colors.
  Classic tests-not-updated-with-design; a small, well-scoped first red→green fix.

**Web (Next.js 15 + TypeScript, bun, Sentry)** — not "plain React JSX" as earlier docs said:
- `web/src/app/`: 22 entries ≈ **17–18 actual routes** (plan said "15 routes" — close; it grew).
- Playwright: 3 spec files containing **67 `test()` cases** (30 m3-web-components + 16 navigation
  + 21 smoke). The plan's "21 Playwright tests" counted only the smoke file. Not executed here
  (needs browsers + a running Next server) — file inspection only.

### Corrections to previously recorded numbers (guardrail check 1, applied to our own docs)
The plan doc's "303 + 140+ Jest tests" is **not reproducible against any branch**. Measured
reality on v4: **250 Expo Jest + 67 Playwright + 22 backend integration tests.** The plan doc's
numbers get corrected to these; the discrepancy is recorded here rather than silently dropped.

**Verdict**: v4 confirmed as the build base. Fast-forward it into `main`, delete v3, fix the 7
stale theme tests, then proceed with the port tasks.

---

## Consequences applied to the task ledger (see 00-spec-system v1.1)

1. **Task 01 rewritten**: ff-merge v4 → main, delete v3, fix 7 stale theme tests (first TDD rep).
2. **Maaxly canonical branch = `gcp-deploy-nov15`** recorded in every reuse map touching maaxly;
   its broken Jest config is quarantined — reuse its *code*, never its test setup.
3. **Task 10 (backup/restore) gains a reuse asset**: maaxly nov15 `scripts/backup/backup.sh` + the
   GCP deployment docs as the starting point.
4. **Task 04 rescoped**: extract inline audit logging from `server.py` into a module, then extend
   schema.
5. Stack description corrected everywhere: web = **Next.js + TypeScript**, mobile = Expo,
   backend = FastAPI. (Supersedes the "React/JSX + Node/Express" phrasing from self-log §10 —
   the decision to keep the real, tested stack was already made in the corrected plan; this
   just fixes the residual wording.)
