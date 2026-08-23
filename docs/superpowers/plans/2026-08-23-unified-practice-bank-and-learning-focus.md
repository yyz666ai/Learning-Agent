# Unified Practice Bank and Learning Focus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one persistent practice bank for lesson checks, homework, and interview questions while tightening the learning sidebar and improving Markdown, emphasis, and generation progress.

**Architecture:** Add a focused `PracticeBankStore` that owns classroom/homework records and a read endpoint that merges them with the existing interview store. Keep deterministic progress and Markdown rendering in small frontend modules, and keep teaching policy in workspace Skills plus Go curriculum atoms.

**Tech Stack:** FastAPI, Pydantic, atomic JSON storage, vanilla JavaScript, CSS, pytest, Node contract tests.

---

### Task 1: Markdown code frames and emphasis

**Files:**
- Modify: `learning-agent-server/frontend/js/markdown.js`
- Modify: `learning-agent-server/frontend/css/style.css`
- Test: `learning-agent-server/tests/test_frontend_contract.py`

- [ ] Write failing Node-backed contract tests proving H4 renders as a heading, fenced Go code renders inside `.markdown-code-frame`, `==text==` renders `<mark>`, and copied code returns visible feedback.
- [ ] Run `pytest tests/test_frontend_contract.py -k 'markdown' -q` and confirm the new tests fail.
- [ ] Extend the renderer to accept heading levels 1–6, emit an accessible code-frame wrapper, hydrate copy buttons, and render escaped highlight syntax.
- [ ] Add compact Corporate Clean styling for code-frame headers, dark code bodies, `mark`, focus, hover, and reduced motion.
- [ ] Re-run the focused tests and confirm they pass.

### Task 2: Honest progress detail

**Files:**
- Modify: `learning-agent-server/frontend/js/activity-progress.js`
- Modify: `learning-agent-server/frontend/js/app.js`
- Modify: `learning-agent-server/frontend/index.html`
- Test: `learning-agent-server/tests/test_frontend_contract.py`

- [ ] Write a failing Node test expecting `estimate()` to return `completedPercent`, `remainingPercent`, elapsed text, and ETA, capped at 92 before completion.
- [ ] Run the focused test and confirm the missing fields fail.
- [ ] Return explicit completed/remaining values from `activity-progress.js`; add `activityCurrentStep` below the bar and update it whenever the generation phase rotates.
- [ ] Render `已完成 X% · 剩余 Y% · 预计还需…` without claiming server-side stage precision.
- [ ] Re-run focused frontend tests.

### Task 3: Persistent unified practice records

**Files:**
- Create: `learning-agent-server/backend/practice_bank.py`
- Modify: `learning-agent-server/backend/main.py`
- Test: `learning-agent-server/tests/test_practice_bank.py`
- Test: `learning-agent-server/tests/test_api.py`

- [ ] Write failing store tests for registering a classroom choice, recording correct/incorrect attempts, registering one homework, deduplicating repeated lesson loads, and preserving wrong-count history.
- [ ] Run `pytest tests/test_practice_bank.py -q` and confirm import/behavior failures.
- [ ] Implement atomic `practice-bank/items/*.json` records and a bank index with source, kind, lesson/page identifiers, prompt, status, attempts, wrong count, last result, and review flag.
- [ ] Write failing API tests expecting lesson generation/current to register choices and homework, lesson check to record attempts, and `/api/practice/bank` to merge practice and interview records.
- [ ] Wire the endpoint and hooks, then run the focused API/store tests.

### Task 4: Unified left-rail bank

**Files:**
- Modify: `learning-agent-server/frontend/index.html`
- Modify: `learning-agent-server/frontend/js/interview-bank.js`
- Modify: `learning-agent-server/frontend/js/artifact.js`
- Modify: `learning-agent-server/frontend/css/style.css`
- Test: `learning-agent-server/tests/test_frontend_contract.py`

- [ ] Write failing tests expecting the label `练习题库`, the `/api/practice/bank` endpoint, classroom/homework/interview source labels, wrong/review status, and a lesson-page reopen event.
- [ ] Run the focused tests and confirm the old interview-only behavior fails.
- [ ] Refactor the controller to render the merged DTO, keep interview expansion/rating for interview items, and reopen local lesson questions/homework without invoking a model.
- [ ] Add compact status badges and a visible `错题·再做一遍` state.
- [ ] Re-run frontend tests.

### Task 5: Learning-focus sidebar and settings

**Files:**
- Modify: `learning-agent-server/frontend/index.html`
- Modify: `learning-agent-server/frontend/css/style.css`
- Modify: `learning-agent-server/frontend/js/app.js`
- Test: `learning-agent-server/tests/test_frontend_contract.py`

- [ ] Write failing tests proving learning mode hides `.sidebar-projects` and `.sidebar-plan-dock`, onboarding still shows projects, and settings retains Plan/project controls.
- [ ] Write failing layout assertions for a 48px brand row, smaller tab/pager boxes, and larger tab/body text.
- [ ] Implement learning/onboarding visibility rules and compact spacing without changing mobile touch targets.
- [ ] Re-run frontend tests.

### Task 6: Teaching policy and Go knowledge atoms

**Files:**
- Modify: `learning-agent-server/workspace/dev/.codex/skills/adaptive-lesson-flow/SKILL.md`
- Modify: `learning-agent-server/backend/lesson_generator.py`
- Modify: `learning-agent-server/workspace/dev/curriculum/go/learning-paths/foundations.md`
- Create: `learning-agent-server/workspace/dev/curriculum/go/atoms/go.pointers.basics.md`
- Create: `learning-agent-server/workspace/dev/curriculum/go/atoms/go.pointers.parameters-receivers.md`
- Create: `learning-agent-server/workspace/dev/curriculum/go/atoms/go.functions.values-closures-callbacks.md`
- Test: `learning-agent-server/tests/test_teaching_contract.py`
- Test: `learning-agent-server/tests/test_lesson_generator.py`

- [ ] Write failing teaching-contract tests requiring controlled `**bold**`/`==highlight==`, pointer/function-value atoms, and explicit clarification that Go uses function values rather than C-style function pointers.
- [ ] Run focused teaching tests and confirm failure.
- [ ] Add the teaching rules and knowledge atoms, then update the Go dependency route so pointers and function values are mandatory before later engineering stages.
- [ ] Add the same emphasis contract to the lesson-generation prompt.
- [ ] Publish the validated workspace release and run the workspace validator.

### Task 7: Current learner migration, docs, and full verification

**Files:**
- Modify: `learning-agent-server/userdir/u_yang/plans/go-plan.md`
- Modify: `learning-agent-server/userdir/u_yang/curriculum.json`
- Modify: `learning-agent-server/design-qa.md`

- [ ] Insert a pointer/function-value chapter into the active Go plan and curriculum while preserving the current knowledge point and completed progress.
- [ ] Record all UI/data/knowledge changes in `design-qa.md`.
- [ ] Run `pytest -q` and require a clean pass except known upstream deprecation warnings.
- [ ] Restart the local service, exercise one correct and one incorrect choice plus homework registration, and verify bank totals/statuses through the real API.
- [ ] Verify desktop learning layout, Plan Markdown H4 rendering, code frame, progress detail, and browser console output.
