# Agentic Intent Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fixed onboarding questionnaire with Codex Skill-driven, multi-turn slot filling while keeping historical learning projects directly accessible from a persistent left rail.

**Architecture:** A focused `learning_intent.py` module defines the validated intent/slot contract and builds the Codex prompt. FastAPI calls Codex and returns only schema-valid decisions; the onboarding controller renders at most three dynamic choices and keeps the shared composer active for corrections. The left rail renders the active and archived projects independently of onboarding, while Python remains responsible only for safe project switching and state persistence.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest, vanilla HTML/CSS/JavaScript, Codex CLI JSONL, workspace Skills.

---

## File map

- `learning-agent-server/backend/learning_intent.py`: slot models, prompt builder and strict model-output parser.
- `learning-agent-server/backend/main.py`: intent endpoint and project-list response.
- `learning-agent-server/backend/project_snapshot.py`: active/archive project metadata.
- `learning-agent-server/tests/test_learning_intent.py`: schema, parser, prompt and multi-turn slot tests.
- `learning-agent-server/tests/test_api.py`: intent API and project-list integration tests.
- `learning-agent-server/frontend/js/onboarding.js`: model-driven onboarding state machine.
- `learning-agent-server/frontend/js/app.js`: persistent project rail and startup routing.
- `learning-agent-server/frontend/index.html`: project rail and accessible tooltip markup anchors.
- `learning-agent-server/frontend/css/style.css`: onboarding layout and compact dynamic choices.
- `learning-agent-server/tests/test_frontend_contract.py`: static UI contract.
- `learning-agent-server/workspace/dev/.codex/skills/learning-intent-router/SKILL.md`: semantic intent and slot-filling policy.
- `learning-agent-server/workspace/dev/.codex/skills/learning-intent-router/evals/evals.json`: behavior cases.
- `learning-agent-server/workspace/dev/.codex/skills/learner-onboarding/SKILL.md`: handoff from filled slots to profile/plan.
- `learning-agent-server/workspace/dev/AGENTS.md`: routing rule for free-text onboarding.
- `docs/superpowers/specs/2026-08-20-chat-first-adaptive-learning-design.md`: change record.
- `docs/superpowers/specs/2026-08-22-agentic-intent-onboarding-design.md`: approved design.

### Task 1: Define the slot-filling contract

**Files:**
- Create: `learning-agent-server/tests/test_learning_intent.py`
- Create: `learning-agent-server/backend/learning_intent.py`

- [x] **Step 1: Write failing parser and prompt tests**

```python
def test_intent_prompt_includes_recent_history_and_existing_slots():
    prompt = build_intent_prompt(
        message="其实我只想看懂项目",
        history=[{"role": "user", "content": "我要学 LangGraph"}],
        slots={"topic": "LangGraph", "learning_scope": "systematic"},
    )
    assert "learning-intent-router" in prompt
    assert "其实我只想看懂项目" in prompt
    assert '"topic": "LangGraph"' in prompt
    assert "最近对话" in prompt


def test_clarification_has_two_or_three_options_and_no_other_choice():
    decision = parse_intent_response(CLARIFY_JSON)
    assert decision.action == "clarify"
    assert 2 <= len(decision.question.options) <= 3
    assert all("其他" not in option.label and "都不" not in option.label for option in decision.question.options)
```

- [x] **Step 2: Run tests and verify RED**

Run: `cd learning-agent-server && pytest tests/test_learning_intent.py -q`
Expected: FAIL because `backend.learning_intent` does not exist.

- [x] **Step 3: Implement Pydantic models and strict parser**

Define `IntentSlots`, `IntentOption`, `IntentQuestion`, `OnboardingDecision`, and `IntentDecision`. Enforce `action` consistency, 2–3 unique options for `clarify`, no catch-all labels, and complete normalized onboarding data for `ready_for_plan`.

- [x] **Step 4: Implement the Skill-aware prompt builder**

The prompt must require `.codex/skills/learning-intent-router/SKILL.md`, carry no more than eight recent messages, serialize current slots as data, allow correction, and request one JSON object without Markdown.

