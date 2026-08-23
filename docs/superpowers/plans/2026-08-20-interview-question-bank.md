# Interview Question Bank Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a persistent interview-question learning system that imports raw questions, deduplicates them into a structured bank, guides systematic mastery, expands related knowledge, and shows answer/mastery state in the left rail without resetting completed learning progress.

**Architecture:** Store immutable intake batches beside normalized question records in each user's workspace. Keep deterministic ingestion, mastery, and plan reconciliation independent from the model; use the model only for explanations and related-question expansion. Expose the workflow through FastAPI and add a compact interview-bank view to the existing chat-first frontend.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, pytest, vanilla JavaScript, HTML, CSS, existing streaming chat and DeepSeek-compatible LLM adapter.

---

### Task 1: Persistent Interview Question Store

**Files:**
- Create: `learning-agent-server/backend/interview_bank.py`
- Create: `learning-agent-server/tests/test_interview_bank.py`

- [x] **Step 1: Write failing storage and ingestion tests**

```python
def test_intake_preserves_source_and_deduplicates_questions(tmp_path):
    store = InterviewBankStore(tmp_path)
    first = store.intake("u_demo", "1. 什么是闭包？\n2. 什么是闭包？")
    assert first["source_count"] == 2
    assert first["new_count"] == 1
    assert len(store.list_questions("u_demo")) == 1
    assert store.list_sources("u_demo")[0]["raw_text"].startswith("1.")

def test_question_state_defaults_to_unanswered_and_unrated(tmp_path):
    store = InterviewBankStore(tmp_path)
    result = store.intake("u_demo", "Go 的 goroutine 和线程有什么区别？")
    question = store.get_question("u_demo", result["question_ids"][0])
    assert question["answer_status"] == "missing"
    assert question["mastery"] == "unrated"
```

- [x] **Step 2: Run the tests and verify they fail**

Run: `cd learning-agent-server && pytest tests/test_interview_bank.py -q`

Expected: FAIL because `backend.interview_bank` does not exist.

- [x] **Step 3: Implement deterministic intake and atomic persistence**

Implement `InterviewBankStore` with `intake`, `list_questions`, `list_sources`, `get_question`, `set_study_mode`, and `record_mastery`. Split numbered/bulleted/newline question text, preserve the raw batch, normalize whitespace and punctuation for a SHA-256 stable ID, merge raw variants, and write JSON through a temporary file followed by `os.replace`.

- [x] **Step 4: Run focused tests**

Run: `cd learning-agent-server && pytest tests/test_interview_bank.py -q`

Expected: all interview-bank storage tests PASS.

- [x] **Step 5: Commit the storage layer**

```bash
git add learning-agent-server/backend/interview_bank.py learning-agent-server/tests/test_interview_bank.py
git commit -m "feat: persist interview question bank"
```

### Task 2: Protected Plan Reconciliation

**Files:**
- Create: `learning-agent-server/backend/interview_plan.py`
- Modify: `learning-agent-server/tests/test_interview_bank.py`

- [x] **Step 1: Add failing progress-protection tests**

```python
def test_reconcile_adds_backlog_without_lowering_display_progress(tmp_path):
    plan = {"display_progress": 60, "progress_floor": 60, "completed": ["syntax"]}
    result = reconcile_interview_plan(plan, [{"id": "q1", "concept_ids": ["closure"]}])
    assert result["display_progress"] == 60
    assert result["progress_floor"] == 60
    assert result["completed"] == ["syntax"]
    assert result["interview_backlog"][0]["question_id"] == "q1"
```

- [x] **Step 2: Verify the new test fails**

Run: `cd learning-agent-server && pytest tests/test_interview_bank.py::test_reconcile_adds_backlog_without_lowering_display_progress -q`

Expected: FAIL because `reconcile_interview_plan` is undefined.

- [x] **Step 3: Implement reconciliation and coverage metrics**

Implement `reconcile_interview_plan(plan, questions)` so completed nodes and `progress_floor` are immutable, `display_progress` never decreases, new question IDs are appended exactly once, and `bank_coverage` is independently calculated as `{mastered, total, percent}`.

- [x] **Step 4: Run focused tests and commit**

Run: `cd learning-agent-server && pytest tests/test_interview_bank.py -q`

Expected: PASS.

```bash
git add learning-agent-server/backend/interview_plan.py learning-agent-server/tests/test_interview_bank.py
git commit -m "feat: reconcile interview learning plans"
```

### Task 3: FastAPI Interview Bank Contract

**Files:**
- Modify: `learning-agent-server/backend/main.py`
- Modify: `learning-agent-server/tests/test_api.py`

- [x] **Step 1: Add failing endpoint tests**

Add API tests for `POST /api/interview/intake`, `GET /api/interview/bank`, `GET /api/interview/questions/{question_id}`, `POST /api/interview/questions/{question_id}/mastery`, and `POST /api/interview/study-mode`. Assert intake returns counts, question IDs, three study-mode choices, and separate plan-progress/bank-coverage values.

- [x] **Step 2: Verify endpoint tests fail**

Run: `cd learning-agent-server && pytest tests/test_api.py -k interview -q`

Expected: FAIL with HTTP 404.

- [x] **Step 3: Add validated request models and endpoints**

Use Pydantic models that constrain study mode to `from_scratch | systematic | assess_first` and mastery to `forgot | hard | smooth`. Resolve storage beneath the configured user workspace and return 404 for unknown question IDs.

