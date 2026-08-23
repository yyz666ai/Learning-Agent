# Model-Driven Learning Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fixed starter lesson with a Codex-generated curriculum and per-knowledge-point lesson loop that always provides an evaluated, clickable next step.

**Architecture:** Persist a validated `curriculum.json` and one validated lesson manifest per knowledge point in each learner folder. Codex generates curricula, lessons and completion decisions; deterministic frontend and backend code render, validate and advance the state machine without guessing from natural-language chat.

**Tech Stack:** FastAPI, Pydantic, existing Codex driver with DeepSeek, JSON/Markdown persistence, vanilla JavaScript, pytest, in-app browser QA.

---

### Task 1: Structured curriculum and detailed `plan.md`

**Files:**
- Create: `learning-agent-server/backend/curriculum.py`
- Reuse: `learning-agent-server/backend/learning_plan_personalizer.py`
- Modify: `learning-agent-server/backend/main.py`
- Test: `learning-agent-server/tests/test_curriculum.py`
- Test: `learning-agent-server/tests/test_api.py`

- [x] Write failing tests proving Go, Java and FastAPI curricula contain topic-specific chapters and knowledge points, and that zero/experienced profiles differ.
- [x] Define Pydantic models `Curriculum`, `Chapter` and `KnowledgePoint` with stable IDs, prerequisites, outcomes, practice, mastery criteria, estimated sessions and status.
- [x] Implement safe load/write helpers confined to `userdir/u_<id>/curriculum.json` and a deterministic renderer that materializes every chapter and knowledge point into `plan.md`.
- [x] Build a Codex prompt that includes topic, route, diagnosed level and time budget; validate topic relevance, unique IDs, prerequisite references and at least five knowledge points before persistence.
- [x] Add `POST /api/curriculum/generate`; invalid model output must return a retryable error and must not replace the previous curriculum.
- [x] Run `pytest -q tests/test_curriculum.py tests/test_api.py -k curriculum` and confirm all focused tests pass.

### Task 2: Model-generated lesson manifests

**Files:**
- Create: `learning-agent-server/backend/lesson_generator.py`
- Modify: `learning-agent-server/backend/lesson_manifest.py`
- Modify: `learning-agent-server/backend/main.py`
- Test: `learning-agent-server/tests/test_lesson_generator.py`
- Test: `learning-agent-server/tests/test_lesson_manifest.py`

- [x] Write failing tests proving the generator receives profile, current knowledge point, prerequisites, recent evidence and session minutes.
- [x] Extend `LessonManifest` with `knowledge_point_id`, `completion_mode`, `completion_prompt` and `completion_actions`; allow 3–12 pages and multiple questions without exposing answer keys.
- [x] Parse Codex JSON output, reject wrong-topic/wrong-language manifests, and atomically persist valid lessons plus private answer keys under `lessons/`.
- [x] Replace `/api/lesson/current` fixed-template generation with saved-manifest loading; add `POST /api/lesson/generate` for missing or explicitly regenerated lessons.
- [x] Keep deterministic answer checking against the saved server-side answer-key file generated with the lesson.
- [x] Run `pytest -q tests/test_lesson_generator.py tests/test_lesson_manifest.py` and confirm all focused tests pass.

### Task 3: Completion evaluation and progression

**Files:**
- Create: `learning-agent-server/backend/lesson_progression.py`
- Modify: `learning-agent-server/backend/main.py`
- Modify: `learning-agent-server/backend/learning_content.py`
- Test: `learning-agent-server/tests/test_lesson_progression.py`
- Test: `learning-agent-server/tests/test_api.py`

- [x] Write failing tests for `advance`, `practice` and `reteach`, including proof that `advance` marks the current knowledge point complete and selects a different next ID.
- [x] Define `CompletionEvidence` and `CompletionDecision` schemas with verdict, feedback, mastery score, next action, next knowledge point and CTA label.
- [x] Build the Codex evaluation prompt from the saved completion criteria, objective quiz attempts, user evidence and recent history.
- [x] Persist attempts and update `learning-state.json` plus `curriculum.json` atomically only after a validated decision.
- [x] Add `POST /api/lesson/complete` and `POST /api/lesson/remediate`; the frontend may also use `/api/lesson/generate` with `force + remediation` for an in-place transition.
- [x] Run `pytest -q tests/test_lesson_progression.py tests/test_api.py -k 'lesson_complete or remediation'` and confirm all focused tests pass.

### Task 4: Final-page action panel

**Files:**
- Modify: `learning-agent-server/frontend/index.html`
- Modify: `learning-agent-server/frontend/css/style.css`
- Modify: `learning-agent-server/frontend/js/artifact.js`
- Modify: `learning-agent-server/frontend/js/app.js`
- Test: `learning-agent-server/tests/test_frontend_contract.py`

- [x] Write failing contract tests for the final-page panel, three action buttons, evidence input and named next-lesson CTA.
- [x] Render the action panel inside the PPT only on the final page; hide the disabled next-page dead end.
- [x] Submit evidence to `/api/lesson/complete`, show the model feedback, and render exactly one of `开始下一课`, `针对性练习` or `换一种讲法`.
- [x] Reload the returned/generated manifest through `ArtifactController` without refreshing the page and reset page progress to page 1.
- [x] Mirror the primary CTA above the chat composer without covering the composer or persisting stale guidance.
- [x] Run `pytest -q tests/test_frontend_contract.py` and confirm all frontend contracts pass.

### Task 5: Reversible learning archive flow

**Files:**
- Modify: `learning-agent-server/frontend/index.html`
- Modify: `learning-agent-server/frontend/css/style.css`
- Modify: `learning-agent-server/frontend/js/app.js`
- Modify: `learning-agent-server/frontend/js/onboarding.js`
- Test: `learning-agent-server/tests/test_frontend_contract.py`

- [x] Write failing tests proving `当前计划` opens the archive view, `＋ 新建学习项目` is explicit, and onboarding has a visible return control.
- [x] Snapshot current messages, context, lesson and page index before new-project onboarding; hide stale step guidance and lesson prompt chips.
- [x] Add `← 返回当前课程`, restore the snapshot on cancel, and switch projects only after curriculum and first lesson are successfully persisted.
- [x] Bind the current-plan archive row to the existing plan dialog instead of onboarding.
- [x] Run `pytest -q tests/test_frontend_contract.py` and confirm all focused tests pass.

### Task 6: Full verification, real model evaluation and documentation

**Files:**
- Modify: `docs/superpowers/specs/2026-08-20-chat-first-adaptive-learning-design.md`
- Modify: `docs/superpowers/plans/2026-08-20-model-driven-learning-loop.md`
- Create: `learning-agent-server/evals/audits/2026-08-20-next-step-flow/03-model-driven-final.png`
- Create: `learning-agent-server/evals/audits/2026-08-20-next-step-flow/04-archive-return.png`

- [x] Run the full `pytest -q` suite and `git diff --check`.
- [x] Run real isolated Codex curriculum/lesson evaluations for all seven routes, including Go zero beginner, experienced engineering, FastAPI project delivery and interview sprint; save raw outputs and score topic match, depth and next-step clarity.
- [x] Browser-test final-page completion, model decision, named next lesson, remediation, archive cancel and resume.
- [x] Append actual implementation files, model timings, generated chapter samples, test count and browser evidence to section 18.
- [x] Commit only this feature's files locally; do not push or create a GitHub PR.
