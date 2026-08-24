from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "frontend/index.html"
APP_JS = ROOT / "frontend/js/app.js"
ONBOARDING_JS = ROOT / "frontend/js/onboarding.js"
ARTIFACT_JS = ROOT / "frontend/js/artifact.js"
MARKDOWN_JS = ROOT / "frontend/js/markdown.js"
STYLE = ROOT / "frontend/css/style.css"
INTERVIEW_JS = ROOT / "frontend/js/interview-bank.js"
TOPIC_INTENT_JS = ROOT / "frontend/js/topic-intent.js"
ACTIVITY_PROGRESS_JS = ROOT / "frontend/js/activity-progress.js"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_first_screen_is_one_chat_with_inline_choices_above_composer() -> None:
    html = read(INDEX)
    assert 'class="app-shell is-onboarding" id="appShell"' in html
    assert html.index('id="choiceTray"') < html.index('id="chatForm"')
    assert 'id="onboardingPanel"' not in html
    assert 'id="onboardingForm"' not in html


def test_mermaid_fences_render_as_diagrams_and_are_hydrated_after_dynamic_updates() -> None:
    script = """
const markdown = require('./frontend/js/markdown.js');
console.log(markdown.render('```mermaid\\nflowchart TD\\nA-->B\\n```'));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True, text=True)
    html = read(INDEX)
    app = read(APP_JS)
    artifact = read(ARTIFACT_JS)

    assert result.returncode == 0, result.stderr
    assert 'class="mermaid"' in result.stdout
    assert '<pre>' not in result.stdout
    assert 'mermaid.min.js' in html
    assert "MarkdownRenderer.hydrate" in app
    assert "MarkdownRenderer.hydrate" in artifact


def test_course_preparation_title_has_animated_ellipsis_with_reduced_motion_fallback() -> None:
    html = read(INDEX)
    css = read(STYLE)

    assert 'id="pageTitle">课程准备中<span class="loading-ellipsis"' in html
    assert "@keyframes loading-dot" in css
    assert ".loading-ellipsis" in css
    assert "prefers-reduced-motion" in css


def test_learning_mode_reserves_sidebar_for_outline_and_moves_plan_projects_to_settings() -> None:
    html = read(INDEX)
    css = read(STYLE)
    roadmap = html[html.index('<nav class="roadmap"') : html.index("</nav>")]

    assert 'id="sidebarPlanDock"' in roadmap
    assert '<details class="sidebar-plan-dock" id="sidebarPlanDock">' in roadmap
    assert '.app-shell:not(.is-onboarding) .sidebar-projects,' in css
    assert '.app-shell:not(.is-onboarding) .sidebar-plan-dock { display: none; }' in css
    settings = html[html.index('id="settingsDialog"') : html.index('id="reminderDialog"')]
    assert 'id="openPlanBtn"' in settings
    assert 'id="projectArchiveList"' in settings


def test_onboarding_has_one_brand_header_and_no_dead_overflow_menu() -> None:
    html = read(INDEX)

    assert html.count('class="brand-row"') == 1
    assert 'class="coach-title"' not in html
    assert 'id="conversationMenuBtn"' not in html


def test_onboarding_projects_are_visible_in_the_sidebar_not_hidden_in_a_footer_popover() -> None:
    html = read(INDEX)
    css = read(STYLE)

    roadmap = html[html.index('<nav class="roadmap"') : html.index("</nav>")]
    assert 'class="sidebar-projects"' in roadmap
    assert roadmap.index('id="learningProjectList"') < roadmap.index('id="settingsBtn"')
    assert 'id="projectSwitcherBtn"' not in html
    assert 'id="projectSwitcherPopover"' not in html
    assert ".app-shell.is-onboarding .sidebar-projects" in css


def test_user_messages_are_compact_and_do_not_render_a_you_label() -> None:
    app = read(APP_JS)
    css = read(STYLE)

    message_builder = app[app.index("function messageElement") : app.index("function renderMessages")]
    assert 'message.role === "user" ? "你"' not in message_builder
    assert 'if (message.role !== "user")' in message_builder
    assert ".message.user .message-label" not in css
    assert "width: fit-content" in css


def test_corporate_clean_tokens_and_one_aligned_chat_grid_are_applied() -> None:
    css = read(STYLE)
    html = read(INDEX)

    assert "--paper: #f8fafc" in css
    assert "--primary: #2563eb" in css
    assert "--primary-strong: #1d4ed8" in css
    assert "--chat-content-width: 1040px" in css
    assert "Inter," not in css
    assert ".app-shell.is-onboarding .conversation-bottom { width: min(var(--chat-content-width), calc(100% - 64px))" in css
    assert "max(32px, calc((100% - var(--chat-content-width)) / 2))" in css
    assert ".choice-tray.is-intent-question { width: 100%" in css
    assert ".coach-composer textarea" in css and "font-size: 16px" in css
    assert '.app-shell:not(.is-chat-first):not(.is-onboarding) .conversation-shell' in css
    assert "bootstrap-icons" in html


def test_primary_controls_use_a_standard_icon_library_instead_of_text_glyphs() -> None:
    html = read(INDEX)
    app = read(APP_JS)
    onboarding = read(ONBOARDING_JS)

    for icon in ("bi-mortarboard-fill", "bi-plus-lg", "bi-arrow-up", "bi-gear"):
        assert icon in html
    assert "bi-three-dots" in app
    assert "bi-info-circle" in onboarding
    assert 'more.textContent = "•••"' not in app
    assert 'detail.textContent = "i"' not in onboarding


def test_inline_diagnosis_is_clickable_and_bounded() -> None:
    js = read(ONBOARDING_JS)
    html = read(INDEX)
    assert "diagnostic" in js
    assert 'className = "inline-choice"' in js
    assert '"/api/diagnostics/answer"' in js
    assert "最多 4" in js
    assert "textarea" not in js
    assert 'id="choiceTrayQuestion"' in html
    assert 'byId("choiceTrayQuestion").textContent = result.question.prompt' in js
    assert 'byId("choiceTrayQuestion").hidden = false' in js
    assert 'byId("choiceTrayQuestion").hidden = true' in js


def test_onboarding_uses_model_intent_and_multiturn_slot_filling() -> None:
    js = read(ONBOARDING_JS)
    app = read(APP_JS)
    html = read(INDEX)
    assert 'request("/api/onboarding/intent"' in js
    assert "intentHistory" in js
    assert "slots" in js
    assert "clarificationCount" in js
    assert "recentIntentHistory" in js
    assert "TopicIntent" not in js
    assert "function askGoal()" not in js
    assert "function askLevel()" not in js
    assert "function askTime()" not in js
    assert "TopicIntent" not in app
    assert "topic-intent.js" not in html
    assert "shouldIntake(value)" not in app


def test_current_lesson_stays_visible_until_model_commits_to_a_new_plan() -> None:
    app = read(APP_JS)
    begin = app[app.index("async function beginOnboarding") : app.index("async function restoreCurrentCourse")]
    before_ready = begin[:begin.index("onIntentReady: async () =>")]
    ready_handler = begin[begin.index("onIntentReady: async () =>") :]

    assert 'classList.add("is-onboarding")' not in before_ready.split("if (!archiveCurrent)", 1)[0]
    assert 'fetch("/api/projects/snapshot"' in ready_handler
    assert ready_handler.index('fetch("/api/projects/snapshot"') < ready_handler.index('classList.add("is-onboarding")')


def test_concept_plan_review_uses_relevant_choices_and_refreshes_real_duration() -> None:
    onboarding = read(ONBOARDING_JS)
    app = read(APP_JS)

    assert 'state.goalRoute === "concept_clarity"' in onboarding
    assert "这份短方案" in onboarding
    assert "把概念讲得更简短" not in onboarding
    assert "await revisePlan(text)" in onboarding
    assert 'setText("#remainingTime", `预计还需 ${context.session_minutes || 25} 分钟`)' in app


def test_topic_onboarding_starts_with_free_text_and_no_preset_goal_choices() -> None:
    js = read(ONBOARDING_JS)
    ask_topic = js[js.index("function askTopic()") : js.index("function recentIntentHistory()")]

    assert "直接输入" in ask_topic
    assert "showChoices(" not in ask_topic
    assert "面试" in ask_topic and "LangGraph" in ask_topic


def test_dynamic_intent_choices_are_compact_and_keep_composer_as_the_correction_path() -> None:
    onboarding = read(ONBOARDING_JS)
    css = read(STYLE)

    assert "options.slice(0, 3)" in onboarding
    assert 'className = "intent-choice-row"' in onboarding
    assert 'className = "choice-detail"' in onboarding
    assert 'role", "tooltip"' in onboarding
    assert "都不符合" not in onboarding
    assert "我直接补充" not in onboarding
    assert "也可以直接打字" in onboarding
    assert ".intent-choice-row" in css
    assert ".choice-tooltip" in css


def test_unsupported_voice_input_is_not_shown_or_loaded() -> None:
    html = read(INDEX)
    app = read(APP_JS)
    css = read(STYLE)

    assert 'id="voiceInputBtn"' not in html
    assert 'src="/js/voice-input.js' not in html
    assert "bindVoiceInput" not in app
    assert "VoiceInput" not in app
    assert ".voice-input-button" not in css
    assert not (ROOT / "frontend/js/voice-input.js").exists()


def test_onboarding_requires_a_model_personalized_plan_before_opening_lesson() -> None:
    js = read(ONBOARDING_JS)
    confirm = js[js.index("async function confirm") : js.index("async function choose")]

    assert 'request("/api/onboarding/confirm"' in confirm
    assert 'request("/api/plans/personalize"' in confirm
    assert confirm.index('request("/api/onboarding/confirm"') < confirm.index('request("/api/plans/personalize"')
    assert "catch" in confirm
    assert "onConfirmed" in confirm
    assert "AbortController" in confirm
    assert "300000" in confirm
    assert "if (!personalized.personalized) throw new Error" in confirm
    assert "onPlanReady" in confirm
    assert 'state.stage = "plan_review"' in confirm
    assert confirm.index('state.stage = "plan_review"') < confirm.index('request("/api/plans/confirm"')
    assert "兜底计划" not in confirm
    assert "详细课程研究与生成超过 5 分钟" in confirm


def test_plan_is_rendered_and_confirmed_before_lesson_generation() -> None:
    html = read(INDEX)
    app = read(APP_JS)
    onboarding = read(ONBOARDING_JS)

    assert 'id="planReviewPane"' not in html
    assert 'id="inlinePlanPreview"' not in html
    assert "showPlanReview" in app
    assert 'request("/api/plans/confirm"' in onboarding
    assert 'request("/api/plans/revise"' in onboarding
    assert "确认并开始" in onboarding
    review = app[app.index("async function showPlanReview") : app.index("function projectTimeLabel")]
    assert "renderPlanConversationMessage" in review
    assert 'classList.add("is-onboarding")' in review


def test_plan_review_has_one_compact_confirmation_and_text_directly_revises() -> None:
    onboarding = read(ONBOARDING_JS)
    css = read(STYLE)

    choices = onboarding[onboarding.index("function planReviewChoices()") : onboarding.index("async function confirm(")]
    assert "return [confirmChoice]" in choices
    assert "前面更快一点" not in choices
    assert "多做项目" not in choices
    assert "我想调整计划" not in choices
    assert "compact: true" in onboarding
    assert 'state.stage === "plan_review"' in onboarding
    assert "await revisePlan(text)" in onboarding
    assert 'state.stage = "plan_feedback"' not in onboarding
    assert ".choice-tray.is-plan-confirmation" in css
    assert ".plan-conversation-message" in css


def test_learning_shell_has_roadmap_artifact_chat_and_resizer() -> None:
    html = read(INDEX)
    assert 'id="learningRoadmap"' in html
    assert 'id="artifactPane"' in html
    assert 'id="conversationShell"' in html
    assert 'id="artifactSplitter"' in html
    assert 'role="separator"' in html


def test_artifact_uses_structured_lesson_api_and_real_practice_path() -> None:
    js = read(ARTIFACT_JS)
    html = read(INDEX)
    assert 'fetch(`/api/lesson/current' in js
    assert 'fetch("/api/lesson/check"' in js
    assert 'id="pageCount"' in html
    assert 'id="practicePath"' in html
    assert "pointermove" in js and "ArrowLeft" in js and "ArrowRight" in js
    assert "localStorage.setItem(widthKey" in js


def test_practice_folder_is_opened_instead_of_copying_its_path() -> None:
    js = read(ARTIFACT_JS)
    html = read(INDEX)

    assert 'id="openPracticeFolderBtn"' in html
    assert "打开文件夹" in html
    assert 'fetch("/api/practice/open"' in js
    assert 'id="copyPathBtn"' not in html
    assert 'writeText(byId("practicePath")' not in js


def test_copy_code_has_visible_accessible_success_feedback() -> None:
    js = read(ARTIFACT_JS)
    html = read(INDEX)

    assert 'aria-live="polite"' in html
    assert "✓ 已复制" in js
    assert "复制失败" in js
    assert "1500" in js


def test_sidebar_prioritizes_route_and_moves_secondary_controls_into_settings() -> None:
    html = read(INDEX)
    css = read(STYLE)
    app = read(APP_JS)

    roadmap = html[html.index('<nav class="roadmap"') : html.index("</nav>")]
    settings = html[html.index('id="settingsDialog"') : html.index("</dialog>", html.index('id="settingsDialog"'))]
    assert 'id="outlinePanel"' in roadmap and 'id="interviewBankPanel"' in roadmap
    assert 'id="newGoalBtn"' not in roadmap and 'id="settingsBtn"' in roadmap
    assert 'id="addLearningProjectBtn"' in roadmap
    assert 'id="reminderBtn"' not in roadmap
    assert 'id="learningProjectList"' in roadmap
    assert 'id="reminderBtn"' in settings
    assert 'id="projectArchiveList"' in settings
    assert 'id="openPlanBtn"' in settings
    assert '$("#settingsBtn").addEventListener("click"' in app
    assert ".roadmap-actions" in css


def test_startup_keeps_project_rail_and_removes_resume_choice() -> None:
    html = read(INDEX)
    app = read(APP_JS)
    css = read(STYLE)

    assert 'id="learningProjectList"' in html
    assert "继续上次学习" not in app
    assert "showStartupGate" not in app
    assert ".app-shell.is-onboarding" in css
    onboarding_css = css[css.index(".app-shell.is-onboarding") : css.index(".app-shell.is-chat-first")]
    assert ".app-shell.is-onboarding .roadmap { grid-column: 1; }" in onboarding_css
    assert ".app-shell.is-onboarding .roadmap { display: none; }" not in onboarding_css


def test_project_list_is_directly_available_and_still_keeps_outline_as_primary_space() -> None:
    html = read(INDEX)
    css = read(STYLE)
    app = read(APP_JS)
    roadmap = html[html.index('<nav class="roadmap"') : html.index("</nav>")]

    assert roadmap.index('id="learningProjectList"') < roadmap.index('id="outlinePanel"')
    assert 'class="sidebar-projects"' in roadmap
    assert 'id="addLearningProjectBtn"' in roadmap
    assert 'id="projectMobileBtn"' in html
    assert 'id="learningProjectList"' in roadmap
    assert 'id="projectSwitcherPopover"' not in html
    assert ".sidebar-projects" in css
    assert "toggleProjectSwitcher" in app
    assert "startNewLearningProject" in app


def test_project_delete_supports_context_long_press_swipe_and_one_confirm_dialog() -> None:
    html = read(INDEX)
    css = read(STYLE)
    app = read(APP_JS)

    assert 'id="projectDeleteDialog"' in html
    assert 'id="confirmProjectDeleteBtn"' in html
    assert "共享知识库中的教案不会被删除" in html
    assert 'addEventListener("contextmenu"' in app
    assert "PROJECT_LONG_PRESS_MS = 600" in app
    assert "PROJECT_SWIPE_THRESHOLD = 64" in app
    assert "requestProjectDeletion" in app
    assert 'method: "DELETE"' in app
    assert ".project-row.is-swiped" in css


def test_existing_project_gate_runs_before_snapshot_or_plan_generation() -> None:
    onboarding = read(ONBOARDING_JS)
    app = read(APP_JS)

    assert 'fetch(`/api/projects/match?' in onboarding
    assert 'state.stage = "existing_project"' in onboarding
    assert "继续已有项目" in onboarding
    assert "把新目标合并进去" in onboarding
    assert "continue_existing" in onboarding
    assert "merge_existing" in onboarding
    assert "onContinueExistingProject" in app
    assert "onMergeExistingProject" in app
    ready = onboarding[onboarding.index('decision.action === "ready_for_plan"') : onboarding.index('decision.action === "interview_bank_intake"')]
    assert ready.index("findExistingProject") < ready.index("onIntentReady")


def test_private_data_reset_clears_all_legacy_browser_learning_records_once() -> None:
    app = read(APP_JS)

    assert 'PRIVATE_DATA_RESET_VERSION = "20260822-project-reset-v1"' in app
    assert 'key.startsWith("learning-agent.messages.")' in app
    assert "localStorage.removeItem(key)" in app
    assert "resetLegacyClientRecords();" in app


def test_chat_can_request_a_validated_lesson_revision() -> None:
    app = read(APP_JS)
    artifact = read(ARTIFACT_JS)

    assert "isLessonRevisionRequest" in app
    assert 'fetch("/api/lesson/remediate"' in app
    assert "正在按你的要求重做讲义" in app
    assert "loadCurrentLesson" in app
    assert "lesson-revision" in read(ROOT / "backend/lesson_generator.py")
    assert "旧讲义仍然保留" in app


def test_each_lesson_page_places_its_next_step_in_the_ppt_and_final_action_panel() -> None:
    html = read(INDEX)
    js = read(APP_JS)
    artifact = read(ARTIFACT_JS)

    assert 'id="pageInstruction"' in html
    assert 'id="stepGuide"' not in html
    assert 'id="lessonCompletionPanel"' in html
    assert 'id="homeworkCard"' in html
    assert 'id="lessonNotesPanel"' in html
    assert 'id="completeSubmitBtn"' in html
    assert 'id="completeReteachBtn"' not in html
    assert 'id="completeStuckBtn"' not in html
    assert 'id="lessonPrimaryAction"' in html
    assert 'id="chatPrimaryAction"' in html
    assert "function guideForPage" not in js
    assert "renderPageInstruction" in artifact
    assert "renderHomework" in artifact
    assert "loadLessonNotes" in artifact
    assert 'fetch("/api/lesson/complete"' in artifact
    assert 'fetch("/api/lesson/generate"' in artifact
    assert 'fetch("/api/curriculum/generate"' in artifact
    assert "generate_lesson" in artifact
    assert "开始下一课：" in artifact or "cta_label" in artifact
    page_change = js[js.index('document.addEventListener("learning-agent:page-change"') : js.index('document.addEventListener("learning-agent:lesson-transition"')]
    assert '$("#chatInput").focus()' not in page_change


def test_async_learning_work_has_a_visible_dynamic_status_and_action_feedback() -> None:
    html = read(INDEX)
    app = read(APP_JS)
    onboarding = read(ONBOARDING_JS)
    artifact = read(ARTIFACT_JS)
    css = read(STYLE)

    assert 'id="activityStatus"' in html
    assert 'aria-live="polite"' in html
    assert "LearningActivity" in onboarding
    assert "startPlanGeneration" in onboarding
    assert "activityPhaseTimer" in app
    assert 'class="activity-track"' in html
    assert "activity-track" in css
    assert "LearningActivity" in artifact
    assert "LearningActivity" in app
    assert "正在检查这道题" in artifact
    assert "下一步：" in artifact
    assert ".activity-status.is-active" in css
    assert "@keyframes activity-pulse" in css


def test_long_generation_shows_determinate_estimated_progress_and_eta() -> None:
    html = read(INDEX)
    app = read(APP_JS)
    artifact = read(ARTIFACT_JS)

    assert 'id="activityProgressFill"' in html
    assert 'id="activityProgressText"' in html
    assert 'src="/js/activity-progress.js' in html
    assert "startLessonGeneration" in app
    assert "startLessonGeneration" in artifact

    script = """
