# Bilingual Learning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement task-by-task.

**Goal:** Default Chinese, globe language menu, English UI and generated learning content without destroying historical material.

**Architecture:** Explicit UI dictionaries, persisted per-user locale, request-local language context propagated into background workers and model calls. Stable machine identifiers and source versions remain unchanged.

**Tech Stack:** Vanilla JavaScript, FastAPI, Python, Codex CLI, pytest and node:test.

## Execution record — 2026-08-31

Tasks 1–3 implemented, tested and independently reviewed. Task 4 automated verification and live browser checks completed. Real model acceptance covers one English beginner Plan and chapter; a fresh paid Chinese/advanced/interview end-to-end matrix and real Windows/mobile device acceptance are **not** claimed. The checklist below is the original test-first work sequence; current evidence and limitations are recorded in [bilingual validation](2026-08-31-bilingual-validation.md).

## Task 1 — UI language layer

Files: create frontend/js/i18n.js and tests/i18n.test.cjs; modify frontend/index.html, frontend/css/style.css and frontend/js/*.js.

- [ ] Write failing node tests: default zh-CN, explicit en, interpolated labels, unknown locale rejection, language persistence failure, menu contract.
- [ ] Run `node --test tests/i18n.test.cjs` and verify missing-feature failure.
- [ ] Add `LearningI18n.t(key, params)`, explicit translation dictionaries, static data-i18n annotations and dynamic call-site translations. No MutationObserver translation of arbitrary user content.
- [ ] Add top-right globe menu in both onboarding/classroom, keyboard dismiss/select, save preference via `/api/preferences`.
- [ ] Use request header `X-Learning-Locale` for fetch calls, preserving task locale after submission.
- [ ] Run node regressions and inspect static/dynamic UI coverage.

## Task 2 — Backend locale and generation

Files: create backend/localization.py, tests/test_localization.py; modify backend/main.py, backend/llm.py, backend/codex_driver.py, backend/generation_jobs.py, backend/diagnosis_jobs.py, backend/lesson_generator.py, backend/lesson_review.py and backend/learning_plan_personalizer.py.

- [ ] Test preferences default, validation and preserving sibling settings, ContextVar reset, copied worker context, English annotation validation and English Plan parsing before code changes.
- [ ] Run `.venv/bin/python -m pytest tests/test_localization.py -q`, observe expected failures.
- [ ] Provide `normalize_locale`, `current_locale`, `locale_context`, `language_instruction`, atomic preference read/write. Preserve existing programming-language field.
- [ ] Set locale at request boundary using explicit header or saved preference. Copy context when submitting threadpool jobs. Add language instruction to both direct and Codex model boundaries.
- [ ] Make code annotation repair/checks language-aware; include locale in generation/cache context; keep semantic coverage gates.
- [ ] Localize deterministic learner feedback, and support English Plan field labels without changing stable IDs.
- [ ] Run focused tests and existing Python regression suite.

## Task 3 — Historical translation variants

Files: create backend/content_translation.py and tests/test_content_translation.py; modify backend/main.py and frontend language actions.

- [ ] Test source unchanged, identity/answer references preserved, invalid output refused, stale version detection and original fallback.
- [ ] Implement explicit confirmed translation requests for current Plan/current lesson only; asynchronous job, source hash and locale in variant key; never regenerate other chapters.
- [ ] Add translated-view actions, source-version checks and original-view fallback. Never translate user code or identifiers.
- [ ] Run translation regressions together with locale tests.

## Task 4 — Acceptance and delivery

- [ ] Independently review spec compliance, then quality; fix findings.
- [ ] Run `.venv/bin/python -m pytest tests -q` and `node --test tests/*.test.cjs`.
- [ ] Validate Chinese and English real generation in isolated test user directories; record time and any unverified steps honestly.
- [ ] Check globe/menu layouts and navigation without altering existing user course data.
- [ ] Document limitations and usage in README; commit only task files on main. Leave untracked .agents/ untouched.
