# Adaptive Onboarding and Teaching Quality Phase B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a one-screen onboarding flow, click-only adaptive diagnosis, deterministic learner-state persistence, small-step teaching contract, evidence-based celebration motion, and four-persona quality regression suite.

**Architecture:** FastAPI owns onboarding, diagnosis, plan/profile persistence, and lesson-start context so Codex cannot repeat profile questions or write invalid plan paths. A focused vanilla-JavaScript onboarding controller renders the one-screen choices and click-only questions, then hands the confirmed context to the existing lesson workbench. A deterministic evaluation runner exercises four isolated users and scores latency, turns-to-teaching, state integrity, and teaching-quality signals.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest, vanilla HTML/CSS/JavaScript, Server-Sent Events, Web Animations API, Codex CLI JSONL, DeepSeek.

---

## File map

- `learning-agent-server/backend/onboarding.py`: validated onboarding types, profile/plan rendering, atomic persistence, first-lesson context.
- `learning-agent-server/backend/diagnostics.py`: fixed diagnostic question bank, adaptive stopping policy, answer scoring.
- `learning-agent-server/backend/main.py`: onboarding and diagnostic API routes; confirmed-profile teaching prompt injection.
- `learning-agent-server/tests/test_onboarding.py`: deterministic persistence and branch tests.
- `learning-agent-server/tests/test_diagnostics.py`: click-only question and 3–4/default/10-maximum rules.
- `learning-agent-server/tests/test_api.py`: API contracts and failure behavior.
- `learning-agent-server/frontend/index.html`: onboarding and diagnostic panels plus success-feedback surface.
- `learning-agent-server/frontend/js/onboarding.js`: onboarding state machine and API integration.
- `learning-agent-server/frontend/js/app.js`: boot routing, lesson handoff, exercise feedback and motion triggers.
- `learning-agent-server/frontend/css/style.css`: choice cards, diagnosis layout, progress and reduced-motion celebration.
- `learning-agent-server/tests/test_frontend_contract.py`: static UI/API/motion contracts.
- `learning-agent-server/workspace/dev/AGENTS.md`: confirmed-profile routing and small-step teaching hard rules.
- `learning-agent-server/workspace/dev/.codex/skills/learner-onboarding/SKILL.md`: UI-confirmed profile fast path.
- `learning-agent-server/workspace/dev/.codex/skills/concept-teaching/SKILL.md`: one-concept/one-current-question teaching limit.
- `learning-agent-server/workspace/dev/.codex/skills/practice-drill/SKILL.md`: one visible exercise at a time for advanced learners.
- `learning-agent-server/evals/personas.json`: four fixed regression personas and success thresholds.
- `learning-agent-server/tools/run_persona_evals.py`: isolated real-call runner and quality scorer.
- `learning-agent-server/tests/test_persona_eval.py`: deterministic scorer tests.
- `learning-agent-server/evals/reports/phase-b-baseline.md`: measured before/after evaluation report.

### Task 1: Deterministic onboarding persistence

**Files:**
- Create: `learning-agent-server/backend/onboarding.py`
- Create: `learning-agent-server/tests/test_onboarding.py`

- [ ] **Step 1: Write failing branch and persistence tests**

```python
def test_zero_beginner_skips_diagnosis():
    submission = OnboardingSubmission(
        user_id="zero",
        learning_mode="systematic",
        level_claim="zero",
        topic={"type": "go", "value": "go"},
    )
    assert needs_diagnosis(submission) is False


def test_missing_knowledge_uses_skill_guided_plan(tmp_path):
    submission = OnboardingSubmission(
        user_id="new-topic",
        learning_mode="systematic",
        level_claim="zero",
        topic={"type": "custom", "value": "webhook retry API"},
    )
    result = confirm_onboarding(tmp_path, submission, diagnosis=None)
    assert result["knowledge_source"] == "skill_guided"
    assert result["first_lesson"]["start_immediately"] is True


def test_confirm_onboarding_writes_resolvable_plan(tmp_path):
    submission = OnboardingSubmission(
        user_id="learner",
        learning_mode="systematic",
        level_claim="some",
        topic={"type": "go", "value": "go"},
    )
    result = confirm_onboarding(tmp_path, submission, diagnosis=None)
    user_dir = tmp_path / "userdir" / "u_learner"
    state = json.loads((user_dir / "learning-state.json").read_text())
    assert state["profile_status"] == "confirmed"
    assert (user_dir / state["active_plan"]).is_file()
    assert result["first_lesson"]["start_immediately"] is True
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/test_onboarding.py -v`
Expected: collection fails because `backend.onboarding` does not exist.

