# Learning Workbench Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有聊天页升级为可运行的学习工作台，提供常驻计划、FastAPI SSE 对话、结构化习题与新的教材式 UI。

**Architecture:** FastAPI 负责静态页、学习上下文、计划、判题和 SSE 流；Codex 驱动层将 `codex exec --json` 的事件转换为统一流事件。前端保持零构建的 HTML/CSS/ES Modules，按学习路线、学习画布和 AI 教练三区组织。

**Tech Stack:** Python 3.13, FastAPI, Uvicorn, pytest, HTTPX, vanilla HTML/CSS/JavaScript, Server-Sent Events, Codex CLI JSONL.

---

## File Map

- `learning-agent-server/requirements.txt`: 运行与测试依赖。
- `learning-agent-server/backend/main.py`: FastAPI 应用、静态文件和 API 路由。
- `learning-agent-server/backend/codex_driver.py`: Codex 子进程与 JSONL 流解析。
- `learning-agent-server/backend/learning_content.py`: 安全读取用户状态、计划和默认习题。
- `learning-agent-server/tests/test_learning_content.py`: 计划路径兼容和学习上下文测试。
- `learning-agent-server/tests/test_codex_stream.py`: Codex JSONL 事件解析测试。
- `learning-agent-server/tests/test_api.py`: FastAPI API/SSE 契约测试。
- `learning-agent-server/frontend/index.html`: 三区工作台语义结构。
- `learning-agent-server/frontend/css/style.css`: 方案 1 视觉系统与响应式。
- `learning-agent-server/frontend/js/app.js`: 计划、课节、习题、SSE 和教练交互。
- `learning-agent-server/frontend/assets/learning-path-collage.png`: AI 生成的编辑式学习插画。
- `learning-agent-server/design-qa.md`: 视觉对比与最终门禁。

### Task 1: Runtime and test foundation

**Files:**
- Create: `learning-agent-server/requirements.txt`
- Create: `learning-agent-server/tests/__init__.py`

- [ ] **Step 1: Declare exact dependencies**

```text
fastapi>=0.116,<1
uvicorn>=0.35,<1
httpx>=0.28,<1
pytest>=8.4,<9
jsonschema>=4.25,<5
PyYAML>=6.0,<7
```

- [ ] **Step 2: Create a local virtual environment and install dependencies**

Run: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`

Expected: installation exits 0 and `.venv/bin/python -c "import fastapi, pytest"` exits 0.

- [ ] **Step 3: Commit the dependency declaration**

Run: `git add learning-agent-server/requirements.txt learning-agent-server/tests/__init__.py && git commit -m "build: declare learning workbench dependencies"`

### Task 2: Learning context and plan compatibility

**Files:**
- Create: `learning-agent-server/backend/learning_content.py`
- Create: `learning-agent-server/tests/test_learning_content.py`

- [ ] **Step 1: Write failing tests**

```python
def test_prefers_active_plan_inside_plans(tmp_path):
    user = make_user(tmp_path, active_plan="plans/go-zero.md")
    (user / "plans/go-zero.md").parent.mkdir()
    (user / "plans/go-zero.md").write_text("# Go 从零开始\n## 当前任务\n运行 Hello Go", encoding="utf-8")
    context = read_learning_context("yang", tmp_path)
    assert context["plan"]["title"] == "Go 从零开始"

def test_reads_legacy_root_plan(tmp_path):
    user = make_user(tmp_path, active_plan="learning-plan.md")
    (user / "learning-plan.md").write_text("# 学习计划：Python\n", encoding="utf-8")
    assert read_learning_context("yang", tmp_path)["plan"]["source"] == "learning-plan.md"