const progress = require('./frontend/js/activity-progress.js');
console.log(JSON.stringify({
  early: progress.estimate(30_000, 120_000),
  late: progress.estimate(150_000, 120_000),
}));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert 0 < payload["early"]["percent"] < 92
    assert "预计还需" in payload["early"]["label"]
    assert payload["late"]["percent"] == 92
    assert "超出常见时间" in payload["late"]["label"]


def test_failed_lesson_generation_replaces_loading_page_with_retry_action() -> None:
    html = read(INDEX)
    artifact = read(ARTIFACT_JS)

    assert 'id="lessonLoadError"' in html
    assert 'id="retryLessonBtn"' in html
    assert "showLessonLoadFailure" in artifact
    assert 'setText("pageTitle", "课程生成失败")' in artifact
    assert 'byId("retryLessonBtn").addEventListener' in artifact


def test_learning_mode_prioritizes_outline_and_keeps_projects_in_settings() -> None:
    html = read(INDEX)
    css = read(STYLE)
    assert 'id="learningProjectsToggle"' in html
    assert 'aria-expanded="false"' in html
    assert ".app-shell:not(.is-onboarding) .sidebar-projects" in css
    assert '.app-shell:not(.is-onboarding) .sidebar-plan-dock { display: none; }' in css
    assert ".app-shell.is-onboarding .sidebar-projects" in css
    assert 'id="projectArchiveList"' in html


