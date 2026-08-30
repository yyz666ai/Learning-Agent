# Safe classroom editing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development task by task, with spec review followed by quality review. User explicitly approved working on main; do not create a branch. Root owns the final combined commit after review of existing changes.

**Goal:** Ship confirmed, reversible lesson editing plus consistent Plan scheduling and teaching constraints; verify real interactions before pushing main.

**Architecture:** Immutable lesson versions and a current pointer are authoritative. Python owns proposal, confirmation, candidate, commit, undo and export; Markdown is a deterministic readable projection, not a competing store. Frontend edits drafts and renders structured questions. Skills guide educational judgment, never grant write permission.

**Tech Stack:** FastAPI/Pydantic, Python pytest, native JavaScript/Node tests, existing Markdown renderer, Codex runtime, isolated browser evaluation.

Approved requirements: LESSON_EDITING_DESIGN.md, PLAN_EVALUATION.md, plus outstanding selection verification in LESSON_EVALUATION.md.

## Execution status — 2026-08-30

The user approved the design and implementation on main. Tasks 1–3 have implementation and regression evidence; Task 4 has final automated and scoped browser checks. Final regression rerun by the coordinating agent: **601 Python tests passed; 22 Node tests passed**. Independent review blockers were addressed, including cancellation while restore is already in flight. Untested browser scenarios below are not certified. Git history is authoritative for commit/push status.

| Task | Current evidence | Remaining acceptance |
| --- | --- | --- |
| 1 — Version store and mutation | Paired immutable versions, private keys, durable Markdown, two confirmations, restore, legacy baseline, shared bank lock and focused regression passed | Runtime/process-restart scenarios are not universally certified; no multi-worker guarantee |
| 2 — Editor and actions | Browser verified editing/save/history, real Codex candidate/apply, cancel restore then confirm undo, persistence after refresh, unmodified editor page navigation | Actual mouse text selection not certified: automation did not produce a native selection; complete visual/keyboard/IME matrix not certified |
| 3 — Scheduling and teaching | Chapter-level budgets and teaching constraints implemented and tested; advanced new generation, interview mixed replay/new generation, beginner recorded-output replay available | Other learner groups and all subsequent chapters remain untested; no blanket teaching-quality pass |
| 4 — Release | Reviews, full suites, deployment check, workspace validation, publish whitelist, scoped browser evidence and documentation completed | Commit/push and remote SHA verification; retain explicit untested scope in release report |

The checklists below retain the original work/acceptance contract; unchecked compound items must not be read as proof that no implementation exists. The table above and [release validation report](SAFE_EDITING_RELEASE_VALIDATION.md) are authoritative for current status. Version-store tests were consolidated into `tests/test_lesson_mutations.py`; there is no separate `tests/test_lesson_versions.py`.

## Task 1 — Persistent version store and mutation workflow

Files: new `backend/lesson_versions.py`, new `backend/lesson_mutations.py`, existing `backend/main.py`, `backend/lesson_generator.py`, `backend/practice_bank.py`, `backend/codex_driver.py`; `tests/test_lesson_mutations.py`, `tests/test_lesson_mutation_api.py` (including version-store regression).

- [ ] RED: create a valid existing lesson fixture, save a manual edit with its base revision, assert history contains old/new versions; undo restores old text and grading keys, while independent learner files and attempt events remain unchanged. Stale revision must raise conflict. Inject failure before pointer replace and assert original content remains readable.
- [ ] RED: propose change without invoking generator; generate only after explicit confirmation, preserve current content until apply; duplicate confirm/apply must be idempotent; cancel and cross-project/stale apply must not overwrite current.
- [ ] RED: direct old remediate and active force-generation cannot bypass confirmation; initial generation and explicit learning evaluation remediation remain purpose-scoped. Supplemental mutation must use the same candidate mechanism rather than immediately replacing active content.
- [ ] Implement immutable store under current project's `lessons/.versions/<knowledge-point-id>/`; preserve legacy JSON import, private answers, Markdown projection and current revision. Use existing project lock/guard; fail closed for invalid IDs and unexpected paths.
- [ ] Implement public workflow API contract:

```text
GET  /api/lesson/edit-state?user_id=...
  -> {lesson: public manifest, history:[{revision, reason, created_at}], can_undo}
POST /api/lesson/edit
  {user_id, base_revision, page_id, title, markdown, code}
  -> {lesson: public manifest, revision}
POST /api/lesson/proposals
  {user_id, base_revision, instruction, page_id?: string, kind: revision|supplemental}
  -> {proposal_id, status: proposed, summary, affected_page_ids, base_revision}
POST /api/lesson/proposals/{proposal_id}/generate
  {user_id, confirmed:true}
  -> candidate metadata including summary, changed pages and before/after text
POST /api/lesson/proposals/{proposal_id}/apply
  {user_id, confirmed:true}
  -> {lesson: public manifest, revision}
POST /api/lesson/proposals/{proposal_id}/cancel
  {user_id}
POST /api/lesson/restore
  {user_id, base_revision, target_revision}
  -> {lesson: public manifest, revision}
GET /api/lesson/export?user_id=...
  -> text/markdown; no private answer keys
```

