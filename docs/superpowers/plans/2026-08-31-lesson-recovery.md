# Lesson Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development for isolated frontend implementation and independent review. User explicitly approved immediate implementation on main; no new branch or additional design confirmation.

**Goal:** Fix the evidenced lesson lexical-coverage failure, preserve classroom navigation when closing PPT, and put infrequent support/export controls in Settings.

**Architecture:** Separate presentation collapse from onboarding state. Keep the current manifest/page/editor draft when hiding the artifact. Backend coverage continues to validate cited page IDs, distinct pages, literal concepts and grounded excerpts; recognize explicit technical term + description titles without requiring one contiguous phrase. Bug export is an opt-in local JSON download containing allowlisted diagnostic metadata, not secrets or conversation content.

**Tech Stack:** FastAPI/Python, vanilla JS/CSS, existing Bootstrap icons, pytest, Node test runner.

**Execution record (2026-08-31):** Implemented and reviewed. 844 Python and 44 Node tests pass. Same nine-topic synthetic Vue lesson passed generation/save/reload (24 pages); intermediate failures are retained. Browser visual and Windows-native acceptance remain explicitly unverified. Added JavaScript `main.js` workspace parity after inspecting generated output. See `docs/lesson-recovery-2026-08-31.md` for actual outcomes; checklists below retain the original plan rather than imply every optional acceptance method ran.

## Task 1 — Classroom controls (frontend implementer)

Files: frontend/index.html, frontend/css/style.css, frontend/js/app.js, frontend/js/lesson-editor.js, tests/lesson_workspace.test.cjs, tests/test_frontend_contract.py.

- [ ] Write red tests for collapse/reopen without curriculum/reset/network side effects, settings-only history/export/Bug controls, icon-only accessible edit state.
- [ ] Run `node --test tests/lesson_workspace.test.cjs`; observe failure against old handler.
- [ ] Introduce a layout-only function, with no state mutation or model calls:
```js
function setArtifactCollapsed(collapsed) {
  document.querySelector('#appShell').classList.toggle('is-artifact-collapsed', collapsed);
  document.querySelector('#reopenArtifactBtn').hidden = !collapsed;
}
```
- [ ] Bind close/open to the layout function; preserve unsaved editor DOM/draft, block hide during active save if needed. Reopen restores same page. Reset collapsed layout when deliberately entering another course, not when clicking close.
- [ ] CSS uses two columns for collapsed classroom (existing sidebar + flexible chat); never hide the roadmap, plan, project selector. Project selector is compact and always reachable in classroom. Responsive sidebar remains accessible.
- [ ] Move history and Markdown export buttons (same IDs) into settings; add `bugReportExportBtn` linking `/api/support/bug-report?user_id=...`. Close settings before history modal. Put edit mode and undo as accessible icon controls in artifact top right, using lock/pencil and arrow icons, title/aria-label/aria-expanded. Existing dirty confirmation remains on edit->read-only; collapse alone preserves draft.
- [ ] Run Node tests + relevant pytest frontend contracts. Report changes without touching backend, userdir, or .agents.

## Task 2 — Actual coverage failure (controller)

Files: backend/lesson_generator.py, tests/test_scope_technical_titles.py.

- [ ] Inspect the actual original/repaired Codex responses read-only. Logs show Proxy 代理 then track / trigger 依赖收集 rejected; cited bodies contain the terms separately.
- [ ] Red tests:
```python
validate('Proxy 代理', ['Proxy 包装目标对象，拦截属性读取。', '访问代理对象触发 Proxy 的 get 拦截。'])
validate('track / trigger 依赖收集', ['track 执行依赖收集。', 'trigger 通知已收集的副作用重新运行。'])
```
- [ ] Normalize only explicit mixed technical-title syntax into literal terms and description. Keep technical token boundaries; preserve negatives for missing trigger, missing 依赖收集, one real page, unrelated title-only evidence, unknown IDs. Do not add a Vue-only synonym list or disable scope validation.
- [ ] Adjust prompt so separate literal terms are acceptable; no demand to repeat full mixed title verbatim. Preserve one bounded repair.
- [ ] Run scope and full lesson regressions. Replay saved output in isolation for coverage only; do NOT publish old output as factually verified courseware. Generate a fresh synthetic Vue lesson using the configured Codex/DeepSeek route and inspect content.

## Task 3 — Support export (controller)

Files: backend/support_report.py, backend/main.py, tests/test_support_report.py.

- [ ] Red test endpoint available without a generated lesson, own user only, attachment JSON, no profile/conversation/secrets/paths/raw prompts.
- [ ] Store bounded allowlisted last generation failure/success metadata in user diagnostics, with error category, timestamp, operation, validation rule (not raw exception). Export that plus software/runtime version. No automatic uploads.
- [ ] Validate user IDs and test malformed records. Never bundle .codex-runtime, .secrets.env, raw model responses, or entire userdir.

## Task 4 — Verification/release

- [ ] Spec compliance review, then code quality review; address issues.
- [ ] `python -m pytest -q`; `node --test tests/*.test.cjs`; `git diff --check`.
- [ ] Check original confirmed Vue scope in isolated test data. Record raw paid-test outputs only under ignored evals/runs.
- [ ] Try permitted browser verification; do not bypass prior browser policy restrictions. If blocked, state visual acceptance is unverified, with automated DOM/interaction coverage instead.
- [ ] Graceful restart of the single managed server only after no active task, verify health and frontend assets. Commit only scoped files, push main; never commit .agents, userdir or secrets.