- [x] **Step 4: Run API tests and commit**

Run: `cd learning-agent-server && pytest tests/test_api.py -k interview -q`

Expected: PASS.

```bash
git add learning-agent-server/backend/main.py learning-agent-server/tests/test_api.py
git commit -m "feat: expose interview bank api"
```

### Task 4: Systematic Answer and Related-Question Expansion

**Files:**
- Create: `learning-agent-server/backend/interview_coach.py`
- Modify: `learning-agent-server/backend/main.py`
- Modify: `learning-agent-server/tests/test_interview_bank.py`
- Modify: `learning-agent-server/tests/test_api.py`

- [x] **Step 1: Add failing tests for safe model output handling**

Test that a valid model JSON response stores a structured answer, prerequisites, variants, follow-ups, and related expanded questions; invalid JSON must leave the original question intact and return a recoverable error. Expanded questions must have `origin="expanded"` and `answer_status="draft"`.

- [x] **Step 2: Verify expansion tests fail**

Run: `cd learning-agent-server && pytest tests/test_interview_bank.py tests/test_api.py -k 'expand or answer' -q`

Expected: FAIL because the coaching service and endpoint do not exist.

- [x] **Step 3: Implement the interview coaching service**

Create a strict prompt and parser around the existing LLM adapter. Validate the returned object before writing. Add `POST /api/interview/questions/{question_id}/expand`; never publish expanded content to the shared knowledge base automatically.

- [x] **Step 4: Run expansion tests and commit**

Run: `cd learning-agent-server && pytest tests/test_interview_bank.py tests/test_api.py -k 'interview or expand' -q`

Expected: PASS.

```bash
git add learning-agent-server/backend/interview_coach.py learning-agent-server/backend/main.py learning-agent-server/tests/test_interview_bank.py learning-agent-server/tests/test_api.py
git commit -m "feat: expand interview knowledge paths"
```

### Task 5: Codex-Like Interview Intake Interaction

**Files:**
- Modify: `learning-agent-server/frontend/index.html`
- Create: `learning-agent-server/frontend/js/interview-bank.js`
- Modify: `learning-agent-server/frontend/js/app.js`
- Modify: `learning-agent-server/frontend/css/style.css`
- Modify: `learning-agent-server/tests/test_frontend_contract.py`

- [x] **Step 1: Add failing frontend contract tests**

Assert the page contains the `大纲 / 题库` rail switcher, bank coverage summary, answer/mastery status hooks, question list, and an inline choice tray above the composer with exactly the three study approaches. Assert no modal dialog is used.

- [x] **Step 2: Verify frontend tests fail**

Run: `cd learning-agent-server && pytest tests/test_frontend_contract.py -k interview -q`

Expected: FAIL because the interview-bank UI is absent.

- [x] **Step 3: Implement bank rail and intake controller**

Create `InterviewBankController` to submit pasted questions, render grouped question rows, load a question into the center learning surface, and show `逐题从头讲 / 系统学习 / 先测后学` as compact buttons immediately above the input. Show answer state and learner mastery on each row, while retaining the existing draggable layout and chat-first behavior.

- [x] **Step 4: Add responsive and accessible styling**

Use restrained warm neutrals, one accent color, 44px minimum interactive targets, visible focus rings, text labels alongside status color, and a single-column mobile fallback. Keep the interface flat and avoid nested card clutter.

- [x] **Step 5: Run frontend tests and commit**

Run: `cd learning-agent-server && pytest tests/test_frontend_contract.py -q`

Expected: PASS.

```bash
git add learning-agent-server/frontend/index.html learning-agent-server/frontend/js/interview-bank.js learning-agent-server/frontend/js/app.js learning-agent-server/frontend/css/style.css learning-agent-server/tests/test_frontend_contract.py
git commit -m "feat: add interview bank learning interface"
```

### Task 6: Interview Personas and End-to-End Verification

**Files:**
- Modify: `learning-agent-server/tests/test_persona_eval.py`
- Create: `learning-agent-server/evals/interview-bank-evaluation.md`

- [x] **Step 1: Add persona route tests**

Cover at least: zero-basis systematic learner, intermediate learner with skipped basics, senior engineer seeking depth, two-day project-reading sprint, hands-on learner, and interview sprint. Verify each reaches teaching in at most two setup decisions and that interview sprint favors spoken/short-answer practice over excessive multiple choice.

- [x] **Step 2: Run the full automated suite**

Run: `cd learning-agent-server && pytest -q`

Expected: all tests PASS with no new failures.

- [x] **Step 3: Perform browser QA**

Open the local app, paste a multi-question interview batch, choose `系统学习`, open questions from the left rail, record each mastery state, resize the center/chat divider, and verify desktop plus narrow viewport layouts. Record observed behavior and screenshots in `evals/interview-bank-evaluation.md`.

- [x] **Step 4: Run one live model quality evaluation**

For representative frontend, backend, and Go interview questions, score explanation quality on correctness, prerequisite coverage, progressive teaching, vividness, no skipped steps, practice relevance, and response latency. Record the prompt, route, score, and any remaining limitation without storing secrets.

- [x] **Step 5: Final verification and commit**

Run: `cd learning-agent-server && pytest -q`

Expected: all tests PASS.

```bash
git add learning-agent-server/tests/test_persona_eval.py learning-agent-server/evals/interview-bank-evaluation.md
git commit -m "test: evaluate interview learning routes"
```
