"use strict";

(function exposeActivityProgress(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.ActivityProgress = api;
}(typeof window === "undefined" ? globalThis : window, function createActivityProgress() {
  function formatDuration(milliseconds) {
    const seconds = Math.max(0, Math.ceil(milliseconds / 1000));
    if (seconds < 60) return `${seconds} 秒`;
    const minutes = Math.ceil(seconds / 60);
    return `${minutes} 分钟`;
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
        etaText: "超出常见时间，仍在生成",
        label: `已完成 92% · 剩余 8% · 已等待 ${formatDuration(elapsed)} · 超出常见时间，仍在生成`,
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
      label: `已完成 ${percent}% · 剩余 ${100 - percent}% · 已等待 ${formatDuration(elapsed)} · 预计还需 ${formatDuration(expected - elapsed)}`,
    };
  }

  return { estimate, formatDuration };
}));
