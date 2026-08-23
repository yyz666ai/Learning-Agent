# Chat-First Learning Theater Phase C Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the form-led workbench with a Codex-style conversation-first learning flow, inline choice tray, safe Markdown rendering, resizable lesson artifact, structured starter deck, and seven-route real-call regression suite.

**Architecture:** FastAPI remains the deterministic owner of onboarding, diagnosis, plan persistence, and lesson manifests. The frontend becomes a progressive-disclosure shell: chat occupies the main surface before onboarding, then a resizable artifact pane opens beside it while the curriculum rail remains read-only. Structured JSON drives choices and lesson pages; model Markdown is escaped and rendered by a local formatter rather than inserted as arbitrary HTML.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest, vanilla HTML/CSS/JavaScript, Server-Sent Events, pointer events, localStorage, Codex CLI JSONL, DeepSeek.

---

## File map

- `learning-agent-server/backend/onboarding.py`: seven goal routes, profile and plan strategy rendering.
- `learning-agent-server/backend/lesson_manifest.py`: structured starter lesson pages, progress and practice workspace metadata.
- `learning-agent-server/backend/main.py`: lesson manifest API and route-aware confirmed teaching prompt.
- `learning-agent-server/frontend/index.html`: conversation-first shell, inline choice tray, artifact pane and splitter.
- `learning-agent-server/frontend/css/style.css`: selected Product Design layout, responsive shell, inline choices and splitter.
- `learning-agent-server/frontend/js/onboarding.js`: conversational onboarding and adaptive diagnostic tray.
- `learning-agent-server/frontend/js/markdown.js`: safe Markdown and syntax-highlighted fenced code rendering.
- `learning-agent-server/frontend/js/artifact.js`: lesson page rendering, progress and pane resizing.
- `learning-agent-server/frontend/js/app.js`: stream rendering, artifact/chat orchestration and progressive disclosure.
- `learning-agent-server/tests/test_onboarding.py`: route strategy and plan coverage.
- `learning-agent-server/tests/test_lesson_manifest.py`: page schema and practice path tests.
- `learning-agent-server/tests/test_api.py`: lesson API and prompt strategy tests.
- `learning-agent-server/tests/test_frontend_contract.py`: shell, inline tray, Markdown and resizer contracts.
- `learning-agent-server/tests/test_markdown_renderer.py`: Node-backed Markdown output and escaping tests.
- `learning-agent-server/evals/personas-v3.json`: seven goal-route personas.
- `learning-agent-server/tools/run_persona_evals.py`: route-specific response scorer and report.
- `learning-agent-server/tests/test_persona_eval.py`: deterministic route scoring tests.

### Task 1: Seven-route plan strategy

**Files:**
- Modify: `learning-agent-server/backend/onboarding.py`
- Modify: `learning-agent-server/tests/test_onboarding.py`

- [ ] **Step 1: Write failing route and plan tests**

Add parametrized tests that construct `OnboardingSubmission` with each route and assert that `render_plan` contains route-specific strategy text:

```python
@pytest.mark.parametrize(
    ("route", "marker"),
    [
        ("foundation_engineer", "完整学习、复习、实战与阶段验收"),
        ("urgent_codebase", "优先入口、调用链和关键文件"),
        ("syntax_reading", "优先语法辨析和代码阅读"),
        ("project_delivery", "真实文件、运行结果和测试"),
        ("gap_upgrade", "已掌握内容快进"),
        ("senior_engineer", "架构取舍、可靠性和重构"),
        ("interview_sprint", "简答、追问和代码推演"),
    ],
)
def test_plan_contains_route_strategy(route, marker):
    submission = make_submission(goal_route=route)
    assert marker in render_plan(submission, None, "knowledge_base")
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/test_onboarding.py -k route -v`
Expected: FAIL because `goal_route` is not accepted and route markers are absent.

- [ ] **Step 3: Implement route types and strategy table**

