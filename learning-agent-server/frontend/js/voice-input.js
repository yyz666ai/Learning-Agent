"use strict";

(function createVoiceInputModule(root) {
  function create({ button, recognitionFactory, onTranscript, onStatus }) {
    if (!button || typeof recognitionFactory !== "function") {
      return { supported: false, listening: false, toggle() {} };
    }

    const recognition = recognitionFactory();
    recognition.lang = "zh-CN";
    recognition.interimResults = false;
    recognition.continuous = false;
    let listening = false;

    function setListening(value) {
      listening = value;
      button.classList.toggle("is-listening", value);
      button.setAttribute("aria-pressed", String(value));
    }

    recognition.onstart = () => {
      setListening(true);
      onStatus?.("listening", "正在听…说出你想学的内容");
    };
    recognition.onresult = (event) => {
      const transcript = [...event.results]
        .map((result) => result[0]?.transcript || "")
        .join("")
        .trim();
      if (transcript) onTranscript?.(transcript);
    };
    recognition.onerror = (event) => {
      setListening(false);
      const denied = event?.error === "not-allowed" || event?.error === "service-not-allowed";
      onStatus?.("error", denied ? "没有获得麦克风权限，可以直接打字" : "这次没听清，点一下再说");
    };
    recognition.onend = () => {
      setListening(false);
      onStatus?.("idle", "语音输入");
    };

    function toggle() {
      if (listening) recognition.stop();
      else recognition.start();
    }

    button.addEventListener("click", toggle);
    return {
      supported: true,
      get listening() { return listening; },
      toggle,
      recognition,
    };
  }

  const api = { create };
  root.VoiceInput = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
}(typeof window !== "undefined" ? window : globalThis));