def test_composer_icon_buttons_are_visually_compact_with_stronger_icons() -> None:
    css = read(STYLE)

    assert ".send-button" in css and "width: 36px; height: 36px" in css
    assert ".composer-actions i" in css
    assert "-webkit-text-stroke" in css


def test_roadmap_is_viewport_locked_and_has_its_own_paging_controls() -> None:
    html = read(INDEX)
    app = read(APP_JS)
    css = read(STYLE)

    assert 'id="outlinePreviousBtn"' in html
    assert 'id="outlineNextBtn"' in html
    assert 'id="outlinePageLabel"' in html
    assert "panel.scrollTo" in app
    assert ".app-shell:not(.is-chat-first) { height: 100dvh; overflow: hidden; }" in css
    assert ".roadmap { height: 100dvh; overflow: hidden;" in css


def test_final_page_does_not_leave_a_disabled_next_button_dead_end() -> None:
    js = read(ARTIFACT_JS)

    assert 'byId("lessonCompletionPanel").hidden = !isFinal' in js
    assert 'byId("nextPageBtn").hidden = isFinal' in js
    assert "submitCompletion" in js
    assert "loadCurrentLesson" in js
    assert "next_knowledge_point_id" in js
    assert 'byId("lessonCompletionPanel").scrollIntoView' in js
    assert 'homeworkCard' in js
    assert 'decision.verdict === "advance" && !decision.next_knowledge_point_id' in js
    assert 'byId("planDialog").showModal()' in js