- [x] **Step 5: Run tests and verify GREEN**

Run: `cd learning-agent-server && pytest tests/test_learning_intent.py -q`
Expected: PASS.

### Task 2: Add the model intent endpoint

**Files:**
- Modify: `learning-agent-server/backend/main.py`
- Modify: `learning-agent-server/tests/test_api.py`

- [x] **Step 1: Write failing API tests**

Test that `POST /api/onboarding/intent` passes the current message, recent history and slots to Codex; returns a validated clarification; rejects malformed model output with a retryable 502; and returns `ready_for_plan` without persisting the active project.

- [x] **Step 2: Run the focused tests and verify RED**

Run: `cd learning-agent-server && pytest tests/test_api.py -k 'onboarding_intent' -q`
Expected: FAIL with 404.

- [x] **Step 3: Add request model and endpoint**

The endpoint calls `chat(user_id, build_intent_prompt(...), release)`, parses through `parse_intent_response`, and returns `decision.model_dump()`. It must not call `confirm_onboarding` or mutate learning state.

- [x] **Step 4: Run the focused tests and verify GREEN**

Run: `cd learning-agent-server && pytest tests/test_api.py -k 'onboarding_intent' -q`
Expected: PASS.

### Task 3: Teach Codex the intent-routing policy

**Files:**
- Create: `learning-agent-server/workspace/dev/.codex/skills/learning-intent-router/SKILL.md`
- Create: `learning-agent-server/workspace/dev/.codex/skills/learning-intent-router/evals/evals.json`
- Modify: `learning-agent-server/workspace/dev/.codex/skills/learner-onboarding/SKILL.md`
- Modify: `learning-agent-server/workspace/dev/AGENTS.md`
- Modify: `learning-agent-server/tests/test_teaching_contract.py`

- [x] **Step 1: Add failing Skill-contract tests**

Assert that the workspace routes raw onboarding text through `learning-intent-router`; the Skill defines correction-capable slots, recent-history limits, one-question maximum, 2–3 topic-specific choices, no catch-all option, and immediate `ready_for_plan` when enough information is present.

- [x] **Step 2: Run and verify RED**

Run: `cd learning-agent-server && pytest tests/test_teaching_contract.py -k 'intent_router' -q`
Expected: FAIL because the Skill does not exist.

- [x] **Step 3: Add the minimal Skill and behavior cases**

Include cases for concept explanation, ambiguous LangGraph learning, interview deadline with stated experience, current-course debugging, interview-question intake, and a later correction that replaces previously filled scope.

- [x] **Step 4: Run and verify GREEN**

Run: `cd learning-agent-server && pytest tests/test_teaching_contract.py -k 'intent_router' -q`
Expected: PASS.

### Task 4: Expose active and archived projects in the left rail

**Files:**
- Modify: `learning-agent-server/backend/project_snapshot.py`
- Modify: `learning-agent-server/backend/main.py`
- Modify: `learning-agent-server/tests/test_api.py`
- Modify: `learning-agent-server/frontend/index.html`
- Modify: `learning-agent-server/frontend/js/app.js`
- Modify: `learning-agent-server/frontend/css/style.css`

- [x] **Step 1: Write failing project-list and frontend-contract tests**

Test that `/api/projects` includes the active project with `current=true`, progress and updated time; the startup layout keeps `learningRoadmap` visible; and there is no startup choice labeled `继续上次学习`.

- [x] **Step 2: Run and verify RED**

Run: `cd learning-agent-server && pytest tests/test_api.py -k 'project' tests/test_frontend_contract.py -k 'startup or sidebar' -q`
Expected: FAIL on active-project metadata and hidden startup rail.

- [x] **Step 3: Add safe project metadata and rail rendering**

Return the current project before archives. Clicking the current item enters learning without switching; clicking an archive uses `/api/projects/switch`. Replace the startup gate choice tray with a quiet agent welcome and keep the shared composer active.

- [x] **Step 4: Add desktop onboarding rail and mobile drawer styling**