- [ ] **Step 3: Implement validated types and atomic writes**

Implement `OnboardingSubmission`, `DiagnosisSummary`, `needs_diagnosis`, `render_profile`, `render_plan`, and `confirm_onboarding`. Use `safe_user_id`; write temporary sibling files, then `Path.replace`; set `active_plan` to `plans/<slug>.md`; return a structured first lesson with `start_immediately=True` and `forbid_more_onboarding=True`. Resolve whether the topic exists in the knowledge index; when absent, mark `knowledge_source="skill_guided"` and still generate a teaching plan from the Skill pipeline instead of blocking.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/pytest tests/test_onboarding.py -v`
Expected: all onboarding tests pass.

- [ ] **Step 5: Commit locally**

```bash
git add learning-agent-server/backend/onboarding.py learning-agent-server/tests/test_onboarding.py
git commit -m "feat: persist deterministic learner onboarding"
```

### Task 2: Click-only adaptive diagnosis

**Files:**
- Create: `learning-agent-server/backend/diagnostics.py`
- Create: `learning-agent-server/tests/test_diagnostics.py`

- [ ] **Step 1: Write failing diagnostic-policy tests**

```python
def test_questions_are_click_only():
    question = start_diagnosis(topic="go", level_claim="some")["question"]
    assert 2 <= len(question["options"]) <= 5
    assert all(set(option) == {"id", "label"} for option in question["options"])


def test_stable_answers_stop_after_three():
    session = start_diagnosis(topic="go", level_claim="some")
    for _ in range(3):
        session = answer_diagnosis(session, selected_option_id=session["question"]["correct_option_id"])
    assert session["complete"] is True
    assert session["answered_count"] == 3


def test_diagnosis_never_exceeds_ten():
    session = start_diagnosis(topic="go", level_claim="some")
    while not session["complete"]:
        # Alternate between a correct and incorrect click so confidence remains
        # near the adaptive boundary until the hard stop is reached.
        selected = (
            session["question"]["correct_option_id"]
            if session["answered_count"] % 2 == 0
            else next(
                option["id"]
                for option in session["question"]["options"]
                if option["id"] != session["question"]["correct_option_id"]
            )
        )
        session = answer_diagnosis(session, selected_option_id=selected)
    assert session["answered_count"] <= 10
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/test_diagnostics.py -v`
Expected: collection fails because `backend.diagnostics` does not exist.

- [ ] **Step 3: Implement bank and stopping policy**

Create fixed Python, Go, project-reading, and advanced-engineering questions. Public payloads omit `correct_option_id`; server session state retains it. Stop after three consistent results, ask a fourth boundary question when confidence is below threshold, and force completion at ten.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/pytest tests/test_diagnostics.py -v`
Expected: all diagnostic tests pass.

- [ ] **Step 5: Commit locally**

```bash
git add learning-agent-server/backend/diagnostics.py learning-agent-server/tests/test_diagnostics.py
git commit -m "feat: add click-only adaptive diagnosis"
```

### Task 3: Onboarding and diagnosis APIs

**Files:**
- Modify: `learning-agent-server/backend/main.py`
- Modify: `learning-agent-server/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

```python
def test_zero_beginner_confirm_starts_lesson(client, monkeypatch, tmp_path):
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    response = client.post("/api/onboarding/confirm", json={
        "user_id": "zero-go",
        "learning_mode": "systematic",
        "level_claim": "zero",
        "topic": {"type": "go", "value": "go"},
    })
    assert response.status_code == 200
    assert response.json()["first_lesson"]["start_immediately"] is True


def test_some_experience_returns_click_question(client):
    response = client.post("/api/onboarding/start", json={
        "user_id": "some-go",
        "learning_mode": "systematic",
        "level_claim": "some",
        "topic": {"type": "go", "value": "go"},
    })
    assert response.json()["next"] == "diagnosis"
    assert response.json()["question"]["options"]


def test_diagnostic_answer_never_exposes_correct_id(client):
    started = client.post("/api/onboarding/start", json={
        "user_id": "private-answer",
        "learning_mode": "systematic",
        "level_claim": "some",
        "topic": {"type": "go", "value": "go"},
    }).json()
    response = client.post("/api/diagnostics/answer", json={
        "user_id": "private-answer",
        "session_id": started["session_id"],
        "question_id": started["question"]["id"],
        "selected_option_id": started["question"]["options"][0]["id"],
    })
    assert "correct_option_id" not in json.dumps(response.json())


