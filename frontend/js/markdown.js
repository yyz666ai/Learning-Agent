"use strict";
{
  const i18n = () => (typeof window !== "undefined" ? window : globalThis).LearningI18n;
  const t = (key, params = {}) => i18n()?.t(key, params) ?? String(key).replace(/\{(\w+)\}/g, (m, k) => params[k] == null ? m : String(params[k]));
  const bindUI = (node, property, render) => { if (i18n()) return i18n().bind(node, property, render); const value = render(); if (property.startsWith("@")) node.setAttribute(property.slice(1), value); else node[property] = value; return value; };
(function createMarkdownRenderer(global) {
  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[character]);
  }

  function highlightCode(source, language = "") {
    const keywords = /^(package|import|func|var|const|type|struct|interface|return|if|else|for|range|go|defer|select|case|default|map|chan|class|def|from|as|in|is|not|and|or|try|except|finally|with|lambda|yield|async|await|true|false|null|none)$/i;
    const tokenPattern = /("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\/\/[^\n]*|#[^\n]*|\b(?:package|import|func|var|const|type|struct|interface|return|if|else|for|range|go|defer|select|case|default|map|chan|class|def|from|as|in|is|not|and|or|try|except|finally|with|lambda|yield|async|await|true|false|null|none)\b|\b\d+(?:\.\d+)?\b)/gi;
    let cursor = 0;
    let output = "";
    for (const match of String(source ?? "").matchAll(tokenPattern)) {
      output += escapeHtml(source.slice(cursor, match.index));
      const token = match[0];
      let kind = "number";
      if (token.startsWith("//") || token.startsWith("#")) kind = "comment";
      else if (token.startsWith('"') || token.startsWith("'")) kind = "string";
      else if (keywords.test(token)) kind = "keyword";
      output += `<span class="token-${kind}">${escapeHtml(token)}</span>`;
      cursor = match.index + token.length;
    }
    output += escapeHtml(String(source ?? "").slice(cursor));
    return output;
  }

  function inline(value) {
    const codes = [];
    const safe = escapeHtml(String(value).replace(/\uE000/g, "&#57344;"));
    return safe.replace(/`([^`]+)`/g, (_, code) => {
      codes.push(`<code>${code}</code>`); return `\uE000${codes.length - 1}\uE000`;
    })
      .replace(/&lt;u&gt;([\s\S]*?)&lt;\/u&gt;/g, "<u>$1</u>")
      .replace(/==([^=]+)==/g, "<mark>$1</mark>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>")
      .replace(/\uE000(\d+)\uE000/g, (_, i) => codes[Number(i)]);
  }

  function render(markdown, allowHints = true) {
    const lines = String(markdown ?? "").replace(/\r\n?/g, "\n").split("\n");
    const html = [];
    let paragraph = [];
    let listType = "";

    function flushParagraph() {
      if (paragraph.length) html.push(`<p>${inline(paragraph.join(" "))}</p>`);
      paragraph = [];
    }
    function closeList() {
      if (listType) html.push(`</${listType}>`);
      listType = "";
    }

    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index];
      // Only our attribute-free hint block is supported. Arbitrary HTML stays
      // escaped; recursive body rendering also disables nested hint blocks.
      if (allowHints && line === "<details>") {
        const summary = (lines[index + 1] || "").match(/^<summary>([^\n]*)<\/summary>$/);
        const end = lines.indexOf("</details>", index + 2);
        if (summary && end !== -1) {
          flushParagraph(); closeList();
          html.push(`<details class="markdown-hints"><summary>${inline(summary[1])}</summary>${render(lines.slice(index + 2, end).join("\n"), false)}</details>`);
          index = end;
          continue;
        }
      }
      const fence = line.match(/^```([\w+-]*)\s*$/);
      if (fence) {
        flushParagraph(); closeList();
        const code = [];
        index += 1;
        while (index < lines.length && !/^```\s*$/.test(lines[index])) { code.push(lines[index]); index += 1; }
        const language = (fence[1] || "text").toLowerCase();
        if (language === "mermaid") html.push(`<div class="mermaid">${escapeHtml(code.join("\n"))}</div>`);
        else html.push(t("<figure class=\"markdown-code-frame\"><figcaption><span>{0}</span><button type=\"button\" class=\"markdown-copy-code\" aria-label=\"复制这段代码\">复制代码</button></figcaption><pre><code class=\"language-{1}\">{2}</code></pre></figure>", {0: escapeHtml(language), 1: escapeHtml(language), 2: highlightCode(code.join("\n"), language)}));
        continue;
      }
      if (!line.trim()) { flushParagraph(); closeList(); continue; }
      const heading = line.match(/^(#{1,6})\s+(.+)$/);
      if (heading) { flushParagraph(); closeList(); const level = heading[1].length; html.push(`<h${level}>${inline(heading[2])}</h${level}>`); continue; }
      const bullet = line.match(/^\s*[-*]\s+(.+)$/);
      const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
      if (bullet || ordered) {
        flushParagraph();
        const nextType = bullet ? "ul" : "ol";
        if (listType !== nextType) { closeList(); listType = nextType; html.push(`<${listType}>`); }
        html.push(`<li>${inline((bullet || ordered)[1])}</li>`);
        continue;
      }
      const quote = line.match(/^>\s?(.*)$/);
      if (quote) { flushParagraph(); closeList(); html.push(`<blockquote>${inline(quote[1])}</blockquote>`); continue; }
      paragraph.push(line.trim());
    }
    flushParagraph(); closeList();
    return html.join("\n");
  }

  let mermaidInitialized = false;
  async function hydrate(root) {
    if (!root?.querySelectorAll) return;
    root.querySelectorAll(".markdown-copy-code:not([data-bound])").forEach((button) => {
      bindUI(button, "textContent", () => t("复制代码"));
      bindUI(button, "@aria-label", () => t("复制这段代码"));
      button.dataset.bound = "true";
      button.addEventListener("click", async () => {
        const code = button.closest(".markdown-code-frame")?.querySelector("code")?.textContent || "";
        try {
          await global.navigator?.clipboard?.writeText(code);
          bindUI(button, "textContent", () => t("✓ 已复制"));
        } catch (error) {
          bindUI(button, "textContent", () => t("复制失败"));
        }
        global.setTimeout?.(() => { bindUI(button, "textContent", () => t("复制代码")); }, 1600);
      });
    });
    if (!global.mermaid) return;
    const nodes = [...root.querySelectorAll(".mermaid:not([data-processed])")];
    if (!nodes.length) return;
    if (!mermaidInitialized) {
      global.mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "neutral" });
      mermaidInitialized = true;
    }
    try { await global.mermaid.run({ nodes }); }
    catch (error) {
      nodes.forEach((node) => { node.classList.add("mermaid-error"); });
      console.warn("Mermaid render failed", error);
    }
  }

  global.MarkdownRenderer = { escapeHtml, highlightCode, render, hydrate };
  if (typeof module !== "undefined" && module.exports) module.exports = global.MarkdownRenderer;
}(typeof window !== "undefined" ? window : globalThis));

}