def test_rejects_plan_path_outside_user_dir(tmp_path):
    user = make_user(tmp_path, active_plan="../../outside.md")
    assert read_learning_context("yang", tmp_path)["plan"]["content"] == ""
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/test_learning_content.py -v`

Expected: FAIL because `backend.learning_content` does not exist.

- [ ] **Step 3: Implement minimal context reader**

Implement `safe_user_id`, `resolve_user_dir`, `resolve_plan_path`, `parse_markdown_plan`, `read_learning_context`, and `default_exercise`. Resolve paths and require the result to remain inside the selected user directory. Return human-facing fields only.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/pytest tests/test_learning_content.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

Run: `git add learning-agent-server/backend/learning_content.py learning-agent-server/tests/test_learning_content.py && git commit -m "feat: expose structured learning context"`

### Task 3: Codex JSONL streaming adapter

**Files:**
- Modify: `learning-agent-server/backend/codex_driver.py`
- Create: `learning-agent-server/tests/test_codex_stream.py`

- [ ] **Step 1: Write failing parser tests**

```python
def test_parse_agent_message():
    line = json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "你好"}})
    assert parse_codex_event(line) == {"event": "message.delta", "data": {"text": "你好"}}

def test_parse_non_message_is_status_or_none():
    line = json.dumps({"type": "turn.started"})
    event = parse_codex_event(line)
    assert event is None or event["event"] == "status"

def test_parse_invalid_json_is_none():
    assert parse_codex_event("not-json") is None
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/test_codex_stream.py -v`

Expected: FAIL because `parse_codex_event` does not exist.

- [ ] **Step 3: Implement parser and generator**

Add `parse_codex_event(line)` and `stream_chat(user_id, message, release_dir, ...)`. Use `subprocess.Popen(..., text=True, bufsize=1)`, yield `session.started`, safe `status`, `message.delta`, `message.completed`, and `error` dictionaries, then terminate the process when the consumer closes.

- [ ] **Step 4: Preserve non-streaming compatibility**

Keep `chat()` available and implement it by aggregating `message.delta` events so command-line callers continue to work.

- [ ] **Step 5: Verify GREEN**

Run: `.venv/bin/pytest tests/test_codex_stream.py -v`

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run: `git add learning-agent-server/backend/codex_driver.py learning-agent-server/tests/test_codex_stream.py && git commit -m "feat: stream codex json events"`

### Task 4: FastAPI application and SSE contract

**Files:**
- Replace: `learning-agent-server/backend/main.py`
- Create: `learning-agent-server/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

```python
def test_health(client):
    assert client.get("/api/health").json()["backend"] == "fastapi"

def test_learning_context(client):
    response = client.get("/api/learning-context?user_id=yang")
    assert response.status_code == 200
    assert "plan" in response.json()

def test_empty_stream_message_rejected(client):
    response = client.post("/api/chat/stream", json={"user_id": "yang", "message": ""})
    assert response.status_code == 422

def test_stream_is_event_stream(client, monkeypatch):
    monkeypatch.setattr(main, "stream_chat", lambda *args, **kwargs: iter([
        {"event": "message.delta", "data": {"text": "你好"}},
        {"event": "message.completed", "data": {}},
    ]))
    response = client.post("/api/chat/stream", json={"user_id": "yang", "message": "Go"})
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: message.delta" in response.text
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/test_api.py -v`

Expected: FAIL because the current stdlib server does not expose a FastAPI app.

- [ ] **Step 3: Implement FastAPI routes**

Create `app = FastAPI()`, mount `/css`, `/js`, and `/assets`, serve `index.html`, and implement `/api/health`, `/api/learning-context`, `/api/state`, `/api/chat`, `/api/chat/stream`, and `/api/grade`. Format SSE as `event: <name>\ndata: <json>\n\n` and set `Cache-Control: no-cache` plus `X-Accel-Buffering: no`.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/pytest tests/test_api.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

Run: `git add learning-agent-server/backend/main.py learning-agent-server/tests/test_api.py && git commit -m "feat: replace bridge with fastapi streaming api"`

### Task 5: Selected visual target and asset integration

**Files:**
- Create: `learning-agent-server/frontend/assets/learning-path-collage.png`
- Replace: `learning-agent-server/frontend/index.html`
- Replace: `learning-agent-server/frontend/css/style.css`

