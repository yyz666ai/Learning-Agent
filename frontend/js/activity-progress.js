"use strict";
{
  const i18n = () => (typeof window !== "undefined" ? window : globalThis).LearningI18n;
  const t = (key, params = {}) => i18n()?.t(key, params) ?? String(key).replace(/\{(\w+)\}/g, (m, k) => params[k] == null ? m : String(params[k]));
  const bindUI = (node, property, render) => { if (i18n()) return i18n().bind(node, property, render); const value = render(); if (property.startsWith("@")) node.setAttribute(property.slice(1), value); else node[property] = value; return value; };
(function exposeActivityProgress(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.ActivityProgress = api;
}(typeof window === "undefined" ? globalThis : window, function createActivityProgress() {
  function formatDuration(milliseconds) {
    const seconds = Math.max(0, Math.ceil(milliseconds / 1000));
    if (seconds < 60) return t("{0} 秒", {0: seconds});
    const minutes = Math.ceil(seconds / 60);
    return t("{0} 分钟", {0: minutes});
  }

  function estimate(elapsedMs, estimateMs) {
    const elapsed = Math.max(0, Number(elapsedMs) || 0);
    const expected = Math.max(1000, Number(estimateMs) || 1000);
    if (elapsed >= expected) {
      return {
        percent: 92,
        completedPercent: 92,
        remainingPercent: 8,
        elapsedText: formatDuration(elapsed),
        get etaText() { return t("超出常见时间，仍在生成"); },
        label: t("已完成 92% · 剩余 8% · 已等待 {0} · 超出常见时间，仍在生成", {0: formatDuration(elapsed)}),
      };
    }
    const ratio = elapsed / expected;
    const percent = Math.max(4, Math.min(91, Math.round(8 + ratio * 76)));
    return {
      percent,
      completedPercent: percent,
      remainingPercent: 100 - percent,
      elapsedText: formatDuration(elapsed),
      etaText: formatDuration(expected - elapsed),
      label: t("已完成 {0}% · 剩余 {1}% · 已等待 {2} · 预计还需 {3}", {0: percent, 1: 100 - percent, 2: formatDuration(elapsed), 3: formatDuration(expected - elapsed)}),
    };
  }

  return { estimate, formatDuration };
}));

}
