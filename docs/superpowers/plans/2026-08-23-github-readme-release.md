# GitHub README Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a secure, bilingual, enterprise-style Learning Agent repository with a generated logo and a clear knowledge-base PR workflow.

**Architecture:** Keep the root README as the public entry point, with an English peer document and a contribution guide. Preserve the existing backend-only secret injection and per-user Codex configuration model, while expanding ignore rules so local runtime and QA state cannot enter the public repository.

**Tech Stack:** Markdown, GitHub Mermaid, shields.io badges, Python/FastAPI, Codex CLI, DeepSeek-compatible API, Git.

---

### Task 1: Define the public repository boundary

**Files:**
- Modify: `.gitignore`
- Create: `learning-agent-server/.secrets.env.example`

- [x] Exclude local plans, secrets, user data, releases, virtual environments, logs, LaunchAgent configuration, QA images, and raw eval runs.
- [x] Keep source, Skills, curriculum, tests, and reusable generated teaching assets public.
- [x] Provide a placeholder-only server secret example.

### Task 2: Create public brand assets

**Files:**
- Create: `docs/assets/learning-agent-logo.png`
- Create: `docs/assets/learning-agent-ui.jpg`

- [x] Generate a compact Learning Agent brand mark with a transparent background.
- [x] Copy a representative real UI screenshot into the public docs assets folder.

### Task 3: Write bilingual project documentation

**Files:**
- Create: `README.md`
- Create: `README_EN.md`
- Create: `CONTRIBUTING.md`

- [x] Document product value, feature matrix, architecture, prerequisites, Codex installation, DeepSeek configuration, startup, testing, project structure, troubleshooting, and security.
- [x] Add Chinese/English links and avoid claiming runtime UI localization that does not exist.
- [x] Explain the knowledge atom and teaching Skill PR flows with exact validation commands.

### Task 4: Verify and publish

**Files:**
- Verify: all staged files

- [x] Run the full Python test suite and workspace validator.
- [x] Scan staged content for credentials, private paths, runtime records, and oversized files.
- [ ] Merge the remote repository's MIT license without rewriting remote history.
- [ ] Commit, configure the GitHub remote, push to `main`, and verify the remote commit.