Use an onboarding shell with a compact 240px rail and full chat area. The learning artifact remains hidden until a Plan is confirmed, but the rail does not disappear.

Desktop keeps the project list directly in the rail. Below 860px the same rail opens as a mobile drawer from the compact “学习项目” button, and the onboarding composer remains pinned to the bottom of the full-height conversation.

- [x] **Step 5: Run and verify GREEN**

Run: `cd learning-agent-server && pytest tests/test_api.py -k 'project' tests/test_frontend_contract.py -k 'startup or sidebar' -q`
Expected: PASS.

### Task 5: Replace the fixed questionnaire with multi-turn model decisions

**Files:**
- Modify: `learning-agent-server/frontend/js/onboarding.js`
- Modify: `learning-agent-server/frontend/js/app.js`
- Modify: `learning-agent-server/frontend/index.html`
- Modify: `learning-agent-server/frontend/css/style.css`
- Modify: `learning-agent-server/tests/test_frontend_contract.py`

- [x] **Step 1: Write failing frontend-contract tests**

Assert that fixed `askGoal`, `askLevel`, and `askTime` lists are absent; `/api/onboarding/intent` is used; current slots and recent onboarding history are submitted; dynamic choices are capped at three; no catch-all D button is generated; and text submission remains active during clarification.

- [x] **Step 2: Run and verify RED**

Run: `cd learning-agent-server && pytest tests/test_frontend_contract.py -k 'intent or onboarding' -q`
Expected: FAIL on the current fixed questionnaire.

- [x] **Step 3: Implement the model-driven onboarding state machine**

Use states `topic`, `analyzing`, `clarifying`, `diagnostic`, `plan_review`. Both a clicked option and direct text call the intent endpoint with accumulated slots and recent history. On `ready_for_plan`, map the validated `onboarding` payload into the existing diagnosis/confirmation flow.

- [x] **Step 4: Implement compact choices and accessible details**

Render only badge, label and an `i` detail control. Show `detail` via hover/focus tooltip and mobile tap. Do not create a fourth option; the unchanged composer placeholder explains that typing and Enter can modify the request.

- [x] **Step 5: Run and verify GREEN**

Run: `cd learning-agent-server && pytest tests/test_frontend_contract.py -k 'intent or onboarding' -q`
Expected: PASS.

### Task 6: Run regression and behavior verification

**Files:**
- Modify: `docs/superpowers/specs/2026-08-22-agentic-intent-onboarding-design.md` only if observed behavior requires clarification.

- [x] **Step 1: Run focused backend and frontend tests**

Run: `cd learning-agent-server && pytest tests/test_learning_intent.py tests/test_onboarding.py tests/test_diagnostics.py tests/test_api.py tests/test_frontend_contract.py tests/test_teaching_contract.py -q`
Expected: PASS.

- [x] **Step 2: Validate the workspace Skills**

Run: `cd learning-agent-server && python workspace/dev/tools/validate_workspace.py workspace/dev`
Expected: validation succeeds and discovers `learning-intent-router`.

- [x] **Step 3: Start the local service and test the approved intent scenarios**

Verify the acceptance cases in `docs/superpowers/specs/2026-08-22-agentic-intent-onboarding-design.md`, including project switching, direct text correction, no D option, and no fixed questionnaire fallback.

2026-08-22 incremental evidence: the old “我想学 Go” route took 21.525s. The Skill-injected Flash route with thinking disabled took 2.646s. Concept, interview, project delivery, and ambiguous project requests completed in 2.715s, 2.990s, 2.832s, and 3.321s respectively; only the ambiguous request returned one clarification question.

- [ ] **Step 4: Review the final diff without committing unrelated user changes**

Run: `git diff -- learning-agent-server/backend/learning_intent.py learning-agent-server/backend/main.py learning-agent-server/backend/project_snapshot.py learning-agent-server/frontend learning-agent-server/tests learning-agent-server/workspace/dev docs/superpowers`
Expected: only scoped intent-onboarding changes plus the user-owned pre-existing modifications that overlap these files.
