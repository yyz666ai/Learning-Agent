# GitHub README and Open Knowledge Release Design

## Goal

Publish Learning Agent as a polished bilingual GitHub project while keeping credentials, learner data, local runtime state, and internal QA artifacts private.

## Documentation design

- The repository root owns the canonical Chinese `README.md` and English `README_EN.md`.
- Both pages share a compact generated Learning Agent logo, enterprise badges, product screenshot, architecture diagram, installation guide, API security model, contribution flow, and troubleshooting.
- Documentation language switching is explicit at the top of both files. This release does not claim that the current Chinese-first product UI has full runtime localization.

## API security design

- API credentials remain server-side in `learning-agent-server/.secrets.env`.
- A committed `.secrets.env.example` documents the required variable without containing a real key.
- `templates/codex-home-config.toml` remains the provider template. The backend copies it into each learner's isolated `CODEX_HOME` and injects `DEEPSEEK_API_KEY` through the process environment.
- No frontend bundle, URL, command-line argument, tracked config, or user profile contains the key.

## Open knowledge collaboration

- Teaching method changes live under `workspace/dev/.codex/skills/`.
- Reusable facts, examples, misconceptions, learning paths, and library coverage live under `workspace/dev/curriculum/`.
- Contributors run the workspace validator and full test suite before opening a PR.
- Learner records, unreviewed runtime state, releases, and local evaluation evidence are excluded from Git.

## Release boundary

Include source code, tests, Skills, curriculum, templates, selected public product assets, plans/specs, PRD, contribution guide, and license. Exclude secrets, `userdir`, `.venv`, release snapshots, local LaunchAgent files, logs, internal planning folders, QA screenshots, and raw eval runs.
