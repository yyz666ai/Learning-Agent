"use strict";

(function createInterviewBankController() {
  const $ = (selector) => document.querySelector(selector);
  const answerLabels = { missing: "答案待生成", draft: "讲解草稿", ready: "已有讲解" };
  const masteryLabels = { unrated: "尚未练习", forgot: "没想起来", hard: "有点困难", smooth: "顺利" };
  const sourceLabels = { classroom: "课堂选择题", homework: "课后作业", supplemental: "追加练习", interview: "面试题", important_question: "重要问题" };
  const statusLabels = { unattempted: "尚未练习", incorrect: "错题 · 再做一遍", mastered: "已掌握", pending: "待完成" };
  const studyChoices = [
    { value: "from_scratch", label: "逐题从头讲", detail: "每道题先建立直觉，再练面试表达" },
    { value: "systematic", label: "系统学习", detail: "按知识依赖重排，补齐相关知识体系" },
    { value: "assess_first", label: "先测后学", detail: "先像真实面试一样回答，再针对薄弱处讲" },
  ];
  let userId = "yang";
  let hooks = {};
  let bank = { questions: [], coverage: { mastered: 0, total: 0, percent: 0 } };
  let reviewSession = { cards: [], total: 0, index: 0 };

  function shouldIntake(text) {
    const value = text.trim();
    const questionMarks = (value.match(/[？?]/g) || []).length;
    const numberedLines = (value.match(/(?:^|\n)\s*\d{1,3}[.)、]/g) || []).length;
    return /^(?:面试题|题目|收录)[：:]/.test(value) || questionMarks >= 2 || numberedLines >= 2;
  }

  function activateTab(name) {
    const bankActive = name === "bank";
    $("#railOutlineTab").classList.toggle("is-active", !bankActive);
    $("#railBankTab").classList.toggle("is-active", bankActive);
    $("#railOutlineTab").setAttribute("aria-selected", String(!bankActive));
    $("#railBankTab").setAttribute("aria-selected", String(bankActive));
    $("#outlinePanel").hidden = bankActive;
    $("#interviewBankPanel").hidden = !bankActive;
  }

  function render() {
    const coverage = bank.coverage || { mastered: 0, total: 0, percent: 0 };
    $("#bankCoverage").textContent = `${coverage.percent || 0}%`;
    $("#bankCoverageMeta").textContent = `已掌握 ${coverage.mastered || 0} / 共 ${coverage.total || 0} 题`;
    $("#bankCount").textContent = String(coverage.total || 0);
    $("#bankEmpty").hidden = Boolean(bank.questions?.length);
    $("#interviewQuestionList").replaceChildren(...(bank.questions || []).map((question, index) => {
      const item = document.createElement("li");
      const button = document.createElement("button"); button.type = "button";
      const count = document.createElement("span"); count.className = "bank-question-index"; count.textContent = String(index + 1).padStart(2, "0");
      const copy = document.createElement("span"); copy.className = "bank-question-copy";
      const title = document.createElement("strong"); title.textContent = question.normalized_text || question.title;
      const status = document.createElement("small");
      const storedInterview = question.source === "interview" && String(question.id).startsWith("iq_");
      const firstStatus = storedInterview
        ? (answerLabels[question.answer_status] || "答案待生成")
        : (sourceLabels[question.source] || "练习");
      const secondStatus = storedInterview
        ? (masteryLabels[question.mastery] || statusLabels[question.status] || "尚未练习")
        : (statusLabels[question.status] || "尚未练习");
      status.innerHTML = `<span>${firstStatus}</span><i aria-hidden="true"></i><span>${secondStatus}</span>`;
      copy.append(title, status); button.append(count, copy);
      button.addEventListener("click", () => {
        if (question.source === "interview" && String(question.id).startsWith("iq_")) openQuestion(question.id);
        else if (["supplemental", "important_question", "interview"].includes(question.source)) openPracticeItem(question);
        else window.ArtifactController?.openPracticeItem(question);
      }); item.append(button); return item;
    }));
  }

  function showStudyChoices(intake) {
    $("#choiceTrayHint").textContent = `已收录 ${intake.new_count} 道新题，想怎么掌握？`;
    $("#choiceProgress").textContent = "选 1 项就开始";
    $("#inlineChoices").replaceChildren(...studyChoices.map((choice, index) => {
      const button = document.createElement("button"); button.type = "button"; button.className = "inline-choice";
      button.innerHTML = `<span class="inline-choice-index">${index + 1}</span><span><strong>${choice.label}</strong><small>${choice.detail}</small></span>`;
      button.addEventListener("click", () => chooseMode(choice)); return button;
    }));
    $("#choiceTray").hidden = false;
  }

  async function chooseMode(choice) {
    const response = await fetch("/api/interview/study-mode", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, mode: choice.value }),
    });
    if (!response.ok) throw new Error("学习方式暂时没有保存成功");
    $("#choiceTray").hidden = true;
    hooks.addUser?.(choice.label);
    hooks.addAgent?.(`好，我们按「${choice.label}」开始。我先带你完成第一道，后续相关知识会自动接入大纲。`);
    if (bank.questions?.[0]) await openQuestion(bank.questions[0].id, choice.value);
  }

  async function intake(rawText) {
    hooks.addUser?.(rawText);
    const response = await fetch("/api/interview/intake", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, raw_text: rawText, source: "chat" }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "面试题暂时没有收录成功");
    await load(); activateTab("bank");
    hooks.addAgent?.(`已整理 ${payload.intake.source_count} 道题：新增 ${payload.intake.new_count} 道，重复 ${payload.intake.duplicate_count} 道。原文也已经保留。`);
    showStudyChoices(payload.intake);
    return payload;
  }

  async function load() {
    const response = await fetch(`/api/practice/bank?user_id=${encodeURIComponent(userId)}`);
    if (!response.ok) return;
    bank = await response.json(); render();
    await refreshReviewCount();
  }

  async function fetchReviewSession() {
    const response = await fetch(`/api/practice/review/session?user_id=${encodeURIComponent(userId)}`);
    if (!response.ok) throw new Error("复习题暂时没有加载成功");
    return response.json();
  }

  async function refreshReviewCount() {
    try {
      const session = await fetchReviewSession();
      $("#bankDueCount").textContent = `今日 ${session.due_count || 0} 题`;
      $("#startBankReviewBtn").disabled = !(session.due_count || 0);
    } catch {
      $("#bankDueCount").textContent = "稍后重试";
    }
  }

  function toggleReviewMode(active) {
    if (active) {
      ["#pageCount", "#pageEyebrow", "#pageTitle", "#pageMarkdown", "#pageInstruction", "#pageCodeBlock", "#pageQuestion", "#practiceLocation", "#lessonNotesPanel", "#lessonInterviewPrompts", "#lessonCompletionPanel"]
        .forEach((selector) => { $(selector).hidden = true; });
    }
    $("#reviewCardPanel").hidden = !active;
    document.querySelector(".page-navigation").hidden = active;
  }

  function renderReviewCard() {
    const card = reviewSession.cards[reviewSession.index];
    if (!card) {
      $("#reviewCardProgress").textContent = "本轮复习完成";
      $("#reviewCardSource").textContent = "薄弱点已经重新安排";
      $("#reviewCardQuestion").textContent = "今天的复习完成了";
      $("#reviewCardOptions").replaceChildren();
      $("#reviewCardAnswer").hidden = false;
      $("#reviewCardAnswer").innerHTML = window.MarkdownRenderer.render("做得好。做错或回忆困难的内容会更早再次出现，你可以继续在对话框要求 **再出几道题**。");
      $("#revealReviewAnswerBtn").hidden = true;
      $("#reviewRatingActions").hidden = true;
      hooks.addAgent?.("本轮复习完成。困难内容已经重新安排，不会因为打开过卡片就算作掌握。");
      return;
    }
    $("#reviewCardProgress").textContent = `复习 ${reviewSession.index + 1} / ${reviewSession.cards.length}`;
    $("#reviewCardSource").textContent = `${sourceLabels[card.source] || "练习题"} · 先回忆，再看答案`;
    $("#reviewCardQuestion").textContent = card.prompt || card.normalized_text || card.title;
    $("#reviewCardOptions").replaceChildren(...(card.options || []).map((option) => {
      const line = document.createElement("p");
      const mark = document.createElement("span"); mark.textContent = String(option.id || "").toUpperCase();
      const label = document.createElement("strong"); label.textContent = option.label;
      line.append(mark, label); return line;
    }));
    $("#reviewCardAnswer").hidden = true;
    $("#reviewCardAnswer").replaceChildren();
    $("#revealReviewAnswerBtn").hidden = false;
    $("#revealReviewAnswerBtn").disabled = false;
    $("#reviewRatingActions").hidden = true;
  }

  async function startReview() {
    try {
      const session = await fetchReviewSession();
      if (!session.cards?.length) {
        hooks.showToast?.("今天暂时没有到期复习题");
        return;
      }
      reviewSession = { ...session, index: 0 };
      document.querySelector("#appShell").classList.remove("is-chat-first");
      toggleReviewMode(true);
      renderReviewCard();
    } catch (error) {
      hooks.showToast?.(error.message);
    }
  }

  function openPracticeItem(question) {
    reviewSession = { cards: [question], total: 1, due_count: 1, index: 0 };
    document.querySelector("#appShell").classList.remove("is-chat-first");
    toggleReviewMode(true);
    renderReviewCard();
  }

  async function revealReviewAnswer() {
    const card = reviewSession.cards[reviewSession.index];
    if (!card) return;
    $("#revealReviewAnswerBtn").disabled = true;
    try {
      const response = await fetch("/api/practice/review/reveal", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, item_id: card.id }),
      });
      const answer = await response.json();
      if (!response.ok) throw new Error(answer.detail || "答案暂时没有加载成功");
      const lastWrong = answer.last_wrong?.selected_option_id
        ? `\n\n> 上次易错记录：选择了 ${String(answer.last_wrong.selected_option_id).toUpperCase()}` : "";
      $("#reviewCardAnswer").innerHTML = window.MarkdownRenderer.render(
        `### 参考答案\n\n**${answer.answer}**\n\n${answer.explanation || ""}${lastWrong}`,
      );
      window.MarkdownRenderer.hydrate($("#reviewCardAnswer"));
      $("#reviewCardAnswer").hidden = false;
      $("#revealReviewAnswerBtn").hidden = true;
      $("#reviewRatingActions").hidden = false;
    } catch (error) {
      hooks.showToast?.(error.message);
      $("#revealReviewAnswerBtn").disabled = false;
    }
  }

  async function rateReview(rating) {
    const card = reviewSession.cards[reviewSession.index];
    if (!card) return;
    const labels = { forgot: "没想起来", hard: "稍微有点困难", easy: "顺利" };
    const buttons = $("#reviewRatingActions").querySelectorAll("button");
    buttons.forEach((button) => { button.disabled = true; });
    try {
      const response = await fetch("/api/practice/review/rate", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, item_id: card.id, rating }),
      });
      const saved = await response.json();
      if (!response.ok) throw new Error(saved.detail || "复习记录没有保存成功");
      hooks.addUser?.(labels[rating]);
      reviewSession.index += 1;
      await load();
      renderReviewCard();
    } catch (error) {
      hooks.showToast?.(error.message);
    } finally {
      buttons.forEach((button) => { button.disabled = false; });
    }
  }

  function showMasteryChoices(question) {
    $("#choiceTrayHint").textContent = "这道面试题现在掌握得怎么样？";
    $("#choiceProgress").textContent = "用于安排复习";
    const options = [
      ["forgot", "没想起来", "红色 · 很快再出现"],
      ["hard", "有点困难", "黄色 · 缩短复习间隔"],
      ["smooth", "顺利", "绿色 · 延长复习间隔"],
    ];
    $("#inlineChoices").replaceChildren(...options.map(([value, label, detail], index) => {
      const button = document.createElement("button"); button.type = "button"; button.className = `inline-choice rating-${value === "forgot" ? "red" : value === "hard" ? "yellow" : "green"}`;
      button.innerHTML = `<span class="inline-choice-index">${index + 1}</span><span><strong>${label}</strong><small>${detail}</small></span>`;
      button.addEventListener("click", () => rate(question.id, value, label)); return button;
    }));
    $("#choiceTray").hidden = false;
  }

  async function rate(questionId, mastery, label) {
    const response = await fetch(`/api/interview/questions/${questionId}/mastery`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, mastery }),
    });
    if (!response.ok) throw new Error("掌握情况暂时没有保存成功");
    await response.json(); await load();
    hooks.addUser?.(label); hooks.addAgent?.("已记录。复习时间会根据这次回忆难度自动安排。");
    $("#choiceTray").hidden = true;
  }

  async function openQuestion(questionId, mode) {
    let response = await fetch(`/api/interview/questions/${questionId}?user_id=${encodeURIComponent(userId)}`);
    let question = (await response.json()).question;
    if (question.answer_status !== "ready") {
      response = await fetch(`/api/interview/questions/${questionId}/expand`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, mode: mode || bank.study_mode || "systematic" }),
      });
      if (!response.ok) throw new Error("讲解生成失败，请稍后重试");
      question = (await response.json()).question; await load();
    }
    document.querySelector("#appShell").classList.remove("is-chat-first");
    $("#pageCount").textContent = "面试题 · 系统讲解";
    $("#pageEyebrow").textContent = "从会看，到会答，再到能应对追问";
    $("#pageTitle").textContent = question.normalized_text;
    $("#pageMarkdown").innerHTML = window.MarkdownRenderer.render(question.answer_markdown);
    window.MarkdownRenderer.hydrate($("#pageMarkdown"));
    ["#pageInstruction", "#pageCodeBlock", "#pageQuestion", "#practiceLocation", "#lessonNotesPanel", "#lessonInterviewPrompts", "#lessonCompletionPanel"]
      .forEach((selector) => { $(selector).hidden = true; });
    showMasteryChoices(question);
  }

  async function openBank() {
    toggleReviewMode(false);
    await load();
    activateTab("bank");
    document.querySelector("#appShell").classList.remove("is-chat-first");
    $("#pageCount").textContent = "练习题库";
    $("#pageEyebrow").textContent = "课堂、课后和面试统一回顾";
    $("#pageTitle").textContent = bank.questions?.length ? "选择左侧的一道题" : "题库还是空的";
    $("#pageMarkdown").innerHTML = window.MarkdownRenderer.render(
      bank.questions?.length
        ? `已经收录 **${bank.questions.length} 道练习**。做错的题会明确标记“再做一遍”；点一项就回到它所在的课程页。`
        : "开始一节课后，课堂题和课后作业会自动收录在这里。"
    );
    window.MarkdownRenderer.hydrate($("#pageMarkdown"));
    $("#pageCodeBlock").hidden = true; $("#pageQuestion").hidden = true; $("#practiceLocation").hidden = true;
    $("#pageCount").hidden = false; $("#pageEyebrow").hidden = false; $("#pageTitle").hidden = false; $("#pageMarkdown").hidden = false;
    $("#pageDots").replaceChildren(); $("#previousPageBtn").disabled = true; $("#nextPageBtn").disabled = true;
  }

  function init(options) {
    userId = options.userId || userId; hooks = options;
    $("#railOutlineTab").addEventListener("click", () => activateTab("outline"));
    $("#railBankTab").addEventListener("click", () => activateTab("bank"));
    $("#refreshInterviewBank").addEventListener("click", load);
    $("#startBankReviewBtn").addEventListener("click", startReview);
    $("#revealReviewAnswerBtn").addEventListener("click", revealReviewAnswer);
    $("#closeReviewCardBtn").addEventListener("click", openBank);
    $("#reviewRatingActions").querySelectorAll("[data-review-rating]").forEach((button) => {
      button.addEventListener("click", () => rateReview(button.dataset.reviewRating));
    });
    load();
  }

  window.InterviewBankController = { init, intake, load, shouldIntake, openBank, startReview, openPracticeItem };
}());
