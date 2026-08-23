# Guided Lesson Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make onboarding open-ended, make every lesson page state its next action, open practice folders safely, improve dialog dismissal, and generate topic-specific learning plans.

**Architecture:** Deterministic UI guidance comes from lesson page types so it is instant and reliable. A validated Codex plan-personalization endpoint replaces the detailed fallback plan only when model output satisfies the required Markdown structure. Local folder opening is handled by a path-confined FastAPI endpoint.

**Tech Stack:** Vanilla JavaScript, FastAPI, Pydantic, macOS `open`, existing Codex driver, pytest, in-app browser QA.

---

### Task 1: Open-ended onboarding

- [x] Add failing frontend tests proving the topic stage has no fixed language choices.
- [x] Make the first prompt request typed topic text and show direct goal-route choices afterward.
- [x] Run frontend contracts.

### Task 2: Safe practice-folder opening

- [x] Add failing backend tests for valid paths, missing paths and traversal attempts.
- [x] Implement a confined folder resolver and `POST /api/practice/open`.
- [x] Replace `复制路径` with `打开文件夹` and test the frontend request.

### Task 3: Per-page and final-page guidance

- [x] Add failing frontend tests for the pinned step guide and final-page chat instruction.
- [x] Render page-type-specific guidance on every page-change event.
- [x] On the final page, add one coach message and focus the composer without duplicating messages.

### Task 4: Dialog dismissal

- [x] Add failing tests for × buttons, sticky headers and backdrop-click handlers.
- [x] Implement both close mechanisms for every dialog.

### Task 5: Detailed personalized plan

- [x] Add failing tests for a detailed route-specific fallback plan.
- [x] Add a tested Codex personalization endpoint with Markdown validation and safe fallback.
- [x] Call personalization before entering the first lesson and persist the accepted plan in the user folder.

### Task 6: Verification and documentation

- [x] Run the full test suite.
- [x] Browser-test onboarding, page guides, final submission and folder opening; dialog dismissal is covered by contract tests because the current narrow QA viewport hides the desktop left rail entry.
- [x] Append actual files, behavior and verification evidence to section 17 of the main design Markdown.
- [x] Commit locally without pushing GitHub.
