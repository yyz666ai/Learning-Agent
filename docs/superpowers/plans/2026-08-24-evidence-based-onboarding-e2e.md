# Evidence-based Onboarding and End-to-end Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent invented learner levels, keep diagnosis prompts attached to their choices, and prove representative learning journeys reach the first HTML lesson.

**Architecture:** The Skill remains responsible for intent judgment, while Pydantic enforces that a ready decision has user evidence for any claimed level. FastAPI retries one semantically invalid model response with explicit validation feedback. The frontend gives the diagnosis prompt a stable element in the choice tray, and an end-to-end runner verifies state transitions through lesson generation.

**Tech Stack:** FastAPI, Pydantic, DeepSeek Flash, vanilla JavaScript, pytest, HTTPX.

---

### Task 1: Enforce level evidence

**Files:**
- Modify: `tests/test_learning_intent.py`
- Modify: `backend/learning_intent.py`
- Modify: `workspace/dev/.codex/skills/learning-intent-router/SKILL.md`
- Modify: `workspace/dev/.codex/skills/learning-intent-router/evals/evals.json`

- [ ] Add failing tests proving an interview role without level returns `clarify`, while explicit `初学` can return `ready_for_plan` with `zero`.
- [ ] Add an `IntentDecision` semantic validator that rejects unsupported ready-level claims.
- [ ] Update the intent Skill and its evals to ask the single three-choice level question.
- [ ] Run the focused intent and teaching-contract tests until green.

### Task 2: Retry semantically invalid model output

**Files:**
- Modify: `tests/test_api.py`
- Modify: `backend/main.py`
- Modify: `backend/learning_intent.py`

- [ ] Add a failing API test where the first model response invents `some` and the second returns a valid level clarification.
- [ ] Add a bounded correction prompt and exactly one retry before returning the recoverable 502 response.
- [ ] Verify no project or diagnostic state is written by the invalid first response.

### Task 3: Keep diagnosis prompt with choices

**Files:**
- Modify: `tests/test_frontend_contract.py`
- Modify: `frontend/index.html`
- Modify: `frontend/js/onboarding.js`
- Modify: `frontend/css/style.css`

- [ ] Add a failing contract for a dedicated `choiceTrayQuestion` element populated by `renderDiagnostic` and cleared by `hideChoices`.
- [ ] Render the prompt immediately above diagnosis options with readable spacing and `aria-live=polite`.
- [ ] Run frontend contracts and JavaScript syntax checks.

### Task 4: Verify role-specific diagnosis contracts

**Files:**
- Modify: `tests/test_diagnostics.py`
- Modify: `backend/diagnostics.py`
- Modify: `workspace/dev/.codex/skills/adaptive-onboarding/SKILL.md`
- Modify: `workspace/dev/.codex/skills/adaptive-onboarding/evals/evals.json`

- [ ] Add failing tests that generated questions include the target role/topic and do not reuse unrelated fallback banks.
- [ ] Strengthen the diagnosis prompt and response validation so dimensions and prompts are role-relevant.
- [ ] Keep three to four clickable questions and valid answer keys.

### Task 5: Add journey-level smoke verification

**Files:**
- Create: `tools/e2e_learning_smoke.py`
- Create: `tests/test_e2e_learning_smoke.py`
- Modify: `product/CHANGELOG.md`

- [ ] Define the six approved journey cases and stage assertions.
- [ ] Implement a live-service runner that uses unique QA users, handles one clarification and optional diagnosis, confirms Plan, accepts it, generates lesson one, and validates page content.
- [ ] Add deterministic endpoint-level tests for the runner with an in-process test client.
- [ ] Run the live matrix against port 8787 and save a concise stage report without API keys or lesson contents.

### Task 6: Verify and deliver

- [ ] Run full pytest, workspace validation, JavaScript syntax, JSON validation, and `git diff --check`.
- [ ] Restart the local launch service and verify health plus the current frontend asset version.
- [ ] Commit, push GitHub `main`, and verify the remote SHA.