def test_dialogs_use_icon_close_sticky_headers_and_backdrop_dismissal() -> None:
    html = read(INDEX)
    js = read(APP_JS)
    css = read(STYLE)

    assert 'aria-label="关闭学习方案"' in html
    assert 'aria-label="关闭学习提醒"' in html
    assert 'class="bi bi-x-lg"' in html
    assert '>关闭</button>' not in html
    assert "event.target === dialog" in js
    assert "position: sticky" in css


def test_chat_uses_streaming_and_safe_markdown_rendering() -> None:
    js = read(APP_JS)
    assert 'fetch("/api/chat/stream"' in js
    assert "response.body.getReader()" in js
    assert "MarkdownRenderer.render(assistant.content)" in js
    assert '.textContent = message.content' in js


def test_markdown_renderer_escapes_html_and_highlights_code() -> None:
    script = f"""
const md = require({str(MARKDOWN_JS)!r});
const rendered = md.render('# 标题\\n\\n<script>alert(1)</script>\\n\\n```go\\nfunc main() {{}}\\n```');
if (rendered.includes('<script>')) process.exit(2);
if (!rendered.includes('&lt;script&gt;')) process.exit(3);
if (!rendered.includes('token-keyword')) process.exit(4);
"""
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_markdown_renders_deep_headings_highlights_and_copyable_code_frames() -> None:
    source = "#### 重点标题\n\n请记住 ==指针保存地址==。\n\n```go\npackage main\n```"
    script = f"""
const md = require({str(MARKDOWN_JS)!r});
const rendered = md.render({json.dumps(source, ensure_ascii=False)});
console.log(rendered);
"""
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert "<h4>重点标题</h4>" in result.stdout
    assert "<mark>指针保存地址</mark>" in result.stdout
    assert 'class="markdown-code-frame"' in result.stdout
    assert 'class="markdown-copy-code"' in result.stdout
    assert "复制代码" in result.stdout
    assert "markdown-copy-code:not([data-bound])" in read(MARKDOWN_JS)
    assert "已复制" in read(MARKDOWN_JS)


