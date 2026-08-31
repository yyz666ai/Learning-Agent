"use strict";
{
  const i18n = () => (typeof window !== "undefined" ? window : globalThis).LearningI18n;
  const t = (key, params = {}) => i18n()?.t(key, params) ?? String(key).replace(/\{(\w+)\}/g, (m, k) => params[k] == null ? m : String(params[k]));
  const resolveText = value => typeof value === "function" ? value() : value;
  const bindUI = (node, property, render) => { if (i18n()) return i18n().bind(node, property, render); const value = render(); if (property.startsWith("@")) node.setAttribute(property.slice(1), value); else node[property] = value; return value; };
(function createInterviewBankController() {
  const $ = (selector) => document.querySelector(selector);
  const answerLabels = { get missing() { return t("答案待生成"); }, get draft() { return t("讲解草稿"); }, get ready() { return t("已有讲解"); } };
  const masteryLabels = { get unrated() { return t("尚未练习"); }, get forgot() { return t("没想起来"); }, get hard() { return t("有点困难"); }, get smooth() { return t("顺利"); } };
  const sourceLabels = { get classroom() { return t("课堂选择题"); }, get homework() { return t("课后作业"); }, get supplemental() { return t("追加练习"); }, get interview() { return t("面试题"); }, get important_question() { return t("重要问题"); } };
  const statusLabels = { get unattempted() { return t("尚未练习"); }, get incorrect() { return t("错题 · 再做一遍"); }, get mastered() { return t("已掌握"); }, get pending() { return t("待完成"); } };
  const studyChoices = [
    { value: "from_scratch", get label() { return t("逐题从头讲"); }, get detail() { return t("每道题先建立直觉，再练面试表达"); } },
    { value: "systematic", get label() { return t("系统学习"); }, get detail() { return t("按知识依赖重排，补齐相关知识体系"); } },
    { value: "assess_first", get label() { return t("先测后学"); }, get detail() { return t("先像真实面试一样回答，再针对薄弱处讲"); } },
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
    bindUI($("#bankCoverage"), "textContent", () => `${coverage.percent || 0}%`);
    bindUI($("#bankCoverageMeta"), "textContent", () => t("已掌握 {0} / 共 {1} 题", {0: coverage.mastered || 0, 1: coverage.total || 0}));
    bindUI($("#bankCount"), "textContent", () => String(coverage.total || 0));
    $("#bankEmpty").hidden = Boolean(bank.questions?.length);
    $("#interviewQuestionList").replaceChildren(...(bank.questions || []).map((question, index) => {
      const item = document.createElement("li");
      const button = document.createElement("button"); button.type = "button";
      const count = document.createElement("span"); count.className = "bank-question-index"; bindUI(count, "textContent", () => String(index + 1).padStart(2, "0"));
      const copy = document.createElement("span"); copy.className = "bank-question-copy";
      const title = document.createElement("strong"); bindUI(title, "textContent", () => question.normalized_text || question.title);
      const status = document.createElement("small");
      const storedInterview = question.source === "interview" && String(question.id).startsWith("iq_");
      const firstStatus = () => storedInterview
        ? (answerLabels[question.answer_status] || t("答案待生成"))
        : (sourceLabels[question.source] || t("练习"));
      const secondStatus = () => storedInterview
        ? (masteryLabels[question.mastery] || statusLabels[question.status] || t("尚未练习"))
        : (statusLabels[question.status] || t("尚未练习"));
      const first = document.createElement("span"), separator = document.createElement("i"), second = document.createElement("span");
      separator.setAttribute("aria-hidden", "true");
      bindUI(first, "textContent", firstStatus); bindUI(second, "textContent", secondStatus);
      status.append(first, separator, second);
      copy.append(title, status); button.append(count, copy);
      button.addEventListener("click", () => {
        if (question.source === "interview" && String(question.id).startsWith("iq_")) openQuestion(question.id);
        else if (["supplemental", "important_question", "interview"].includes(question.source)) openPracticeItem(question);
        else window.ArtifactController?.openPracticeItem(question);
      }); item.append(button); return item;
    }));
  }

  function showStudyChoices(intake) {
    bindUI($("#choiceTrayHint"), "textContent", () => t("已收录 {0} 道新题，想怎么掌握？", {0: intake.new_count}));
    bindUI($("#choiceProgress"), "textContent", () => t("选 1 项就开始"));
    $("#inlineChoices").replaceChildren(...studyChoices.map((choice, index) => {
      const button = document.createElement("button"); button.type = "button"; button.className = "inline-choice";
      bindUI(button, "innerHTML", () => `<span class="inline-choice-index">${index + 1}</span><span><strong>${choice.label}</strong><small>${choice.detail}</small></span>`);
      button.addEventListener("click", () => chooseMode(choice)); return button;
    }));
    $("#choiceTray").hidden = false;
  }

  async function chooseMode(choice) {
    const response = await fetch("/api/interview/study-mode", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, mode: choice.value }),
    });
    if (!response.ok) throw new Error(t("学习方式暂时没有保存成功"));
    $("#choiceTray").hidden = true;
    hooks.addUser?.(choice.label);
    hooks.addAgent?.(t("好，我们按「{0}」开始。我先带你完成第一道，后续相关知识会自动接入大纲。", {0: choice.label}));
    if (bank.questions?.[0]) await openQuestion(bank.questions[0].id, choice.value);
  }

  async function intake(rawText) {
    hooks.addUser?.(rawText);
    const response = await fetch("/api/interview/intake", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, raw_text: rawText, source: "chat" }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || t("面试题暂时没有收录成功"));
    await load(); activateTab("bank");
    hooks.addAgent?.(t("已整理 {0} 道题：新增 {1} 道，重复 {2} 道。原文也已经保留。", {0: payload.intake.source_count, 1: payload.intake.new_count, 2: payload.intake.duplicate_count}));
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
    if (!response.ok) throw new Error(t("复习题暂时没有加载成功"));
    return response.json();
  }

  async function refreshReviewCount() {
    try {
      const session = await fetchReviewSession();
      bindUI($("#bankDueCount"), "textContent", () => t("今日 {0} 题", {0: session.due_count || 0}));
      $("#startBankReviewBtn").disabled = !(session.due_count || 0);
    } catch {
      bindUI($("#bankDueCount"), "textContent", () => t("稍后重试"));
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
      bindUI($("#reviewCardProgress"), "textContent", () => t("本轮复习完成"));
      bindUI($("#reviewCardSource"), "textContent", () => t("薄弱点已经重新安排"));
      bindUI($("#reviewCardQuestion"), "textContent", () => t("今天的复习完成了"));
      $("#reviewCardOptions").replaceChildren();
      $("#reviewCardAnswer").hidden = false;
      bindUI($("#reviewCardAnswer"), "innerHTML", () => window.MarkdownRenderer.render(t("做得好。做错或回忆困难的内容会更早再次出现，你可以继续在对话框要求 **再出几道题**。")));
      $("#revealReviewAnswerBtn").hidden = true;
      $("#reviewRatingActions").hidden = true;
      hooks.addAgent?.(t("本轮复习完成。困难内容已经重新安排，不会因为打开过卡片就算作掌握。"));
      return;
    }
    bindUI($("#reviewCardProgress"), "textContent", () => t("复习 {0} / {1}", {0: reviewSession.index + 1, 1: reviewSession.cards.length}));
    bindUI($("#reviewCardSource"), "textContent", () => t("{0} · 先回忆，再看答案", {0: sourceLabels[card.source] || t("练习题")}));
    bindUI($("#reviewCardQuestion"), "textContent", () => card.prompt || card.normalized_text || card.title);
    $("#reviewCardOptions").replaceChildren(...(card.options || []).map((option) => {
      const line = document.createElement("p");
      const mark = document.createElement("span"); bindUI(mark, "textContent", () => String(option.id || "").toUpperCase());
      const label = document.createElement("strong"); bindUI(label, "textContent", () => option.label);
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
        hooks.showToast?.(() => t("今天暂时没有到期复习题"));
        return;
      }
      reviewSession = { ...session, index: 0 };
      document.querySelector("#appShell").classList.remove("is-chat-first");
      toggleReviewMode(true);
      renderReviewCard();
    } catch (error) {
      hooks.showToast?.((window.LearningI18n?.errorText(error.message) ?? error.message));
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
      if (!response.ok) throw new Error(answer.detail || t("答案暂时没有加载成功"));
      const lastWrong = answer.last_wrong?.selected_option_id
        ? t("\n\n> 上次易错记录：选择了 {0}", {0: String(answer.last_wrong.selected_option_id).toUpperCase()}) : "";
      bindUI($("#reviewCardAnswer"), "innerHTML", () => window.MarkdownRenderer.render(
        t("### 参考答案\n\n**{0}**\n\n{1}{2}", {0: answer.answer, 1: answer.explanation || "", 2: lastWrong}),
      ));
      window.MarkdownRenderer.hydrate($("#reviewCardAnswer"));
      $("#reviewCardAnswer").hidden = false;
      $("#revealReviewAnswerBtn").hidden = true;
      $("#reviewRatingActions").hidden = false;
    } catch (error) {
      hooks.showToast?.((window.LearningI18n?.errorText(error.message) ?? error.message));
      $("#revealReviewAnswerBtn").disabled = false;
    }
  }

  async function rateReview(rating) {
    const card = reviewSession.cards[reviewSession.index];
    if (!card) return;
    const labels = { get forgot() { return t("没想起来"); }, get hard() { return t("稍微有点困难"); }, get easy() { return t("顺利"); } };
    const buttons = $("#reviewRatingActions").querySelectorAll("button");
    buttons.forEach((button) => { button.disabled = true; });
    try {
      const response = await fetch("/api/practice/review/rate", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, item_id: card.id, rating }),
      });
      const saved = await response.json();
      if (!response.ok) throw new Error(saved.detail || t("复习记录没有保存成功"));
      hooks.addUser?.(labels[rating]);
      reviewSession.index += 1;
      await load();
      renderReviewCard();
    } catch (error) {
      hooks.showToast?.((window.LearningI18n?.errorText(error.message) ?? error.message));
    } finally {
      buttons.forEach((button) => { button.disabled = false; });
    }
  }

  function showMasteryChoices(question) {
    bindUI($("#choiceTrayHint"), "textContent", () => t("这道面试题现在掌握得怎么样？"));
    bindUI($("#choiceProgress"), "textContent", () => t("用于安排复习"));
    const options = [
      ["forgot", "没想起来", "红色 · 很快再出现"],
      ["hard", "有点困难", "黄色 · 缩短复习间隔"],
      ["smooth", "顺利", "绿色 · 延长复习间隔"],
    ];
    $("#inlineChoices").replaceChildren(...options.map(([value, label, detail], index) => {
      const button = document.createElement("button"); button.type = "button"; button.className = `inline-choice rating-${value === "forgot" ? "red" : value === "hard" ? "yellow" : "green"}`;
      bindUI(button, "innerHTML", () => `<span class="inline-choice-index">${index + 1}</span><span><strong>${t(label)}</strong><small>${t(detail)}</small></span>`);
      button.addEventListener("click", () => rate(question.id, value, t(label))); return button;
    }));
    $("#choiceTray").hidden = false;
  }

  async function rate(questionId, mastery, label) {
    const response = await fetch(`/api/interview/questions/${questionId}/mastery`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, mastery }),
    });
    if (!response.ok) throw new Error(t("掌握情况暂时没有保存成功"));
    await response.json(); await load();
    hooks.addUser?.(label); hooks.addAgent?.(t("已记录。复习时间会根据这次回忆难度自动安排。"));
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
      if (!response.ok) throw new Error(t("讲解生成失败，请稍后重试"));
      question = (await response.json()).question; await load();
    }
    document.querySelector("#appShell").classList.remove("is-chat-first");
    bindUI($("#pageCount"), "textContent", () => t("面试题 · 系统讲解"));
    bindUI($("#pageEyebrow"), "textContent", () => t("从会看，到会答，再到能应对追问"));
    bindUI($("#pageTitle"), "textContent", () => question.normalized_text);
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
    bindUI($("#pageCount"), "textContent", () => t("练习题库"));
    bindUI($("#pageEyebrow"), "textContent", () => t("课堂、课后和面试统一回顾"));
    bindUI($("#pageTitle"), "textContent", () => bank.questions?.length ? t("选择左侧的一道题") : t("题库还是空的"));
    bindUI($("#pageMarkdown"), "innerHTML", () => window.MarkdownRenderer.render(
      bank.questions?.length
        ? t("已经收录 **{0} 道练习**。做错的题会明确标记“再做一遍”；点一项就回到它所在的课程页。", {0: bank.questions.length})
        : t("开始一节课后，课堂题和课后作业会自动收录在这里。")
    ));
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

}