Add `GoalRoute` as a `Literal` of the seven route IDs, add `goal_route` and `deadline_days` to `OnboardingSubmission`, and define a `ROUTE_STRATEGIES` mapping with `plan_marker`, `teaching_focus`, `practice_focus`, `review_intensity`, and `graduation_evidence`. Render these fields plus `session_minutes` into `profile.md` and `plan.md`; persist `goal_route` into learning state.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/pytest tests/test_onboarding.py -v`
Expected: all onboarding tests pass.

- [ ] **Step 5: Commit locally**

```bash
git add learning-agent-server/backend/onboarding.py learning-agent-server/tests/test_onboarding.py
git commit -m "feat: add goal-route learning strategies"
```

### Task 2: Structured starter lesson manifest

**Files:**
- Create: `learning-agent-server/backend/lesson_manifest.py`
- Create: `learning-agent-server/tests/test_lesson_manifest.py`
- Modify: `learning-agent-server/backend/main.py`
- Modify: `learning-agent-server/tests/test_api.py`

- [ ] **Step 1: Write failing manifest tests**

Test that `build_starter_manifest(language="go", topic="Go", session_minutes=25)` returns typed pages `explain`, `example`, `check`, `practice`, and `mastery`; check pages expose 2–5 public options without `correct_option_id`; the practice path is relative and contains no `..`; and the API returns the manifest for a confirmed user.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/test_lesson_manifest.py tests/test_api.py -k lesson_manifest -v`
Expected: collection or request failure because the module and API do not exist.

- [ ] **Step 3: Implement manifest models and builder**

Create Pydantic models `LessonOption`, `LessonPage`, `LessonProgress`, and `LessonManifest`. Store answer keys only in a private sibling field returned to the server, never in `public_manifest()`. Build a five-page Go/Python/custom starter manifest with Markdown code, a click question, a practice directory such as `projects/<plan-slug>/lesson-01`, and an evidence-gated mastery page.

- [ ] **Step 4: Add `GET /api/lesson/current`**

Read the confirmed learning context, construct the starter manifest, create the safe practice directory and `task.md` if absent, then return `public_manifest()`. Reject unconfirmed users with HTTP 409 and recovery `complete_onboarding`.

- [ ] **Step 5: Verify GREEN and commit**

Run: `.venv/bin/pytest tests/test_lesson_manifest.py tests/test_api.py -v`
Expected: all tests pass.

```bash
git add learning-agent-server/backend/lesson_manifest.py learning-agent-server/backend/main.py learning-agent-server/tests/test_lesson_manifest.py learning-agent-server/tests/test_api.py
git commit -m "feat: expose structured starter lessons"
```

### Task 3: Conversation-first shell and inline choice tray

**Files:**
- Modify: `learning-agent-server/frontend/index.html`
- Modify: `learning-agent-server/frontend/css/style.css`
- Modify: `learning-agent-server/tests/test_frontend_contract.py`

- [ ] **Step 1: Write failing frontend contracts**

Assert that the HTML contains `id="conversationShell"`, `id="choiceTray"` immediately before `id="chatForm"`, `id="artifactPane"`, and `id="artifactSplitter"`; assert the old `onboardingForm`, onboarding card grid and `diagnosticPanel` are absent. Assert CSS defines `--chat-width`, `.is-chat-first`, `.choice-tray`, `[role="separator"]`, and a restrained surface without gradients.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/test_frontend_contract.py -k 'conversation or choice or splitter' -v`
Expected: FAIL because the chat-first elements are missing.

- [ ] **Step 3: Replace the page structure**

Keep the brand, curriculum rail, chat feed, composer, plan dialog and feedback surfaces. Remove the standalone onboarding screen and mode tabs. Add a main grid with the rail plus `conversationShell`; inside it place `artifactPane`, a keyboard-accessible separator, and `coachPanel`. Place `choiceTray` between `chatFeed` and `chatForm`, with an aria-live question label, progress label and option container.

- [ ] **Step 4: Implement selected visual direction**

Use the visual target tokens and proportions: 272px rail; artifact/chat variable split; 420px chat default; warm ivory surfaces; one-pixel dividers; no nested modal for PPT. In `.is-chat-first`, hide the artifact and splitter and let chat fill the main width. On mobile, show chat by default and open artifact/rail as full-height views.

- [ ] **Step 5: Verify GREEN and commit**

Run: `.venv/bin/pytest tests/test_frontend_contract.py -v`
Expected: all static contracts pass.

```bash
git add learning-agent-server/frontend/index.html learning-agent-server/frontend/css/style.css learning-agent-server/tests/test_frontend_contract.py
git commit -m "feat: build chat-first learning shell"
```

### Task 4: Conversational onboarding state machine

**Files:**
- Rewrite: `learning-agent-server/frontend/js/onboarding.js`
- Modify: `learning-agent-server/tests/test_frontend_contract.py`

- [ ] **Step 1: Write failing controller contracts**

Assert the controller defines stages `topic`, `goal_route`, `level_claim`, and `preferences`; renders options through `renderChoiceTray`; does not reference `onboardingForm`, `choice-card`, `dialog`, or `chatInput`; and posts the final structured submission to existing onboarding APIs.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/test_frontend_contract.py -k onboarding -v`
Expected: FAIL because the existing controller expects a form and large choice cards.