def test_generation_progress_reports_completed_remaining_eta_and_current_step() -> None:
    script = f"""
const progress = require({str(ACTIVITY_PROGRESS_JS)!r});
console.log(JSON.stringify(progress.estimate(30000, 120000)));
"""
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    payload = json.loads(result.stdout)

    assert payload["percent"] <= 92
    assert payload["completedPercent"] == payload["percent"]
    assert payload["remainingPercent"] == 100 - payload["percent"]
    assert "已完成" in payload["label"]
    assert "剩余" in payload["label"]
    assert "预计还需" in payload["label"]
    assert 'id="activityCurrentStep"' in read(INDEX)
    assert 'setText("#activityCurrentStep"' in read(APP_JS)
    assert 'setText("#activityStatusDetail", phases[phaseIndex])' not in read(APP_JS)


def test_learning_sidebar_is_compact_and_keeps_more_space_for_outline() -> None:
    css = read(STYLE)

    assert ".brand-row { height: 48px;" in css
    assert ".rail-tabs button { min-height: 32px;" in css
    assert ".rail-tabs button" in css and "font-size: 12px" in css
    assert ".outline-pager button { width: 24px; height: 22px;" in css
    assert ".stage-item h3" in css and "font-size: 13px" in css


def test_anki_ratings_and_verified_confetti_are_present() -> None:
    js = read(APP_JS)
    bank = read(INTERVIEW_JS)
    css = read(STYLE)
    assert "没想起来" in bank
    assert "稍微有点困难" in bank
    assert "顺利" in bank
    assert 'fetch("/api/practice/review/rate"' in bank
    assert "InterviewBankController.startReview" in js
    assert "result.correct === true && result.verified === true" in js
    assert ".confetti-piece" in css
    assert "1500ms" in css
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_selected_visual_tokens_and_responsive_layout_are_preserved() -> None:
    css = read(STYLE)
    assert "--paper:" in css
    assert "--primary:" in css
    assert "--success:" in css
    assert "grid-template-columns: 270px minmax(480px, 1fr) 9px var(--coach-width)" in css
    assert "@media (max-width: 860px)" in css


