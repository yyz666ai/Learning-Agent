"use strict";
(function (global) {
  function createQuoteState() {
    let manifest = null, draft = null;
    return {
      setManifest(value) {
        if (!value || manifest?.lesson_id !== value.lesson_id || manifest?.revision !== value.revision) draft = null;
        manifest = value;
      },
      select(pageId, text) {
        const quote = String(text || "").trim();
        if (!manifest?.revision || !manifest.pages.some(p => p.id === pageId) || !quote || quote.length > 2000) return false;
        draft = {lesson_id: manifest.lesson_id, page_id: pageId, revision: manifest.revision, quote};
        return true;
      },
      get() { return draft ? {...draft} : null; },
      clear() { draft = null; },
    };
  }
  if (typeof module !== "undefined") module.exports = {createQuoteState};
  if (!global.document) return;
  const state = createQuoteState();
  let manifest = null, page = null, candidate = null;
  const byId = id => global.document.getElementById(id);
  const button = global.document.createElement("button");
  button.type = "button"; button.id = "askSelectionBtn"; button.className = "ask-selection";
  button.textContent = "提问"; button.hidden = true;
  button.setAttribute("aria-label", "引用选中内容并提问");
  global.document.body.append(button);
  function render() {
    const quote = state.get(), panel = byId("lessonQuote");
    if (!panel) return;
    panel.hidden = !quote;
    byId("lessonQuoteText").textContent = quote ? `${manifest?.pages.find(p => p.id === quote.page_id)?.title || "课件引用"} · ${quote.quote}` : "";
  }
  function clear() { state.clear(); candidate = null; button.hidden = true; render(); }
  function capture() {
    const selection = global.getSelection();
    const text = selection?.toString().trim();
    const containers = ["pageTitle", "pageMarkdown", "pageCode", "pageQuestionText"].map(byId).filter(Boolean);
    const container = containers.find(node => node.contains(selection?.anchorNode) && node.contains(selection?.focusNode));
    if (!text || !container || !page || text.length > 2000 || !selection.rangeCount) { button.hidden = true; candidate = null; return; }
    candidate = {pageId: page.id, text};
    const rect = selection.getRangeAt(0).getBoundingClientRect();
    button.style.left = `${Math.max(8, Math.min(rect.left, global.innerWidth - 90))}px`;
    button.style.top = `${Math.max(8, rect.top - 48)}px`;
    button.hidden = false;
  }
  global.document.addEventListener("pointerup", event => { if (event.target !== button) capture(); });
  global.document.addEventListener("keyup", event => { if (event.key === "Escape") { button.hidden = true; candidate = null; } else if (event.key.startsWith("Arrow") || event.key === "Shift") capture(); });
  button.addEventListener("pointerdown", event => event.preventDefault());
  button.addEventListener("click", () => {
    if (candidate && state.select(candidate.pageId, candidate.text)) { render(); byId("chatInput").focus(); }
    button.hidden = true;
  });
  byId("removeLessonQuote").addEventListener("click", () => { clear(); byId("chatInput").focus(); });
  global.document.addEventListener("learning-agent:manifest-change", event => {
    manifest = event.detail; state.setManifest(manifest); candidate = null; button.hidden = true; render();
  });
  global.document.addEventListener("learning-agent:page-change", event => { page = event.detail.page; candidate = null; button.hidden = true; });
  global.LessonSelection = {get: state.get, clear};
})(typeof window !== "undefined" ? window : globalThis);
