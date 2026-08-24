"use strict";

(function createLearningApp() {
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];
  const USER_ID = window.OnboardingController?.userId || new URLSearchParams(window.location.search).get("user_id") || "yang";
  const PRIVATE_DATA_RESET_VERSION = "20260822-project-reset-v1";
  const PRIVATE_DATA_RESET_KEY = "learning-agent.private-data-reset";
  function resetLegacyClientRecords() {
    if (localStorage.getItem(PRIVATE_DATA_RESET_KEY) === PRIVATE_DATA_RESET_VERSION) return;
    Object.keys(localStorage).forEach((key) => {
      if (key.startsWith("learning-agent.messages.")) localStorage.removeItem(key);
    });
    localStorage.setItem(PRIVATE_DATA_RESET_KEY, PRIVATE_DATA_RESET_VERSION);
  }
  resetLegacyClientRecords();
  const STORAGE_MESSAGES = `learning-agent.messages.v3.${USER_ID}`;
  const STORAGE_PREVIOUS_MESSAGES = `learning-agent.messages.previous.v1.${USER_ID}`;
  const PROJECT_LONG_PRESS_MS = 600;
  const PROJECT_SWIPE_THRESHOLD = 64;
  const state = {
    context: null,
    messages: [],
    archivedMessages: loadJSON(STORAGE_MESSAGES, []),
    previousMessages: loadJSON(STORAGE_PREVIOUS_MESSAGES, []),
    guidedFinalPages: new Set(),
    onboardingSnapshot: null,
    projectSnapshotId: null,
    startupGateActive: false,
    busy: false,
    ready: false,
    projects: [],
    selectedProject: null,
  };

  function loadJSON(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } }
  function saveMessages() {
    state.archivedMessages = state.messages.slice(-50);
    localStorage.setItem(STORAGE_MESSAGES, JSON.stringify(state.archivedMessages));
  }
  function setText(selector, value) { const node = $(selector); if (node) node.textContent = value ?? ""; }
  function showToast(message) {
    const toast = $("#toast"); toast.textContent = message; toast.hidden = false;
    clearTimeout(showToast.timer); showToast.timer = window.setTimeout(() => { toast.hidden = true; }, 2200);
  }
  let activityPhaseTimer = null;
  let activityProgressTimer = null;
  let activityRun = null;
  const ACTIVITY_DEFAULTS = { general: 15, intent: 8, plan: 240, lesson: 180 };
  function storedEstimate(operation, fallbackSeconds) {
    const samples = loadJSON(`learning-agent.duration.v1.${operation}`, []).filter((value) => Number.isFinite(value)).slice(-5).sort((a, b) => a - b);
    return (samples.length ? samples[Math.floor(samples.length / 2)] : fallbackSeconds) * 1000;
  }
  function renderActivityProgress() {
    if (!activityRun || !window.ActivityProgress) return;
    const result = window.ActivityProgress.estimate(Date.now() - activityRun.startedAt, activityRun.estimateMs);
    $("#activityProgressFill").style.width = `${result.percent}%`;
    setText("#activityProgressText", result.label);
  }
  function showActivity(label, detail = "这一步完成后会告诉你接下来做什么。", phases = [], options = {}) {
    const panel = $("#activityStatus");
    setText("#activityStatusLabel", label); setText("#activityStatusDetail", detail);
    setText("#activityCurrentStep", `当前：${detail.replace(/…+$/, "")}`);
    panel.hidden = false; panel.classList.add("is-active");
    clearTimeout(showActivity.timer);
    window.clearInterval(activityPhaseTimer);
    window.clearInterval(activityProgressTimer);
    const operation = options.operation || "general";
    activityRun = {
      operation,
      startedAt: Date.now(),
      estimateMs: storedEstimate(operation, options.estimateSeconds || ACTIVITY_DEFAULTS[operation] || ACTIVITY_DEFAULTS.general),
    };
    $("#activityProgressFill").style.width = "4%";
    renderActivityProgress();
    activityProgressTimer = window.setInterval(renderActivityProgress, 1000);
    if (phases.length) {
      let phaseIndex = 0;
      activityPhaseTimer = window.setInterval(() => {
        phaseIndex = (phaseIndex + 1) % phases.length;
        setText("#activityCurrentStep", `当前：${phases[phaseIndex].replace(/…+$/, "")}`);
      }, 2800);
    }
  }
  function finishActivity(label, detail) {
    const panel = $("#activityStatus");
    if (label) { setText("#activityStatusLabel", label); setText("#activityStatusDetail", detail || "下一步已经为你准备好了。"); }
    panel.classList.remove("is-active");
    window.clearInterval(activityPhaseTimer);
    activityPhaseTimer = null;
    window.clearInterval(activityProgressTimer);
    activityProgressTimer = null;
    if (activityRun) {
      const durationSeconds = Math.max(1, Math.round((Date.now() - activityRun.startedAt) / 1000));
      const key = `learning-agent.duration.v1.${activityRun.operation}`;
      const samples = loadJSON(key, []).filter((value) => Number.isFinite(value)).slice(-4);
      localStorage.setItem(key, JSON.stringify([...samples, durationSeconds]));
    }
    $("#activityProgressFill").style.width = "100%";
    setText("#activityProgressText", "本次等待已结束");
    setText("#activityCurrentStep", "当前：已完成");
    activityRun = null;
    clearTimeout(showActivity.timer);
    showActivity.timer = window.setTimeout(() => { panel.hidden = true; }, 2200);
  }
  function startPlanGeneration() {
    showActivity("正在生成你的学习大纲", "正在判断你真正要达到的结果…", [
      "正在核对可靠资料和必要知识点…",
      "正在根据你的目标排列学习顺序…",
      "正在检查大纲是否有跳步或遗漏…",
      "正在把结果整理成可确认的 Plan…",
    ], { operation: "plan", estimateSeconds: 240 });
  }
  function startLessonGeneration() {
    showActivity("正在生成完整章节", "正在按大纲生成讲解、中文注释代码和选择题…", [
      "正在拆分本章知识点和顺序…",
      "正在生成逐页讲解与代码演示…",
      "正在检查选择题答案和中文注释…",
      "正在整理课后练习和项目目录…",
    ], { operation: "lesson", estimateSeconds: 180 });
  }
  window.LearningActivity = { start: showActivity, startPlanGeneration, startLessonGeneration, finish: finishActivity };

  function updateOutlinePageLabel() {
    const panel = $("#outlinePanel"); const label = $("#outlinePageLabel");
    if (!panel || !label) return;
    const pageHeight = Math.max(panel.clientHeight, 1);
    const pages = Math.max(1, Math.ceil(panel.scrollHeight / pageHeight));
    const current = Math.min(pages, Math.round(panel.scrollTop / pageHeight) + 1);
    label.textContent = `大纲 ${current} / ${pages}`;
    $("#outlinePreviousBtn").disabled = panel.scrollTop <= 1;
    $("#outlineNextBtn").disabled = panel.scrollTop + panel.clientHeight >= panel.scrollHeight - 1;
  }
  function pageOutline(direction) {
    const panel = $("#outlinePanel");
    const pageHeight = Math.max(panel.clientHeight, 1);
    const pages = Math.max(1, Math.ceil(panel.scrollHeight / pageHeight));
    const currentIndex = Math.round(panel.scrollTop / pageHeight);
    const targetIndex = Math.max(0, Math.min(pages - 1, currentIndex + direction));
    panel.scrollTo({ top: targetIndex * pageHeight, behavior: "smooth" });
    window.setTimeout(updateOutlinePageLabel, 320);
  }

  function celebrateVerifiedSuccess(result) {
    if (!(result.correct === true && result.verified === true)) return;
    const layer = $("#celebrationLayer");
    const palette = ["#bd684d", "#58724f", "#d5a83f", "#7893aa", "#24231f"];
    const pieces = Array.from({ length: 28 }, (_, index) => {
      const piece = document.createElement("i");
      piece.className = "confetti-piece";
      piece.style.left = `${4 + ((index * 17) % 92)}%`;
      piece.style.setProperty("--confetti-color", palette[index % palette.length]);
      piece.style.setProperty("--confetti-delay", `${(index % 8) * 34}ms`);
      piece.style.setProperty("--confetti-drift", `${((index % 5) - 2) * 34}px`);
      return piece;
    });
    layer.replaceChildren(...pieces); layer.hidden = false;
    const praise = $("#praiseToast"); praise.hidden = false;
    clearTimeout(celebrateVerifiedSuccess.timer);
    celebrateVerifiedSuccess.timer = window.setTimeout(() => { layer.hidden = true; praise.hidden = true; layer.replaceChildren(); }, 2450);
  }

  function messageElement(message, streaming = false) {
    const item = document.createElement("article");
    item.className = `message ${message.role === "user" ? "user" : "agent"}${streaming ? " is-streaming" : ""}`;
    const content = document.createElement("div"); content.className = "markdown-body";
    if (message.role === "user") content.textContent = message.content;
    else {
      content.innerHTML = window.MarkdownRenderer.render(message.content);
      window.queueMicrotask(() => window.MarkdownRenderer.hydrate(content));
    }
    if (message.role !== "user") {
      const label = document.createElement("span"); label.className = "message-label"; label.textContent = "Learning Agent";
      item.append(label);
    }
    item.append(content);
    return item;
  }

  function renderMessages() {
    const feed = $("#chatFeed"); feed.replaceChildren(...state.messages.map((message) => messageElement(message)));
    feed.scrollTop = feed.scrollHeight;
  }
  function addMessage(role, content, persist = true) {
    const message = { role, content };
    state.messages.push(message);
    $("#chatFeed").append(messageElement(message));
    $("#chatFeed").scrollTop = $("#chatFeed").scrollHeight;
    if (persist) saveMessages();
  }

  function parseSSEBlock(block) {
    let event = "message"; const dataLines = [];
    block.split("\n").forEach((line) => { if (line.startsWith("event:")) event = line.slice(6).trim(); if (line.startsWith("data:")) dataLines.push(line.slice(5).trim()); });
    if (!dataLines.length) return null;
    try { return { event, data: JSON.parse(dataLines.join("\n")) }; } catch { return null; }
  }

  function isLessonRevisionRequest(message) {
    return /(PPT|讲义|课件|这一页|这节课)/i.test(message) && /(修改|重做|重新生成|再生成|太浅|太深|太难|太长|看不懂|加.*图|加.*代码)/.test(message);
  }

  function isSupplementalPracticeRequest(message) {
    return /(再出|多出|追加|多练|再练).{0,8}(题|练习)|针对.{0,8}(题|练习)/.test(message);
  }

  async function generateSupplementalPractice(instruction) {
    state.busy = true;
    addMessage("user", instruction);
    $("#sendBtn").disabled = true;
    window.LearningActivity.start("正在生成针对性练习", "正在读取出题规则并检查每道题的答案…");
    try {
      const response = await fetch("/api/practice/supplemental/generate", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: USER_ID,
          module: state.context?.current_task || state.context?.topic || instruction,
          level: state.context?.level || "beginner",
          count: 3,
        }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || "练习题暂时没有生成成功");
      addMessage("agent", `已把 **${result.added_count || 0} 道针对性练习**加入题库。现在可以直接开始做；重复题不会再次收录。`);
      await window.InterviewBankController?.load?.();
      await window.InterviewBankController?.startReview?.();
      window.LearningActivity.finish("针对性练习已准备好", "题目已经加入题库，并打开复习卡。 ");
    } catch (error) {
      addMessage("agent", `这次练习没有生成成功：${error.message}。你可以直接重新发送刚才的要求。`);
      window.LearningActivity.finish("练习暂时没有生成", "你的要求已经保留，可以直接重试。 ");
    } finally {
      state.busy = false;
      $("#sendBtn").disabled = false;
    }
  }

  async function reviseCurrentLesson(instruction) {
    state.busy = true;
    addMessage("user", instruction);
    $("#sendBtn").disabled = true;
    window.LearningActivity.start("正在按你的要求重做讲义", "Agent 会读取 lesson-revision Skill；新版本通过校验后才替换旧讲义。 ");
    try {
      const response = await fetch("/api/lesson/remediate", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: USER_ID, remediation: instruction, force: true }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail?.message || "讲义修改暂时没有完成。 ");
      await window.ArtifactController.loadCurrentLesson();
      addMessage("agent", "讲义已经按你的要求重新生成，并从第 1 页打开。你可以继续告诉我哪里太浅、太快，或需要更多图和代码。");
      window.LearningActivity.finish("新版讲义已准备好", "新版本已经通过结构校验，可以从第 1 页重新查看。 ");
    } catch (error) {
      addMessage("agent", `这次没有生成出合格的新讲义：${error.message}\n\n旧讲义仍然保留，你可以换一种更具体的说法再试。`);
      window.LearningActivity.finish("讲义没有被替换", "旧讲义仍然保留，你的修改意见也在对话里。 ");
    } finally {
      state.busy = false;
      $("#sendBtn").disabled = false;
    }
  }

  async function sendMessage(message, { echoUser = true } = {}) {
    const value = message.trim();
    if (!value || state.busy) return;
    if (state.ready && isSupplementalPracticeRequest(value)) {
      await generateSupplementalPractice(value);
      return;
    }
    if (state.ready && isLessonRevisionRequest(value)) {
      await reviseCurrentLesson(value);
      return;
    }
    state.busy = true;
    const history = state.messages.slice(-12);
    if (!echoUser && history.at(-1)?.role === "user" && history.at(-1)?.content === value) history.pop();
    if (echoUser) addMessage("user", value);
    const assistant = { role: "agent", content: "" };
    const node = messageElement(assistant, true);
    $("#chatFeed").append(node);
    const output = node.querySelector(".markdown-body");
    $("#sendBtn").disabled = true; setText("#connectionText", "正在回应");
    window.LearningActivity.start("正在组织讲解", "教练正在结合你的当前进度生成回复。");
    try {
      const response = await fetch("/api/chat/stream", {
        method: "POST", headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({ user_id: USER_ID, message: value, history, lesson_id: window.ArtifactController?.currentLessonId?.() || null }),
      });
      if (!response.ok || !response.body) throw new Error("连接暂时中断，请稍后再试。");
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = "";
      while (true) {
        const { value: chunk, done } = await reader.read();
        buffer += decoder.decode(chunk || new Uint8Array(), { stream: !done });
        const blocks = buffer.split("\n\n"); buffer = blocks.pop() || "";
        blocks.forEach((block) => {
          const packet = parseSSEBlock(block); if (!packet) return;
          if (packet.event === "message.delta") { assistant.content += packet.data.text || ""; output.innerHTML = window.MarkdownRenderer.render(assistant.content); }
          if (packet.event === "notes.updated") document.dispatchEvent(new CustomEvent("learning-agent:notes-updated", { detail: packet.data }));
          if (packet.event === "error") throw new Error(packet.data.message || "学习引擎暂时不可用。");
        });
        $("#chatFeed").scrollTop = $("#chatFeed").scrollHeight;
        if (done) break;
      }
      node.classList.remove("is-streaming");
      window.MarkdownRenderer.hydrate(output);
      state.messages.push(assistant); saveMessages();
      window.LearningActivity.finish("讲解已送达", "可以继续提问，或按讲义里的下一步操作。 ");
    } catch (error) {
      node.remove(); addMessage("agent", `连接没有成功：${error.message}\n\n你刚才的内容还在，可以直接重试。`);
      window.LearningActivity.finish("这次没有完成", "你的输入已保留，点击发送即可重试。");
    } finally {
      state.busy = false; $("#sendBtn").disabled = false; setText("#connectionText", "已连接");
    }
  }

  function renderLearningContext(context) {
    state.context = context;
    const plan = context.plan || {};
    const stages = plan.stages?.length ? plan.stages : [{ title: "阶段 1：建立直觉", status: "active" }];
    const activeIndex = Math.max(0, stages.findIndex((stage) => stage.status === "active"));
    const knowledge = context.knowledge_progress || {};
    const progress = knowledge.total
      ? Math.round((Number(knowledge.completed || 0) / Number(knowledge.total)) * 100)
      : Math.round((activeIndex / Math.max(stages.length, 1)) * 100);
    setText("#planTitle", plan.title || `${context.topic || "我的"}学习计划`);
    setText("#planMeta", "计划会根据练习证据持续调整");
    setText("#planProgress", `${progress}%`); $("#progressFill").style.width = `${progress}%`;
    setText("#completedLessons", knowledge.total ? `${knowledge.completed || 0} / ${knowledge.total} 知识点` : `${activeIndex} / ${stages.length} 阶段`);
    setText("#masteryText", `掌握 ${progress}%`);
    setText("#remainingTime", `预计还需 ${context.session_minutes || 25} 分钟`);
    setText("#dueReviewCount", `${context.due_review_count || 0} 个知识点`);
    setText("#coachContext", context.current_task || `正在学习：${context.topic}`);
    $("#stageList").replaceChildren(...stages.map((stage, index) => {
      const item = document.createElement("li");
      item.className = `stage-item ${index < activeIndex ? "is-complete" : index === activeIndex ? "is-active" : ""}`;
      const marker = document.createElement("span"); marker.className = "stage-marker";
      const body = document.createElement("div"); const title = document.createElement("h3"); title.textContent = stage.title;
      const status = document.createElement("p"); status.textContent = index < activeIndex ? "已完成" : index === activeIndex ? "正在学习" : "待解锁";
      body.append(title, status); item.append(marker, body); return item;
    }));
    window.requestAnimationFrame(updateOutlinePageLabel);
    $("#planDocument").innerHTML = window.MarkdownRenderer.render(plan.content || "计划正在生成。");
    window.MarkdownRenderer.hydrate($("#planDocument"));
  }

  function renderPlanConversationMessage(markdown, conceptPlan) {
    $("#planConversationMessage")?.remove();
    const prefix = conceptPlan
      ? "我把这个概念的学习顺序整理好了："
      : "我把建议的学习路线整理好了：";
    const node = messageElement({
      role: "agent",
      content: `${prefix}\n\n${markdown}\n\n---\n\n需要调整时，直接在下面告诉我要增加、删除或改变什么。`,
    });
    node.id = "planConversationMessage";
    node.classList.add("plan-conversation-message");
    $("#chatFeed").append(node);
    node.scrollIntoView({ block: "start", behavior: "smooth" });
  }

  function removePlanConversationMessage() {
    $("#planConversationMessage")?.remove();
  }

  async function showPlanReview(planResult = null) {
    let context = state.context;
    try {
      const response = await fetch(`/api/learning-context?user_id=${encodeURIComponent(USER_ID)}`);
      if (response.ok) context = await response.json();
    } catch { /* The generated markdown in the response remains available. */ }
    if (context) renderLearningContext(context);
    const markdown = planResult?.plan_markdown || context?.plan?.content || "计划正在生成。";
    const conceptPlan = context?.goal_route === "concept_clarity";
    $("#appShell").classList.remove("is-chat-first");
    $("#appShell").classList.add("is-onboarding");
    renderPlanConversationMessage(markdown, conceptPlan);
    $("#promptChips").hidden = true;
    setText("#coachContext", "正在确认学习计划");
  }

  function projectTimeLabel(updatedAt) {
    const date = new Date(updatedAt || "");
    if (Number.isNaN(date.getTime())) return "随时可以继续";
    return `上次 ${new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric" }).format(date)}`;
  }

  async function activateStoredProject(project) {
    if (!project.current) {
      const response = await fetch("/api/projects/switch", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: USER_ID, project_id: project.id }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail?.message || "切换学习项目失败，请重试。");
      state.messages = [];
      renderMessages();
      await refreshProjectArchive();
    }
    const contextResponse = await fetch(`/api/learning-context?user_id=${encodeURIComponent(USER_ID)}`);
    if (contextResponse.ok) {
      state.context = await contextResponse.json();
      renderLearningContext(state.context);
    }
  }

  async function openLearningProject(project, button = null) {
    if (button) button.disabled = true;
    showActivity(project.current ? "正在打开当前学习" : "正在切换学习项目", "大纲、讲义和进度会一起恢复。");
    try {
      await activateStoredProject(project);
      state.startupGateActive = false;
      setProjectSwitcherOpen(false);
      window.OnboardingController.stop?.();
      await enterLearning();
    } catch (error) {
      if (button) button.disabled = false;
      finishActivity("项目没有打开", "原项目仍然保留，可以稍后重试。");
      showToast(error.message);
    }
  }

  function setProjectSwitcherOpen(open) {
    $("#projectMobileBtn").setAttribute("aria-expanded", String(open));
    $("#appShell").classList.toggle("is-project-drawer-open", open && window.matchMedia("(max-width: 860px)").matches);
  }

  function toggleProjectSwitcher() {
    setProjectSwitcherOpen(!$("#appShell").classList.contains("is-project-drawer-open"));
  }

  function closeProjectContextMenu() {
    $("#projectContextMenu").hidden = true;
  }

  function openProjectContextMenu(project, x, y) {
    state.selectedProject = project;
    const menu = $("#projectContextMenu");
    menu.style.left = `${Math.min(x, window.innerWidth - 170)}px`;
    menu.style.top = `${Math.min(y, window.innerHeight - 60)}px`;
    menu.hidden = false;
  }

  function requestProjectDeletion(project) {
    state.selectedProject = project;
    closeProjectContextMenu();
    setText("#projectDeleteTitle", `删除「${project.topic || "未命名项目"}」？`);
    $("#projectDeleteDialog").showModal();
  }

  function bindProjectGestures(row, project) {
    let startX = 0; let startY = 0; let longPressTimer = null;
    const cancelLongPress = () => { window.clearTimeout(longPressTimer); longPressTimer = null; };
    row.addEventListener("contextmenu", (event) => {
      event.preventDefault(); openProjectContextMenu(project, event.clientX, event.clientY);
    });
    row.addEventListener("pointerdown", (event) => {
      startX = event.clientX; startY = event.clientY;
      cancelLongPress();
      longPressTimer = window.setTimeout(() => openProjectContextMenu(project, event.clientX, event.clientY), PROJECT_LONG_PRESS_MS);
    });
    row.addEventListener("pointermove", (event) => {
      if (Math.abs(event.clientX - startX) > 10 || Math.abs(event.clientY - startY) > 10) cancelLongPress();
    });
    row.addEventListener("pointerup", (event) => {
      cancelLongPress();
      const horizontal = event.clientX - startX;
      if (horizontal <= -PROJECT_SWIPE_THRESHOLD) row.classList.add("is-swiped");
      else if (horizontal >= PROJECT_SWIPE_THRESHOLD / 2) row.classList.remove("is-swiped");
    });
    row.addEventListener("pointercancel", cancelLongPress);
  }

  async function startNewLearningProject() {
    setProjectSwitcherOpen(false);
    window.OnboardingController.stop?.();
    const hasCurrent = Boolean(state.context);
    await beginOnboarding(hasCurrent);
    $("#returnCurrentCourseBtn").hidden = !hasCurrent;
    $("#promptChips").hidden = true;
    $("#appShell").classList.remove("is-chat-first");
    $("#appShell").classList.add("is-onboarding");
    state.ready = false;
    $("#chatInput").focus();
  }

  async function confirmProjectDeletion() {
    const project = state.selectedProject;
    if (!project) return;
    const button = $("#confirmProjectDeleteBtn");
    button.disabled = true;
    try {
      const response = await fetch(`/api/projects/${encodeURIComponent(project.id)}?user_id=${encodeURIComponent(USER_ID)}`, {
        method: "DELETE",
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail?.message || "项目暂时没有删除成功。");
      $("#projectDeleteDialog").close();
      renderLearningProjects(result.projects || []);
      if (project.current) {
        localStorage.removeItem(STORAGE_MESSAGES);
        state.context = null; state.messages = []; state.ready = false;
        showOnboardingHome(null);
      }
      showToast("学习项目已删除，共享教案仍然保留");
    } catch (error) { showToast(error.message); }
    finally { button.disabled = false; state.selectedProject = null; }
  }

  function projectListItem(project, { rail = false } = {}) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = rail
      ? `learning-project-button${project.current ? " is-current" : ""}`
      : "project-archive-button";
    const title = document.createElement("strong");
    title.textContent = project.topic || "未命名学习项目";
    const hint = document.createElement("small");
    hint.textContent = project.current ? `当前学习 · ${projectTimeLabel(project.updated_at)}` : projectTimeLabel(project.updated_at);
    button.append(title, hint);
    if (rail) {
      const progress = document.createElement("em");
      progress.textContent = `${Number(project.progress || 0)}%`;
      button.append(progress);
    }
    button.addEventListener("click", () => openLearningProject(project, button));
    if (rail) {
      item.className = "project-row";
      const content = document.createElement("div"); content.className = "project-row-content";
      const more = document.createElement("button"); more.type = "button"; more.className = "project-row-more";
      more.setAttribute("aria-label", `管理${project.topic || "学习项目"}`);
      const moreIcon = document.createElement("i"); moreIcon.className = "bi bi-three-dots"; moreIcon.setAttribute("aria-hidden", "true"); more.append(moreIcon);
      more.addEventListener("click", (event) => { event.stopPropagation(); openProjectContextMenu(project, event.clientX, event.clientY); });
      const swipeDelete = document.createElement("button"); swipeDelete.type = "button"; swipeDelete.className = "project-row-delete";
      swipeDelete.textContent = "删除"; swipeDelete.addEventListener("click", () => requestProjectDeletion(project));
      content.append(button, more); item.append(swipeDelete, content); bindProjectGestures(item, project);
    } else item.append(button);
    return item;
  }

  function renderLearningProjects(projects = []) {
    state.projects = projects;
    const rail = $("#learningProjectList");
    rail.replaceChildren(...projects.map((project) => projectListItem(project, { rail: true })));
    $("#learningProjectEmpty").hidden = projects.length > 0;
    setText("#learningProjectCount", String(projects.length));

    const archived = projects.filter((project) => !project.current);
    const settings = $("#projectArchiveList");
    settings.replaceChildren(...archived.map((project) => projectListItem(project)));
    settings.hidden = archived.length === 0;
  }

  async function refreshProjectArchive() {
    try {
      const response = await fetch(`/api/projects?user_id=${encodeURIComponent(USER_ID)}`);
      if (!response.ok) return;
      const result = await response.json();
      renderLearningProjects(result.projects || []);
    } catch { /* The active course remains usable even if the project list is temporarily unavailable. */ }
  }

  async function enterLearning() {
    window.LearningActivity.start("正在准备讲义", "先读取你的大纲和进度，再生成当前这一小节。");
    try {
      const response = await fetch(`/api/learning-context?user_id=${encodeURIComponent(USER_ID)}`);
      const context = await response.json();
      renderLearningContext(context);
      removePlanConversationMessage();
      $("#appShell").classList.remove("is-chat-first", "is-onboarding");
      $(".sidebar-projects").classList.add("is-collapsed");
      $("#learningProjectsToggle").setAttribute("aria-expanded", "false");
      $("#promptChips").hidden = false;
      $("#choiceTray").hidden = true;
      state.ready = true;
      await window.ArtifactController.load((result) => {
        addMessage("agent", result.feedback);
        celebrateVerifiedSuccess(result);
      });
      if (!state.messages.some((message) => message.role === "agent" && /第一课|开讲/.test(message.content))) {
        addMessage("agent", "第一课已经打开。先看讲义中的第一小步；遇到题目直接点击，答案会在题目下方立即出现。", true);
      }
      window.LearningActivity.finish("讲义已准备好", "从第 1 页开始；最后一页会明确告诉你在哪里提交。 ");
    } catch (error) {
      window.LearningActivity.finish("讲义暂时未准备好", "请稍后重试，当前学习状态不会丢失。 ");
      throw error;
    }
  }

  async function beginOnboarding(archiveCurrent = false, initialTopic = "") {
    state.startupGateActive = false;
    removePlanConversationMessage();
    if (archiveCurrent) {
      state.onboardingSnapshot = {
        messages: [...state.messages], context: state.context,
        pageIndex: window.ArtifactController?.getPageIndex?.() || 0,
        ready: state.ready,
        onboardingLayout: $("#appShell").classList.contains("is-onboarding"),
      };
    }
    if (archiveCurrent && state.archivedMessages.length) {
      localStorage.setItem(STORAGE_PREVIOUS_MESSAGES, JSON.stringify(state.archivedMessages));
      state.previousMessages = [...state.archivedMessages];
    }
    if (!archiveCurrent) {
      $("#appShell").classList.remove("is-chat-first");
      $("#appShell").classList.add("is-onboarding");
    }
    window.OnboardingController.begin({
      hasActiveProject: archiveCurrent || Boolean(state.context),
      addAgent: (content) => addMessage("agent", content),
      addUser: (content) => addMessage("user", content),
      onIntentReady: async () => {
        if (archiveCurrent && !state.projectSnapshotId) {
          const response = await fetch("/api/projects/snapshot", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: USER_ID }),
          });
          const backup = await response.json().catch(() => ({}));
          if (!response.ok) throw new Error(backup.detail?.message || "当前课程暂时无法安全备份。");
          state.projectSnapshotId = backup.snapshot_id;
        }
        $("#returnCurrentCourseBtn").hidden = !archiveCurrent;
        $("#promptChips").hidden = true;
        $("#chatPrimaryAction").hidden = true;
        $("#appShell").classList.remove("is-chat-first");
        $("#appShell").classList.add("is-onboarding");
        state.ready = false;
      },
      onContinueExistingProject: async (project) => {
        await openLearningProject(project);
      },
      onMergeExistingProject: async (project) => {
        await activateStoredProject(project);
        $("#returnCurrentCourseBtn").hidden = false;
        $("#appShell").classList.remove("is-chat-first");
        $("#appShell").classList.add("is-onboarding");
        state.ready = false;
      },
      onAnswerInContext: async (message) => {
        const restoresVisibleInput = Boolean(state.onboardingSnapshot);
        if (restoresVisibleInput) await restoreCurrentCourse();
        await sendMessage(message, { echoUser: restoresVisibleInput });
      },
      onInterviewIntake: async (message) => {
        if (state.onboardingSnapshot) await restoreCurrentCourse();
        await window.InterviewBankController?.intake(message);
      },
      onPlanReady: showPlanReview,
      onConfirmed: async () => {
        if (archiveCurrent) {
          localStorage.removeItem(STORAGE_PREVIOUS_MESSAGES);
          state.previousMessages = [];
        }
        await enterLearning();
        if (state.projectSnapshotId) {
          const response = await fetch("/api/projects/snapshot/archive", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: USER_ID, snapshot_id: state.projectSnapshotId }),
          });
          if (!response.ok) throw new Error("新课程已创建，但旧课程暂时没有归档成功。请稍后重试。 ");
          await refreshProjectArchive();
        }
        $("#returnCurrentCourseBtn").hidden = true;
        state.onboardingSnapshot = null;
        state.projectSnapshotId = null;
      },
      onFailed: async () => {
        if (!archiveCurrent || !state.projectSnapshotId) return;
        try {
          await restoreCurrentCourse();
          showToast("已回到原来的课程；你的新主题选择仍会保留在对话记录里。 ");
        } catch (error) {
          showToast(error.message || "新课程没有生成成功，原课程恢复也需要重试。 ");
        }
      },
    }, initialTopic);
  }

  async function restoreCurrentCourse() {
    const snapshot = state.onboardingSnapshot;
    if (!snapshot) return;
    if (state.projectSnapshotId) {
      const response = await fetch("/api/projects/restore", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: USER_ID, snapshot_id: state.projectSnapshotId }),
      });
      const restored = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(restored.detail?.message || "原课程恢复失败，请重试。");
    }
    window.OnboardingController.stop();
    state.messages = [...snapshot.messages]; state.context = snapshot.context;
    renderMessages();
    if (snapshot.context) renderLearningContext(snapshot.context);
    $("#choiceTray").hidden = true;
    $("#returnCurrentCourseBtn").hidden = true;
    $("#promptChips").hidden = snapshot.onboardingLayout;
    $("#appShell").classList.remove("is-chat-first", "is-onboarding");
    if (snapshot.onboardingLayout) $("#appShell").classList.add("is-onboarding");
    state.ready = Boolean(snapshot.ready);
    removePlanConversationMessage();
    if (snapshot.ready) window.ArtifactController?.showPage(snapshot.pageIndex);
    state.onboardingSnapshot = null;
    state.projectSnapshotId = null;
  }

  function actionChoice(option, index) {
    const button = document.createElement("button"); button.type = "button"; button.className = "inline-choice";
    const badge = document.createElement("span"); badge.className = "inline-choice-index"; badge.textContent = String(index + 1);
    const copy = document.createElement("span"); const strong = document.createElement("strong"); strong.textContent = option.label;
    const small = document.createElement("small"); small.textContent = option.detail; copy.append(strong, small); button.append(badge, copy);
    button.addEventListener("click", async () => {
      $("#inlineChoices").querySelectorAll("button").forEach((item) => { item.disabled = true; });
      try { await option.action(); } catch (error) {
        showToast(error.message); $("#inlineChoices").querySelectorAll("button").forEach((item) => { item.disabled = false; });
      }
    });
    return button;
  }

  function showOnboardingHome(context) {
    state.context = context;
    state.ready = false;
    state.startupGateActive = true;
    state.messages = [];
    renderMessages();
    $("#appShell").classList.remove("is-chat-first");
    $("#appShell").classList.add("is-onboarding");
    $(".sidebar-projects").classList.remove("is-collapsed");
    $("#promptChips").hidden = true;
    $("#choiceTray").hidden = true;
    setText("#coachContext", "输入你现在想解决的事");
    addMessage("agent", "想继续以前的内容，直接点左边的学习项目。\n\n想学新东西，就在下面随便说——概念、项目、面试、API 或者一个具体问题都可以。", false);
    $("#chatInput").placeholder = "例如：下周面试 Java 后端，或我想用 LangGraph 做客服 Agent…";
  }

  async function confirmPendingPlanAndStart() {
    const response = await fetch("/api/plans/confirm", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: USER_ID }),
    });
    if (!response.ok) throw new Error("计划确认失败，请重试。 ");
    $("#choiceTray").hidden = true;
    await enterLearning();
  }

  async function initialize() {
    state.messages = [];
    renderMessages();
    try {
      const [healthResponse, contextResponse] = await Promise.all([
        fetch("/api/health"), fetch(`/api/learning-context?user_id=${encodeURIComponent(USER_ID)}`),
      ]);
      if (!healthResponse.ok) throw new Error("学习服务未连接");
      $("#statusDot").classList.add("is-online"); setText("#connectionText", "已连接");
      const context = await contextResponse.json();
      if (context.plan_status === "awaiting_confirmation") {
        state.startupGateActive = false;
        await refreshProjectArchive();
        renderLearningContext(context);
        state.messages = [];
        renderMessages();
        const conceptPlan = context.goal_route === "concept_clarity";
        addMessage("agent", conceptPlan
          ? "这份概念速学方案还在等你确认。确认后就会直接开始概念讲解。"
          : "这份学习计划还在等你确认。你可以先阅读；确认后才会开始生成第一章。", false);
        await showPlanReview({ plan_markdown: context.plan?.content });
        $("#choiceTrayHint").textContent = "Plan 等待确认";
        $("#choiceProgress").textContent = "开课前";
        $("#inlineChoices").replaceChildren(actionChoice({
          label: "确认并开始",
          detail: conceptPlan ? "锁定范围，开始概念讲解" : "锁定当前大纲，开始生成第一章",
          action: confirmPendingPlanAndStart,
        }, 0));
        $("#choiceTray").classList.add("is-plan-confirmation");
        $("#choiceTray").hidden = false;
        return;
      }
      if (["ready", "confirmed"].includes(context.profile_status)) {
        await refreshProjectArchive();
        renderLearningContext(context); showOnboardingHome(context);
      } else {
        await refreshProjectArchive();
        beginOnboarding();
      }
    } catch (error) {
      setText("#connectionText", "连接失败");
      if (!state.messages.length) addMessage("agent", `暂时没能连接学习服务：${error.message}。请确认后台服务正在运行。`, false);
    }
  }

  function showAnkiRating() {
    if (window.OnboardingController.active) return;
    $("#settingsDialog").close();
    window.InterviewBankController.startReview();
  }

  async function openReminderSettings() {
    try {
      const response = await fetch(`/api/reminders?user_id=${encodeURIComponent(USER_ID)}`);
      const reminder = await response.json();
      $("#reminderEnabled").checked = Boolean(reminder.enabled);
      $("#reminderTime").value = reminder.time || "20:00";
      $("#reminderKind").value = reminder.kind || "both";
    } catch { /* The form keeps safe defaults when the service is unavailable. */ }
    $("#reminderDialog").showModal();
  }

  async function saveReminder(event) {
    event.preventDefault();
    try {
      const response = await fetch("/api/reminders", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: USER_ID,
          enabled: $("#reminderEnabled").checked,
          time: $("#reminderTime").value,
          kind: $("#reminderKind").value,
        }),
      });
      if (!response.ok) throw new Error("提醒没有保存成功");
      showToast($("#reminderEnabled").checked ? "每日提醒已保存" : "每日提醒已关闭");
      $("#reminderDialog").close();
    } catch (error) { showToast(error.message); }
  }

  function bind() {
    window.InterviewBankController?.init({ userId: USER_ID, addUser: (content) => addMessage("user", content), addAgent: (content) => addMessage("agent", content), showToast });
    $("#chatForm").addEventListener("submit", async (event) => {
      event.preventDefault(); const input = $("#chatInput"); const value = input.value; if (!value.trim()) return;
      input.value = "";
      try {
        if (window.OnboardingController.active) await window.OnboardingController.handleText(value);
        else if (state.startupGateActive || state.ready) {
          await beginOnboarding(true, value);
        }
        else await sendMessage(value);
      } catch (error) { showToast(error.message); input.value = value; }
    });
    $("#chatInput").addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); $("#chatForm").requestSubmit(); } });
    $$("[data-prompt]").forEach((button) => button.addEventListener("click", () => sendMessage(button.dataset.prompt)));
    $("#settingsBtn").addEventListener("click", () => $("#settingsDialog").showModal());
    $("#projectMobileBtn").addEventListener("click", toggleProjectSwitcher);
    $("#addLearningProjectBtn").addEventListener("click", () => startNewLearningProject().catch((error) => showToast(error.message)));
    $("#learningProjectsToggle").addEventListener("click", () => {
      const section = $(".sidebar-projects");
      const expanded = section.classList.toggle("is-collapsed") === false;
      $("#learningProjectsToggle").setAttribute("aria-expanded", String(expanded));
      $("#learningProjectsToggle").setAttribute("aria-label", expanded ? "收起学习项目" : "展开学习项目");
    });
    $("#projectContextDeleteBtn").addEventListener("click", () => state.selectedProject && requestProjectDeletion(state.selectedProject));
    $("#confirmProjectDeleteBtn").addEventListener("click", confirmProjectDeletion);
    $("#cancelProjectDeleteBtn").addEventListener("click", () => $("#projectDeleteDialog").close());
    $("#openPlanBtn").addEventListener("click", () => { $("#settingsDialog").close(); $("#planDialog").showModal(); });
    $("#sidebarOpenPlanBtn").addEventListener("click", () => $("#planDialog").showModal());
    $("#currentPlanArchiveBtn").addEventListener("click", () => { $("#settingsDialog").close(); $("#planDialog").showModal(); });
    $("#reminderBtn").addEventListener("click", openReminderSettings);
    $$("[data-close-dialog]").forEach((button) => button.addEventListener("click", () => document.getElementById(button.dataset.closeDialog).close()));
    $$("dialog").forEach((dialog) => dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); }));
    document.addEventListener("click", (event) => {
      if (!event.target.closest("#learningRoadmap") && !event.target.closest("#projectMobileBtn")) setProjectSwitcherOpen(false);
      if (!event.target.closest("#projectContextMenu") && !event.target.closest(".project-row-more")) closeProjectContextMenu();
    });
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") { setProjectSwitcherOpen(false); closeProjectContextMenu(); } });
    $("#reviewModeBtn").addEventListener("click", showAnkiRating);
    $("#outlinePreviousBtn").addEventListener("click", () => pageOutline(-1));
    $("#outlineNextBtn").addEventListener("click", () => pageOutline(1));
    $("#outlinePanel").addEventListener("scroll", updateOutlinePageLabel, { passive: true });
    $("#returnCurrentCourseBtn").addEventListener("click", () => restoreCurrentCourse().catch((error) => showToast(error.message)));
    $("#collapseArtifactBtn").addEventListener("click", () => $("#appShell").classList.add("is-chat-first"));
    $("#reminderForm").addEventListener("submit", saveReminder);
    document.addEventListener("learning-agent:page-change", (event) => {
      setText("#lessonCounter", `本章 ${event.detail.index + 1} / ${event.detail.total}`);
      setText("#coachContext", `正在学习：${event.detail.page.title}`);
    });
    document.addEventListener("learning-agent:lesson-transition", async (event) => {
      const response = await fetch(`/api/learning-context?user_id=${encodeURIComponent(USER_ID)}`);
      if (response.ok) renderLearningContext(await response.json());
      addMessage("agent", `已经为你打开：**${event.detail.cta_label}**。从第 1 页开始，继续按讲义里的提示往下走。`);
    });
  }

  document.addEventListener("DOMContentLoaded", () => { bind(); initialize(); }, { once: true });
  window.LearningApp = { sendMessage, celebrateVerifiedSuccess, renderLearningContext };
}());
