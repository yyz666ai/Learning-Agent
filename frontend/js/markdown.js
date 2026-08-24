"use strict";

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
    return escapeHtml(value).split(/(`[^`]+`)/g).map((segment) => {
      if (segment.startsWith("`") && segment.endsWith("`")) {
        return `<code>${segment.slice(1, -1)}</code>`;
      }
      return segment
        .replace(/==([^=]+)==/g, "<mark>$1</mark>")
        .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
        .replace(/\*([^*]+)\*/g, "<em>$1</em>");
    }).join("");
  }

  function render(markdown) {
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
      const fence = line.match(/^```([\w+-]*)\s*$/);
      if (fence) {
        flushParagraph(); closeList();
        const code = [];
        index += 1;
        while (index < lines.length && !/^```\s*$/.test(lines[index])) { code.push(lines[index]); index += 1; }
        const language = (fence[1] || "text").toLowerCase();
        if (language === "mermaid") html.push(`<div class="mermaid">${escapeHtml(code.join("\n"))}</div>`);
        else html.push(`<figure class="markdown-code-frame"><figcaption><span>${escapeHtml(language)}</span><button type="button" class="markdown-copy-code" aria-label="复制这段代码">复制代码</button></figcaption><pre><code class="language-${escapeHtml(language)}">${highlightCode(code.join("\n"), language)}</code></pre></figure>`);
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
      button.dataset.bound = "true";
      button.addEventListener("click", async () => {
        const code = button.closest(".markdown-code-frame")?.querySelector("code")?.textContent || "";
        try {
          await global.navigator?.clipboard?.writeText(code);
          button.textContent = "✓ 已复制";
        } catch (error) {
          button.textContent = "复制失败";
        }
        global.setTimeout?.(() => { button.textContent = "复制代码"; }, 1600);
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
