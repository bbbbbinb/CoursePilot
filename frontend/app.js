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
    docs: "zhiheng.docs.v1",
    session: "zhiheng.session.v1",
    settings: "zhiheng.settings.v1",
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
    { id: "demo-1", name: "集团差旅与费用报销制度_v3.2.pdf", pages: 18, chunks: 64, status: "ready", demo: true },
    { id: "demo-2", name: "大客户报价与折扣审批流程.md", pages: 6, chunks: 24, status: "ready", demo: true },
    { id: "demo-3", name: "对外合同法律审核管理办法.pdf", pages: 14, chunks: 51, status: "ready", demo: true },
    { id: "demo-4", name: "信息安全事件响应SOP.txt", pages: 9, chunks: 31, status: "ready", demo: true },
  ];

  const mockSources = {
    travel: [
      {
        index: 1,
        file_name: "集团差旅与费用报销制度_v3.2.pdf",
        page: 6,
        snippet: "员工出差住宿费按目的地城市等级执行限额标准：一线城市每人每晚不超过 650 元，其他城市不超过 450 元。",
      },
      {
        index: 2,
        file_name: "集团差旅与费用报销制度_v3.2.pdf",
        page: 9,
        snippet: "住宿费报销须提供酒店发票和入住明细。超过住宿标准的部分原则上由个人承担，特殊情况需提前获得直属负责人审批。",
      },
    ],
    discount: [
      {
        index: 1,
        file_name: "大客户报价与折扣审批流程.md",
        page: 4,
        snippet: "标准折扣区间内由销售负责人审批；低于标准折扣下限的报价，须经财务测算并由事业部总经理审批。",
      },
      {
        index: 2,
        file_name: "大客户报价与折扣审批流程.md",
        page: 5,
        snippet: "涉及非标准付款条件、长期价格锁定或排他条款的折扣申请，应在合同签署前提交法务复核。",
      },
    ],
    contract: [
      {
        index: 1,
        file_name: "对外合同法律审核管理办法.pdf",
        page: 7,
        snippet: "涉及知识产权许可、数据出境、排他条款、责任上限调整或非标准争议解决的对外合同，必须提交法务复核。",
      },
      {
        index: 2,
        file_name: "对外合同法律审核管理办法.pdf",
        page: 8,
        snippet: "业务部门应在合同签署前至少预留三个工作日提交法务审核，不得以客户要求紧急为由先签后审。",
      },
    ],
    security: [
      {
        index: 1,
        file_name: "信息安全事件响应SOP.txt",
        page: 2,
        snippet: "发现疑似数据泄露、账号失陷或核心系统不可用后，应在 30 分钟内报告信息安全响应负责人。",
      },
      {
        index: 2,
        file_name: "信息安全事件响应SOP.txt",
        page: 6,
        snippet: "重大信息安全事件应在 2 小时内形成首份事件简报，并同步业务负责人、法务和公共关系团队。",
      },
    ],
    generic: [
      {
        index: 1,
        file_name: "对外合同法律审核管理办法.pdf",
        page: 7,
        snippet: "本段内容涉及对外业务文件中的审核要求、职责边界和提交时点，需要结合具体业务场景进一步确认。",
      },
    ],
  };

  const mockAnswers = {
    travel: `员工出差住宿需同时满足**城市等级标准**和**凭证要求** [1]。

- **住宿限额**：一线城市每人每晚不超过 650 元，其他城市不超过 450 元。
- **报销材料**：必须提供酒店发票和入住明细 [2]。
- **超标处理**：超出标准的部分原则上由个人承担；确有特殊情况，应提前取得直属负责人审批。

建议在预订前确认目的地对应的城市等级，并保留完整入住凭证，避免报销时发生口径争议。`,
    discount: `客户申请非标折扣需要走正式审批，不应由销售人员在客户侧直接承诺 [1]：

1. 客户经理提交折扣申请、客户背景和预计成交规模。
2. 标准折扣区间内，由销售负责人审批。
3. 低于标准折扣下限时，由财务完成测算，并提交事业部总经理审批。
4. 如同时涉及非标准付款条件、长期价格锁定或排他条款，合同签署前还需提交法务复核 [2]。

最终对外报价应以审批通过的版本为准。`,
    contract: `以下对外合同必须提交法务复核 [1]：

- 涉及知识产权许可或权利归属调整；
- 涉及数据出境、共享或委托处理；
- 包含排他合作、最惠待遇等特殊商业条款；
- 调整责任上限、赔偿范围或采用非标准争议解决方式。

业务部门应在签署前至少预留 **三个工作日** 提交法务审核，不得先签后审 [2]。`,
    security: `发现疑似信息安全事件后，应立即启动报告流程 [1]：

1. **30 分钟内**报告信息安全响应负责人。
2. 保留日志、截图和相关账号信息，不要在未经指示时自行删除或覆盖数据。
3. 重大事件应在 **2 小时内**形成首份事件简报，并同步业务负责人、法务和公共关系团队 [2]。

如果无法判断事件等级，按更高等级先报告，再由响应团队完成定级。`,
    fallback: `我在已入库资料中找到一段可能相关的内容 [1]。不过当前证据不足以直接形成确定结论，建议补充更具体的制度名称、业务场景或时间范围后重新核验。`,
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
      el.input.value = button.dataset.question || button.textContent.trim();
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
      el.composerHint.textContent = `Enter 提交 · Shift + Enter 换行 · 证据召回 ${state.settings.topK} 段`;
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
      el.healthText.textContent = "知识服务已连接";
      el.demoHint.hidden = true;
    } catch {
      enterDemoMode();
    }
  }

  function enterDemoMode() {
    state.online = false;
    el.healthDot.className = "status-dot is-demo";
    el.healthText.textContent = "演示工作区（未连接知识服务）";
    el.demoHint.hidden = false;
    if (state.docs.length === 0) {
      state.docs = demoDocs.slice();
      renderDocs();
    }
  }

  /* ---------------- documents ---------------- */

  function renderDocs() {
    el.docList.innerHTML = "";
    el.docCount.textContent = `${state.docs.length} 份资料`;
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
        toast(`${file.name} 已加入资料空间`);
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
    toast(`演示工作区：${doc.name} 已加入资料空间`);
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
      ai.statusEl.textContent = "核验中断";
      ai.answerEl.innerHTML = `<div class="refusal"><div><strong>本次核验未完成</strong>${escapeHtml(error.message || "未知错误")}</div></div>`;
      setVerification(ai, { status: "error" });
      toast(error.message || "核验请求失败", true);
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

    ai.statusEl.textContent = "正在检索企业资料…";

    await readSSE(response.body, {
      meta(data) {
        if (data.session_id) setSession(data.session_id);
        ai.statusEl.textContent = "正在组织答复…";
      },
      status(data) {
        if (data.message) ai.statusEl.textContent = data.message;
      },
      sources(data) {
        setSources(ai, data.sources || data.documents || []);
      },
      token(data) {
        ai.raw += data.text || data.content || "";
        ai.statusEl.textContent = "正在组织答复…";
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
        ai.statusEl.textContent = `核验完成${seconds}`;
        setVerification(ai, {
          status: ai.sources.length ? "complete" : "no-evidence",
          latencyMs: Number(data.latency_ms) || 0,
        });
      },
      error(data) {
        throw new Error(data.message || "后端处理失败");
      },
    });

    ai.answerEl.classList.remove("is-streaming");
    renderAnswer(ai);
  }

  async function mockAnswer(question, ai) {
    ai.statusEl.textContent = "正在检索企业资料…";
    await sleep(520);

    const matched = pickMock(question);
    if (matched.sources) setSources(ai, matched.sources);
    await sleep(340);

    if (matched.refusal) {
      ai.statusEl.textContent = "已停止推断";
      renderRefusal(ai, matched.refusal);
      return;
    }

    ai.statusEl.textContent = "正在组织答复…";
    ai.answerEl.classList.add("is-streaming");

    const text = matched.text;
    for (let index = 0; index < text.length; index += 3) {
      ai.raw += text.slice(index, index + 3);
      scheduleRender(ai);
      await sleep(15);
    }

    ai.answerEl.classList.remove("is-streaming");
    renderAnswer(ai);
    ai.statusEl.textContent = "核验完成 · 演示";
    setVerification(ai, { status: "complete" });
  }

  function pickMock(question) {
    if (/天气|股票|新闻|明天几点|房价|汇率/.test(question)) {
      return {
        refusal: "这类问题不在当前企业资料空间内。请补充对应的制度、流程或业务文件后再进行核验。",
      };
    }
    if (/差旅|住宿|报销|出差/.test(question)) {
      return { text: mockAnswers.travel, sources: mockSources.travel };
    }
    if (/折扣|报价|非标|审批路径/.test(question)) {
      return { text: mockAnswers.discount, sources: mockSources.discount };
    }
    if (/合同|法务|条款|采购/.test(question)) {
      return { text: mockAnswers.contract, sources: mockSources.contract };
    }
    if (/信息安全|安全事件|应急|上报|事故/.test(question)) {
      return { text: mockAnswers.security, sources: mockSources.security };
    }
    return { text: mockAnswers.fallback, sources: mockSources.generic };
  }

  function appendUserMessage(text) {
    const article = document.createElement("article");
    article.className = "msg msg-user";
    article.innerHTML = `
      <div class="msg-body"><div class="bubble"></div></div>
      <div class="avatar" aria-hidden="true">问</div>`;
    article.querySelector(".bubble").textContent = text;
    el.messages.appendChild(article);
    scrollToBottom(true);
  }

  function appendAssistantMessage() {
    const article = document.createElement("article");
    article.className = "msg msg-assistant";
    article.innerHTML = `
      <div class="avatar" aria-hidden="true">衡</div>
      <div class="msg-body">
        <div class="msg-meta">
          <span>知识核验助手</span>
          <span class="msg-status">正在核验…</span>
        </div>
        <div class="answer is-streaming" aria-live="polite">
          <div class="typing" aria-label="正在核验"><i></i><i></i><i></i></div>
        </div>
        <div class="verification-bar" hidden></div>
        <div class="sources" hidden></div>
      </div>`;

    el.messages.appendChild(article);
    scrollToBottom(true);

    return {
      article,
      answerEl: article.querySelector(".answer"),
      statusEl: article.querySelector(".msg-status"),
      verificationEl: article.querySelector(".verification-bar"),
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
    if (ai.sources.length) setVerification(ai, { status: "evidence" });
    renderSources(ai);
    renderAnswer(ai);
  }

  function setVerification(ai, { status = "evidence", latencyMs = 0 } = {}) {
    if (!ai.verificationEl) return;

    const count = ai.sources.length;
    const time = latencyMs > 0 ? `${(latencyMs / 1000).toFixed(1)}s` : "";
    ai.verificationEl.hidden = false;
    ai.verificationEl.className = "verification-bar";

    if (status === "refusal" || status === "no-evidence" || status === "error") {
      ai.verificationEl.classList.add("is-warning");
      const text = status === "error"
        ? "本次未形成核验结果"
        : "依据不足 · 需补充资料或人工确认";
      ai.verificationEl.innerHTML = `
        <span class="verification-label">核验状态</span>
        <span>${text}</span>
        <span class="verification-time">${status === "error" ? "已中断" : "已停止推断"}</span>`;
      return;
    }

    const label = status === "complete" ? "核验完成" : "已建立证据链";
    ai.verificationEl.innerHTML = `
      <span class="verification-label">${label}</span>
      <span>${count} 条原文依据 · 编号可追溯</span>
      <span class="verification-time">${time || "证据已就绪"}</span>`;
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
    const sourceItems = ai.sources.map((source) => {
      const sourceName = source.file_name || source.title || source.source || "未知文件";
      const sourceUrl = source.source_type === "web" ? safeHttpUrl(source.url) : "";
      const nameHtml = sourceUrl
        ? `<a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noreferrer">${escapeHtml(sourceName)}</a>`
        : escapeHtml(sourceName);
      const sourceMeta = source.source_type === "web"
        ? "网页"
        : `p.${escapeHtml(String(source.page ?? "—"))}`;

      return `<li class="source-item" data-source="${source.index}">
        <span class="source-index">${source.index}</span>
        <div>
          <div class="source-file" title="${escapeHtml(sourceName)}">
            ${nameHtml}
            <span class="source-page">${sourceMeta}</span>
          </div>
          <p class="source-snippet">${escapeHtml(source.snippet || source.content || "")}</p>
        </div>
      </li>`;
    }).join("");

    ai.sourcesEl.innerHTML = `
      <button class="sources-head" type="button" aria-expanded="true">
        <span>证据链</span>
        <span>· ${ai.sources.length} 条可追溯依据</span>
        <span class="chevron">▾</span>
      </button>
      <ol class="source-list">
        ${sourceItems}
      </ol>`;
  }

  function renderRefusal(ai, reason) {
    ai.answerEl.classList.remove("is-streaming");
    if (ai.refusalEl) ai.refusalEl.remove();
    ai.answerEl.innerHTML = "";
    const node = document.createElement("div");
    node.className = "refusal";
    node.innerHTML = `<div><strong>依据不足，已停止推断</strong>${escapeHtml(reason)}</div>`;
    ai.answerEl.appendChild(node);
    ai.refusalEl = node;
    setVerification(ai, { status: "refusal" });
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
    el.sessionLabel.textContent = `核验 #${state.sessionId.slice(0, 8)} · 仅基于已入库资料`;
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
    el.composerHint.textContent = `Enter 提交 · Shift + Enter 换行 · 证据召回 ${state.settings.topK} 段`;
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

  function safeHttpUrl(value) {
    try {
      const url = new URL(String(value));
      return ["http:", "https:"].includes(url.protocol) ? url.href : "";
    } catch {
      return "";
    }
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
