# Persistent Agent Memory and Interview Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist learner intent and conversations, isolate every project completely, add interview-specific slots, and let Codex append validated exercises to the active HTML PPT.

**Architecture:** Add one focused user-memory module for JSON/JSONL writes, extend the validated intent schema, and keep model judgment in workspace Skills. Reuse the Codex driver for supplemental practice, then atomically update both the unified bank and the current lesson only after validation.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, vanilla JavaScript, Codex CLI, DeepSeek, pytest.

---

### Task 1: Complete project snapshot isolation

**Files:**
- Modify: `backend/project_snapshot.py`
- Test: `tests/test_project_snapshot.py`

- [x] Write failing tests proving `projects/`, `practice-bank/`, `profile.json`, and `onboarding/` survive archive/switch and never leak between projects.
- [ ] Run `pytest tests/test_project_snapshot.py -q` and confirm the new assertions fail.
- [x] Extend the snapshot allowlist with the missing project-owned paths.
- [x] Run the focused tests and confirm they pass.

### Task 2: Persist profile, intent state, and conversation events

**Files:**
- Create: `backend/user_memory.py`
- Modify: `backend/onboarding.py`
- Modify: `backend/main.py`
- Modify: `frontend/js/onboarding.js`
- Test: `tests/test_user_memory.py`
- Test: `tests/test_api.py`
- Test: `tests/test_frontend_contract.py`

- [x] Write failing tests for atomic `profile.json`, `intent-state.json`, append-only intent events, and user/assistant conversation JSONL events.
- [ ] Run focused tests and confirm the persistence APIs are missing.
- [x] Implement bounded JSON and JSONL helpers under `userdir/u_<id>/`.
- [x] Persist every validated intent decision and merge it into `profile.json` during onboarding confirmation.
- [x] Add an intent-state read endpoint and restore unfinished onboarding state in the frontend.
- [x] Persist both sides of successful streaming conversations without treating browser localStorage as the source of truth.
- [x] Run focused tests and confirm they pass.

### Task 3: Add interview-specific slot filling

**Files:**
- Modify: `backend/learning_intent.py`
- Modify: `backend/onboarding.py`
- Modify: `frontend/js/onboarding.js`
- Modify: `workspace/dev/.codex/skills/learning-intent-router/SKILL.md`
- Modify: `workspace/dev/.codex/skills/learning-plan/SKILL.md`
- Modify: `workspace/dev/.codex/skills/new-topic-research/SKILL.md`
- Modify: `workspace/dev/.codex/skills/learning-intent-router/evals/evals.json`
- Test: `tests/test_learning_intent.py`
- Test: `tests/test_onboarding.py`

- [x] Add failing tests for `target_role`, `tech_stack`, and `interview_question_source` and for the exact two-step missing-slot sequence.
- [ ] Run focused tests and confirm the current model accepts a Plan too early.
- [x] Extend Pydantic and frontend slot schemas while preserving old saved state compatibility.
- [x] Enforce that interview Plans require role, level evidence, technology stack, and question source.
- [x] Update Skills so existing evidence skips questions, collected questions route to intake, and `none` triggers research.
- [ ] Run Skill behavior evaluations and focused tests.

### Task 4: Generate supplemental exercises through Codex and append them to PPT

**Files:**
- Modify: `backend/supplemental_practice.py`
- Modify: `backend/main.py`
- Modify: `frontend/js/app.js`
- Test: `tests/test_supplemental_practice.py`
- Test: `tests/test_api.py`
- Test: `tests/test_frontend_contract.py`

- [x] Write failing tests that require the Codex driver, reject malformed answers, avoid duplicates, and insert unique check pages before mastery.
- [ ] Run focused tests and confirm direct LLM generation and non-appending behavior fail the contract.
- [x] Add a pure helper that returns a new LessonBundle without mutating the old bundle.
- [x] Switch the endpoint to `codex_driver.chat`, include the current lesson id, and atomically save only after all validation passes.
- [x] Reload the current PPT in the frontend and report how many pages and bank items were added.
- [x] Run focused tests and confirm they pass.

### Task 5: Publish, regression-test, and document

**Files:**
- Modify: `product/PRD.md`
- Modify: `product/WORKFLOWS.md`
- Modify: `product/CHANGELOG.md`

- [x] Document the persistent memory boundary, interview slot sequence, and Codex-backed PPT exercise append flow.
- [ ] Run `python -m backend.publish` and validate the published workspace.
- [ ] Run the complete pytest suite and frontend contract tests.
- [ ] Restart the local service and run a live API flow for a new interview learner and an exercise append request.
- [ ] Commit and push the verified branch to GitHub.
