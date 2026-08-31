"use strict";
{
  const i18n = () => (typeof window !== "undefined" ? window : globalThis).LearningI18n;
  const t = (key, params = {}) => i18n()?.t(key, params) ?? String(key).replace(/\{(\w+)\}/g, (m, k) => params[k] == null ? m : String(params[k]));
  const bindUI = (node, property, render) => { if (i18n()) return i18n().bind(node, property, render); const value = render(); if (property.startsWith("@")) node.setAttribute(property.slice(1), value); else node[property] = value; return value; };
(function expose(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.DiagnosisJobs = api;
}(typeof window === "undefined" ? null : window, function factory() {
  const base = "/api/onboarding/diagnosis";
  const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
  const stale = () => Object.assign(new Error(t("这轮诊断已不属于当前页面。")), {name: "AbortError"});

  async function readJob(url, options = {}, fetcher = fetch, timeoutMs = 8000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetcher(url, {...options, signal: controller.signal});
      const value = await response.json();
      if (!response.ok) {
        const error = new Error(value.detail?.message || t("诊断状态暂时不可用，请重试。"));
        error.status = response.status;
        error.recovery = value.detail?.recovery;
        error.terminal = [400, 404, 409, 422].includes(response.status);
        throw error;
      }
      return value;
    } finally { clearTimeout(timer); }
  }

  function statusText(job) {
    if (job.status === "unknown") return t("暂时无法读取状态，正在重连。尚不能确认后台是否完成。");
    const phase = {get queued() { return t("已排队，等待生成诊断题"); }, get generating() { return t("正在生成与你的目标相关的诊断题"); }, get validating() { return t("正在校验题目与选项"); }, get repairing() { return t("正在修正题目结构"); }, get completed() { return t("诊断题已准备好"); }, get cancelled() { return t("这轮诊断已取消"); }, get failed() { return t("诊断暂时未完成"); }, get interrupted() { return t("服务重启，原任务已中断"); }};
    const elapsed = Number.isFinite(job.elapsed_seconds) ? t(" · 已等待 {0} 秒", {0: Math.floor(job.elapsed_seconds)}) : "";
    return (phase[job.phase] || phase[job.status] || t("正在读取诊断任务状态")) + elapsed;
  }

  async function waitForDiagnosis({payload, fetcher = fetch, onStatus = () => {}, isCurrent = () => true,
    sleep = pause, now = Date.now, maxWaitMs = 390000, pollMs = 1200}) {
    payload = {...payload, locale: payload.locale || i18n()?.getLocale() || "zh-CN"};
    const started = now();
    let accepted = false;
    let failures = 0;
    const query = new URLSearchParams({user_id: payload.user_id || "yang", request_id: payload.request_id || ""});
    while (now() - started < maxWaitMs) {
      if (!isCurrent()) throw stale();
      let job;
      try {
        // A lost POST response repeats the same id. The server owns deduplication.
        job = await readJob(accepted ? `${base}/status?${query}` : `${base}/start`, accepted ? {} : {
          method: "POST", headers: {"Content-Type": "application/json", "X-Learning-Locale": payload.locale}, body: JSON.stringify(payload),
        }, fetcher);
        if (!isCurrent()) throw stale();
        accepted = true;
        failures = 0;
      } catch (error) {
        if (!isCurrent()) throw stale();
        if (error.terminal) throw error;
        onStatus({status: "unknown"});
        failures++;
        await sleep(Math.min(4000, pollMs * failures));
        continue;
      }
      onStatus(job);
      if (job.status === "completed") return {...job.result, locale:job.locale || job.result?.locale || payload.locale};
      if (["failed", "cancelled", "interrupted"].includes(job.status)) {
        const error = new Error(job.error || statusText(job));
        error.terminal = true;
        error.retryable = job.retryable !== false;
        throw error;
      }
      await sleep(pollMs);
    }
    throw new Error(t("暂时无法确认诊断结果。你的请求标识已保留，点击重试将读取同一任务，不会重复生成。"));
  }
  return {readJob, waitForDiagnosis, statusText};
}));

}
