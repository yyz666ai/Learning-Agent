# Intent Use Case Implementation Plan

> For agentic workers: execute task-by-task with test-driven-development; independent intent_evaluator reviews evidence. User approved implementation on 2026-08-30. Keep main and existing edits; no automatic remote publication.

**Goal:** Fix demonstrated intent regressions, support dynamic input and academic routes, and retain reproducible evidence.

**Architecture:** Semantic choices stay with the model/Skill. Python validates source evidence, material excerpts and session version; frontend submits one generic message path. Tests isolate user state.

**Tech Stack:** Python/Pydantic/FastAPI, vanilla JavaScript, pytest, Node test runner, DeepSeek intent endpoint.

## 1. Contract and semantic regression

- [x] Add `tests/test_intent_use_cases.py` for greeting/open questions, concept plus code, scoped experience/negation, current-context definitions, already-filled-slot rejection and academic routes.
- [x] Run `.venv/bin/python -m pytest tests/test_intent_use_cases.py -q` and record failing baseline (initial 10 failed / 1 passed; later defect tests also failed before fixes).
- [x] Update `backend/learning_intent.py`: typed interaction, targeted correction, learner-authored evidence instead of keyword-only classification; model-authored material excerpts verified against input.
- [x] Run new tests plus `tests/test_learning_intent.py`; update only assertions that explicitly encode superseded contracts.

## 2. Recovery and data submission

- [x] Add memory/API regressions: bounded history survives refresh; new session clears active onboarding only; same request id replays; stale revision cannot overwrite. Full concurrent project-switch E2E remains outside this run.
- [x] Update `backend/user_memory.py`, `backend/main.py`: version/session metadata, lock-protected compare-and-save, authoritative evidence recovery, verified material processing/counts.
- [x] Verify with `tests/test_user_memory.py`, intent-specific API tests and new cases.

## 3. Dynamic frontend

- [x] Add Node execution tests of actual onboarding controller: initial no selection; inline free text and IME; natural no-material sent to intent; first-message material no second paste.
- [x] Update `frontend/js/onboarding.js`: inline text row, generic semantic routing, preserve question/history, request/session metadata and stale-result guard. Add compact accessible CSS, bump resource version.
- [x] Run Node tests and frontend contracts. Real browser verified Enter + refresh; 390px and 1440px screenshots have no horizontal overflow.

## 4. Skill and academic integration

- [x] Rewrite `workspace/dev/.codex/skills/learning-intent-router/SKILL.md` against recorded failures, removing fixed question sequences where unnecessary; validate metadata and real responses.
- [x] Add `academic_course` and `exam_review` to shared route contracts/strategies, persist constraints and academic context to profile, add plan-generation guidance without forcing graduation projects.
- [x] Test onboarding persistence, plan prompt and schema compatibility for both routes. Real downstream Plan/PPT not included.

## 5. Real evidence and evaluation

- [x] Make a reusable isolated runner in `tools/evaluate_intent.py`; save raw/final responses, latency, versions and errors under ignored `evals/runs/`.
- [x] Run original failures and held-out variants against dev Skill, with independent evaluation. No fake UI/Plan/PPT pass from API results.
- [x] Update Use Case document with actual after-results and unresolved items; update changelog; run broad regression and diff checks.
- [x] Keep deployment/push explicit; no new branch, no remote push, no restart of the user's active service. Use `bash run.sh` after stopping old process to load the updated code/Skill snapshot.
