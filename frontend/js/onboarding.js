"use strict";

(function createConversationalOnboarding(global) {
  const query = new URLSearchParams(global.location.search);
  const userId = query.get("user_id") || "yang";
  const EMPTY_SLOTS = {
    intent_family: null, topic: null, goal: null, desired_outcome: null,
    target_context: null, level_evidence: null, deadline: null,
    learning_scope: null, constraints: [], target_role: null, tech_stack: [],
    interview_question_source: "unknown", interview_question_count: 0,
  };
  const state = {
    active: false, stage: "topic", topic: "", topicType: "custom",
    goalRoute: "foundation_engineer", learningMode: "systematic", levelClaim: "zero",
    sessionMinutes: 25, deadlineDays: null, teachingPreference: "balanced",
    conceptScope: "not_applicable", slots: { ...EMPTY_SLOTS }, intentHistory: [],
    clarificationCount: 0, diagnostic: null, pendingAction: null, callbacks: {},
    busy: false, confirmationResult: null, generationId: null,
    existingProject: null, existingDecision: null,
  };
  const byId = (id) => document.getElementById(id);

  function request(path, payload, options = {}) {
    return fetch(path, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload), ...options,
    }).then(async (response) => {
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        const error = new Error(result.detail?.message || "连接暂时中断，你刚才的内容已保留。");
        error.recovery = result.detail?.recovery;
        throw error;
      }
      return result;
    });
  }

  function submission() {
    return {
      user_id: userId,
      learning_mode: state.learningMode,
      goal_route: state.goalRoute,
      level_claim: state.levelClaim,
      topic: { type: state.topicType, value: state.topic },
      session_minutes: state.sessionMinutes,
      deadline_days: state.deadlineDays,
      teaching_preference: state.teachingPreference,
      concept_scope: state.conceptScope,
    };
  }

  async function cancelActiveGeneration() {
    const generationId = state.generationId;
    if (!generationId) return false;
    state.generationId = null;
    try {
      const result = await request("/api/generations/cancel", {
        user_id: userId, generation_id: generationId,
      });
      return Boolean(result.cancelled);
    } catch (error) {
      // Restoring or switching the project also invalidates the lease server-side.
      return false;
    }
  }

  function addAgent(content) { state.callbacks.addAgent?.(content); }
  function addUser(content) { state.callbacks.addUser?.(content); }
  function setBusy(value) {
    state.busy = value;
    [...byId("inlineChoices").querySelectorAll("button")].forEach((button) => { button.disabled = value; });
    byId("sendBtn").disabled = value;
  }
  function clearError() { byId("onboardingError").hidden = true; }
  function showError(error) {
    byId("onboardingErrorText").textContent = error.message || "连接暂时中断，你刚才的内容已保留。";
    byId("retryOnboardingBtn").textContent = error.recovery === "restart_diagnosis" ? "重新开始诊断" : "重试";
    byId("onboardingError").hidden = false;
  }

  function intentChoice(option, index) {
    const row = document.createElement("div"); row.className = "intent-choice-row";
    const button = document.createElement("button"); button.type = "button"; button.className = "inline-choice";
    const badge = document.createElement("span"); badge.className = "inline-choice-index"; badge.textContent = String.fromCharCode(65 + index);
    const title = document.createElement("strong"); title.textContent = option.label;
    button.append(badge, title);
    button.addEventListener("click", () => choose(option));
    const detail = document.createElement("button"); detail.type = "button"; detail.className = "choice-detail";
    detail.setAttribute("aria-label", `了解「${option.label}」`);
    const detailIcon = document.createElement("i"); detailIcon.className = "bi bi-info-circle"; detailIcon.setAttribute("aria-hidden", "true");
    const tooltip = document.createElement("span"); tooltip.className = "choice-tooltip";
    tooltip.setAttribute("role", "tooltip"); tooltip.textContent = option.detail;
    detail.append(detailIcon, tooltip);
    detail.addEventListener("click", (event) => { event.stopPropagation(); row.classList.toggle("is-detail-open"); });
    row.append(button, detail);
    return row;
  }

  function regularChoice(option, index) {
    const button = document.createElement("button"); button.type = "button"; button.className = "inline-choice";
    const badge = document.createElement("span"); badge.className = "inline-choice-index"; badge.textContent = String.fromCharCode(65 + index);
    const title = document.createElement("strong"); title.textContent = option.label;
    button.append(badge, title);
    button.addEventListener("click", () => choose(option));
    return button;
  }

  function showChoices(options, { hint = "点一下就可以", progress = "", compact = false, intent = false } = {}) {
    const safeOptions = intent ? options.slice(0, 3) : options.slice(0, 10);
    byId("choiceTrayHint").textContent = hint;
    byId("choiceProgress").textContent = progress;
    byId("inlineChoices").replaceChildren(...safeOptions.map((option, index) => (
      intent ? intentChoice(option, index) : regularChoice(option, index)
    )));
    byId("choiceTray").classList.toggle("is-plan-confirmation", compact);
    byId("choiceTray").classList.toggle("is-intent-question", intent);
    byId("choiceTray").hidden = false;
  }

  function hideChoices() {
    byId("choiceTray").hidden = true;
    byId("choiceTrayQuestion").hidden = true;
    byId("choiceTrayQuestion").textContent = "";
    byId("choiceTray").classList.remove("is-plan-confirmation", "is-intent-question");
    byId("inlineChoices").replaceChildren();
  }

  function askTopic() {
    state.stage = "topic";
    hideChoices();
    addAgent("你现在想解决什么？直接输入就行。可以是一个概念、一个项目、一场面试，也可以是“我想用 LangGraph 做客服 Agent”这样的具体结果。");
    byId("chatInput").placeholder = "例如：下周面试 Java 后端，或用 LangGraph 做客服 Agent…";
    byId("chatInput").focus();
  }

  function recentIntentHistory() { return state.intentHistory.slice(-8); }

  async function restoreIntentState() {
    try {
      const response = await fetch(`/api/onboarding/intent-state?user_id=${encodeURIComponent(userId)}`);
      if (!response.ok) return false;
      const persisted = await response.json();
      state.slots = { ...EMPTY_SLOTS, ...(persisted.slots || {}) };
      state.topic = state.slots.topic || "";
      if (persisted.action === "interview_bank_intake") {
        if (Number(state.slots.interview_question_count || 0) > 0) {
          addAgent(`已恢复 ${state.slots.interview_question_count} 道已入库面试题，继续生成针对性计划。`);
          await analyzeIntent(
            `已经收录 ${state.slots.interview_question_count} 道真实面试题，请生成针对性计划`,
            { recordUser: false },
          );
          return true;
        }
        state.stage = "interview_intake";
        addAgent("继续上次没有完成的建档：把你收集的面试题直接粘贴到输入框，我会先去重入库，再生成针对性 Plan。");
        byId("chatInput").placeholder = "直接粘贴面试题，支持编号列表或多行问题…";
        return true;
      }
      if (persisted.action !== "clarify" || !persisted.question?.options?.length) return false;
      state.stage = "clarifying";
      state.clarificationCount = 1;
      addAgent(`继续上次没有完成的建档：${persisted.question.prompt}`);
      showChoices(persisted.question.options, {
        hint: "选一个最接近的；也可以直接输入修改或补充",
        progress: "已恢复上次进度",
        intent: true,
      });
      byId("chatInput").placeholder = "也可以直接输入你真正想要的结果…";
      return true;
    } catch {
      return false;
    }
  }

  async function findExistingProject(topic) {
    const query = new URLSearchParams({ user_id: userId, topic });
    const response = await fetch(`/api/projects/match?${query.toString()}`);
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail?.message || "暂时无法检查已有学习项目。");
    return result.project || null;
  }

  function applyIntentDecision(decision) {
    state.slots = { ...EMPTY_SLOTS, ...(decision.slots || {}) };
    if (state.slots.topic) state.topic = state.slots.topic;
    if (!decision.onboarding) return;
    state.goalRoute = decision.onboarding.goal_route;
    state.learningMode = decision.onboarding.learning_mode;
    state.levelClaim = decision.onboarding.level_claim;
    state.sessionMinutes = decision.onboarding.session_minutes;
    state.conceptScope = decision.onboarding.concept_scope;
    state.topicType = decision.onboarding.topic_type || "custom";
    state.deadlineDays = decision.onboarding.deadline_days ?? null;
    state.teachingPreference = decision.onboarding.teaching_preference || "balanced";
  }

  async function analyzeIntent(text, { recordUser = true } = {}) {
    const message = text.trim();
    if (!message) return;
    if (recordUser) { addUser(message); state.intentHistory.push({ role: "user", content: message }); }
    const priorHistory = recentIntentHistory().slice(0, -1);
    setBusy(true); clearError(); hideChoices(); state.stage = "analyzing";
    state.pendingAction = () => analyzeIntent(message, { recordUser: false });
    global.LearningActivity?.start("正在理解你的需求", "正在结合你刚才的话和前面对话判断下一步。", [
      "正在区分是答疑、面试、项目还是系统学习…",
      "正在检查你已经说过哪些信息，避免重复追问…",
    ]);
    try {
      const decision = await request("/api/onboarding/intent", {
        user_id: userId, message, history: priorHistory, slots: state.slots,
        has_active_project: Boolean(state.callbacks.hasActiveProject),
        clarification_count: state.clarificationCount,
      });
      applyIntentDecision(decision);
      state.intentHistory.push({ role: "assistant", content: decision.question?.prompt || decision.summary });
      if (decision.action === "clarify") {
        state.stage = "clarifying"; state.clarificationCount += 1;
        addAgent(decision.question.prompt);
        showChoices(decision.question.options, {
          hint: "选一个最接近的；也可以直接打字修改或补充",
          progress: "正在理解需求", intent: true,
        });
        byId("chatInput").placeholder = "不想选也没关系，直接输入你真正想要的结果…";
        global.LearningActivity?.finish("还差一个关键决定", "点选项或直接打字都可以。");
        return;
      }
      if (decision.action === "ready_for_plan") {
        const existingProject = await findExistingProject(state.topic);
        if (existingProject) {
          state.stage = "existing_project";
          state.existingProject = existingProject;
          state.existingDecision = decision;
          addAgent(`你已经有一个「${existingProject.topic}」学习项目，不需要再建一个重复项目。`);
          showChoices([
            { id: "continue-existing", label: "继续已有项目", value: "continue_existing", detail: `从现有 ${existingProject.progress || 0}% 进度继续` },
            { id: "merge-existing", label: "把新目标合并进去", value: "merge_existing", detail: "保留已完成进度，调整后续 Plan" },
          ], { hint: "选一个；想换主题也可以直接输入", progress: "已有同主题项目", intent: true });
          global.LearningActivity?.finish("找到了已有学习项目", "继续学习或把新目标合并进去，不会创建副本。");
          return;
        }
        hideChoices();
        await state.callbacks.onIntentReady?.(decision);
        if (state.levelClaim === "zero" || state.goalRoute === "concept_clarity") await confirm();
        else await beginDiagnosis();
        return;
      }
      if (decision.action === "interview_bank_intake") {
        state.stage = "interview_intake";
        hideChoices();
        addAgent("把你收集的面试题直接粘贴到输入框即可；可以一次发多道，我会先去重收录，再生成针对性 Plan。");
        byId("chatInput").placeholder = "直接粘贴面试题，支持编号列表或多行问题…";
        global.LearningActivity?.finish("等待你粘贴面试题", "题目会先保存到你的个人题库。 ");
        return;
      }
      state.active = false; hideChoices();
      await state.callbacks.onAnswerInContext?.(message);
      global.LearningActivity?.finish("已切换到对应处理方式", "不会为这句话新建学习计划。");
    } catch (error) {
      showError(error);
      global.LearningActivity?.finish("意图还没有分析完成", "你的输入和已填信息都还在，可以直接重试。");
    } finally { setBusy(false); }
  }

  function renderDiagnostic(result) {
    state.stage = "diagnostic"; state.diagnostic = result;
    byId("choiceTrayQuestion").textContent = result.question.prompt;
    byId("choiceTrayQuestion").hidden = false;
    showChoices(result.question.options.map((option) => ({ ...option, value: option.id })), {
      hint: "真实选择题，直接点击", progress: `诊断 ${result.answered_count + 1} / 最多 4`,
    });
  }

  async function beginDiagnosis() {
    setBusy(true); clearError(); state.pendingAction = beginDiagnosis;
    global.LearningActivity?.start("正在校准起点", "只用几道点击题找到合适的第一课。");
    try {
      renderDiagnostic(await request("/api/onboarding/start", submission()));
      global.LearningActivity?.finish("第一题准备好了", "直接点击输入框上方的选项即可。");
    } catch (error) { showError(error); }
    finally { setBusy(false); }
  }

  async function answerDiagnostic(option) {
    setBusy(true); clearError(); state.pendingAction = beginDiagnosis; addUser(option.label);
    global.LearningActivity?.start("正在判断你的起点", "这会决定哪些内容快进、哪些内容慢讲。");
    try {
      const next = await request("/api/diagnostics/answer", {
        user_id: userId, session_id: state.diagnostic.session_id,
        question_id: state.diagnostic.question.id, selected_option_id: option.value,
      });
      if (next.complete) await confirm({ diagnostic_session_id: next.session_id });
      else { renderDiagnostic(next); global.LearningActivity?.finish("下一道诊断题已准备好", "再点一题，就能更准确地开始。"); }
    } catch (error) { showError(error); }
    finally { setBusy(false); }
  }

  function planReviewChoices() {
    const confirmChoice = { label: "确认并开始", value: "confirm_plan", description: state.goalRoute === "concept_clarity" ? "开始概念讲解" : "生成第一章讲义" };
    return [confirmChoice];
  }

  async function confirm(extra = {}) {
    setBusy(true); clearError(); hideChoices(); state.pendingAction = () => confirm(extra);
    addAgent("路线已经清楚了。我会先生成完整 `plan.md` 给你确认，确认后才开始第一章。");
    global.LearningActivity?.startPlanGeneration?.();
    try {
      const result = await request("/api/onboarding/confirm", { ...submission(), ...extra });
      state.generationId = result.generation_id;
      const controller = new AbortController();
      const personalizationTimeout = window.setTimeout(() => controller.abort(), 660000);
      try {
        const personalized = await request("/api/plans/personalize", {
          ...submission(), generation_id: result.generation_id,
        }, { signal: controller.signal });
        if (!personalized.personalized) throw new Error(personalized.user_message || "模型还没有生成合格的详细课程大纲，请点击重试。");
        state.generationId = null;
        state.confirmationResult = result; state.stage = "plan_review";
        await state.callbacks.onPlanReady?.(personalized);
        addAgent(state.goalRoute === "concept_clarity"
          ? "这份短方案已经显示。确认后我就开始概念讲解；不会再问时长或做起点诊断。"
          : "完整计划已经显示。先看看是否符合你的目标；需要修改就直接在下面说。");
        showChoices(planReviewChoices(), { hint: "满意就开始；要改直接在下面说", compact: true });
        global.LearningActivity?.finish("专属大纲已生成", "请先阅读并确认，课程不会自动开始。");
      } finally { window.clearTimeout(personalizationTimeout); }
    } catch (error) {
      await cancelActiveGeneration();
      const message = error?.name === "AbortError" || /aborted/i.test(error?.message || "")
        ? "详细课程研究与生成超过 11 分钟，请重试；你刚才的主题和目标都已保留。"
        : error?.message || "详细课程暂时没有生成成功，请重试。";
      showError(new Error(message));
      global.LearningActivity?.finish("生成暂时中断", "你的选择已保留，可以直接重试。");
      await state.callbacks.onFailed?.(error);
    } finally { setBusy(false); }
  }

  async function confirmPlan() {
    setBusy(true); clearError(); hideChoices(); state.pendingAction = confirmPlan;
    global.LearningActivity?.start("正在锁定学习计划", "确认后马上为你准备第一章。");
    try {
      await request("/api/plans/confirm", { user_id: userId }); state.active = false;
      await state.callbacks.onConfirmed?.(state.confirmationResult || {});
      global.LearningActivity?.finish("学习计划已确认", "第一章已经开始生成。");
    } catch (error) { showError(error); global.LearningActivity?.finish("计划还没有确认", "当前草案仍然保留，可以重试。"); }
    finally { setBusy(false); }
  }

  async function revisePlan(feedback) {
    setBusy(true); clearError(); hideChoices(); state.pendingAction = () => revisePlan(feedback);
    global.LearningActivity?.start("正在按你的意见调整 Plan", "已完成的路线不会被清空。");
    try {
      const revised = await request("/api/plans/revise", { ...submission(), feedback });
      if (!revised.revised) throw new Error("这次修改没有生成合格的新计划，请换一种说法再试。");
      state.stage = "plan_review"; await state.callbacks.onPlanReady?.(revised);
      addAgent("计划已经按你的意见更新。请再看一遍，满意后点确认；还可以继续调整。");
      showChoices(planReviewChoices(), { hint: "满意就开始；还要改就继续输入", compact: true });
      global.LearningActivity?.finish("Plan 已更新", "请阅读新版计划并确认。");
    } catch (error) { showError(error); global.LearningActivity?.finish("计划修改暂时中断", "旧草案还在，可以直接重试。"); }
    finally { setBusy(false); }
  }

  async function choose(option) {
    if (state.busy) return;
    if (state.stage === "diagnostic") { await answerDiagnostic(option); return; }
    if (state.stage === "plan_review") { addUser(option.label); if (option.value === "confirm_plan") await confirmPlan(); return; }
    if (state.stage === "existing_project") {
      addUser(option.label); hideChoices(); setBusy(true);
      try {
        if (option.value === "continue_existing") {
          state.active = false;
          await state.callbacks.onContinueExistingProject?.(state.existingProject);
        } else if (option.value === "merge_existing") {
          await state.callbacks.onMergeExistingProject?.(state.existingProject);
          await revisePlan(`保留已有学习进度，并合并这次的新目标：${state.existingDecision?.summary || state.slots.desired_outcome || state.slots.goal}`);
        }
      } catch (error) { showError(error); }
      finally { setBusy(false); }
      return;
    }
    if (state.stage === "clarifying") {
      addUser(option.label); state.intentHistory.push({ role: "user", content: option.label });
      await analyzeIntent(option.label, { recordUser: false });
    }
  }

  async function handleText(value) {
    const text = value.trim();
    if (!state.active || !text || state.busy) return false;
    if (state.stage === "plan_review") { addUser(text); await revisePlan(text); }
    else if (state.stage === "interview_intake") {
      addUser(text); setBusy(true); clearError();
      global.LearningActivity?.start("正在收录面试题", "正在去重、分类并保存到你的个人题库。 ");
      try {
        const payload = await request("/api/interview/intake", {
          user_id: userId, raw_text: text, source: "chat",
        });
        state.slots.interview_question_source = "has_questions";
        state.slots.interview_question_count = Number(payload.intake?.source_count || 0);
        addAgent(`已收录 ${payload.intake?.source_count || 0} 道题，其中新增 ${payload.intake?.new_count || 0} 道。现在根据这些题生成学习方案。`);
        await analyzeIntent(`已经收录 ${state.slots.interview_question_count} 道真实面试题，请生成针对性计划`, { recordUser: false });
      } catch (error) {
        byId("chatInput").value = text;
        state.pendingAction = () => {
          byId("chatInput").value = "";
          handleText(text);
        };
        showError(error);
      }
      finally { setBusy(false); }
    }
    else if (state.stage === "diagnostic") {
      addUser(text);
      addAgent("这几道是用来定起点的点击题，直接点上方选项就行；做完后继续用输入框问任何问题。");
    } else await analyzeIntent(text);
    return true;
  }

  function begin(callbacks, initialTopic = "") {
    Object.assign(state, {
      callbacks, active: true, stage: "topic", topic: "", topicType: "custom",
      goalRoute: "foundation_engineer", learningMode: "systematic", levelClaim: "zero",
      sessionMinutes: 25, deadlineDays: null, teachingPreference: "balanced",
      conceptScope: "not_applicable", slots: { ...EMPTY_SLOTS }, intentHistory: [],
      clarificationCount: 0, diagnostic: null, pendingAction: null, confirmationResult: null,
      generationId: null, existingProject: null, existingDecision: null,
    });
    if (initialTopic.trim()) analyzeIntent(initialTopic);
    else if (callbacks.restorePersistedIntent) {
      restoreIntentState().then((restored) => { if (!restored) askTopic(); });
    } else askTopic();
  }

  function stop() { state.active = false; hideChoices(); }

  document.addEventListener("DOMContentLoaded", () => {
    byId("retryOnboardingBtn").addEventListener("click", () => state.pendingAction?.());
  }, { once: true });

  global.OnboardingController = {
    begin, handleText, stop, cancelActiveGeneration,
    get active() { return state.active; }, userId,
  };
}(window));