- [ ] **Step 3: Implement inline stages**

On `show`, append the assistant prompt “今天想学什么？” and render topic choices above the composer. Advance through goal route, level, and daily time one prompt at a time. Allow text entry only for a custom topic or project path. For zero level, confirm directly; otherwise call diagnosis and render exactly one returned question at a time in the same tray.

- [ ] **Step 4: Enforce diagnostic bounds**

Display `诊断 n / 4` while `n <= 4` and `继续确认 n / 10` afterward. Never render more than one question or more than five options. If the server returns `answered_count >= 10` without completion, stop and show a recoverable error instead of asking an eleventh question.

- [ ] **Step 5: Verify syntax, contracts and commit**

Run: `node --check frontend/js/onboarding.js && .venv/bin/pytest tests/test_frontend_contract.py -v`
Expected: syntax and all contracts pass.

```bash
git add learning-agent-server/frontend/js/onboarding.js learning-agent-server/tests/test_frontend_contract.py
git commit -m "feat: move onboarding into the conversation"
```

### Task 5: Safe Markdown and code rendering

**Files:**
- Create: `learning-agent-server/frontend/js/markdown.js`
- Create: `learning-agent-server/tests/test_markdown_renderer.py`
- Modify: `learning-agent-server/frontend/index.html`
- Modify: `learning-agent-server/frontend/js/app.js`
- Modify: `learning-agent-server/frontend/css/style.css`

- [ ] **Step 1: Write failing renderer tests**

Execute `markdown.js` in Node and assert fenced Go code becomes `<pre><code data-language="go">`, inline code is escaped, headings and lists render, `<script>` becomes text, and JavaScript URLs never enter output.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/test_markdown_renderer.py -v`
Expected: FAIL because `markdown.js` is missing.

- [ ] **Step 3: Implement local safe renderer**

Expose `window.MarkdownRenderer.render(markdown)`. Escape the full source first, tokenize fenced blocks, render headings/lists/paragraphs/strong/inline code, and apply conservative keyword spans for Go, Python, JSON, shell and JavaScript. Do not accept raw HTML.

- [ ] **Step 4: Render streamed chat and plan Markdown**

Use the renderer for every assistant message, exercise feedback, plan document and review document. During SSE deltas re-render the accumulated Markdown; incomplete fences remain an escaped paragraph until closed. User messages remain text-only.

- [ ] **Step 5: Verify GREEN and commit**

Run: `.venv/bin/pytest tests/test_markdown_renderer.py tests/test_frontend_contract.py -v && node --check frontend/js/markdown.js && node --check frontend/js/app.js`
Expected: all tests and syntax checks pass.

```bash
git add learning-agent-server/frontend/js/markdown.js learning-agent-server/frontend/index.html learning-agent-server/frontend/js/app.js learning-agent-server/frontend/css/style.css learning-agent-server/tests/test_markdown_renderer.py learning-agent-server/tests/test_frontend_contract.py
git commit -m "feat: render safe markdown and highlighted code"
```

### Task 6: Resizable artifact and lesson pages

**Files:**
- Create: `learning-agent-server/frontend/js/artifact.js`
- Modify: `learning-agent-server/frontend/index.html`
- Modify: `learning-agent-server/frontend/js/app.js`
- Modify: `learning-agent-server/frontend/css/style.css`
- Modify: `learning-agent-server/tests/test_frontend_contract.py`

- [ ] **Step 1: Write failing artifact contracts**

Assert the script fetches `/api/lesson/current`, renders page progress, mastery progress, remaining minutes, practice path and previous/next controls; uses pointer events for resizing; clamps chat width to 340–760px; persists the width in a per-user localStorage key; and supports ArrowLeft/ArrowRight on the separator.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/test_frontend_contract.py -k artifact -v`
Expected: FAIL because `artifact.js` is missing.

- [ ] **Step 3: Implement artifact controller**

Expose `window.ArtifactController.openCurrent(userId)`, `close()`, `next()`, `previous()` and `renderPage()`. Use MarkdownRenderer for page content and code. A check page sends its question into the shared inline choice tray; a practice page displays its real path and completion criteria.