def test_browser_state_is_isolated_per_learner() -> None:
    assert '`learning-agent.messages.v3.${USER_ID}`' in read(APP_JS)
    assert '`learning-agent.coach-width.v1.${userId}`' in read(ARTIFACT_JS)


def test_choice_only_concept_finishes_without_terminal_output_inputs() -> None:
    artifact = read(ARTIFACT_JS)

    assert 'state.manifest.completion_mode === "choice"' in artifact
    assert 'completionOutputs' not in artifact
    assert "完成这个概念" in artifact


def test_reminder_settings_use_persistent_backend_api() -> None:
    html = read(INDEX)
    js = read(APP_JS)
    assert 'id="reminderEnabled"' in html
    assert 'id="reminderTime"' in html
    assert 'id="reminderKind"' in html
    assert 'fetch("/api/reminders"' in js
    assert 'fetch(`/api/reminders?' in js


def test_unified_practice_bank_lives_in_left_rail_and_uses_inline_choices() -> None:
    html = read(INDEX)
    js = read(INTERVIEW_JS)
    assert 'id="railOutlineTab"' in html and 'id="railBankTab"' in html
    assert '练习题库' in html
    assert 'id="interviewBankPanel"' in html
    assert 'id="bankCoverage"' in html
    assert 'id="interviewQuestionList"' in html
    assert html.index('id="choiceTray"') < html.index('id="chatForm"')
    assert "逐题从头讲" in js
    assert "系统学习" in js
    assert "先测后学" in js
    assert 'fetch("/api/interview/intake"' in js
    assert 'fetch(`/api/practice/bank?' in js
    assert '课堂选择题' in js and '课后作业' in js and '面试题' in js
    assert '错题 · 再做一遍' in js
    assert "ArtifactController?.openPracticeItem" in js
    assert "openPracticeItem" in read(ARTIFACT_JS)
    assert "showModal" not in js


