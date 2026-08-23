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

Python 3.10+ is required. Use macOS, Linux, or WSL 2 on Windows.

### 3. Configure DeepSeek

```bash
cp .secrets.env.example .secrets.env
```

Edit the project-local `.secrets.env`:

```dotenv
DEEPSEEK_API_KEY=your_deepseek_api_key
```

This configuration affects this project only. Secrets and local learning records are ignored by Git. No OpenAI API key or Codex login is required.

### 4. Start

```bash
./run.sh
```

The first run prepares the teaching workspace automatically. Open:

<http://127.0.0.1:8787>

## How to use it

1. Type your real goal, such as “Learn Go from scratch,” “Help me understand this LangGraph project,” or “Prepare me for a Java backend interview.”
2. If essential context is missing, answer the 3–4 compact follow-up choices.
3. Review the generated plan. Confirm it or ask for changes directly in chat.
4. Learn through the HTML slides, answer classroom quizzes, and run code in the generated project.
5. Ask questions in chat; mistakes, assignments, notes, and mastery are stored locally.
6. On your next visit, resume an existing learning project from the sidebar.

Local data is stored in `userdir/` and survives restarts. It is never committed to Git.

## Repository layout

```text
Learning-Agent/
├── backend/       # FastAPI, Codex integration, plans, and lesson state
├── frontend/      # Chat, HTML slides, outline, and question bank
├── workspace/dev/ # Teaching Skills, curriculum, and knowledge base
├── templates/     # Project-local Codex / DeepSeek templates
├── tests/         # Regression and curriculum contribution checks
├── projects/      # Example and lesson project resources
├── run.sh         # One-command startup
└── requirements.txt
```

## Tests and contributions

The `tests/` directory is intentionally public: it protects teaching flows, quiz answers, code comments, safe paths, and curriculum pull requests.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python workspace/dev/tools/validate_workspace.py
```

Contributions to curriculum atoms, learning paths, interview questions, exercises, misconceptions, teaching Skills, and product code are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

[MIT](LICENSE)