def test_expired_diagnostic_session_returns_recoverable_error(client):
    response = client.post("/api/diagnostics/answer", json={
        "user_id": "expired",
        "session_id": "missing",
        "question_id": "go-1",
        "selected_option_id": "a",
    })
    assert response.status_code == 409
    assert response.json()["detail"]["recovery"] == "restart_diagnosis"
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/test_api.py -k 'onboarding or diagnostic' -v`
Expected: tests fail with HTTP 404.

- [ ] **Step 3: Implement routes and confirmed teaching prompt**

Add `POST /api/onboarding/start`, `POST /api/onboarding/confirm`, and `POST /api/diagnostics/answer`. Store diagnostic sessions under `$USER_DIR/onboarding/diagnostic.json`. Reject mismatched, expired, or replayed answers with a structured recoverable error; never silently advance corrupted state. Update `build_prompt` so confirmed first lessons prepend: `画像已由界面确认；禁止继续摸底或要求再次确认；立即讲一个核心概念并给一道当前题。`

- [ ] **Step 4: Verify GREEN and regression suite**

Run: `.venv/bin/pytest tests/test_api.py -v`
Expected: all API tests pass.

- [ ] **Step 5: Commit locally**

```bash
git add learning-agent-server/backend/main.py learning-agent-server/tests/test_api.py
git commit -m "feat: expose onboarding and diagnosis APIs"
```

### Task 4: One-screen onboarding and diagnosis UI

**Files:**
- Modify: `learning-agent-server/frontend/index.html`
- Create: `learning-agent-server/frontend/js/onboarding.js`
- Modify: `learning-agent-server/frontend/js/app.js`
- Modify: `learning-agent-server/frontend/css/style.css`
- Modify: `learning-agent-server/tests/test_frontend_contract.py`

- [ ] **Step 1: Write failing frontend contract tests**

```python
def test_onboarding_is_click_first():
    html = INDEX.read_text(encoding="utf-8")
    assert 'id="onboardingPanel"' in html
    assert 'data-learning-mode="systematic"' in html
    assert 'data-level="zero"' in html
    assert 'id="beginLearningBtn"' in html


def test_diagnosis_uses_option_buttons_not_chat():
    js = ONBOARDING_JS.read_text(encoding="utf-8")
    assert "renderDiagnosticOptions" in js
    assert 'fetch("/api/diagnostics/answer"' in js
    assert "chatInput" not in js
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/test_frontend_contract.py -v`
Expected: tests fail because the onboarding panel and controller do not exist.

- [ ] **Step 3: Implement the one-screen card**

Render learning-mode, level, and topic choices as real buttons with `aria-pressed`; keep time and teaching preference under an optional details disclosure. Disable the primary button until required selections exist. On zero level call confirm directly; otherwise render one diagnostic question at a time with 2–5 option buttons and “诊断 n / 4”. Read an optional `user_id` query parameter for isolated QA while retaining the current learner as the normal default.

- [ ] **Step 4: Hand off to the lesson workspace**

After confirmation, hide onboarding, render returned plan/context, open the lesson tab, and add one coach message stating the first small step. Do not synthesize a user chat message or ask for confirmation. For network or expired-session errors, keep the learner's selections, show an inline retry/restart action, and never fall back to chat typing.

- [ ] **Step 5: Verify GREEN**

Run: `.venv/bin/pytest tests/test_frontend_contract.py -v && node --check frontend/js/onboarding.js && node --check frontend/js/app.js`
Expected: all contract tests and syntax checks pass.

- [ ] **Step 6: Commit locally**

```bash
git add learning-agent-server/frontend learning-agent-server/tests/test_frontend_contract.py
git commit -m "feat: add click-first adaptive onboarding"
```

### Task 5: Small-step teaching contract

**Files:**
- Modify: `learning-agent-server/workspace/dev/AGENTS.md`
- Modify: `learning-agent-server/workspace/dev/.codex/skills/learner-onboarding/SKILL.md`
- Modify: `learning-agent-server/workspace/dev/.codex/skills/concept-teaching/SKILL.md`
- Modify: `learning-agent-server/workspace/dev/.codex/skills/practice-drill/SKILL.md`
- Modify: `learning-agent-server/workspace/dev/tools/validate_workspace.py`
- Create: `learning-agent-server/tests/test_teaching_contract.py`

- [ ] **Step 1: Write failing contract tests**

```python
def test_confirmed_profile_forbids_more_onboarding():
    agents = AGENTS.read_text(encoding="utf-8")
    assert "画像已由界面确认时，不得再次摸底" in agents