def test_interview_bank_exposes_answer_and_mastery_status_without_color_only() -> None:
    js = read(INTERVIEW_JS)
    assert "答案待生成" in js
    assert "已有讲解" in js
    assert "尚未练习" in js
    assert "没想起来" in js and "有点困难" in js and "顺利" in js
    assert 'fetch(`/api/interview/questions/${questionId}/mastery`' in js


def test_confirmed_profile_shows_project_home_without_auto_opening_lesson() -> None:
    js = read(APP_JS)
    initialize = js[js.index("async function initialize()") : js.index("function showAnkiRating()")]

    assert "showOnboardingHome(context" in initialize
    assert "await enterLearning()" not in initialize
    assert 'classList.add("is-onboarding")' in js
    assert "archivedMessages" in js
    assert 'setText("#coachContext", "输入你现在想解决的事")' in js
    assert "previousMessages" in js
    assert "STORAGE_PREVIOUS_MESSAGES" in js


def test_startup_home_uses_left_projects_and_free_text_for_new_intent() -> None:
    js = read(APP_JS)
    interview_js = read(INTERVIEW_JS)

    assert "继续上次学习" not in js
    assert "直接点左边的学习项目" in js
    assert "startupGateActive" in js
    assert "beginOnboarding(true, value)" in js
    assert "showOnboardingHome" in js
    assert "openLearningProject" in js
    assert "openBank" in interview_js
    assert "window.InterviewBankController = { init, intake, load, shouldIntake, openBank, startReview, openPracticeItem }" in interview_js


def test_learning_archive_and_new_project_flow_are_unambiguous_and_reversible() -> None:
    html = read(INDEX)
    js = read(APP_JS)

    assert 'id="currentPlanArchiveBtn"' in html
    assert 'id="newGoalBtn"' not in html
    assert "＋ 新建学习项目" not in html
    assert "问当前课程，或直接输入想学的新知识" in html
    assert 'id="projectArchiveList"' in html
    assert 'id="returnCurrentCourseBtn"' in html
    assert "bi-arrow-left" in html and "返回当前课程" in html
    assert '$("#currentPlanArchiveBtn").addEventListener("click"' in js
    assert '$("#settingsDialog").close()' in js
    assert "onboardingSnapshot" in js
    assert "getPageIndex" in js
    assert "restoreCurrentCourse" in js
    assert '$("#stepGuide").hidden = true' not in js
    assert '$("#promptChips").hidden = true' in js
    assert "OnboardingController.stop" in js
    assert 'fetch("/api/projects/snapshot"' in js
    assert 'fetch("/api/projects/restore"' in js
    assert 'fetch("/api/projects/snapshot/archive"' in js


