# Onboarding Research UI Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the unsupported voice UI, separate progress summary from current substep, and make explicit beginner interview intent produce a valid researched interview plan.

**Architecture:** Keep UI progress state in the existing activity controller, but give summary and substep separate update paths. Keep routing judgment in the workspace Skill and structured intent schema. Keep research validation strict while canonicalizing only approved display qualifiers.

**Tech Stack:** Vanilla JavaScript, FastAPI/Pydantic, Markdown Skills, pytest.

---

### Task 1: Progress and voice UI contracts

- [x] Replace the existing voice success test with a failing absence contract covering HTML, JavaScript and CSS.
- [x] Add a failing contract proving phase rotation updates only `activityCurrentStep`.
- [x] Remove the voice button, script, initializer, source file and CSS.
- [x] Keep `activityStatusDetail` static while rotating `activityCurrentStep`.
- [x] Run the focused frontend contract and JavaScript syntax tests.

### Task 2: Interview intent routing

- [x] Add a failing Skill evaluation for “我想面试 AI 前端，初学”.
- [x] Add a prompt contract requiring `interview_sprint`, `zero`, and `not_applicable` without generic learning-depth choices.
- [x] Update `learning-intent-router/SKILL.md` and the bounded intent prompt.
- [x] Run intent, teaching-contract and API intent tests.

### Task 3: Research topic canonicalization

- [x] Add a failing test with requested topic `AI前端` and artifact topic `AI前端工程师（面试冲刺 · 零基础 · meaning_only）`.
- [x] Implement exact canonical comparison after removing approved parenthetical and role suffixes.
- [x] Rewrite the accepted artifact topic to the requested topic and retain source evidence.
- [x] Verify a genuinely different topic is still rejected.

### Task 4: Documentation, verification and delivery

- [x] Document backend `publish` in README without describing it as a package or GitHub publish.
- [x] Update this checklist and the product change record.
- [x] Run full pytest, workspace validation, JS syntax, JSON and diff checks.
- [x] Commit and push directly to GitHub `main`, then verify the remote SHA.
