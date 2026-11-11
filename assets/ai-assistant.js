/* 小白学菜 · AI 助手面板 (D5)
 * 用法：在页面 </body> 前加 <script src="assets/ai-assistant.js" defer></script>
 * 可选：window.XIAOBAI_AI_API = "https://your-api.example.com";
 */
(function () {
  if (window.__xbxcAI) return;
  window.__xbxcAI = true;

  const script = document.currentScript || Array.from(document.scripts).find((s) => /ai-assistant\.js(\?|$)/.test(s.src));
  const scriptUrl = script ? new URL(script.src) : new URL("assets/ai-assistant.js", location.href);
  const cssUrl = new URL("ai-assistant.css", scriptUrl);
  const siteRoot = new URL("../", scriptUrl);
  const apiBase = (window.XIAOBAI_AI_API || "http://127.0.0.1:8000").replace(/\/+$/, "");
  const params = new URLSearchParams(location.search);

  if (!document.querySelector('link[data-xbxc-ai-css]')) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = cssUrl.href;
    link.dataset.xbxcAiCss = "1";
    document.head.appendChild(link);
  }

  const root = document.createElement("div");
  root.id = "xbxc-ai";
  root.innerHTML = `
    <button class="xbxc-ai-launch" type="button" aria-expanded="false" aria-controls="xbxc-ai-panel">
      <span class="dot" aria-hidden="true"></span><span>问小白</span>
    </button>
    <section class="xbxc-ai-panel" id="xbxc-ai-panel" role="dialog" aria-label="小白学菜 AI 助手" aria-modal="false">
      <header class="xbxc-ai-head">
        <div class="xbxc-ai-title">
          <strong>问小白</strong>
          <small>菜谱 · 步骤 · 份量 · 采购清单</small>
        </div>
        <button class="xbxc-ai-close" type="button" aria-label="关闭 AI 助手">×</button>
      </header>
      <div class="xbxc-ai-messages" role="log" aria-live="polite"></div>
      <div class="xbxc-ai-suggestions" aria-label="示例问题">
        <button class="xbxc-ai-suggestion" type="button">番茄炒蛋第 2 步怎么判断？</button>
        <button class="xbxc-ai-suggestion" type="button">两人份改四人份，鸡蛋几个？</button>
        <button class="xbxc-ai-suggestion" type="button">麻婆豆腐买什么？</button>
      </div>
      <div class="xbxc-ai-status" hidden></div>
      <form class="xbxc-ai-composer">
        <textarea class="xbxc-ai-input" rows="1" maxlength="500" placeholder="问一道菜：第几步、几人份、买什么…" aria-label="输入问题"></textarea>
        <button class="xbxc-ai-send" type="submit" aria-label="发送">
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M4 12 20 4l-4.5 16-4-6.5L4 12Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
            <path d="m11.5 13.5 4-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
          </svg>
        </button>
      </form>
    </section>
  `;
  document.body.appendChild(root);

  const launch = root.querySelector(".xbxc-ai-launch");
  const panel = root.querySelector(".xbxc-ai-panel");
  const closeBtn = root.querySelector(".xbxc-ai-close");
  const messages = root.querySelector(".xbxc-ai-messages");
  const suggestions = root.querySelector(".xbxc-ai-suggestions");
  const input = root.querySelector(".xbxc-ai-input");
  const sendBtn = root.querySelector(".xbxc-ai-send");
  const status = root.querySelector(".xbxc-ai-status");
  const form = root.querySelector(".xbxc-ai-composer");

  let busy = false;
  let controller = null;
  let greeted = false;
  const history = [];

  const GREETING = "我是小白学菜助手。可以问我某道菜第几步怎么判断、2 人份改 4 人份，或者要做哪几道菜的采购清单。";
  const TOOL_LABELS = {
    search_recipes: "已找到菜谱",
    get_step: "已定位到步骤",
    scale_servings: "已按份量换算",
    build_shopping_list: "已生成采购清单",
  };

  function scrollToBottom() {
    messages.scrollTop = messages.scrollHeight;
  }

  function addMessage(role, text) {
    const wrap = document.createElement("div");
    wrap.className = "xbxc-ai-msg " + role;
    const bubble = document.createElement("div");
    bubble.className = "xbxc-ai-bubble";
    const span = document.createElement("span");
    span.className = "text";
    span.textContent = text;
    bubble.appendChild(span);
    wrap.appendChild(bubble);
    messages.appendChild(wrap);
    scrollToBottom();
    return { wrap, bubble, span };
  }

  function addAssistantBubble() {
    const wrap = document.createElement("div");
    wrap.className = "xbxc-ai-msg assistant";
    const bubble = document.createElement("div");
    bubble.className = "xbxc-ai-bubble";
    const span = document.createElement("span");
    span.className = "text";
    const cursor = document.createElement("span");
    cursor.className = "cursor";
    cursor.setAttribute("aria-hidden", "true");
    const cites = document.createElement("div");
    cites.className = "xbxc-ai-cites";
    bubble.append(span, cursor, cites);
    wrap.appendChild(bubble);
    messages.appendChild(wrap);
    scrollToBottom();
    return { wrap, bubble, span, cursor, cites };
  }

  function setStatus(text, isError) {
    status.hidden = !text;
    status.textContent = text || "";
    status.classList.toggle("xbxc-ai-error", Boolean(isError));
  }

  function cleanAnswer(text) {
    return (text || "").replace(/\s*\[C\d+\]/g, "").trim();
  }

  function openPanel(focusInput) {
    root.classList.add("open");
    launch.setAttribute("aria-expanded", "true");
    if (!greeted) {
      addMessage("assistant", GREETING);
      greeted = true;
    }
    if (focusInput !== false) {
      window.setTimeout(() => input.focus(), 220);
    }
  }

  function closePanel() {
    root.classList.remove("open");
    launch.setAttribute("aria-expanded", "false");
    if (controller) controller.abort();
    busy = false;
    sendBtn.disabled = false;
    setStatus("");
  }

  function citeLabel(c) {
    if (c.type === "step") return "第 " + c.step_index + " 步 · " + c.recipe_name;
    if (c.type === "ingredients") return "用料 · " + c.recipe_name;
    return c.recipe_name || "菜谱";
  }

  function renderCitations(container, citations) {
    container.textContent = "";
    if (!citations || !citations.length) return;
    const label = document.createElement("div");
    label.className = "xbxc-ai-cites-label";
    label.textContent = "依据";
    container.appendChild(label);
    citations.forEach((c) => {
      const a = document.createElement("a");
      a.className = "xbxc-ai-cite";
      a.href = new URL(c.url || "index.html", siteRoot).href;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = citeLabel(c);
      container.appendChild(a);
    });
  }

  function handleEvent(eventName, payload, assistant) {
    if (eventName === "meta") {
      if (payload && payload.tool) setStatus(TOOL_LABELS[payload.tool] || "AI 正在回答");
      return;
    }
    if (eventName === "citations") {
      renderCitations(assistant.cites, payload.citations || []);
      return;
    }
    if (eventName === "token") {
      assistant.span.textContent += payload.text || "";
      scrollToBottom();
      return;
    }
    if (eventName === "done") {
      assistant.cursor.remove();
      setStatus("");
      return;
    }
    if (eventName === "error") {
      throw new Error(payload.message || "AI 服务返回错误");
    }
  }

  function parseSSE(raw, assistant) {
    const lines = raw.replace(/\r\n/g, "\n").split("\n");
    let eventName = "message";
    const data = [];
    for (const line of lines) {
      if (line.startsWith("event:")) eventName = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
    }
    if (!data.length) return;
    let payload;
    try {
      payload = JSON.parse(data.join("\n"));
    } catch (err) {
      return;
    }
    handleEvent(eventName, payload, assistant);
  }

  async function streamChat(question, assistant) {
    controller = new AbortController();
    const response = await fetch(apiBase + "/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: question, history: history.slice(-6) }),
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error("AI 服务 HTTP " + response.status);
    }
    if (!response.body) {
      throw new Error("浏览器不支持流式响应");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let index;
      while ((index = buffer.indexOf("\n\n")) >= 0) {
        const chunk = buffer.slice(0, index);
        buffer = buffer.slice(index + 2);
        parseSSE(chunk, assistant);
      }
    }
    if (buffer.trim()) parseSSE(buffer, assistant);
    assistant.span.textContent = cleanAnswer(assistant.span.textContent);
    assistant.cursor.remove();
  }

  async function staticChat(question, assistant) {
    controller = new AbortController();
    const response = await fetch(apiBase + "/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: question, history: history.slice(-6) }),
      signal: controller.signal,
    });
    if (!response.ok) throw new Error("AI 服务 HTTP " + response.status);
    const data = await response.json();
    assistant.span.textContent = cleanAnswer(data.answer || "菜谱里没有找到足够依据，换个说法试试。");
    renderCitations(assistant.cites, data.citations || []);
    assistant.cursor.remove();
  }

  async function send(question) {
    const text = (question || "").trim();
    if (!text || busy) return;

    openPanel(false);
    setStatus("");
    addMessage("user", text);
    history.push({ role: "user", content: text });
    input.value = "";
    input.style.height = "auto";
    busy = true;
    sendBtn.disabled = true;

    const assistant = addAssistantBubble();
    try {
      if (params.get("nostream") === "1") {
        await staticChat(text, assistant);
      } else {
        await streamChat(text, assistant);
      }
      const answer = assistant.span.textContent;
      if (answer) history.push({ role: "assistant", content: answer });
      if (!answer) {
        assistant.span.textContent = "菜谱里没有找到足够依据，换个说法试试。";
      }
    } catch (err) {
      if (err.name === "AbortError") return;
      assistant.cursor.remove();
      assistant.span.textContent = "AI 服务暂时不可用。请确认本地 API 已启动（python -m ai.dev_server --port 8000），或稍后再试。";
      assistant.bubble.classList.add("xbxc-ai-error");
      setStatus("连接失败：" + err.message, true);
    } finally {
      busy = false;
      sendBtn.disabled = false;
      if (root.classList.contains("open")) input.focus();
    }
  }

  launch.addEventListener("click", () => openPanel(true));
  closeBtn.addEventListener("click", closePanel);
  panel.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closePanel();
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    send(input.value);
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      send(input.value);
    }
  });
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 104) + "px";
  });
  suggestions.addEventListener("click", (event) => {
    const btn = event.target.closest(".xbxc-ai-suggestion");
    if (btn) send(btn.textContent);
  });

  // 深链：?ai=1 打开面板，&q=问题 可直接发问；&nostream=1 用非流式（截图/旧浏览器）
  if (params.get("ai") === "1") {
    window.setTimeout(() => {
      openPanel(false);
      const q = params.get("q");
      if (q) window.setTimeout(() => send(q), 260);
    }, 350);
  }
})();
