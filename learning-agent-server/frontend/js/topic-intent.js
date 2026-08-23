"use strict";

(function createTopicIntent(root) {
  const PRONOUN_TOPICS = /^(?:这个|它|这里|这段|这一页|刚才这个|上面这个)$/;

  function cleanTopic(value) {
    return String(value || "")
      .replace(/^[\s，,。.!！?？：:]+|[\s，,。.!！?？：:]+$/g, "")
      .replace(/^(?:请|麻烦你|你能)?\s*(?:给我)?\s*/u, "")
      .trim();
  }

  function safeConcept(topic) {
    const cleaned = cleanTopic(topic)
      .replace(/^(?:我)?\s*(?:想|要)?\s*(?:了解|知道|弄懂|理解|问一下)\s*/u, "")
      .trim();
    return !cleaned || PRONOUN_TOPICS.test(cleaned) ? "" : cleaned;
  }

  function classify(value) {
    const text = cleanTopic(value);
    if (!text) return { kind: "conversation", topic: "" };

    let match = text.match(/^什么是\s*(.+)$/u);
    if (match) {
      const topic = safeConcept(match[1]);
      if (topic) return { kind: "concept", topic };
    }

    match = text.match(/^(.+?)\s*(?:是什么意思|是什么|怎么理解|的概念是什么|的原理是什么)$/u);
    if (match) {
      const topic = safeConcept(match[1]);
      if (topic) return { kind: "concept", topic };
    }

    match = text.match(/^(?:请)?\s*(?:解释一下|讲讲|带我了解)\s*(.+)$/u);
    if (match) {
      const topic = safeConcept(match[1]);
      if (topic) return { kind: "concept", topic };
    }

    match = text.match(/^(?:我)?\s*(?:想|要|准备)?\s*(?:开始)?\s*(?:系统学习|学(?:习|会|一下)?|入门|精进|掌握)\s*(.+)$/u);
    if (match && cleanTopic(match[1])) return { kind: "learning_path", topic: cleanTopic(match[1]) };

    return { kind: "conversation", topic: "" };
  }

  const api = { classify };
  root.TopicIntent = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
}(typeof window !== "undefined" ? window : globalThis));
