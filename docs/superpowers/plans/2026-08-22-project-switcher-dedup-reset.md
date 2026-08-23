# Collapsible Learning Projects Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the course outline priority, manage projects from a bottom popover, prevent duplicate topics, support confirmed deletion, and reset all private learner data without deleting shared generated lessons.

**Architecture:** `project_snapshot.py` owns deterministic topic identities and private project lifecycle operations. FastAPI exposes match/delete endpoints. The frontend uses one bottom project switcher and one confirmation dialog, while the onboarding controller pauses before Plan creation when the backend reports an existing topic. Shared generated curriculum is outside every deletion path.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest, vanilla HTML/CSS/JavaScript, Workspace Skills.

---

### Task 1: Topic identity and duplicate lookup

**Files:**
- Modify: `learning-agent-server/backend/project_snapshot.py`
- Modify: `learning-agent-server/tests/test_api.py`

- [x] **Step 1: Write failing tests**

Add tests proving that `LangGraph`, `langgraph`, and `Lang Graph` normalize to the same key; `/api/projects/match` returns the best existing project by progress then update time; and unrelated topics do not match.

- [x] **Step 2: Run the focused tests and verify RED**

Run: `cd learning-agent-server && .venv/bin/python -m pytest tests/test_api.py -k 'project_match or topic_key' -q`
Expected: FAIL because matching is not implemented.

- [x] **Step 3: Implement identity and lookup**

Add `normalize_project_topic(topic)`, include `topic_key` in project metadata, and add `find_learning_project(server_root, user_id, topic)` that sorts matches by `progress` and `updated_at` without mutating state.

- [x] **Step 4: Run the focused tests and verify GREEN**

Run the Step 2 command. Expected: PASS.

### Task 2: Safe delete API

**Files:**
- Modify: `learning-agent-server/backend/project_snapshot.py`
- Modify: `learning-agent-server/backend/main.py`
- Modify: `learning-agent-server/tests/test_api.py`

- [x] **Step 1: Write failing deletion tests**

Cover archived deletion, current-project deletion, invalid IDs, another user's ID, and a sentinel file in `workspace/dev/curriculum/generated/` that must remain unchanged.

- [x] **Step 2: Run and verify RED**

Run: `cd learning-agent-server && .venv/bin/python -m pytest tests/test_api.py -k 'delete_project' -q`
Expected: FAIL with 404 for the missing endpoint.

- [x] **Step 3: Implement exact private deletion**

Add `DELETE /api/projects/{project_id}` with `user_id` query data. `current` removes only `PROJECT_PATHS` and private snapshot/archive folders; an archive ID removes only its validated archive folder. Return the updated project list.

- [x] **Step 4: Run and verify GREEN**

Run the Step 2 command. Expected: PASS.

### Task 3: Bottom project switcher

**Files:**
- Modify: `learning-agent-server/frontend/index.html`
- Modify: `learning-agent-server/frontend/css/style.css`
- Modify: `learning-agent-server/frontend/js/app.js`
- Modify: `learning-agent-server/tests/test_frontend_contract.py`

- [x] **Step 1: Write failing layout tests**

Assert that the project list is no longer above `roadmap-heading`, a `projectSwitcherBtn` exists in `roadmap-actions`, the popover is hidden by default, and the outline panel retains the flexible height.

- [x] **Step 2: Run and verify RED**

Run: `cd learning-agent-server && .venv/bin/python -m pytest tests/test_frontend_contract.py -k 'project_switcher' -q`
Expected: FAIL because the top project region still exists.

- [x] **Step 3: Implement the compact switcher**

Move `learningProjectList` into an upward-opening bottom popover. Add a compact count button and “添加学习项目”; close on outside click and Escape. The add action calls the existing free-input onboarding home and focuses `chatInput`.

- [x] **Step 4: Run and verify GREEN**

Run the Step 2 command. Expected: PASS.

### Task 4: Context menu, long press, swipe and confirmation