Implemented transport: candidate generation is a synchronous request (model timeout 180 seconds), with `GET /api/lesson/proposals/{proposal_id}?user_id=...` for durable proposal status. Initial Plan/lesson generation retains its separate background-job transport. Proposal metadata and candidates are persisted; interrupted-generation recovery is covered by isolated tests, not a claim that every process/crash configuration has been tested. One current pointer commit controls manifest/answers/Markdown; no private versions under static serving.

- [ ] Candidate generator reads original lesson and calls Codex in restricted/isolated context, validates result, preserves unrelated page identities. Ordinary dialogue/proposal cannot write the active lesson. Read-only runtime modes must not be overridden by global default full access.
- [ ] Synchronize version-aware question associations without destroying attempted/other-source items. Preserve historical learner code when undoing appended exercise pages.
- [x] GREEN: focused version/mutation/API tests and the full Python suite passed. Spec findings were fixed and independently rechecked before quality review. Repeat with `pytest tests/test_lesson_mutations.py tests/test_lesson_mutation_api.py tests/test_lesson_chat_api.py tests/test_supplemental_coding_api.py -q`.

## Task 2 — Markdown editor, safe formatting and conversation actions

Files: new `frontend/js/lesson-editor.js`; `frontend/index.html`, `frontend/js/app.js`, `frontend/js/artifact.js`, `frontend/js/markdown.js`, `frontend/css/style.css`; new `tests/lesson_editor.test.cjs`, extend selection/rendering tests.

- [ ] RED Node tests: toolbar transforms selected text for H1/H2/H3, bold, italic, highlight, underline; fenced/inline code stays literal; no selection inserts editable text; hostile HTML cannot execute. Draft cancellation preserves original and user chat input; failed save keeps draft; conflict cannot silently overwrite.
- [ ] Implement default read-only compact toolbar, editable title/body/code with preview, Save/Cancel, version history and undo/restore. Desktop editor/preview share width; narrow screens switch panels without horizontal overflow.
- [ ] Use base_revision from manifest for save. Keep local draft keyed by user/project/lesson/page/revision, prompt before abandoning unsaved edits. Successful save reloads current lesson and preserves page by ID; cancel does not save.
- [ ] Right chat revision/supplemental requests create proposal UI, no eager generation. Explicit confirm generates candidate, preview offers apply/cancel. Render returned text safely; historical message buttons cannot apply an unrelated proposal. Reference-based revision targets the selected page. Ordinary explanation/negative requests remain read-only dialogue.
- [ ] Wire stable public events for manifest changes; formatting does not break selection highlighting, code copying, quizzes or history restoration. Add safe underline extension and nested formatting without changing code characters.
- [ ] GREEN: `node --test tests/*.test.cjs`; browser test actual readonly→edit→format→preview→save→refresh→undo, confirm/cancel/apply, real text selection, 390px and desktop screenshot/keyboard checks.

## Task 3 — Plan scheduling and educational constraints

Files: `backend/curriculum.py`, `backend/learning_plan_personalizer.py`, related tests; `.codex/skills/learning-plan/SKILL.md` and scoped references; domain route references only where necessary.

- [ ] RED: parse a one-session chapter with four concepts; chapter total must remain one (not four). Parse legacy `约 1–2 次课` and canonical `预计课次`; distinguish missing/estimated from exact. Render/parse preserve chapter session budget and explicit linear dependency contract.
- [ ] Add chapter-level total sessions and lesson/session minutes consistently. Preserve legacy point metadata as compatibility, not authoritative chapter scheduling. Do not claim entire chapter fits one session when it explicitly requires several.
- [ ] RED evaluation baseline is recorded in PLAN_EVALUATION.md: pointer receiver before pointer, SQL prerequisites missing, coverage without tasks, backpressure title-only, unspecified interview rubric/role, synthetic diagnosis phrased as actual answers.
- [ ] Update learning-plan rules and routed references: every promised ability maps to prerequisites, chapter, practice and evidence; novice Go bridges pointers/SQL; gap upgrade bridges only missing prerequisites; interview unknown role remains provisional general preparation, rubric explicit, supplied materials direct-use. Classroom/after-class budgets separate; free browsing is not mastery.
- [ ] Preserve user-confirmed goals and existing learning data; do not silently rewrite existing users' Plans. New plans and explicit user-approved revisions use new rules. Generate isolated sample plans across novice/advanced/interview and other listed scenarios; independent evaluator records remaining limits without certifying untested groups.
- [ ] GREEN: curriculum/plan tests and full Python suite, saved real model runs with timing and semantic review.

## Task 4 — Integrated acceptance and release

- [ ] Run Python suite, Node suite, diff check; run workspace validation and ensure new references are publishable.
- [ ] Independently review specification then code quality; fix findings and retest affected paths. Browser screenshots for toolbar, editor, confirmation and undo states; actual selection and refresh restoration, no simulated-DOM substitution.
- [ ] Exercise failed generation, old base conflict, cancel, restart, repeated click, student file preservation, answer privacy and version export consistency in isolated service.
- [ ] Review all tracked/untracked changes included in release, preserve unrelated local skill collections, exclude evals/runs, secrets, runtimes and user records. Never print credentials. Inspect exact Git remote and upstream status before normal main push; no force push.
- [ ] Update README and changelog with implemented—not proposed—behavior, tests and known limitations. Commit only reviewed project paths and push to origin main. Verify remote SHA equals local commit.

No “never fails” claim. A test executed is not a passing teaching outcome; report stage, evidence and remaining scope accurately.