def test_teaching_limits_visible_work():
    skill = CONCEPT_SKILL.read_text(encoding="utf-8")
    assert "每轮最多一个新核心概念" in skill
    assert "默认只展示一道当前题" in skill


def test_advanced_drill_does_not_dump_a_batch():
    skill = PRACTICE_SKILL.read_text(encoding="utf-8")
    assert "一次只展示一道练习" in skill


def test_workspace_validator_reads_real_codex_skills():
    validator = VALIDATOR.read_text(encoding="utf-8")
    assert 'root / ".codex/skills"' in validator
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/test_teaching_contract.py -v`
Expected: assertions fail against the current Skill text.

- [ ] **Step 3: Update routing and Skill rules**

Add a UI-confirmed fast path, one-core-concept limit, one-visible-question limit, click-question then hands-on evidence sequence, and a prohibition on treating skip as success. Preserve existing USER_DIR and read-only boundaries. Correct the workspace validator from the stale `.agents/skills` path to `.codex/skills`, and synchronize its required-skill set with the current teaching pipeline.

- [ ] **Step 4: Verify GREEN and workspace validation**

Run: `.venv/bin/pytest tests/test_teaching_contract.py -v` and `.venv/bin/python workspace/dev/tools/validate_workspace.py`
Expected: tests and workspace validation pass.

- [ ] **Step 5: Commit locally**

```bash
git add learning-agent-server/workspace/dev/AGENTS.md learning-agent-server/workspace/dev/.codex/skills learning-agent-server/workspace/dev/tools/validate_workspace.py learning-agent-server/tests/test_teaching_contract.py
git commit -m "feat: enforce small-step teaching contract"
```

### Task 6: Evidence-based celebration motion

**Files:**
- Modify: `learning-agent-server/backend/main.py`
- Modify: `learning-agent-server/tests/test_api.py`
- Modify: `learning-agent-server/frontend/index.html`
- Modify: `learning-agent-server/frontend/js/app.js`
- Modify: `learning-agent-server/frontend/css/style.css`
- Modify: `learning-agent-server/tests/test_frontend_contract.py`

- [ ] **Step 1: Write failing motion contract tests**

```python
def test_success_motion_requires_verified_correctness():
    js = APP_JS.read_text(encoding="utf-8")
    assert "function celebrateVerifiedSuccess" in js
    assert "result.correct === true" in js


def test_grade_response_has_machine_readable_verdict(client, monkeypatch):
    monkeypatch.setattr(main, "grade_answer", lambda **_: {
        "feedback": "正确，证据完整。", "correct": True, "verified": True
    })
    response = client.post("/api/grade", json={
        "user_id": "motion-test",
        "question": "2 + 2 = ?",
        "answer": "4",
    })
    assert response.json()["correct"] is True
    assert response.json()["verified"] is True


def test_reduced_motion_is_supported():
    css = STYLE.read_text(encoding="utf-8")
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert ".celebration-particle" in css
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/test_frontend_contract.py -k motion -v`
Expected: tests fail because the celebration surface does not exist.

- [ ] **Step 3: Implement progress-bloom motion**

Return machine-readable `correct` and `verified` fields from grading, with a safe `None/false` fallback when the model output cannot be verified. Add an eight-particle maximum overlay and a success progress line. Trigger only when the server returns `correct: true` and `verified: true`; never trigger for skipped, unverifiable, or failed work. Use Web Animations API or CSS keyframes for 1.2–1.8 seconds, no sound, no blocked controls, and no particle movement under reduced motion.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/pytest tests/test_frontend_contract.py -v && node --check frontend/js/app.js`
Expected: tests and syntax checks pass.

- [ ] **Step 5: Commit locally**

```bash
git add learning-agent-server/backend/main.py learning-agent-server/tests/test_api.py learning-agent-server/frontend learning-agent-server/tests/test_frontend_contract.py
git commit -m "feat: celebrate verified learning evidence"
```

### Task 7: Four-persona quality regression runner

