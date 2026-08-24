# Evidence-based Onboarding and End-to-end Readiness Design

## Problem

The onboarding model currently may invent a learner level when the user gives only a role, for example `我要面试前端岗`. The frontend then treats the invented `some` level as evidence and starts a technical diagnosis. Diagnosis prompts are written to the chat feed while their choices remain pinned near the composer, so the prompt can scroll out of view and leave apparently context-free answers. Previous verification stopped at the intent endpoint and did not prove that Plan and the first HTML lesson could be generated.

## Approved behavior

1. Slot filling may normalize evidence but may not invent it. If an interview request contains a target role but no level evidence, the model asks exactly one compact question with `初学`, `有基础`, and `熟练` choices.
2. `初学` maps to `zero` and skips technical diagnosis. It proceeds directly to a draft Plan.
3. `有基础` and `熟练` map to `some` and `experienced`, then receive three or four role-specific clickable diagnosis questions.
4. The active diagnosis prompt is rendered inside the choice tray, immediately above the options, as well as in the conversation history. The prompt and options therefore cannot be visually separated by scrolling.
5. Intent decisions are semantically validated: `ready_for_plan` cannot use a non-concept learner level unless `slots.level_evidence` contains evidence from the user or prior dialogue. Invalid model output receives at most two bounded repair attempts. If all fail, only an explicit interview request may be recovered from facts already written by the user; ordinary learning requests still return a recoverable error rather than being guessed.
6. Completion is proven by an end-to-end smoke suite that covers intent, optional diagnosis, Plan creation, Plan confirmation, first lesson generation, and HTML lesson payload validation.

## Components

- `backend/learning_intent.py`: semantic evidence rules and correction prompt construction.
- `backend/main.py`: bounded retry when the model returns a structurally valid but semantically unsupported decision.
- `workspace/dev/.codex/skills/learning-intent-router/SKILL.md`: source-of-truth agent instruction for missing level evidence.
- `frontend/index.html` and `frontend/js/onboarding.js`: persistent diagnosis question in the choice tray.
- `tests/`: regression tests for missing evidence, visual prompt binding, role-specific diagnosis, Plan, and first lesson readiness.
- `tools/e2e_learning_smoke.py`: optional live-service smoke runner using unique QA users and reporting the last successful stage.

## Failure handling

- Malformed or evidence-free model decisions do not mutate project state.
- Failed repair attempts return the existing recoverable intent error and preserve the typed text, except when an explicit interview role and level can be recovered verbatim without inference.
- Failed Plan or lesson generation reports the exact stage and keeps the draft/project state available for retry.

## Acceptance matrix

- Frontend interview, no level: asks one level question; selecting beginner reaches Plan without diagnosis.
- Java backend interview, some experience: receives Java/backend-specific diagnosis, then reaches Plan.
- AI frontend interview, beginner stated: reaches Plan directly.
- AI product manager interview, experienced: receives product/AI-specific diagnosis, then reaches Plan.
- RAG concept: skips diagnosis and reaches a short Plan and first lesson.
- LangGraph project learning: captures project outcome, produces a project Plan and first lesson.

Every case passes only when the first generated lesson contains at least one page with a title and teaching content.