- [ ] **Step 4: Implement resizing and persistence**

On pointer move, calculate chat width from the right edge and clamp it. Set `--chat-width`, update `aria-valuenow`, and persist on pointer up. Keyboard arrows change width by 24px; Home and End choose min/max. Reset to chat-first when onboarding is uninitialized.

- [ ] **Step 5: Verify GREEN and commit**

Run: `.venv/bin/pytest tests/test_frontend_contract.py -v && node --check frontend/js/artifact.js`
Expected: all tests and syntax checks pass.

```bash
git add learning-agent-server/frontend/js/artifact.js learning-agent-server/frontend/index.html learning-agent-server/frontend/js/app.js learning-agent-server/frontend/css/style.css learning-agent-server/tests/test_frontend_contract.py
git commit -m "feat: add resizable lesson artifacts"
```

### Task 7: Seven-route Codex regression runner

**Files:**
- Create: `learning-agent-server/evals/personas-v3.json`
- Modify: `learning-agent-server/tools/run_persona_evals.py`
- Modify: `learning-agent-server/tests/test_persona_eval.py`

- [ ] **Step 1: Write failing route scorer tests**

Add fixtures showing that interview responses fail when dominated by multiple-choice text, urgent-project responses fail without project/entry/call-chain markers, project-delivery responses fail without file/run/test markers, and senior responses fail without architecture/trade-off/project evidence.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/test_persona_eval.py -k route -v`
Expected: FAIL because route-aware scores are absent.

- [ ] **Step 3: Add seven isolated personas and route scoring**

Each persona includes `goal_route`, `expected_markers`, `forbidden_markers`, `max_diagnostic_questions`, `max_turns_to_teaching`, and a distinct user ID. Extend `score_run` with route checks and include them in `passed`. Keep raw SSE, response text, plan state and latency in each JSON result.

- [ ] **Step 4: Verify deterministic tests**

Run: `.venv/bin/pytest tests/test_persona_eval.py -v`
Expected: all scorer tests pass.

- [ ] **Step 5: Publish the workspace and run real calls**

Run: `.venv/bin/python backend/publish.py` then `.venv/bin/python tools/run_persona_evals.py --personas evals/personas-v3.json --base-url http://127.0.0.1:8791 --output evals/runs/phase-c-final`.

Expected: seven result JSON files plus `summary.md`; any failed route remains an explicit finding and must not be relabeled as passing.

- [ ] **Step 6: Commit runner and evidence**

```bash
git add learning-agent-server/evals/personas-v3.json learning-agent-server/tools/run_persona_evals.py learning-agent-server/tests/test_persona_eval.py learning-agent-server/evals/runs/phase-c-final
git commit -m "test: evaluate seven learning routes"
```

### Task 8: Browser and design QA

**Files:**
- Modify: `learning-agent-server/design-qa.md`
- Create: `learning-agent-server/evals/phase-c-*.png`

- [ ] **Step 1: Run complete automated verification**

Run: `.venv/bin/pytest -q`, `.venv/bin/python workspace/dev/tools/validate_workspace.py --root workspace/dev`, `node --check frontend/js/app.js`, `node --check frontend/js/onboarding.js`, `node --check frontend/js/markdown.js`, `node --check frontend/js/artifact.js`, and `git diff --check`.

Expected: zero failures and no workspace validation errors.

- [ ] **Step 2: Exercise the core browser flow**

At 1440 × 1024, verify initial chat-first state, four inline onboarding stages, three-click stable diagnosis, artifact opening, Markdown code, next/previous pages, splitter drag and persistence. At 390 × 844, verify chat-first opening, inline choices, full-screen artifact and no horizontal overflow. Check console errors after each route.

- [ ] **Step 3: Compare against the selected visual**

Capture the implementation and combine it side-by-side with `docs/superpowers/specs/assets/chat-first-learning-theater.png`. Review typography, spacing, colors, image quality, copy and interaction states. Fix every P0/P1/P2 issue and repeat the comparison.

- [ ] **Step 4: Update QA report and commit**

Record source and implementation paths, viewports, interaction checks, console checks, comparison history and `final result: passed|blocked` in `learning-agent-server/design-qa.md`.

```bash
git add learning-agent-server/design-qa.md learning-agent-server/evals/phase-c-*.png
git commit -m "test: verify chat-first learning theater"
```
