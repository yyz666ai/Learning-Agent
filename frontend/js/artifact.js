"use strict";

(function createArtifactController(global) {
  const query = new URLSearchParams(global.location?.search || "");
  const userId = query.get("user_id") || "yang";
  const widthKey = `learning-agent.coach-width.v1.${userId}`;
  const state = { manifest: null, pageIndex: 0, onResult: null, quizAttempts: [], completionDecision: null, notes: [] };
  const byId = (id) => document.getElementById(id);

  function setText(id, value) { const node = byId(id); if (node) node.textContent = value ?? ""; }
  function showQuestionFeedback(message, tone = "") {
    const panel = byId("questionFeedback");
    panel.textContent = message; panel.className = `question-feedback${tone ? ` is-${tone}` : ""}`; panel.hidden = false;
  }
  function startActivity(label, detail) { global.LearningActivity?.start(label, detail); }
  function startLessonGeneration() { global.LearningActivity?.startLessonGeneration?.(); }
  function finishActivity(label, detail) { global.LearningActivity?.finish(label, detail); }
  function codeFilename(language) { return ({ python: "main.py", go: "main.go", java: "Main.java", rust: "main.rs" })[language] || "notes.md"; }

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
      button.textContent = String(index + 1);
      button.className = index === state.pageIndex ? "is-active" : "";
      button.setAttribute("aria-label", `第 ${index + 1} 页：${page.title}`);
      button.disabled = index > blockingIndex && blockingIndex >= 0;
      button.addEventListener("click", () => showPage(index));
      return button;
    });
    byId("pageDots").replaceChildren(...dots);
  }

  async function checkOption(page, option, button) {
    [...byId("pageOptions").querySelectorAll("button")].forEach((item) => { item.disabled = true; });
    showQuestionFeedback("正在检查这道题…马上告诉你哪里对、下一步怎么做。 ");
    startActivity("正在检查这道题", "答案会显示在题目下方；不需要再去别处提交。 ");
    try {
      const response = await fetch("/api/lesson/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, lesson_id: state.manifest.lesson_id, page_id: page.id, selected_option_id: option.id }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail?.message || "暂时无法批改，请再试一次。");
      button.dataset.result = result.correct ? "correct" : "incorrect";
      state.quizAttempts = state.quizAttempts.filter((attempt) => attempt.page_id !== page.id);
      state.quizAttempts.push({ page_id: page.id, correct: Boolean(result.correct) });
      global.InterviewBankController?.load?.();
      state.onResult?.({ ...result, question: page.question, answer: option.label });
      if (result.correct) {
        showQuestionFeedback(`${result.feedback || "答对了。"} 下一步：900ms 后自动进入下一页。`, "correct");
        finishActivity("答对了", "这一页已通过，马上进入下一小步。 ");
        window.setTimeout(() => showPage(Math.min(state.pageIndex + 1, state.manifest.pages.length - 1)), 900);
      } else {
        showQuestionFeedback(`${result.feedback || "还差一点。"} 下一步：再选一次；需要提示可以点右侧“给我提示”。`, "incorrect");
        finishActivity("还差一点", "答案提示已经显示在题目下方，可以马上再试。 ");
        [...byId("pageOptions").querySelectorAll("button")].forEach((item) => { item.disabled = false; });
      }
    } catch (error) {
      state.onResult?.({ correct: false, verified: false, feedback: error.message });
      showQuestionFeedback(`暂时无法检查：${error.message}。下一步：点击选项重试。`, "incorrect");
      finishActivity("检查没有完成", "你的选择没有丢失，重新点击即可。 ");
      [...byId("pageOptions").querySelectorAll("button")].forEach((item) => { item.disabled = false; });
    }
  }

  function renderQuestion(page) {
    const section = byId("pageQuestion");
    section.hidden = !page.question;
    if (!page.question) { byId("pageOptions").replaceChildren(); return; }
    byId("questionFeedback").hidden = true;
    setText("pageQuestionText", page.question);
    const buttons = (page.options || []).slice(0, 10).map((option, index) => {
      const button = document.createElement("button");
      button.type = "button";
      const badge = document.createElement("span"); badge.textContent = String.fromCharCode(65 + index);
      const label = document.createElement("span"); label.textContent = option.label;
      button.append(badge, label);
      button.addEventListener("click", () => checkOption(page, option, button));
      return button;
    });
    byId("pageOptions").replaceChildren(...buttons);
  }

  function pageInstruction(page) {
    if (page.type === "check" || page.question) return "直接点击一个选项。答对后会自动进入下一页；答错可以马上重选。";
    if (page.type === "practice") return "这是课后练习，不是课堂门禁。打开练习文件夹自己完成；代码、结果或问题直接发到右侧输入栏。";
    if (page.type === "mastery" && state.manifest?.completion_mode === "choice") return "这个概念的必答题通过后，点击“完成这个概念”即可。";
    if (page.type === "mastery") return "课堂到这里结束。课后自己练；愿意讨论时，把代码、运行结果或问题直接发到右侧输入栏。";
    if (page.code) return "先读这段代码，确认它做什么；理解后点击下一页继续。";
    return "读完这一页，抓住它解决的问题，再点击下一页。";
  }

  function renderPageInstruction(page) {
    byId("pageInstructionText").textContent = pageInstruction(page);
    byId("pageInstruction").hidden = false;
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
    setText("homeworkTitle", homework.title);
    byId("homeworkDescription").innerHTML = global.MarkdownRenderer.render(homework.markdown || "打开练习文件夹，自己完成这道课后练习。");
    global.MarkdownRenderer.hydrate(byId("homeworkDescription"));
    setText("homeworkPath", homework.practice_path || state.manifest.practice_path);
  }

  function renderInterviewPrompts() {
    const prompts = state.manifest?.interview_prompts || [];
    const section = byId("lessonInterviewPrompts");
    section.hidden = !prompts.length;
    if (!prompts.length) { byId("lessonInterviewPromptList").replaceChildren(); return; }
    byId("lessonInterviewPromptList").replaceChildren(...prompts.map((prompt, index) => {
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = `${index + 1}. ${prompt.question}`;
      const answer = document.createElement("div"); answer.className = "markdown-body";
      const structure = (prompt.answer_structure || []).map((item) => `- ${item}`).join("\n");
      const omissions = (prompt.common_omissions || []).map((item) => `- ${item}`).join("\n");
      const followUps = (prompt.follow_ups || []).map((item) => (
        `- **${item.prompt}**：${(item.answer_points || []).join("、")}`
      )).join("\n");
      answer.innerHTML = global.MarkdownRenderer.render(
        `#### 参考答案\n\n${prompt.reference_answer}\n\n**回答结构**\n\n${structure}`
        + (omissions ? `\n\n**常见遗漏**\n\n${omissions}` : "")
        + (followUps ? `\n\n**常见追问**\n\n${followUps}` : ""),
      );
      global.MarkdownRenderer.hydrate(answer);
      details.append(summary, answer); return details;
    }));
  }

  function renderLessonNotes(notes) {
    state.notes = Array.isArray(notes) ? notes : [];
    const panel = byId("lessonNotesPanel"); const list = byId("lessonNotesList");
    panel.hidden = state.notes.length === 0;
    if (!state.notes.length) { list.replaceChildren(); setText("lessonReward", ""); return; }
    list.replaceChildren(...state.notes.map((note, index) => {
      const article = document.createElement("article");
      const title = document.createElement("strong"); title.textContent = `笔记 ${index + 1}${note.important ? " · 重点" : ""}`;
      const question = document.createElement("p"); question.textContent = `我的问题：${note.question || ""}`;
      const summary = document.createElement("p"); summary.textContent = `教练总结：${note.summary || ""}`;
      article.append(title, question, summary); return article;
    }));
    setText("lessonReward", state.notes[state.notes.length - 1]?.reward || "");
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
    byId("reviewCardPanel").hidden = true;
    document.querySelector(".page-navigation").hidden = false;
    const requestedIndex = Math.max(0, Math.min(index, state.manifest.pages.length - 1));
    const blockingIndex = requestedIndex > state.pageIndex ? firstBlockingCheck(requestedIndex) : -1;
    state.pageIndex = blockingIndex >= 0 ? blockingIndex : requestedIndex;
    const page = state.manifest.pages[state.pageIndex];
    const total = state.manifest.pages.length;
    setText("pageCount", `第 ${state.pageIndex + 1} 页 / 共 ${total} 页`);
    setText("pageEyebrow", page.eyebrow || "当前小步");
    setText("pageTitle", page.title);
    byId("pageMarkdown").innerHTML = global.MarkdownRenderer.render(page.markdown || "");
    global.MarkdownRenderer.hydrate(byId("pageMarkdown"));
    const codeBlock = byId("pageCodeBlock");
    codeBlock.hidden = !page.code;
    if (page.code) {
      setText("codeFilename", codeFilename(page.language));
      byId("pageCode").className = `language-${page.language || "text"}`;
      byId("pageCode").innerHTML = global.MarkdownRenderer.highlightCode(page.code, page.language);
    }
    renderQuestion(page);
    renderPageInstruction(page);
    const path = page.practice_path || (page.type === "practice" ? state.manifest.practice_path : "");
    byId("practiceLocation").hidden = !path;
    setText("practicePath", path);
    byId("previousPageBtn").disabled = state.pageIndex === 0;
    const isFinal = state.pageIndex === total - 1;
    byId("lessonCompletionPanel").hidden = !isFinal;
    byId("nextPageBtn").hidden = isFinal;
    byId("nextPageBtn").disabled = isFinal || Boolean(page.question && (page.options || []).length && !passedCheck(page.id));
    if (blockingIndex >= 0) showQuestionFeedback("这一页需要先答对，才能继续看后面的内容。直接点击一个选项即可。", "incorrect");
    if (isFinal) {
      const choiceOnly = state.manifest.completion_mode === "choice";
      setText("completionPrompt", choiceOnly
        ? "必答选择题都答对就能完成；不需要写代码、粘贴终端输出或额外解释。"
        : "本章课堂已经讲完。课后练习留在真实项目里，你可以自己消化；完成后的代码、运行结果或问题直接发到右侧输入栏。系统不再检查打印输出。 ");
      renderHomework();
      renderInterviewPrompts();
      setText("completeSubmitBtn", choiceOnly ? "完成这个概念" : "完成课堂，进入下一章");
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
      state.onResult?.({ correct: false, verified: false, feedback: "这道练习属于其他课程，请先在设置里切换到对应学习项目。" });
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
    state.pageIndex = 0;
    state.quizAttempts = [];
    state.completionDecision = null;
    byId("completionResult").hidden = true;
    byId("lessonPrimaryAction").hidden = true;
    byId("chatPrimaryAction").hidden = true;
    byId("nextPageBtn").hidden = false;
    setText("lessonCounter", `本章 1 / ${payload.pages.length}`);
    setText("lessonRemaining", `预计还需 ${payload.progress.remaining_minutes} 分钟`);
    setText("remainingTime", `预计还需 ${payload.progress.remaining_minutes} 分钟`);
    showPage(0);
    loadLessonNotes();
    return payload;
  }

  function showLessonLoadFailure(message) {
    state.manifest = null;
    setText("pageCount", "课程尚未就绪");
    setText("pageEyebrow", "准备没有完成");
    setText("pageTitle", "课程生成失败");
    setText("lessonLoadErrorText", `${message || "这次课程没有生成完成。"}学习进度没有丢失，可以直接重试。`);
    byId("lessonLoadError").hidden = false;
    byId("pageMarkdown").replaceChildren();
    ["pageInstruction", "pageCodeBlock", "pageQuestion", "practiceLocation", "lessonNotesPanel", "lessonCompletionPanel"].forEach((id) => { byId(id).hidden = true; });
    byId("previousPageBtn").disabled = true;
    byId("nextPageBtn").hidden = true;
    byId("pageDots").replaceChildren();
  }

  async function loadCurrentLesson(retryStale = true) {
    byId("lessonLoadError").hidden = true;
    startActivity("正在准备讲义", "正在检查当前知识点，并生成这一节的讲解与练习。 ");
    try {
      let response = await fetch(`/api/lesson/current?user_id=${encodeURIComponent(userId)}`);
      let payload = await response.json().catch(() => ({}));
      if (!response.ok && payload.detail?.recovery === "generate_curriculum") {
        const curriculumResponse = await fetch("/api/curriculum/generate", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: userId }),
        });
        const curriculumResult = await curriculumResponse.json().catch(() => ({}));
        if (!curriculumResponse.ok) throw new Error(curriculumResult.detail?.message || "详细课程大纲没有生成成功。");
        response = await fetch(`/api/lesson/current?user_id=${encodeURIComponent(userId)}`);
        payload = await response.json().catch(() => ({}));
      }
      if (!response.ok && payload.detail?.recovery === "generate_lesson") {
        startLessonGeneration();
        response = await fetch("/api/lesson/generate", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: userId }),
        });
        payload = await response.json().catch(() => ({}));
      }
      if (!response.ok && payload.detail?.recovery === "stale_generation") {
        if (retryStale) {
          finishActivity("项目已经切换", "迟到课件已丢弃，正在读取当前项目。 ");
          return loadCurrentLesson(false);
        }
        throw new Error("项目已经切换，请确认当前学习计划后再生成讲义。");
      }
      if (!response.ok) throw new Error(payload.detail?.message || "课程暂时没有准备好。");
      const manifest = applyManifest(payload);
      finishActivity("讲义已准备好", "先阅读这一页；有题时直接点击答案。 ");
      return manifest;
    } catch (error) {
      showLessonLoadFailure(error.message);
      finishActivity("讲义生成失败", "已在讲义区显示失败原因和重试按钮。");
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
    setText("completionVerdict", result.verdict === "advance" ? "课堂已经完成" : result.verdict === "practice" ? "再练一小步" : "换个角度重新理解");
    setText("completionFeedback", result.feedback);
    ["lessonPrimaryAction", "chatPrimaryAction"].forEach((id) => {
      const button = byId(id); button.textContent = result.cta_label; button.hidden = false;
    });
    state.onResult?.({ ...result, correct: result.verdict === "advance", verified: result.verdict === "advance" });
  }

  async function submitCompletion(action) {
    if (!state.manifest) return;
    setCompletionBusy(true);
    const choiceOnly = state.manifest.completion_mode === "choice";
    startActivity(choiceOnly ? "正在确认概念检测" : "正在保存课堂进度", "只确认课堂选择题；课后练习不会做输出检测。 ");
    try {
      const response = await fetch("/api/lesson/complete", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId, lesson_id: state.manifest.lesson_id, action,
          quiz_attempts: state.quizAttempts,
        }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail?.message || "本章评价没有成功，请重试。");
      showCompletionDecision(result);
      finishActivity(result.verdict === "advance" ? "课堂进度已保存" : "还有课堂题未完成", result.verdict === "advance" ? `课后练习已留好。点击“${result.cta_label}”继续。` : "回到课堂选择题再试一次。 ");
    } catch (error) {
      state.onResult?.({ correct: false, verified: false, feedback: error.message });
      finishActivity("课堂进度没有保存", "选择题记录仍在，可以直接重试。 ");
    } finally { setCompletionBusy(false); }
  }

  async function runPrimaryAction() {
    const decision = state.completionDecision;
    if (!decision) return;
    if (decision.verdict === "advance" && !decision.next_knowledge_point_id) {
      byId("planDialog").showModal();
      document.dispatchEvent(new CustomEvent("learning-agent:course-complete", { detail: decision }));
      return;
    }
    setCompletionBusy(true);
    startActivity("正在生成下一小节", "正在根据这次评价准备下一份讲义和练习。 ");
    try {
      const response = await fetch("/api/lesson/generate", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, force: decision.verdict !== "advance", remediation: decision.verdict === "advance" ? "" : decision.feedback, next_knowledge_point_id: decision.next_knowledge_point_id }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok && payload.detail?.recovery === "stale_generation") {
        await loadCurrentLesson(false);
        finishActivity("项目已经切换", "已安全丢弃旧课件，并读取当前课程。 ");
        return;
      }
      if (!response.ok) throw new Error(payload.detail?.message || "下一步课程没有生成成功，请重试。");
      applyManifest(payload);
      document.dispatchEvent(new CustomEvent("learning-agent:lesson-transition", { detail: decision }));
      finishActivity("下一小节已准备好", "从讲义第 1 页开始；每一步都会告诉你接下来做什么。 ");
    } catch (error) {
      state.onResult?.({ correct: false, verified: false, feedback: error.message });
      finishActivity("下一小节没有生成", "当前讲义仍保留，点击按钮即可重试。 ");
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
    splitter.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
      event.preventDefault();
      const current = parseFloat(getComputedStyle(shell).getPropertyValue("--coach-width")) || 390;
      setWidth(current + (event.key === "ArrowLeft" ? 24 : -24));
    });
  }

  async function openPracticeFolder(path, button) {
    button.disabled = true;
    try {
      const response = await fetch("/api/practice/open", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, path }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail?.message || "文件夹暂时无法打开。");
      button.textContent = "✓ 已打开";
    } catch (error) {
      button.textContent = "重试打开";
      state.onResult?.({ correct: false, verified: false, feedback: error.message });
    } finally {
      window.setTimeout(() => { button.disabled = false; button.textContent = "打开练习文件夹"; }, 1600);
    }
  }

  function bind() {
    byId("retryLessonBtn").addEventListener("click", async () => {
      const button = byId("retryLessonBtn");
      button.disabled = true; button.innerHTML = '<i class="bi bi-arrow-clockwise" aria-hidden="true"></i>正在重新生成…';
      try { await loadCurrentLesson(); }
      catch { /* The persistent error panel already explains the retry result. */ }
      finally { button.disabled = false; button.innerHTML = '<i class="bi bi-arrow-clockwise" aria-hidden="true"></i>重新生成课程'; }
    });
    byId("previousPageBtn").addEventListener("click", () => showPage(state.pageIndex - 1));
    byId("nextPageBtn").addEventListener("click", () => showPage(state.pageIndex + 1));
    byId("completeSubmitBtn").addEventListener("click", () => submitCompletion("submit"));
    byId("lessonPrimaryAction").addEventListener("click", runPrimaryAction);
    byId("chatPrimaryAction").addEventListener("click", runPrimaryAction);
    byId("copyCodeBtn").addEventListener("click", async () => {
      const button = byId("copyCodeBtn");
      const original = "复制代码";
      button.disabled = true;
      try {
        await navigator.clipboard.writeText(state.manifest?.pages[state.pageIndex]?.code || "");
        button.textContent = "✓ 已复制";
      } catch {
        button.textContent = "复制失败";
      } finally {
        window.setTimeout(() => { button.disabled = false; button.textContent = original; }, 1500);
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
