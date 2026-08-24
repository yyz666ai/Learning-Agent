# Generation Transaction Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent slow Plan and lesson generations from writing into a restored or switched learning project.

**Architecture:** Add a server-owned generation lease and transactional commit helper. Bind frontend requests to that lease, cancel it before restoring a project, and reject all late or mismatched writes. Use collision-resistant Unicode topic filenames and validate the project revision at both ends of lesson generation.

**Tech Stack:** FastAPI, Pydantic, Python filesystem transactions, vanilla JavaScript, pytest.

---

### Task 1: Collision-resistant Plan paths

**Files:**
- Modify: `backend/onboarding.py`
- Test: `tests/test_onboarding.py`

- [ ] Add failing tests proving `AI`, `AI前端`, and different Chinese topics receive different stable Plan paths.
- [ ] Run the focused tests and verify the old slug implementation fails.
- [ ] Implement readable Unicode normalization plus a short SHA-256 suffix.
- [ ] Run the focused tests and verify they pass.

### Task 2: Generation leases and transactional Plan commit

**Files:**
- Create: `backend/generation_transaction.py`
- Modify: `backend/onboarding.py`
- Modify: `backend/main.py`
- Test: `tests/test_generation_transaction.py`
- Test: `tests/test_api.py`

- [ ] Add failing tests for late completion after restore, superseded generations, cancellation, and rollback after a partial filesystem failure.
- [ ] Verify all new tests fail for the expected missing lease or stale-write behavior.
- [ ] Implement generation records, user locks, state preconditions, staging, atomic replacement, rollback, and preserved recovery backups.
- [ ] Make onboarding confirmation return the generation lease and make Plan personalization require it.
- [ ] Add a cancellation endpoint and structured `stale_generation` responses.
- [ ] Run focused backend tests until green.

### Task 3: Frontend cancellation and recovery ordering

**Files:**
- Modify: `frontend/js/onboarding.js`
- Modify: `frontend/js/app.js`
- Test: `tests/test_frontend_contract.py`

- [ ] Add failing contract tests requiring generation ID propagation and cancel-before-restore behavior.
- [ ] Verify the tests fail against the current fixed timeout flow.
- [ ] Store the generation ID, pass it to Plan generation, and cancel it before restore/switch.
- [ ] Replace the five-minute abort with the server-aligned timeout and show a distinct stale/cancelled message.
- [ ] Run frontend contract tests until green.

### Task 4: Lesson generation project guard

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/lesson_generator.py`
- Modify: `frontend/js/artifact.js`
- Test: `tests/test_lesson_generator.py`
- Test: `tests/test_api.py`

- [ ] Add failing tests that switch the project or current knowledge point while a lesson is being generated.
- [ ] Verify the generator currently writes the stale result.
- [ ] Capture a project revision before generation and re-check it immediately before lesson persistence.
- [ ] Return a structured stale response and reload the current project in the frontend.
- [ ] Run focused lesson tests until green.

### Task 5: Current-user recovery and full verification

**Files:**
- Modify: `docs/CHANGELOG.md` or the existing project change log
- Create: timestamped recovery backup under `userdir/u_yang/` during execution only

- [ ] Back up every project-owned path before touching current user state.
- [ ] Select one internally consistent archived/current project and restore it without deleting mixed artifacts.
- [ ] Run the complete pytest suite.
- [ ] Start the service and execute Plan success, Plan cancellation, project switch, Plan confirmation, and first lesson generation smoke tests.
- [ ] Inspect the resulting state, Plan, curriculum, and lesson topic for exact agreement.
