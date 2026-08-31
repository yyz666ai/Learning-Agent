"use strict";
{
  const i18n = () => (typeof window !== "undefined" ? window : globalThis).LearningI18n;
  const t = (key, params = {}) => i18n()?.t(key, params) ?? String(key).replace(/\{(\w+)\}/g, (m, k) => params[k] == null ? m : String(params[k]));
  const resolveText = value => typeof value === "function" ? value() : value;
  const bindUI = (node, property, render) => { if (i18n()) return i18n().bind(node, property, render); const value = render(); if (property.startsWith("@")) node.setAttribute(property.slice(1), value); else node[property] = value; return value; };
(function createArtifactController(global) {
  const query = new URLSearchParams(global.location?.search || "");
  const userId = query.get("user_id") || "yang";
  const widthKey = `learning-agent.coach-width.v1.${userId}`;
  const state = { manifest: null, pageIndex: 0, onResult: null, quizAttempts: [], completionDecision: null, notes: [] };
  const byId = (id) => document.getElementById(id);

  function setText(id, value) { const node = byId(id); if (node) bindUI(node, "textContent", () => (typeof value === "function" ? value() : value) ?? ""); }
  function showQuestionFeedback(message, tone = "") {
    const panel = byId("questionFeedback");
    bindUI(panel, "textContent", () => resolveText(message)); panel.className = `question-feedback${tone ? ` is-${tone}` : ""}`; panel.hidden = false;
  }
  function startActivity(label, detail) { global.LearningActivity?.start(label, detail); }
  function startLessonGeneration() { global.LearningActivity?.startLessonGeneration?.(); }
  function finishActivity(label, detail) { global.LearningActivity?.finish(label, detail); }
  function codeFilename(language) {
    return ({ python: "main.py", go: "main.go", java: "Main.java", rust: "main.rs", bash: "Terminal", shell: "Terminal", sh: "Terminal" })[language] || "notes.md";
  }

  async function requestLessonGeneration(payload) {
    payload = {...payload, locale: payload.locale || global.LearningI18n?.getLocale() || "zh-CN"};
    const started = await fetch("/api/lesson/generate/start", {
      method: "POST", headers: { "Content-Type": "application/json", "X-Learning-Locale": payload.locale },
      body: JSON.stringify(payload),
    });
    const accepted = await started.json().catch(() => ({}));
    if (!started.ok) return { ok: false, payload: accepted };
    const deadline = Date.now() + (11 * 60 * 1000);
    while (Date.now() < deadline) {
      await new Promise((resolve) => window.setTimeout(resolve, 1200));
      let response;
      try {
        const query = new URLSearchParams({ user_id: userId, job_id: accepted.generation_id });
        response = await fetch(`/api/lesson/generate/status?${query.toString()}`);
      } catch (_error) {
        continue;
      }
      const status = await response.json().catch(() => ({}));
      if (!response.ok) return { ok: false, payload: status };
      if (status.status === "completed") return { ok: true, payload: status.result?.lesson || {}, locale: status.locale || status.result?.locale || payload.locale };
      if (status.status === "failed") return { ok: false, payload: { detail: status.result?.detail || status.result } };
    }
    return { ok: false, payload: { detail: { get message() { return t("课件仍在后台生成，请稍后点击重试继续读取。"); } } } };
  }

  function passedCheck(pageId) {
    return state.quizAttempts.some((attempt) => attempt.page_id === pageId && attempt.correct === true);
  }

  function firstBlockingCheck(targetIndex) {
    for (let index = 0; index < targetIndex; index += 1) {
      const page = state.manifest.pages[index];
      if (page.question && (page.options || []).length && !passedCheck(page.id)) return index;
    }
    return -1;
  }

  function renderDots() {
    const blockingIndex = firstBlockingCheck(state.manifest.pages.length);
    const dots = state.manifest.pages.map((page, index) => {
      const button = document.createElement("button");
      button.type = "button";
      bindUI(button, "textContent", () => String(index + 1));
      button.className = index === state.pageIndex ? "is-active" : "";
      bindUI(button, "@aria-label", () => t("第 {0} 页：{1}", {0: index + 1, 1: page.title}));
      button.disabled = index > blockingIndex && blockingIndex >= 0;
      button.addEventListener("click", () => showPage(index));
      return button;
    });
    byId("pageDots").replaceChildren(...dots);
  }

  async function checkOption(page, option, button) {
    const t = (key, params = {}) => window.LearningI18n?.t(key, params) ?? String(key).replace(/\{(\w+)\}/g, (match, name) => params[name] == null ? match : String(params[name]));
    const requestedManifest = state.manifest;
    const requestedIndex = state.pageIndex;
    const stillCurrent = () => state.manifest === requestedManifest && state.pageIndex === requestedIndex;
    [...byId("pageOptions").querySelectorAll("button")].forEach((item) => { item.disabled = true; });
    showQuestionFeedback(() => t("正在检查这道题…马上告诉你哪里对、下一步怎么做。 "));
    startActivity(() => t("正在检查这道题"), () => t("答案会显示在题目下方；不需要再去别处提交。 "));
    try {
      const response = await fetch("/api/lesson/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, lesson_id: state.manifest.lesson_id, revision: state.manifest.revision, page_id: page.id, selected_option_id: option.id }),
      });
      const result = await response.json();
      if (!stillCurrent()) return;
      if (!response.ok) throw new Error(result.detail?.message || t("暂时无法批改，请再试一次。"));
      button.dataset.result = result.correct ? "correct" : "incorrect";
      state.quizAttempts = state.quizAttempts.filter((attempt) => attempt.page_id !== page.id);
      state.quizAttempts.push({ page_id: page.id, correct: Boolean(result.correct) });
      global.InterviewBankController?.load?.();
      state.onResult?.({ ...result, question: page.question, answer: option.label });
      if (result.correct) {
        showQuestionFeedback(() => t("{0} 下一步：900ms 后自动进入下一页。", {0: result.feedback || t("答对了。")}), "correct");
        finishActivity(() => t("答对了"), () => t("这一页已通过，马上进入下一小步。 "));
        window.setTimeout(() => { if (stillCurrent()) showPage(Math.min(requestedIndex + 1, requestedManifest.pages.length - 1)); }, 900);
      } else {
        showQuestionFeedback(() => t("{0} 下一步：再选一次；需要提示可以点右侧“给我提示”。", {0: result.feedback || t("还差一点。")}), "incorrect");
        finishActivity(() => t("还差一点"), () => t("答案提示已经显示在题目下方，可以马上再试。 "));
        [...byId("pageOptions").querySelectorAll("button")].forEach((item) => { item.disabled = false; });
      }
    } catch (error) {
      if (!stillCurrent()) return;
      state.onResult?.({ correct: false, verified: false, feedback: (window.LearningI18n?.errorText(error.message) ?? error.message) });
      showQuestionFeedback(() => t("暂时无法检查：{0}。下一步：点击选项重试。", {0: (window.LearningI18n?.errorText(error.message) ?? error.message)}), "incorrect");
      finishActivity(() => t("检查没有完成"), () => t("你的选择没有丢失，重新点击即可。 "));
      [...byId("pageOptions").querySelectorAll("button")].forEach((item) => { item.disabled = false; });
    }
  }

  function renderQuestion(page) {
    const section = byId("pageQuestion");
    section.hidden = !page.question || !page.options?.length;
    if (section.hidden) { byId("pageOptions").replaceChildren(); return; }
    byId("questionFeedback").hidden = true;
    setText("pageQuestionText", () => page.question);
    const buttons = (page.options || []).slice(0, 10).map((option, index) => {
      const button = document.createElement("button");
      button.type = "button";
      const badge = document.createElement("span"); bindUI(badge, "textContent", () => String.fromCharCode(65 + index));
      const label = document.createElement("span"); bindUI(label, "textContent", () => option.label);
      button.append(badge, label);
      button.addEventListener("click", () => checkOption(page, option, button));
      return button;
    });
    byId("pageOptions").replaceChildren(...buttons);
  }

  function pageInstruction(page) {
    if (page.type === "check" || (page.question && page.options?.length)) return t("直接点击一个选项。答对后会自动进入下一页；答错可以马上重选。");
    if (page.type === "practice") return t("这是课后练习，不是课堂门禁。打开练习文件夹自己完成；代码、结果或问题直接发到右侧输入栏。");
    if (page.type === "mastery" && state.manifest?.completion_mode === "choice") return t("这个概念的必答题通过后，点击“完成这个概念”即可。");
    if (page.type === "mastery") return t("课堂到这里结束。课后自己练；愿意讨论时，把代码、运行结果或问题直接发到右侧输入栏。");
    if (page.code) return t("先读这段代码，确认它做什么；理解后点击下一页继续。");
    return t("读完这一页，抓住它解决的问题，再点击下一页。");
  }

  function renderPageInstruction(page) {
    bindUI(byId("pageInstructionText"), "textContent", () => pageInstruction(page));
    byId("pageInstruction").hidden = /本页(?:请做|行动|任务)[：:]/.test((page.markdown || "").replace(/[*_`]/g, ""));
  }

  function homeworkPage() {
    return state.manifest?.pages.find((page) => page.practice_kind === "homework")
      || state.manifest?.pages.find((page) => page.type === "practice") || null;
  }

  function renderHomework() {
    const homework = homeworkPage();
    const card = byId("homeworkCard");
    card.hidden = !homework;
    if (!homework) return;
    setText("homeworkTitle", () => homework.title);
    bindUI(byId("homeworkDescription"), "innerHTML", () => global.MarkdownRenderer.render(homework.markdown || t("打开练习文件夹，自己完成这道课后练习。")));
    global.MarkdownRenderer.hydrate(byId("homeworkDescription"));
    setText("homeworkPath", () => homework.practice_path || state.manifest.practice_path);
  }

  function renderInterviewPrompts() {
    const prompts = state.manifest?.interview_prompts || [];
    const section = byId("lessonInterviewPrompts");
    section.hidden = !prompts.length;
    if (!prompts.length) { byId("lessonInterviewPromptList").replaceChildren(); return; }
    byId("lessonInterviewPromptList").replaceChildren(...prompts.map((prompt, index) => {
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      bindUI(summary, "textContent", () => `${index + 1}. ${prompt.question}`);
      const answer = document.createElement("div"); answer.className = "markdown-body";
      const structure = (prompt.answer_structure || []).map((item) => `- ${item}`).join("\n");
      const omissions = (prompt.common_omissions || []).map((item) => `- ${item}`).join("\n");
      const followUps = (prompt.follow_ups || []).map((item) => (
        `- **${item.prompt}**：${(item.answer_points || []).join("、")}`
      )).join("\n");
      bindUI(answer, "innerHTML", () => global.MarkdownRenderer.render(
        t("#### 参考答案\n\n{0}\n\n**回答结构**\n\n{1}", {0: prompt.reference_answer, 1: structure})
        + (omissions ? t("\n\n**常见遗漏**\n\n{0}", {0: omissions}) : "")
        + (followUps ? t("\n\n**常见追问**\n\n{0}", {0: followUps}) : ""),
      ));
      global.MarkdownRenderer.hydrate(answer);
      details.append(summary, answer); return details;
    }));
  }

  function renderLessonNotes(notes) {
    state.notes = Array.isArray(notes) ? notes : [];
    const panel = byId("lessonNotesPanel"); const list = byId("lessonNotesList");
    panel.hidden = state.notes.length === 0;
    if (!state.notes.length) { list.replaceChildren(); setText("lessonReward", () => ""); return; }
    list.replaceChildren(...state.notes.map((note, index) => {
      const article = document.createElement("article");
      const title = document.createElement("strong"); bindUI(title, "textContent", () => t("笔记 {0}{1}", {0: index + 1, 1: note.important ? t(" · 重点") : ""}));
      const question = document.createElement("p"); bindUI(question, "textContent", () => t("我的问题：{0}", {0: note.question || ""}));
      const summary = document.createElement("p"); bindUI(summary, "textContent", () => t("教练总结：{0}", {0: note.summary || ""}));
      article.append(title, question, summary); return article;
    }));
    setText("lessonReward", () => state.notes[state.notes.length - 1]?.reward || "");
  }

  async function loadLessonNotes() {
    if (!state.manifest?.lesson_id) return;
    try {
      const response = await fetch(`/api/lesson/notes?user_id=${encodeURIComponent(userId)}&lesson_id=${encodeURIComponent(state.manifest.lesson_id)}`);
      const payload = await response.json().catch(() => ({}));
      if (response.ok) renderLessonNotes(payload.notes);
    } catch { /* Notes never block the lesson. */ }
  }

  function showPage(index) {
    if (!state.manifest) return;
    if (index !== state.pageIndex && window.LessonEditor?.isOpen() && !window.LessonEditor.canLeave()) return;
    byId("reviewCardPanel").hidden = true;
    document.querySelector(".page-navigation").hidden = false;
    const requestedIndex = Math.max(0, Math.min(index, state.manifest.pages.length - 1));
    const blockingIndex = requestedIndex > state.pageIndex ? firstBlockingCheck(requestedIndex) : -1;
    state.pageIndex = blockingIndex >= 0 ? blockingIndex : requestedIndex;
    const page = state.manifest.pages[state.pageIndex];
    const total = state.manifest.pages.length;
    setText("pageCount", () => t("第 {0} 页 / 共 {1} 页", {0: state.pageIndex + 1, 1: total}));
    setText("pageEyebrow", () => page.eyebrow || t("当前小步"));
    setText("pageTitle", () => page.title);
    byId("pageMarkdown").innerHTML = global.MarkdownRenderer.render(page.markdown || "");
    global.MarkdownRenderer.hydrate(byId("pageMarkdown"));
    const codeBlock = byId("pageCodeBlock");
    codeBlock.hidden = !page.code;
    if (page.code) {
      setText("codeFilename", () => codeFilename(page.language));
      byId("pageCode").className = `language-${page.language || "text"}`;
      byId("pageCode").innerHTML = global.MarkdownRenderer.highlightCode(page.code, page.language);
    }
    renderQuestion(page);
    renderPageInstruction(page);
    const path = page.practice_path || (page.type === "practice" ? state.manifest.practice_path : "");
    byId("practiceLocation").hidden = !path;
    setText("practicePath", () => path);
    byId("previousPageBtn").disabled = state.pageIndex === 0;
    const isFinal = state.pageIndex === total - 1;
    byId("lessonCompletionPanel").hidden = !isFinal;
    byId("nextPageBtn").hidden = isFinal;
    byId("nextPageBtn").disabled = isFinal || Boolean(page.question && (page.options || []).length && !passedCheck(page.id));
    if (blockingIndex >= 0) showQuestionFeedback(() => t("这一页需要先答对，才能继续看后面的内容。直接点击一个选项即可。"), "incorrect");
    if (isFinal) {
      const choiceOnly = state.manifest.completion_mode === "choice";
      setText("completionPrompt", () => choiceOnly
        ? t("必答选择题都答对就能完成；不需要写代码、粘贴终端输出或额外解释。")
        : t("本章课堂已经讲完。课后练习留在真实项目里，你可以自己消化；完成后的代码、运行结果或问题直接发到右侧输入栏。系统不再检查打印输出。 "));
      renderHomework();
      renderInterviewPrompts();
      setText("completeSubmitBtn", () => choiceOnly ? t("完成这个概念") : t("完成课堂，进入下一章"));
    }
    if (!isFinal) byId("lessonInterviewPrompts").hidden = true;
    renderDots();
    byId("artifactPane").scrollTop = 0;
    if (isFinal) {
      window.requestAnimationFrame(() => {
        byId("lessonCompletionPanel").scrollIntoView({ behavior: "smooth", block: "nearest" });
      });
    }
    document.dispatchEvent(new CustomEvent("learning-agent:page-change", { detail: { page, index: state.pageIndex, total } }));
  }

  function openPracticeItem(item) {
    if (!state.manifest || item?.lesson_id !== state.manifest.lesson_id) {
      state.onResult?.({ correct: false, verified: false, get feedback() { return t("这道练习属于其他课程，请先在设置里切换到对应学习项目。"); } });
      return false;
    }
    const index = state.manifest.pages.findIndex((page) => page.id === item.page_id);
    if (index < 0) return false;
    showPage(index);
    byId("artifactPane").focus();
    return true;
  }

  function applyManifest(payload) {
    byId("lessonLoadError").hidden = true;
    state.manifest = payload;
    document.dispatchEvent(new CustomEvent("learning-agent:manifest-change", { detail: payload }));
    state.pageIndex = 0;
    state.quizAttempts = Array.isArray(payload.quiz_attempts) ? payload.quiz_attempts.filter(attempt => attempt.correct === true) : [];
    state.completionDecision = null;
    byId("completionResult").hidden = true;
    byId("lessonPrimaryAction").hidden = true;
    byId("chatPrimaryAction").hidden = true;
    byId("nextPageBtn").hidden = false;
    setText("lessonCounter", () => t("本章 1 / {0}", {0: payload.pages.length}));
    const timeLabel = () => payload.planned_sessions
      ? t("本章约 {0} 次 · 每次 {1} 分钟", {0: payload.planned_sessions, 1: payload.session_minutes || payload.progress.remaining_minutes})
      : t("建议每次 {0} 分钟 · 本章课次待估", {0: payload.session_minutes || payload.progress.remaining_minutes});
    setText("lessonRemaining", () => timeLabel());
    setText("remainingTime", () => timeLabel());
    showPage(0);
    loadLessonNotes();
    return payload;
  }

  function showLessonLoadFailure(message) {
    state.manifest = null;
    setText("pageCount", () => t("课程尚未就绪"));
    setText("pageEyebrow", () => t("准备没有完成"));
    setText("pageTitle", () => t("课程生成失败"));
    setText("lessonLoadErrorText", () => t("{0}学习进度没有丢失，可以直接重试。", {0: i18n()?.errorText(message) || message || t("这次课程没有生成完成。")}));
    byId("lessonLoadError").hidden = false;
    byId("pageMarkdown").replaceChildren();
    ["pageInstruction", "pageCodeBlock", "pageQuestion", "practiceLocation", "lessonNotesPanel", "lessonCompletionPanel"].forEach((id) => { byId(id).hidden = true; });
    byId("previousPageBtn").disabled = true;
    byId("nextPageBtn").hidden = true;
    byId("pageDots").replaceChildren();
  }

  async function loadCurrentLesson(retryStale = true) {
    byId("lessonLoadError").hidden = true;
    startActivity(() => t("正在准备讲义"), () => t("正在检查当前知识点，并生成这一节的讲解与练习。 "));
    try {
      let response = await fetch(`/api/lesson/current?user_id=${encodeURIComponent(userId)}`);
      let payload = await response.json().catch(() => ({}));
      if (!response.ok && payload.detail?.recovery === "generate_curriculum") {
        const curriculumResponse = await fetch("/api/curriculum/generate", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: userId }),
        });
        const curriculumResult = await curriculumResponse.json().catch(() => ({}));
        if (!curriculumResponse.ok) throw new Error(curriculumResult.detail?.message || t("详细课程大纲没有生成成功。"));
        response = await fetch(`/api/lesson/current?user_id=${encodeURIComponent(userId)}`);
        payload = await response.json().catch(() => ({}));
      }
      if (!response.ok && payload.detail?.recovery === "generate_lesson") {
        startLessonGeneration();
        const generated = await requestLessonGeneration({ user_id: userId });
        response = { ok: generated.ok };
        payload = generated.payload;
        if (generated.ok) global.LearningI18n?.noticeJobLocale('lesson', generated.locale || payload.locale || 'zh-CN');
      }
      if (!response.ok && payload.detail?.recovery === "stale_generation") {
        if (retryStale) {
          finishActivity(() => t("项目已经切换"), () => t("迟到课件已丢弃，正在读取当前项目。 "));
          return loadCurrentLesson(false);
        }
        throw new Error(t("项目已经切换，请确认当前学习计划后再生成讲义。"));
      }
      if (!response.ok) throw new Error(payload.detail?.message || t("课程暂时没有准备好。"));
      const manifest = applyManifest(payload);
      finishActivity(() => t("讲义已准备好"), () => t("先阅读这一页；有题时直接点击答案。 "));
      return manifest;
    } catch (error) {
      showLessonLoadFailure((window.LearningI18n?.errorText(error.message) ?? error.message));
      finishActivity(() => t("讲义生成失败"), () => t("已在讲义区显示失败原因和重试按钮。"));
      throw error;
    }
  }

  async function load(onResult) {
    state.onResult = onResult;
    return loadCurrentLesson();
  }

  function setCompletionBusy(busy) {
    ["completeSubmitBtn", "lessonPrimaryAction", "chatPrimaryAction"].forEach((id) => { byId(id).disabled = busy; });
  }

  function showCompletionDecision(result) {
    state.completionDecision = result;
    byId("completionResult").hidden = false;
    setText("completionVerdict", () => result.verdict === "advance" ? t("课堂已经完成") : result.verdict === "practice" ? t("再练一小步") : t("换个角度重新理解"));
    setText("completionFeedback", () => global.LearningI18n?.completionText(result.feedback) || result.feedback);
    ["lessonPrimaryAction", "chatPrimaryAction"].forEach((id) => {
      const button = byId(id); bindUI(button, "textContent", () => global.LearningI18n?.completionText(result.cta_label) || result.cta_label); button.hidden = false;
    });
    state.onResult?.({ ...result, feedback: global.LearningI18n?.completionText(result.feedback) || result.feedback, correct: result.verdict === "advance", verified: result.verdict === "advance" });
  }

  async function submitCompletion(action) {
    if (!state.manifest) return;
    setCompletionBusy(true);
    const choiceOnly = state.manifest.completion_mode === "choice";
    startActivity(() => choiceOnly ? t("正在确认概念检测") : t("正在保存课堂进度"), () => t("只确认课堂选择题；课后练习不会做输出检测。 "));
    try {
      const response = await fetch("/api/lesson/complete", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId, lesson_id: state.manifest.lesson_id, action,
          quiz_attempts: state.quizAttempts, revision: state.manifest.revision,
        }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail?.message || t("本章评价没有成功，请重试。"));
      showCompletionDecision(result);
      finishActivity(() => result.verdict === "advance" ? t("课堂进度已保存") : t("还有课堂题未完成"), () => result.verdict === "advance" ? t("课后练习已留好。点击“{0}”继续。", {0: global.LearningI18n?.completionText(result.cta_label) || result.cta_label}) : t("回到课堂选择题再试一次。 "));
    } catch (error) {
      state.onResult?.({ correct: false, verified: false, feedback: (window.LearningI18n?.errorText(error.message) ?? error.message) });
      finishActivity(() => t("课堂进度没有保存"), () => t("选择题记录仍在，可以直接重试。 "));
    } finally { setCompletionBusy(false); }
  }

  async function runPrimaryAction() {
    const decision = state.completionDecision;
    if (!decision) return;
    if (decision.verdict !== "advance") {
      await global.LessonEditor.propose(decision.feedback || t("请用更循序渐进的方式重新讲解当前课件"), "revision");
      return;
    }
    if (global.LessonEditor && !global.LessonEditor.canLeave()) return;
    if (decision.verdict === "advance" && !decision.next_knowledge_point_id) {
      byId("planDialog").showModal();
      document.dispatchEvent(new CustomEvent("learning-agent:course-complete", { detail: decision }));
      return;
    }
    setCompletionBusy(true);
    startActivity(() => t("正在生成下一小节"), () => t("正在根据这次评价准备下一份讲义和练习。 "));
    try {
      const generated = await requestLessonGeneration({ user_id: userId, force: decision.verdict !== "advance", remediation: decision.verdict === "advance" ? "" : decision.feedback, next_knowledge_point_id: decision.next_knowledge_point_id });
      const response = { ok: generated.ok };
      const payload = generated.payload;
      if (!response.ok && payload.detail?.recovery === "stale_generation") {
        await loadCurrentLesson(false);
        finishActivity(() => t("项目已经切换"), () => t("已安全丢弃旧课件，并读取当前课程。 "));
        return;
      }
      if (!response.ok) throw new Error(payload.detail?.message || t("下一步课程没有生成成功，请重试。"));
      applyManifest(payload);
      global.LearningI18n?.noticeJobLocale('lesson', generated.locale || payload.locale || 'zh-CN');
      document.dispatchEvent(new CustomEvent("learning-agent:lesson-transition", { detail: decision }));
      finishActivity(() => t("下一小节已准备好"), () => t("从讲义第 1 页开始；每一步都会告诉你接下来做什么。 "));
    } catch (error) {
      state.onResult?.({ correct: false, verified: false, feedback: (window.LearningI18n?.errorText(error.message) ?? error.message) });
      finishActivity(() => t("下一小节没有生成"), () => t("当前讲义仍保留，点击按钮即可重试。 "));
    } finally { setCompletionBusy(false); }
  }

  function bindResizer() {
    const splitter = byId("artifactSplitter");
    const shell = byId("appShell");
    const stored = Number(localStorage.getItem(widthKey));
    if (stored >= 320 && stored <= 680) shell.style.setProperty("--coach-width", `${stored}px`);
    function setWidth(value) {
      const width = Math.max(320, Math.min(680, value));
      shell.style.setProperty("--coach-width", `${width}px`);
      splitter.setAttribute("aria-valuenow", String(Math.round(width)));
      localStorage.setItem(widthKey, String(Math.round(width)));
    }
    splitter.addEventListener("pointerdown", (event) => {
      splitter.setPointerCapture(event.pointerId);
      document.body.style.userSelect = "none";
    });
    splitter.addEventListener("pointermove", (event) => {
      if (!splitter.hasPointerCapture(event.pointerId)) return;
      setWidth(window.innerWidth - event.clientX);
    });
    splitter.addEventListener("pointerup", (event) => { splitter.releasePointerCapture(event.pointerId); document.body.style.userSelect = ""; });
    splitter.addEventListener("pointercancel", () => { document.body.style.userSelect = ""; });
    splitter.addEventListener("lostpointercapture", () => { document.body.style.userSelect = ""; });
    splitter.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
      event.preventDefault();
      const current = parseFloat(getComputedStyle(shell).getPropertyValue("--coach-width")) || 390;
      setWidth(current + (event.key === "ArrowLeft" ? 24 : -24));
    });
  }

  async function openPracticeFolder(path, button) {
    const t = key => window.LearningI18n?.t(key) ?? key;
    const bindUI = (node, property, render) => window.LearningI18n ? window.LearningI18n.bind(node, property, render) : (node[property] = render());
    button.disabled = true;
    try {
      const response = await fetch("/api/practice/open", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, path }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail?.message || t("文件夹暂时无法打开。"));
      if (result.opened) bindUI(button, "textContent", () => t("已请求系统打开"));
      else {
        bindUI(button, "textContent", () => t("请手动打开"));
        state.onResult?.({ correct: false, verified: false, feedback: `${t(result.message || "当前环境不能打开文件夹。")}\n${result.resolved_path || result.path || path}` });
      }
    } catch (error) {
      bindUI(button, "textContent", () => t("重试打开"));
      state.onResult?.({ correct: false, verified: false, feedback: (window.LearningI18n?.errorText(error.message) ?? error.message) });
    } finally {
      window.setTimeout(() => { button.disabled = false; bindUI(button, "textContent", () => t("打开练习文件夹")); }, 1600);
    }
  }

  function bind() {
    byId("retryLessonBtn").addEventListener("click", async () => {
      const button = byId("retryLessonBtn");
      button.disabled = true; bindUI(button, "innerHTML", () => t("<i class=\"bi bi-arrow-clockwise\" aria-hidden=\"true\"></i>正在重新生成…"));
      try { await loadCurrentLesson(); }
      catch { /* The persistent error panel already explains the retry result. */ }
      finally { button.disabled = false; bindUI(button, "innerHTML", () => t("<i class=\"bi bi-arrow-clockwise\" aria-hidden=\"true\"></i>重新生成课程")); }
    });
    byId("previousPageBtn").addEventListener("click", () => showPage(state.pageIndex - 1));
    byId("nextPageBtn").addEventListener("click", () => showPage(state.pageIndex + 1));
    byId("completeSubmitBtn").addEventListener("click", () => submitCompletion("submit"));
    byId("lessonPrimaryAction").addEventListener("click", runPrimaryAction);
    byId("chatPrimaryAction").addEventListener("click", runPrimaryAction);
    byId("copyCodeBtn").addEventListener("click", async () => {
      const button = byId("copyCodeBtn");
      const original = () => t("复制代码");
      button.disabled = true;
      try {
        await navigator.clipboard.writeText(state.manifest?.pages[state.pageIndex]?.code || "");
        bindUI(button, "textContent", () => t("✓ 已复制"));
      } catch {
        bindUI(button, "textContent", () => t("复制失败"));
      } finally {
        window.setTimeout(() => { button.disabled = false; bindUI(button, "textContent", () => original()); }, 1500);
      }
    });
    byId("openPracticeFolderBtn").addEventListener("click", async () => {
      const button = byId("openPracticeFolderBtn");
      await openPracticeFolder(byId("practicePath").textContent, button);
    });
    byId("openHomeworkFolderBtn").addEventListener("click", async () => {
      await openPracticeFolder(byId("homeworkPath").textContent, byId("openHomeworkFolderBtn"));
    });
    document.addEventListener("learning-agent:notes-updated", (event) => {
      if (!event.detail?.lesson_id || event.detail.lesson_id === state.manifest?.lesson_id) loadLessonNotes();
    });
    bindResizer();
  }

  document.addEventListener("DOMContentLoaded", bind, { once: true });
  global.ArtifactController = {
    load, loadCurrentLesson, showPage, openPracticeItem, submitCompletion, userId,
    getPageIndex: () => state.pageIndex,
    currentLessonId: () => state.manifest?.lesson_id || null,
  };
}(window));

}
