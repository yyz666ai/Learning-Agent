"use strict";

(function createInterviewBankController() {
  const $ = (selector) => document.querySelector(selector);
  const answerLabels = { missing: "答案待生成", draft: "讲解草稿", ready: "已有讲解" };
  const masteryLabels = { unrated: "尚未练习", forgot: "没想起来", hard: "有点困难", smooth: "顺利" };
  const sourceLabels = { classroom: "课堂选择题", homework: "课后作业", interview: "面试题" };
  const statusLabels = { unattempted: "尚未练习", incorrect: "错题 · 再做一遍", mastered: "已掌握", pending: "待完成" };
  const studyChoices = [
    { value: "from_scratch", label: "逐题从头讲", detail: "每道题先建立直觉，再练面试表达" },
    { value: "systematic", label: "系统学习", detail: "按知识依赖重排，补齐相关知识体系" },
    { value: "assess_first", label: "先测后学", detail: "先像真实面试一样回答，再针对薄弱处讲" },
  ];
  let userId = "yang";
  let hooks = {};
  let bank = { questions: [], coverage: { mastered: 0, total: 0, percent: 0 } };

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
      const firstStatus = question.source === "interview"
        ? (answerLabels[question.answer_status] || "答案待生成")
        : (sourceLabels[question.source] || "练习");
      const secondStatus = question.source === "interview"
        ? (masteryLabels[question.mastery] || statusLabels[question.status] || "尚未练习")
        : (statusLabels[question.status] || "尚未练习");
      status.innerHTML = `<span>${firstStatus}</span><i aria-hidden="true"></i><span>${secondStatus}</span>`;
      copy.append(title, status); button.append(count, copy);
      button.addEventListener("click", () => {
        if (question.source === "interview") openQuestion(question.id);
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
    $("#pageCodeBlock").hidden = true; $("#pageQuestion").hidden = true; $("#practiceLocation").hidden = true;
    showMasteryChoices(question);
  }

  async function openBank() {
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
    $("#pageDots").replaceChildren(); $("#previousPageBtn").disabled = true; $("#nextPageBtn").disabled = true;
  }

  function init(options) {
    userId = options.userId || userId; hooks = options;
    $("#railOutlineTab").addEventListener("click", () => activateTab("outline"));
    $("#railBankTab").addEventListener("click", () => activateTab("bank"));
    $("#refreshInterviewBank").addEventListener("click", load);
    load();
  }

  window.InterviewBankController = { init, intake, load, shouldIntake, openBank };
}());