**Files:**
- Create: `learning-agent-server/evals/personas.json`
- Create: `learning-agent-server/tools/run_persona_evals.py`
- Create: `learning-agent-server/tests/test_persona_eval.py`

- [ ] **Step 1: Write failing scorer tests**

```python
def test_repeated_question_fails_quality_gate():
    score = score_run({
        "events": [
            {"role": "assistant", "text": "你学过 Go 吗？"},
            {"role": "assistant", "text": "再确认一次，你学过 Go 吗？"},
        ],
        "diagnostic_question_count": 2,
        "turns_to_first_teaching": 3,
    })
    assert score["passed"] is False
    assert score["duplicate_question_count"] == 1


def test_invalid_active_plan_fails_quality_gate(tmp_path):
    user_dir = tmp_path / "userdir" / "u_invalid-plan"
    user_dir.mkdir(parents=True)
    score = score_state(user_dir, {"active_plan": "Go 精进计划"})
    assert score["active_plan_resolves"] is False


def test_three_click_questions_can_pass():
    score = score_run({
        "events": [
            {"role": "assistant", "text": "先用快递柜来理解 Go channel：它连接发送者和接收者。"},
            {"role": "assistant", "text": "现在只做一道题：这个发送会不会阻塞？"},
        ],
        "diagnostic_question_count": 3,
        "turns_to_first_teaching": 2,
    })
    assert score["diagnostic_question_count"] == 3
    assert score["turns_to_first_teaching"] <= 2
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/test_persona_eval.py -v`
Expected: collection fails because the runner does not exist.

- [ ] **Step 3: Implement persona fixtures and deterministic scoring**

Define the four approved personas, isolated user IDs, expected maximum turns, and required teaching signals. The runner stores raw SSE events, durations, resulting profile/state/plan paths, automated metrics, and a Markdown summary under `evals/runs/<timestamp>/`.

- [ ] **Step 4: Verify scorer GREEN**

Run: `.venv/bin/pytest tests/test_persona_eval.py -v`
Expected: scorer tests pass without calling the model.

- [ ] **Step 5: Commit locally**

```bash
git add learning-agent-server/evals/personas.json learning-agent-server/tools/run_persona_evals.py learning-agent-server/tests/test_persona_eval.py
git commit -m "test: add teaching persona regression runner"
```

### Task 8: Real-call evaluation, browser QA, and final report

**Files:**
- Create: `learning-agent-server/evals/reports/phase-b-baseline.md`
- Modify: `learning-agent-server/design-qa.md`

- [ ] **Step 1: Run the complete automated suite**

Run: `.venv/bin/pytest -v` and `node --check frontend/js/onboarding.js && node --check frontend/js/app.js`
Expected: zero failures and zero syntax errors.

- [ ] **Step 2: Start the updated app on the QA port**

Run: `.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8791`
Expected: `/api/health` reports FastAPI and streaming enabled.

- [ ] **Step 3: Browser-test core paths**

At 1440×1024 and 390×844 verify: zero beginner starts without diagnosis; experienced learner completes 3–4 click-only questions; no chat typing is required; plan remains visible; selection/hands-on tabs work; correct verified answer triggers motion; skip/error does not; reduced motion disables particles; console has no errors.

- [ ] **Step 4: Run real four-persona calls**

Run: `.venv/bin/python tools/run_persona_evals.py --base-url http://127.0.0.1:8791 --output evals/runs/phase-b-final`
Expected: all four personas start teaching in at most two product steps, no repeated profile questions, every `active_plan` resolves, and quality gates pass.

- [ ] **Step 5: Write the before/after report**

Record baseline evidence from the four existing `u_eval_*` users and final run metrics. Include per-persona teaching-quality scores for vividness, simplicity, pacing, relevance, exercise quality, feedback quality, and state consistency.

- [ ] **Step 6: Run Product Design QA**

Compare the approved onboarding/motion visual companion with browser screenshots in one combined image. Fix all P0/P1/P2 findings and update `design-qa.md` to `final result: passed`.

- [ ] **Step 7: Final verification and local commit**

Run: `.venv/bin/pytest -v` and `git diff --check`
Expected: all tests pass and no whitespace errors.

```bash
git add learning-agent-server/evals/reports/phase-b-baseline.md learning-agent-server/design-qa.md learning-agent-server
git commit -m "test: verify adaptive teaching experience"
```

No `git push`, GitHub API call, PR creation, or remote publication is part of this plan.