**Files:**
- Modify: `learning-agent-server/frontend/index.html`
- Modify: `learning-agent-server/frontend/css/style.css`
- Modify: `learning-agent-server/frontend/js/app.js`
- Modify: `learning-agent-server/tests/test_frontend_contract.py`

- [x] **Step 1: Write failing interaction contract tests**

Assert handlers for `contextmenu`, a 600ms pointer timer, horizontal swipe threshold, a shared `requestProjectDeletion(project)` function, and a confirmation dialog containing the project title and shared-knowledge warning.

- [x] **Step 2: Run and verify RED**

Run: `cd learning-agent-server && .venv/bin/python -m pytest tests/test_frontend_contract.py -k 'project_delete' -q`
Expected: FAIL because deletion UI is missing.

- [x] **Step 3: Implement the shared deletion flow**

All gestures select one project and show the same menu. The menu's delete action opens `projectDeleteDialog`; only the dialog's destructive submit calls the API. On current deletion, reset visible context and start free-input onboarding. On archive deletion, refresh the list in place.

- [x] **Step 4: Run and verify GREEN**

Run the Step 2 command. Expected: PASS.

### Task 5: Existing-project gate in onboarding

**Files:**
- Modify: `learning-agent-server/frontend/js/onboarding.js`
- Modify: `learning-agent-server/frontend/js/app.js`
- Modify: `learning-agent-server/workspace/dev/.codex/skills/learning-intent-router/SKILL.md`
- Modify: `learning-agent-server/tests/test_frontend_contract.py`
- Modify: `learning-agent-server/tests/test_teaching_contract.py`

- [x] **Step 1: Write failing gate tests**

Verify that `ready_for_plan` calls `/api/projects/match` before snapshots or Plan creation; a match displays only “继续已有项目” and “把新目标合并进去”; direct text remains available; the Skill forbids duplicate same-topic projects.

- [x] **Step 2: Run and verify RED**

Run: `cd learning-agent-server && .venv/bin/python -m pytest tests/test_frontend_contract.py tests/test_teaching_contract.py -k 'duplicate_project or existing_project' -q`
Expected: FAIL because no gate exists.

- [x] **Step 3: Implement the gate**

Pause the onboarding state at `existing_project`. Continue switches directly to that project. Merge restores the existing project, applies the new filled slots as Plan-revision feedback, and keeps completed knowledge-point progress.

- [x] **Step 4: Run and verify GREEN**

Run the Step 2 command. Expected: PASS.

### Task 6: Verify, document and reset private data

**Files:**
- Modify: `docs/superpowers/specs/2026-08-22-project-switcher-dedup-reset-design.md`
- Modify: `docs/superpowers/plans/2026-08-22-project-switcher-dedup-reset.md`

- [x] **Step 1: Run the full suite and workspace validator**

Run: `cd learning-agent-server && .venv/bin/python -m pytest -q && .venv/bin/python workspace/dev/tools/validate_workspace.py --workspace workspace/dev`
Expected: all tests pass and `errors` is empty.

- [x] **Step 2: Verify shared knowledge before reset**

Record file counts and checksums for `workspace/dev/curriculum/generated/` and `workspace/releases/current/curriculum/generated/`.

- [x] **Step 3: Move private data to Trash and recreate the root**

Stop the launchd service, move the exact `learning-agent-server/userdir` directory to `~/.Trash/Learning-agent-userdir-<timestamp>`, recreate an empty `userdir`, then restart the launchd service. Do not use recursive deletion.

- [x] **Step 4: Verify the reset and knowledge preservation**

Confirm no `u_*` directories remain, shared checksums are unchanged, `/api/health` returns 200, and the first screen has zero projects and no previous chat messages.

- [x] **Step 5: Append the observed result to the design record**

Record the test count, backup location, preserved knowledge file counts, and any remaining limitation. Do not commit or push unrelated workspace changes.