- [ ] **Step 1: Copy and inspect the generated illustration**

Copy the selected generated asset to `frontend/assets/learning-path-collage.png`. Verify it has alpha and visually matches the selected revised mockup.

- [ ] **Step 2: Implement semantic three-zone layout**

Create accessible regions for the roadmap (`nav`), lesson canvas (`main`), and coach (`aside`). Include skip link, mobile toggles, persistent plan title, lesson goal, generated illustration, code sample, exercise surface, and coach composer.

- [ ] **Step 3: Implement the design system**

Use warm ivory surfaces, charcoal typography, terracotta accent, restrained sage, 15–16px reading type, minimal shadows, 300px roadmap, fluid center, and 360px coach. Use CSS variables, visible focus, reduced-motion support, and responsive breakpoints at 1200px and 768px.

- [ ] **Step 4: Verify static semantics**

Run: `.venv/bin/python -m http.server 8999 -d frontend` and inspect the page at a 1440×1024 viewport. Confirm there is one `main`, navigation has an accessible label, all inputs have labels, and no horizontal overflow appears.

- [ ] **Step 5: Commit**

Run: `git add learning-agent-server/frontend && git commit -m "feat: build editorial learning workbench"`

### Task 6: Frontend learning and streaming interactions

**Files:**
- Replace: `learning-agent-server/frontend/js/app.js`

- [ ] **Step 1: Define deterministic UI state helpers**

Implement pure helpers `normalizeContext`, `formatSseChunk`, `mergeStreamText`, `renderPlan`, and `exerciseFeedbackClass`. Keep server data escaped before insertion and use DOM creation for user/model content.

- [ ] **Step 2: Load persistent learning context**

On startup call `/api/learning-context?user_id=yang`, render the real plan title, stages, current task, time estimate, and learner-friendly evidence. Fall back to the Go demo content when no plan is active.

- [ ] **Step 3: Implement fetch-based SSE consumption**

Use `fetch('/api/chat/stream', {method:'POST'})`, `response.body.getReader()`, `TextDecoder`, and event-block parsing. Render `status`, append `message.delta`, process `artifact`, handle `message.completed`, and expose Cancel/Retry with `AbortController`.

- [ ] **Step 4: Wire core interactions**

Make roadmap stages collapsible, lesson/notes/exercise tabs functional, hint button send a contextual request, exercise submission call `/api/grade`, mobile roadmap/coach drawers work, Escape closes overlays, and focus returns to the invoking control.

- [ ] **Step 5: Browser verification**

Verify initial context, roadmap selection, exercise submission, coach streaming, cancel/retry, keyboard navigation, and mobile drawers in the browser. Check console errors.

- [ ] **Step 6: Commit**

Run: `git add learning-agent-server/frontend/js/app.js && git commit -m "feat: connect learning workspace interactions"`

### Task 7: Full verification and design QA

**Files:**
- Create: `learning-agent-server/design-qa.md`

- [ ] **Step 1: Run automated tests**

Run: `.venv/bin/pytest -v`

Expected: all tests pass with zero failures.

- [ ] **Step 2: Start the real application**

Run: `.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8790`

Expected: health endpoint reports `backend=fastapi`.

- [ ] **Step 3: Capture matching reference and implementation states**

Use a 1440×1024 viewport. Open the revised selected reference and capture the implementation with the first Go lesson, roadmap open, and coach visible.

- [ ] **Step 4: Run Product Design design QA**

Compare layout proportions, typography, spacing, borders, illustration crop, roadmap density, lesson hierarchy, coach hierarchy, and responsive behavior. Record issues in `design-qa.md`, fix P0/P1/P2, and repeat until the file says `final result: passed`.

- [ ] **Step 5: Re-run verification**

Run: `.venv/bin/pytest -v` and inspect browser console.

Expected: tests pass and console has no errors.

- [ ] **Step 6: Commit**

Run: `git add learning-agent-server/design-qa.md learning-agent-server && git commit -m "test: verify learning workbench experience"`
