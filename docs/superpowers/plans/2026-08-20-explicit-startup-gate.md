# Explicit Startup Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure every fresh page load starts in the chat initialization view and requires an explicit learner choice before restoring any lesson.

**Architecture:** Keep persisted learning data untouched, but insert a client-side startup gate before `enterLearning()`. Reuse the existing inline choice tray for resume, new-topic onboarding, and interview-bank access.

**Tech Stack:** Vanilla JavaScript, existing FastAPI learning-context and interview-bank APIs, pytest frontend contract tests, in-app browser QA.

---

### Task 1: Lock the startup contract

- [x] Add a failing frontend test proving `initialize()` cannot call `enterLearning()` directly from persisted profile status.
- [x] Add a failing test for the inline startup actions and conditional interview-bank action.
- [x] Run focused tests and confirm the old automatic-resume branch causes the failure.

### Task 2: Implement the startup gate

- [x] Add `showStartupGate(context, bank)` in `frontend/js/app.js`.
- [x] Keep `is-chat-first` active while the gate is visible.
- [x] Wire `继续上次学习` to `enterLearning()`, `学习新内容` to clean onboarding, and `打开面试题库` to the interview controller.
- [x] Preserve stored messages and learning files; do not delete history.

### Task 3: Verify behavior

- [x] Run frontend contracts and the full Python test suite.
- [x] Reload a user with a confirmed plan and verify no lesson is visible before choosing.
- [x] Click each startup action and verify its destination.
- [x] Commit only startup-gate files and keep the branch local.
