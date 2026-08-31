<div align="center">
  <img src="assets/learning-agent-logo.png" width="120" alt="Learning Agent Logo" />
  <h1>Learning Agent</h1>
  <p><strong>An Agentic AI learning system that turns your goal into a plan, interactive lessons, practice, and review.</strong></p>
  <p><a href="README.md">简体中文</a> · <a href="README_EN.md">English</a></p>
</div>

---

## What it does

Learning Agent first understands what you want to learn, your current level, and the outcome you want. It then creates a personalized `plan.md`. After you approve the plan, it teaches through HTML slides, clickable quizzes, commented code, and a real practice project.

- Free-form onboarding instead of a long fixed form;
- Different course depth for concepts, beginners, projects, advanced practice, and interviews;
- Classroom quizzes, homework, mistakes, and review cards in one learning record;
- Versioned teaching Skills and curriculum under `workspace/dev/`;
- A community-maintained knowledge base that accepts pull requests.

<div align="center">
  <img src="assets/learning-agent-ui.jpg" width="920" alt="Learning Agent interface" />
</div>

## Quick install

### 1. Install Codex

Install Python 3.10+ and, for npm, Node.js LTS. Native Windows uses npm; Homebrew is an alternative on macOS / Linux.

```bash
npm install -g @openai/codex
# or
brew install codex

codex --version
```

Only the Codex command is required. You do not need to run `codex login` or change your global Codex configuration.

### 2. Clone and install

```bash
git clone https://github.com/yyz666ai/Learning-Agent.git
cd Learning-Agent

python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The commands above are for macOS / Linux. After cloning, native Windows users can run these in PowerShell (no virtual-environment activation or execution-policy change needed):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Configure DeepSeek

```bash
cp .secrets.env.example .secrets.env
```

In Windows PowerShell, use `Copy-Item .secrets.env.example .secrets.env`.

Edit the project-local `.secrets.env`:

```dotenv
DEEPSEEK_API_KEY=your_deepseek_api_key
```

This configuration affects this project only. Secrets and local learning records are ignored by Git. No OpenAI API key or Codex login is required.

### 4. Start

```bash
./run.sh
```

On native Windows, use PowerShell or Command Prompt:

```powershell
.\run.cmd
```

Use `./run.sh 8899` or `.\run.cmd 8899` for a custom port. Both launchers use the project's `.venv`, check Codex / DeepSeek and teaching files, refresh the teaching snapshot on every start, then start the server. Failed checks stop the sequence and preserve the exit code. Open:

<http://127.0.0.1:8787>

The browser's skill diagnosis, initial Plan and HTML lesson generation use background jobs and short polling. Diagnosis start returns a task ID immediately; refresh resumes the same task. Progress shows the server's actual phase and elapsed time, not a fabricated model-completion percentage. A temporary network failure queries the existing task before starting another one; diagnosis interrupted by a server restart can be retried.

Lesson revision candidates and the legacy `/api/onboarding/start` endpoint remain synchronous and require adequate proxy timeouts. Run a single server process: diagnosis scheduling and editing transactions do not support multiple workers or instances. Cancelling diagnosis prevents stale results from being committed, but an in-flight model call can continue until completion or timeout and may still incur charges.

Folder opening uses the native file manager; headless or unavailable desktops return a path without claiming it was opened. Native Windows system reminders are not implemented. Windows command resolution and startup contracts have offline simulation tests, not a real Windows end-to-end acceptance run. macOS / Linux and WSL continue to use `run.sh`.

## How to use it

1. Type your real goal, such as “Learn Go from scratch,” “Help me understand this LangGraph project,” or “Prepare me for a Java backend interview.”
2. Answer only the follow-ups that affect your plan. Options are dynamic shortcuts, never preselected; you can type your own answer. Paste existing interview questions or project material directly into chat.
3. Review the generated plan. Confirm it or ask for changes directly in chat.
4. Learn through the HTML slides, answer classroom quizzes, and run code in the generated project.
5. Ask questions in chat; mistakes, assignments, notes, and mastery are stored locally.
6. On your next visit, resume an existing learning project from the sidebar.

Local data is stored in `userdir/` and survives restarts. It is never committed to Git.

### Edit, confirm, and undo lessons

The classroom is read-only by default. Use **Edit** to change the current page's title, Markdown, or code. The toolbar supports H1/H2/H3, bold, italic, highlighting, and underline, with preview and Save/Cancel. Existing quiz questions remain protected from this text editor.

To revise a lesson or add practice through chat, describe the change, confirm candidate generation, review the differences, and then choose **Apply** or **Cancel**. A generated candidate does not replace your current lesson automatically. **Undo** and **Version history** restore lesson versions without deleting your code or past attempts; revised questions require fresh answers.

HTML keeps interactive quizzes and page navigation, while a same-version Markdown copy is stored on the backend and available through **Export Markdown**. It excludes private grading keys. Current version locks support a single service process, not multiple workers. See the [release validation report](projects/learning-agent/design/outputs/SAFE_EDITING_RELEASE_VALIDATION.md) for tested paths and limitations.

## Interface and teaching language

Chinese is the default. Use the **globe icon in the upper-right corner** to select **English** or **中文**. The preference survives a refresh. Newly started onboarding, Plans, lessons, exercises and chat responses use that language; in-progress jobs keep the language captured when they started.

Existing courses, conversations and learner notes are not rewritten. Use **Translate to current language** in the full Plan window or lesson controls, confirm the scope, and view a read-only translation of the current Plan or chapter. Close that view to return to the original. Translation preserves source content, code, question identities and answer records. After editing the original, confirm a new translation.

Preferences live in `userdir/u_<id>/preferences.json`; read-only variants live in that user's `translations/` directory. Saving errors offer retry instead of claiming success. Interface `locale` is separate from the programming `language` field.

See the [bilingual validation record](docs/superpowers/plans/2026-08-31-bilingual-validation.md) for evidence and limitations. This adds language support to the local application, not a production account, billing or quota system.

## Repository layout

```text
Learning-Agent/
├── backend/       # FastAPI, Codex integration, plans, and lesson state
├── frontend/      # Chat, HTML slides, outline, and question bank
├── workspace/dev/ # Teaching Skills, curriculum, and knowledge base
├── templates/     # Project-local Codex / DeepSeek templates
├── tests/         # Regression and curriculum contribution checks
├── projects/      # Example and lesson project resources
├── run.sh         # macOS / Linux startup
├── run.cmd        # Native Windows startup
└── requirements.txt
```

## Tests and contributions

The `tests/` directory is intentionally public: it protects teaching flows, quiz answers, code comments, safe paths, and curriculum pull requests.

```bash
.venv/bin/python -m pytest -q
node --test tests/*.test.cjs
.venv/bin/python workspace/dev/tools/validate_workspace.py
```

Contributions to curriculum atoms, learning paths, interview questions, exercises, misconceptions, teaching Skills, and product code are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

### Interactive compatibility report

After downloading the repository, open the [Detect report](projects/learning-agent/detect/outputs/report/index.html) in a browser. It supports filters, failure/retest details, local review drafts, and JSON/JSONL downloads. GitHub's code view does not execute HTML. The report distinguishes actual model calls, controlled tests, simulated Windows behavior, and missing evidence; machine passes are not human approval.

Rebuild with `python tools/build_detect_report.py projects/learning-agent/detect/outputs/report/report_data.json /tmp/new-detect-report` (on Windows choose a new empty output directory). Existing evidence batches are never overwritten.

## License

[MIT](LICENSE)
