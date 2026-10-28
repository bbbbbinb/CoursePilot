(() => {
  "use strict";

  const API_BASE = location.protocol === "file:"
    ? "http://127.0.0.1:8765/api/v1"
    : "/api/v1";
  const query = new URLSearchParams(location.search);
  const forceDemo = query.get("demo") === "1";

  const $ = (selector, root = document) => root.querySelector(selector);

  const el = {
    sidebar: $("#sidebar"),
    backdrop: $("#backdrop"),
    menuBtn: $("#menuBtn"),
    sidebarClose: $("#sidebarClose"),
    docList: $("#docList"),
    docCount: $("#docCount"),
    docEmpty: $("#docEmpty"),
    dropzone: $("#dropzone"),
    fileInput: $("#fileInput"),
    healthDot: $("#healthDot"),
    healthText: $("#healthText"),
    demoHint: $("#demoHint"),
    sessionLabel: $("#sessionLabel"),
    chatScroll: $("#chatScroll"),
    messages: $("#messages"),
    welcome: $("#welcome"),
    suggestions: $("#suggestions"),
    composer: $("#composer"),
    input: $("#input"),
    sendBtn: $("#sendBtn"),
    composerHint: $("#composerHint"),
    newChatBtn: $("#newChatBtn"),
    settingsBtn: $("#settingsBtn"),
    settingsPop: $("#settingsPop"),
    settingsClose: $("#settingsClose"),
    topK: $("#topK"),
    topKValue: $("#topKValue"),
    showSources: $("#showSources"),
    toasts: $("#toasts"),
  };

  const STORAGE = {
    docs: "coursepilot.docs.v1",
    session: "coursepilot.session.v1",
    settings: "coursepilot.settings.v1",
  };

  const savedDocs = readJSON(STORAGE.docs, []);

  const state = {
    online: false,
    busy: false,
    sessionId: readJSON(STORAGE.session, null) || newSessionId(),
    docs: (Array.isArray(savedDocs) ? savedDocs : []).filter((doc) => doc.status !== "uploading"),
    settings: Object.assign(
      { topK: 4, showSources: true },
      readJSON(STORAGE.settings, {})
    ),
  };

  const demoDocs = [
    { id: "demo-1", name: "数据结构_第08章_递归.pdf", pages: 24, chunks: 71, status: "ready", demo: true },
    { id: "demo-2", name: "数据结构_实验05_树.pdf", pages: 18, chunks: 52, status: "ready", demo: true },
    { id: "demo-3", name: "期中复习提纲.md", pages: 1, chunks: 29, status: "ready", demo: true },
  ];

  const mockSources = {
    recursion: [
      {
        index: 1,
        file_name: "数据结构_第08章_递归.pdf",
        page: 12,
        snippet: "递归函数通过调用自身来分解问题，每一层调用的局部变量保存在调用栈中。",
      },
      {
        index: 2,
        file_name: "数据结构_第08章_递归.pdf",
        page: 15,
        snippet: "迭代使用循环和显式状态推进，避免调用栈开销，适合处理大规模数据。",
      },
    ],
    exam: [
      {
        index: 1,
        file_name: "期中复习提纲.md",
        page: 1,
        snippet: "重点：递归与迭代的转换、树的前中后序遍历、时间复杂度分析、常见排序算法稳定性。",
      },
      {
        index: 2,
        file_name: "数据结构_第08章_递归.pdf",
        page: 3,
        snippet: "掌握递归三要素：基准情形、递归关系、向基准情形收敛。",
      },
    ],
    plan: [
      {
        index: 1,
        file_name: "期中复习提纲.md",
        page: 1,
        snippet: "建议按「概念回顾 → 手写代码 → 错题复盘」三轮推进，每天保留一次限时练习。",
      },
    ],
    generic: [
      {
        index: 1,
        file_name: "数据结构_第08章_递归.pdf",
        page: 8,
        snippet: "本章从递归定义出发，讨论递归与迭代在状态保存和空间开销上的差异。",
      },
    ],
  };

  const mockAnswers = {
    recursion: `递归和迭代都是重复执行逻辑的方式，区别在于**由谁保存中间状态**。

- **递归**：函数调用自身，每一层的局部变量和返回位置保存在调用栈里 [1]。写法贴近数学定义，但深度受限，空间开销是 O(n)。
- **迭代**：用循环变量和可变状态推进 [2]。没有额外调用栈，通常更适合大规模数据。

所以判断标准不是“谁更高级”，而是问题是否能自然分解成同构子问题。能自然分解时递归更清晰，否则优先迭代。`,
    exam: `根据复习提纲，这门课的重点集中在四块 [1]：

1. **递归与迭代的相互转换**，尤其是尾递归改写。
2. **树的前序、中序、后序遍历**，能手写非递归版本。
3. **时间复杂度分析**，包括最好、最坏和平均情况。
4. **排序算法的稳定性与原地性**，常考比较题。

复习时建议先把递归三要素写熟：基准情形、递归关系、向基准情形收敛 [2]。`,
    plan: `可以按三轮推进，每轮都产出可检查的东西 [1]：

- **第 1–2 天**：过一遍概念，给每个知识点写一句自己的解释。
- **第 3–5 天**：手写遍历和递归题，不看答案，记录卡住的步骤。
- **第 6–7 天**：限时做一套题，整理错题，再回看对应讲义页码。

每天留 30 分钟复盘，比单纯延长学习时间更有效。`,
    fallback: `我在已索引的资料里找到一段相关内容 [1]。它讨论的是本章的核心概念与适用场景。如果你能把问题再具体一点，比如指出想了解的算法或章节，我可以检索更精确的片段。`,
  };

  /* ---------------- boot ---------------- */

  init();

  async function init() {
    renderDocs();
    updateSessionLabel();
    bindEvents();
    restoreSettings();
    updateSendState();
    await checkHealth();

    const sample = query.get("q");
    if (sample) {
      setTimeout(() => {
        el.input.value = sample;
        autoGrow();
        submitQuestion();
      }, 320);
    }
  }

  function bindEvents() {
    el.fileInput.addEventListener("change", (event) => {
      uploadFiles(Array.from(event.target.files || []));
      event.target.value = "";
    });

    ["dragenter", "dragover"].forEach((name) => {
      el.dropzone.addEventListener(name, (event) => {
        event.preventDefault();
        el.dropzone.classList.add("is-over");
      });
    });

    ["dragleave", "drop"].forEach((name) => {
      el.dropzone.addEventListener(name, (event) => {
        event.preventDefault();
        el.dropzone.classList.remove("is-over");
      });
    });

    el.dropzone.addEventListener("drop", (event) => {
      uploadFiles(Array.from(event.dataTransfer?.files || []));
    });

    el.composer.addEventListener("submit", (event) => {
      event.preventDefault();
      submitQuestion();
    });

    el.input.addEventListener("input", () => {
      autoGrow();
      updateSendState();
    });

    el.input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        submitQuestion();
      }
    });

    el.suggestions.addEventListener("click", (event) => {
      const button = event.target.closest(".suggestion");
      if (!button) return;
      el.input.value = button.textContent.trim();
      autoGrow();
      submitQuestion();
    });

    el.newChatBtn.addEventListener("click", newChat);
    el.menuBtn.addEventListener("click", openSidebar);
    el.sidebarClose.addEventListener("click", closeSidebar);
    el.backdrop.addEventListener("click", closeSidebar);

    el.settingsBtn.addEventListener("click", toggleSettings);
    el.settingsClose.addEventListener("click", () => hideSettings());

    el.topK.addEventListener("input", () => {
      state.settings.topK = Number(el.topK.value);
      el.topKValue.textContent = String(state.settings.topK);
      el.composerHint.textContent = `检索 top ${state.settings.topK} · 流式回答`;
      writeJSON(STORAGE.settings, state.settings);
    });

    el.showSources.addEventListener("change", () => {
      state.settings.showSources = el.showSources.checked;
      writeJSON(STORAGE.settings, state.settings);
      document.querySelectorAll(".sources").forEach((node) => {
        node.hidden = !state.settings.showSources;
      });
    });

    document.addEventListener("click", (event) => {
      if (!el.settingsPop.hidden
        && !el.settingsPop.contains(event.target)
        && !el.settingsBtn.contains(event.target)) {
        hideSettings();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        hideSettings();
        closeSidebar();
      }
    });

    el.messages.addEventListener("click", (event) => {
      const cite = event.target.closest(".cite");
      if (cite) {
        flashSource(cite);
        return;
      }

      const head = event.target.closest(".sources-head");
      if (head) {
        head.closest(".sources").classList.toggle("is-collapsed");
      }
    });
  }

  /* ---------------- health / demo ---------------- */

  async function checkHealth() {
    if (forceDemo) {
      enterDemoMode();
      return;
    }

    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 1600);
      const response = await fetch(`${API_BASE}/health`, {
        signal: controller.signal,
        cache: "no-store",
      });
      clearTimeout(timer);
      if (!response.ok) throw new Error("backend unavailable");
      state.online = true;
      el.healthDot.className = "status-dot is-online";
      el.healthText.textContent = "后端已连接";
      el.demoHint.hidden = true;
    } catch {
      enterDemoMode();
    }
  }

  function enterDemoMode() {
    state.online = false;
    el.healthDot.className = "status-dot is-demo";
    el.healthText.textContent = "演示模式（未连接后端）";
    el.demoHint.hidden = false;
    if (state.docs.length === 0) {
      state.docs = demoDocs.slice();
      renderDocs();
    }
  }

  /* ---------------- documents ---------------- */

  function renderDocs() {
    el.docList.innerHTML = "";
    el.docCount.textContent = `${state.docs.length} 份`;
    el.docEmpty.hidden = state.docs.length > 0;

    for (const doc of state.docs) {
      const item = document.createElement("li");
      item.className = "doc-item";
      item.dataset.id = doc.id;
      const ext = (doc.name.split(".").pop() || "FILE").slice(0, 4).toUpperCase();
      const meta = doc.status === "uploading"
        ? `解析中 ${doc.progress || 0}%`
        : `${doc.pages || "—"} 页 · ${doc.chunks || "—"} 片段`;

      item.innerHTML = `
        <span class="doc-icon">${escapeHtml(ext)}</span>
        <div class="doc-main">
          <div class="doc-name" title="${escapeHtml(doc.name)}">${escapeHtml(doc.name)}</div>
          <div class="doc-meta">${meta}${doc.demo ? '<span class="doc-badge">示例</span>' : ""}</div>
          ${doc.status === "uploading" ? '<div class="doc-progress"><i></i></div>' : ""}
        </div>`;

      el.docList.appendChild(item);
      updateDocProgress(doc);
    }
  }

  async function uploadFiles(files) {
    for (const file of files) {
      if (!/\.(pdf|md|txt)$/i.test(file.name)) {
        toast(`不支持的文件类型：${file.name}`, true);
        continue;
      }
      if (file.size > 20 * 1024 * 1024) {
        toast(`${file.name} 超过 20MB`, true);
        continue;
      }

      const doc = {
        id: uid("doc"),
        name: file.name,
        pages: 0,
        chunks: 0,
        progress: 0,
        status: "uploading",
        demo: !state.online,
      };

      state.docs.unshift(doc);
      renderDocs();

      if (!state.online) {
        await simulateUpload(doc);
        continue;
      }

      try {
        const result = await uploadOne(file, doc);
        Object.assign(doc, {
          status: "ready",
          pages: result.pages || result.page_count || "—",
          chunks: result.chunks || result.chunk_count || "—",
          demo: false,
        });
        toast(`${file.name} 已入库`);
      } catch (error) {
        state.docs = state.docs.filter((item) => item.id !== doc.id);
        toast(`上传失败：${error.message}`, true);
      }

      renderDocs();
      persistDocs();
    }
  }

  function uploadOne(file, doc) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE}/documents`);

      xhr.upload.onprogress = (event) => {
        if (!event.lengthComputable) return;
        doc.progress = Math.min(99, Math.round((event.loaded / event.total) * 100));
        updateDocProgress(doc);
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText || "{}"));
          } catch {
            resolve({});
          }
        } else {
          reject(new Error(readError(xhr.responseText) || `HTTP ${xhr.status}`));
        }
      };

      xhr.onerror = () => reject(new Error("网络错误"));

      const form = new FormData();
      form.append("file", file);
      xhr.send(form);
    });
  }

  function updateDocProgress(doc) {
    const item = el.docList.querySelector(`[data-id="${cssEscape(doc.id)}"]`);
    if (!item) return;
    const bar = item.querySelector(".doc-progress i");
    if (bar) bar.style.width = `${doc.progress || 0}%`;
    if (doc.status === "uploading") {
      const meta = item.querySelector(".doc-meta");
      if (meta) meta.textContent = `解析中 ${doc.progress || 0}%`;
    }
  }

  async function simulateUpload(doc) {
    for (const step of [18, 46, 73, 92]) {
      await sleep(160);
      doc.progress = step;
      updateDocProgress(doc);
    }
    await sleep(220);
    doc.status = "ready";
    doc.pages = 8 + Math.floor(Math.random() * 15);
    doc.chunks = doc.pages * 3 + Math.floor(Math.random() * 8);
    doc.progress = 100;
    renderDocs();
    toast(`演示模式：${doc.name} 已加入列表`);
  }

  function persistDocs() {
    writeJSON(STORAGE.docs, state.docs.filter((doc) => !doc.demo));
  }

  /* ---------------- chat ---------------- */

  function submitQuestion() {
    const question = el.input.value.trim();
    if (!question || state.busy) return;
    el.input.value = "";
    autoGrow();
    ask(question);
  }

  async function ask(question) {
    hideWelcome();
    appendUserMessage(question);
    const ai = appendAssistantMessage();
    setBusy(true);

    try {
      if (state.online) {
        await streamAnswer(question, ai);
      } else {
        await mockAnswer(question, ai);
      }
    } catch (error) {
      ai.answerEl.classList.remove("is-streaming");
      ai.statusEl.textContent = "请求失败";
      ai.answerEl.innerHTML = `<div class="refusal"><div><strong>这次请求没有成功</strong>${escapeHtml(error.message || "未知错误")}</div></div>`;
      toast(error.message || "请求失败", true);
    } finally {
      setBusy(false);
      scrollToBottom(true);
    }
  }

  async function streamAnswer(question, ai) {
    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.sessionId,
        question,
        top_k: state.settings.topK,
      }),
    });

    if (!response.ok) {
      throw new Error(readError(await response.text()) || `HTTP ${response.status}`);
    }
    if (!response.body) {
      throw new Error("当前浏览器不支持流式响应");
    }

    ai.statusEl.textContent = "检索资料…";

    await readSSE(response.body, {
      meta(data) {
        if (data.session_id) setSession(data.session_id);
        ai.statusEl.textContent = "生成中…";
      },
      sources(data) {
        setSources(ai, data.sources || data.documents || []);
      },
      token(data) {
        ai.raw += data.text || data.content || "";
        ai.statusEl.textContent = "生成中…";
        scheduleRender(ai);
      },
      replace(data) {
        ai.raw = data.text || "";
        scheduleRender(ai);
      },
      refusal(data) {
        renderRefusal(ai, data.reason || data.message || "资料中没有找到足够依据。");
      },
      done(data) {
        ai.answerEl.classList.remove("is-streaming");
        const seconds = Number(data.latency_ms) > 0
          ? ` · ${(Number(data.latency_ms) / 1000).toFixed(1)}s`
          : "";
        ai.statusEl.textContent = `完成${seconds}`;
      },
      error(data) {
        throw new Error(data.message || "后端处理失败");
      },
    });

    ai.answerEl.classList.remove("is-streaming");
    renderAnswer(ai);
  }

  async function mockAnswer(question, ai) {
    ai.statusEl.textContent = "检索资料…";
    await sleep(520);

    const matched = pickMock(question);
    if (matched.sources) setSources(ai, matched.sources);
    await sleep(340);

    if (matched.refusal) {
      ai.statusEl.textContent = "已拒答";
      renderRefusal(ai, matched.refusal);
      return;
    }

    ai.statusEl.textContent = "生成中…";
    ai.answerEl.classList.add("is-streaming");

    const text = matched.text;
    for (let index = 0; index < text.length; index += 3) {
      ai.raw += text.slice(index, index + 3);
      scheduleRender(ai);
      await sleep(15);
    }

    ai.answerEl.classList.remove("is-streaming");
    renderAnswer(ai);
    ai.statusEl.textContent = "完成 · 演示";
  }

  function pickMock(question) {
    if (/天气|股票|新闻|明天几点|杭州.*房价/.test(question)) {
      return {
        refusal: "这类问题不在已索引的课程资料中。当前知识库只包含数据结构相关的讲义与复习提纲，建议先补充对应资料。",
      };
    }
    if (/递归|迭代|调用栈/.test(question)) {
      return { text: mockAnswers.recursion, sources: mockSources.recursion };
    }
    if (/考试|重点|考什么|提纲/.test(question)) {
      return { text: mockAnswers.exam, sources: mockSources.exam };
    }
    if (/计划|复习|安排/.test(question)) {
      return { text: mockAnswers.plan, sources: mockSources.plan };
    }
    return { text: mockAnswers.fallback, sources: mockSources.generic };
  }

  function appendUserMessage(text) {
    const article = document.createElement("article");
    article.className = "msg msg-user";
    article.innerHTML = `
      <div class="msg-body"><div class="bubble"></div></div>
      <div class="avatar" aria-hidden="true">我</div>`;
    article.querySelector(".bubble").textContent = text;
    el.messages.appendChild(article);
    scrollToBottom(true);
  }

  function appendAssistantMessage() {
    const article = document.createElement("article");
    article.className = "msg msg-assistant";
    article.innerHTML = `
      <div class="avatar" aria-hidden="true">C</div>
      <div class="msg-body">
        <div class="msg-meta">
          <span>课程助教</span>
          <span class="msg-status">正在思考…</span>
        </div>
        <div class="answer is-streaming" aria-live="polite">
          <div class="typing" aria-label="正在生成"><i></i><i></i><i></i></div>
        </div>
        <div class="sources" hidden></div>
      </div>`;

    el.messages.appendChild(article);
    scrollToBottom(true);

    return {
      article,
      answerEl: article.querySelector(".answer"),
      statusEl: article.querySelector(".msg-status"),
      sourcesEl: article.querySelector(".sources"),
      raw: "",
      sources: [],
      sourceMap: new Map(),
      refusalEl: null,
      raf: null,
    };
  }

  function setSources(ai, sources) {
    ai.sources = (sources || []).map((source, index) => ({
      ...source,
      index: Number(source.index) || index + 1,
    }));
    ai.sourceMap = new Map(ai.sources.map((source) => [source.index, source]));
    renderSources(ai);
    renderAnswer(ai);
  }

  function scheduleRender(ai) {
    if (ai.raf) return;
    ai.raf = requestAnimationFrame(() => {
      ai.raf = null;
      renderAnswer(ai);
    });
  }

  function renderAnswer(ai) {
    if (!ai.raw) return;
    ai.answerEl.innerHTML = renderMarkdown(ai.raw, ai.sourceMap);
  }

  function renderSources(ai) {
    if (!ai.sources.length) {
      ai.sourcesEl.hidden = true;
      ai.sourcesEl.innerHTML = "";
      return;
    }

    ai.sourcesEl.hidden = !state.settings.showSources;
    ai.sourcesEl.innerHTML = `
      <button class="sources-head" type="button" aria-expanded="true">
        <span>引用来源</span>
        <span>· ${ai.sources.length}</span>
        <span class="chevron">▾</span>
      </button>
      <ol class="source-list">
        ${ai.sources.map((source) => `
          <li class="source-item" data-source="${source.index}">
            <span class="source-index">${source.index}</span>
            <div>
              <div class="source-file" title="${escapeHtml(source.file_name || source.source || "未知文件")}">
                ${escapeHtml(source.file_name || source.source || "未知文件")}
                <span class="source-page">p.${escapeHtml(String(source.page ?? "—"))}</span>
              </div>
              <p class="source-snippet">${escapeHtml(source.snippet || source.content || "")}</p>
            </div>
          </li>`).join("")}
      </ol>`;
  }

  function renderRefusal(ai, reason) {
    ai.answerEl.classList.remove("is-streaming");
    if (ai.refusalEl) ai.refusalEl.remove();
    ai.answerEl.innerHTML = "";
    const node = document.createElement("div");
    node.className = "refusal";
    node.innerHTML = `<div><strong>资料中未找到依据</strong>${escapeHtml(reason)}</div>`;
    ai.answerEl.appendChild(node);
    ai.refusalEl = node;
    scrollToBottom();
  }

  /* ---------------- SSE ---------------- */

  async function readSSE(body, handlers) {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    const dispatch = (frame) => {
      let event = "message";
      const dataLines = [];

      for (const line of frame.split(/\r?\n/)) {
        if (!line || line.startsWith(":")) continue;
        const colon = line.indexOf(":");
        if (colon < 0) continue;
        const field = line.slice(0, colon);
        let value = line.slice(colon + 1);
        if (value.startsWith(" ")) value = value.slice(1);

        if (field === "event") event = value.trim();
        if (field === "data") dataLines.push(value);
      }

      if (!dataLines.length) return;
      const payload = dataLines.join("\n");
      let data;
      try {
        data = JSON.parse(payload);
      } catch {
        data = { text: payload };
      }

      const handler = handlers[event];
      if (handler) handler(data);
    };

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let match;
      while ((match = buffer.match(/\r?\n\r?\n/))) {
        const index = match.index;
        const frame = buffer.slice(0, index);
        buffer = buffer.slice(index + match[0].length);
        dispatch(frame);
      }
    }

    buffer += decoder.decode();
    if (buffer.trim()) dispatch(buffer);
  }

  /* ---------------- markdown ---------------- */

  function renderMarkdown(raw, sourceMap) {
    const parts = String(raw).split("```");
    let html = "";

    parts.forEach((part, index) => {
      if (index % 2 === 1) {
        const firstBreak = part.indexOf("\n");
        const code = firstBreak >= 0 ? part.slice(firstBreak + 1) : part;
        html += `<pre><code>${escapeHtml(code.replace(/\n$/, ""))}</code></pre>`;
      } else {
        html += renderBlocks(part, sourceMap);
      }
    });

    return html;
  }

  function renderBlocks(text, sourceMap) {
    return text.split(/\n{2,}/).map((block) => {
      const trimmed = block.trim();
      if (!trimmed) return "";

      if (/^#{1,4}\s+/.test(trimmed)) {
        return `<h3>${inline(trimmed.replace(/^#{1,4}\s+/, ""), sourceMap)}</h3>`;
      }

      if (/^>\s?/.test(trimmed)) {
        return `<blockquote>${inline(trimmed.replace(/^>\s?/gm, ""), sourceMap)}</blockquote>`;
      }

      const lines = trimmed.split("\n");
      if (lines.every((line) => /^\s*[-*]\s+/.test(line))) {
        return `<ul>${lines.map((line) => `<li>${inline(line.replace(/^\s*[-*]\s+/, ""), sourceMap)}</li>`).join("")}</ul>`;
      }

      if (lines.every((line) => /^\s*\d+[.)]\s+/.test(line))) {
        return `<ol>${lines.map((line) => `<li>${inline(line.replace(/^\s*\d+[.)]\s+/, ""), sourceMap)}</li>`).join("")}</ol>`;
      }

      return `<p>${inline(trimmed, sourceMap).replace(/\n/g, "<br>")}</p>`;
    }).join("");
  }

  function inline(text, sourceMap) {
    const codes = [];
    let output = escapeHtml(text);

    output = output.replace(/`([^`]+)`/g, (_, code) => {
      codes.push(code);
      return `\u0000${codes.length - 1}\u0000`;
    });

    output = output.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    output = output.replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");

    output = output.replace(/\[(\d{1,2})\]/g, (match, number) => {
      const index = Number(number);
      if (!sourceMap || !sourceMap.has(index)) return match;
      return `<button class="cite" type="button" data-cite="${index}" aria-label="查看来源 ${index}">${index}</button>`;
    });

    output = output.replace(/\u0000(\d+)\u0000/g, (_, index) => `<code>${codes[Number(index)]}</code>`);
    return output;
  }

  /* ---------------- ui helpers ---------------- */

  function flashSource(cite) {
    const message = cite.closest(".msg");
    const index = cite.dataset.cite;
    const target = message?.querySelector(`.source-item[data-source="${index}"]`);
    if (!target) return;

    const sources = target.closest(".sources");
    if (sources?.classList.contains("is-collapsed")) {
      sources.classList.remove("is-collapsed");
    }
    sources.hidden = false;
    target.scrollIntoView({ behavior: "smooth", block: "nearest" });
    target.classList.add("is-flash");
    setTimeout(() => target.classList.remove("is-flash"), 1300);
  }

  function hideWelcome() {
    if (el.welcome) el.welcome.hidden = true;
  }

  function newChat() {
    if (state.busy) return;
    state.sessionId = newSessionId();
    writeJSON(STORAGE.session, state.sessionId);
    updateSessionLabel();
    el.messages.innerHTML = "";
    if (el.welcome) {
      el.welcome.hidden = false;
      el.messages.appendChild(el.welcome);
    }
    el.input.value = "";
    autoGrow();
    updateSendState();
    el.chatScroll.scrollTop = 0;
    el.input.focus();
    closeSidebar();
  }

  function setSession(sessionId) {
    state.sessionId = sessionId;
    writeJSON(STORAGE.session, sessionId);
    updateSessionLabel();
  }

  function updateSessionLabel() {
    el.sessionLabel.textContent = `会话 ${state.sessionId.slice(0, 8)} · 资料会作为上下文`;
  }

  function autoGrow() {
    el.input.style.height = "auto";
    el.input.style.height = `${Math.min(el.input.scrollHeight, 160)}px`;
  }

  function updateSendState() {
    el.sendBtn.disabled = state.busy || !el.input.value.trim();
  }

  function setBusy(busy) {
    state.busy = busy;
    updateSendState();
  }

  function scrollToBottom(force = false) {
    const distance = el.chatScroll.scrollHeight - el.chatScroll.scrollTop - el.chatScroll.clientHeight;
    if (force || distance < 160) {
      el.chatScroll.scrollTop = el.chatScroll.scrollHeight;
    }
  }

  function openSidebar() {
    el.sidebar.classList.add("is-open");
    el.backdrop.classList.add("is-open");
  }

  function closeSidebar() {
    el.sidebar.classList.remove("is-open");
    el.backdrop.classList.remove("is-open");
  }

  function toggleSettings() {
    const willOpen = el.settingsPop.hidden;
    el.settingsPop.hidden = !willOpen;
    el.settingsBtn.setAttribute("aria-expanded", String(willOpen));
  }

  function hideSettings() {
    el.settingsPop.hidden = true;
    el.settingsBtn.setAttribute("aria-expanded", "false");
  }

  function restoreSettings() {
    el.topK.value = String(state.settings.topK);
    el.topKValue.textContent = String(state.settings.topK);
    el.showSources.checked = state.settings.showSources !== false;
    el.composerHint.textContent = `检索 top ${state.settings.topK} · 流式回答`;
  }

  function toast(message, isError = false) {
    const node = document.createElement("div");
    node.className = `toast${isError ? " is-error" : ""}`;
    node.textContent = message;
    el.toasts.appendChild(node);
    setTimeout(() => {
      node.style.opacity = "0";
      node.style.transform = "translateY(4px)";
      setTimeout(() => node.remove(), 220);
    }, 3200);
  }

  /* ---------------- utils ---------------- */

  function readJSON(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch {
      return fallback;
    }
  }

  function writeJSON(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* storage may be unavailable */
    }
  }

  function readError(text) {
    try {
      const data = JSON.parse(text);
      return data.detail || data.message || "";
    } catch {
      return String(text || "").slice(0, 160);
    }
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function cssEscape(value) {
    return window.CSS?.escape ? CSS.escape(value) : String(value).replace(/["\\]/g, "\\$&");
  }

  function uid(prefix) {
    const random = Math.random().toString(36).slice(2, 8);
    return `${prefix}-${Date.now().toString(36)}-${random}`;
  }

  function newSessionId() {
    if (window.crypto?.randomUUID) return crypto.randomUUID();
    return uid("sess");
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
})();