def test_learning_archive_lists_saved_projects_and_switches_without_reonboarding() -> None:
    js = read(APP_JS)

    assert "renderLearningProjects" in js
    assert "openLearningProject" in js
    assert 'fetch(`/api/projects?user_id=${encodeURIComponent(USER_ID)}`)' in js
    assert 'fetch("/api/projects/snapshot/archive"' in js
    assert 'fetch("/api/projects/switch"' in js
    assert "await enterLearning()" in js
    assert "location.reload()" not in js
    assert "onFailed: async () =>" in js
    assert "await state.callbacks.onFailed?.(error)" in read(ONBOARDING_JS)
    assert "await refreshProjectArchive();" in js


def test_progress_uses_completed_knowledge_points_when_curriculum_exists() -> None:
    js = read(APP_JS)

    assert "context.knowledge_progress" in js
    assert "knowledge.completed" in js
    assert "/ Number(knowledge.total)" in js


def test_outline_pager_moves_one_full_sidebar_page_and_updates_nearest_page_label() -> None:
    js = read(APP_JS)

    assert "Math.round(panel.scrollTop / pageHeight) + 1" in js
    assert "top: targetIndex * pageHeight" in js


def test_all_frontend_javascript_parses() -> None:
    for path in (APP_JS, ONBOARDING_JS, ARTIFACT_JS, MARKDOWN_JS, INTERVIEW_JS, TOPIC_INTENT_JS):
        result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True)
        assert result.returncode == 0, f"{path.name}: {result.stderr}"


def test_frontend_entry_uses_a_versioned_script_url_after_ui_updates() -> None:
    html = read(INDEX)

    assert '/js/app.js?v=' in html


def test_lesson_completion_uses_optional_homework_and_chat_without_output_boxes() -> None:
    html = read(INDEX)
    artifact = read(ARTIFACT_JS)
    css = read(STYLE)

    assert 'id="completionOutputs"' not in html
    assert "renderCompletionOutputs" not in artifact
    assert "completion-output" not in css
    assert "检查运行结果" not in artifact
    assert "课后练习" in artifact
    assert "右侧输入栏" in artifact
    assert 'id="lessonNotesPanel"' in html
    assert 'id="lessonReward"' in html
    assert "这一步已经真正掌握了" not in html
    assert "答对了，继续下一页" in html
    assert "loadLessonNotes" in artifact
    assert "learning-agent:notes-updated" in artifact


def test_unanswered_choice_pages_cannot_be_skipped_with_dots_or_next() -> None:
    artifact = read(ARTIFACT_JS)

    assert "firstBlockingCheck" in artifact
    assert "这一页需要先答对" in artifact
    assert "button.disabled = index > blockingIndex" in artifact


def test_run_script_prepares_workspace_on_first_start() -> None:
    source = (Path(__file__).parents[1] / "run.sh").read_text(encoding="utf-8")

    assert 'if [[ ! -d "workspace/releases/current" ]]' in source
    assert '"$PYTHON" -m backend.publish' in source
    assert 'if [[ ! -s ".secrets.env" ]]' in source
    assert "replace_with_your_deepseek_api_key" in source


def test_question_bank_has_real_anki_review_session_controls() -> None:
    html = read(INDEX)
    bank = read(INTERVIEW_JS)

    assert 'id="startBankReviewBtn"' in html
    assert 'id="bankDueCount"' in html
    assert 'id="reviewCardPanel"' in html
    assert 'id="revealReviewAnswerBtn"' in html
    assert 'id="reviewRatingActions"' in html
    assert "/api/practice/review/session" in bank
    assert "/api/practice/review/reveal" in bank
    assert "/api/practice/review/rate" in bank
    assert "没想起来" in bank
    assert "稍微有点困难" in bank
    assert "顺利" in bank


def test_chat_can_generate_supplemental_practice_into_the_bank() -> None:
    app = read(APP_JS)
    bank = read(INTERVIEW_JS)

    assert "isSupplementalPracticeRequest" in app
    assert 'fetch("/api/practice/supplemental/generate"' in app
    assert "openPracticeItem" in bank
    assert "startReview" in bank


def test_interview_course_shows_answered_short_answer_cards_on_final_slide() -> None:
    html = read(INDEX)
    artifact = read(ARTIFACT_JS)

    assert 'id="lessonInterviewPrompts"' in html
    assert "renderInterviewPrompts" in artifact
    assert "参考答案" in artifact
