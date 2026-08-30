# Generation latency and Plan recovery implementation plan

> **For agentic workers:** Use subagent-driven-development for the isolated parser repair; integrate and verify the tightly coupled generation path in this session.

**Goal:** Preserve Codex CLI while eliminating avoidable planning tool loops, explicitly disabling reasoning for generation, and recovering harmless Markdown formatting drift.

**Architecture:** Prepare bounded trusted Skills and learner context in Python. Known, stable curriculum uses its local map without mandatory live research; unfamiliar/version-sensitive requests retain research before generation. Existing validation, explicit Plan confirmation and transactional writes remain authoritative. Runtime generation overrides affect the project invocation, never the user's global Codex configuration.

**Tech Stack:** Python, FastAPI, Codex CLI, DeepSeek Responses, pytest.

**Execution record:** All implementation and diagnostic steps below were executed on 2026-08-30. See `docs/generation-performance-2026-08-30.md` for measured results. The fresh beginner journey passed; another advanced/interview sample failed content validation. This is not an all-routes acceptance claim. These remaining quality failures are intentionally not bypassed.

## Task 1 — Markdown parser regression

Files: `backend/learning_plan_personalizer.py`, `tests/test_plan_list_wrapper.py`.

- [x] Add a test moving the real-world `- #### 知识点` list to the end of each stage; assert normalization passes without changing content.
- [x] Run `.venv/bin/python -m pytest tests/test_plan_list_wrapper.py -q` and observe failure.
- [x] Normalize only the exact knowledge heading and its child list, independently of position; keep rejection of missing/insufficient knowledge and executable code fences.
- [x] Re-run parser tests and replay the saved 26-stage failure against the real normalizer.

## Task 2 — Prepared generation and research routing

Files: new `backend/generation_context.py`, `backend/learning_plan_personalizer.py`, `backend/main.py`, `backend/lesson_generator.py`, generation tests.

- [x] Tests: known Go/Python foundation plans must not require live research merely because their route is comprehensive; unknown topics still do. Explicit version-sensitive intent retains research. Assert confirmed intent fields and exact-topic local knowledge are supplied.
- [x] Build a bounded context from allowlisted Skill/reference files, profile JSON and exact language map. Do not enumerate unrelated histories or topics, fabricate sources, truncate selected rules, or let missing required files silently weaken policy.
- [x] Inject this context for Plan and lesson calls. State which resources are already supplied, which research remains necessary, and that generated text is returned rather than written by the model. Keep full output/semantic validation and confirmation gates.
- [x] Update conflicting runtime Skill wording for prepared context and conditional research; publish after verification.

## Task 3 — Project-scoped non-thinking generation

Files: `backend/codex_driver.py`, related driver tests.

- [x] Test the actual command built for a prepared generation: explicit `model_reasoning_effort="none"`, preserve project provider, no mutation of global configuration.
- [x] Add generation-only keyword flags to `chat`; optional tool-free mode for fully prepared tasks disables shell tools. Research-enabled tasks retain necessary tools.
- [x] Supply the running interpreter path in the environment/instructions so research does not depend on a `python` alias.
- [x] Verify error handling remains fail-closed and normal interactive Codex calls retain existing behavior.

## Task 4 — Acceptance

- [x] Run full Python and Node suites, review diffs, verify no real user data or secrets staged.
- [x] Run fresh isolated Go beginner Plan → explicit confirmation → first lesson. Inspect real Codex usage for reasoning tokens and tool counts; report failures rather than hiding them or silently changing the test.
- [x] Check a non-Go/unknown-topic research route remains available and source requirements are not bypassed.
- [x] Save measured timings and limitations, then safely restart the current server with synchronized Skills. Do not interrupt active learner generation.
