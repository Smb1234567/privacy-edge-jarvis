const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const uploadForm = document.getElementById("upload-form");
const fileInput = document.getElementById("file-input");
const toolTrace = document.getElementById("tool-trace");
const citations = document.getElementById("citations");
const metrics = document.getElementById("metrics");
const systemStatus = document.getElementById("system-status");
const metricsBtn = document.getElementById("metrics-btn");
const template = document.getElementById("msg-template");

function createMessage(role, content = "") {
  const node = template.content.cloneNode(true);
  node.querySelector(".role").textContent = role;
  node.querySelector(".content").textContent = content;
  const msg = node.querySelector(".msg");
  if (role === "Assistant") msg.classList.add("assistant");
  if (role === "You") msg.classList.add("user");
  const contentEl = node.querySelector(".content");
  chatLog.appendChild(node);
  chatLog.scrollTop = chatLog.scrollHeight;
  return contentEl;
}

function setEmpty(container, text) {
  container.innerHTML = "";
  const p = document.createElement("p");
  p.className = "muted";
  p.textContent = text;
  container.appendChild(p);
}

function card(label, value, tone = "") {
  const el = document.createElement("div");
  el.className = `kv ${tone}`.trim();
  el.innerHTML = `<p class="k">${label}</p><p class="v">${value}</p>`;
  return el;
}

function renderToolTrace(items) {
  toolTrace.innerHTML = "";
  if (!items || items.length === 0) return setEmpty(toolTrace, "No tools called yet");
  for (const t of items) {
    const hitText = t.hits !== undefined ? `${t.hits} hits` : t.rows !== undefined ? `${t.rows} rows` : "";
    const tone = t.status === "ok" ? "ok" : "warn";
    toolTrace.appendChild(card(`${t.tool}`, `${t.status}${hitText ? ` • ${hitText}` : ""}`, tone));
  }
}

function renderCitations(items) {
  citations.innerHTML = "";
  if (!items || items.length === 0) return setEmpty(citations, "No citations yet");
  for (const c of items) {
    const source = c.source.split("/").slice(-1)[0];
    citations.appendChild(card(`${source} • ${c.chunk_id}`, `score ${c.score}`));
  }
}

function renderMetrics(data) {
  metrics.innerHTML = "";
  if (!data) return setEmpty(metrics, "No metrics yet");
  metrics.appendChild(card("Process RSS", `${data.process_rss_mb} MB`));
  metrics.appendChild(card("CPU", `${data.cpu_percent}%`));
  metrics.appendChild(card("RAM", `${data.ram_percent}%`));
}

function renderStatus(data) {
  systemStatus.innerHTML = "";
  if (!data || !data.llm || !data.index) return setEmpty(systemStatus, "No status yet");

  const llmTone = data.llm.status === "ok" ? "ok" : "warn";
  const docs = data.index.documents ?? 0;
  const chunks = data.index.chunks ?? 0;

  systemStatus.appendChild(card("Model", `${data.llm.model}`, llmTone));
  systemStatus.appendChild(card("LLM Status", `${data.llm.status}`, llmTone));
  systemStatus.appendChild(card("Indexed Docs", `${docs}`));
  systemStatus.appendChild(card("Indexed Chunks", `${chunks}`));
}

async function refreshMetrics() {
  try {
    const res = await fetch("/api/benchmark/metrics");
    renderMetrics(await res.json());
  } catch {
    setEmpty(metrics, "Metrics unavailable");
  }
}

async function refreshSystemStatus() {
  try {
    const res = await fetch("/api/status");
    renderStatus(await res.json());
  } catch {
    setEmpty(systemStatus, "Status unavailable");
  }
}

async function runStreamingChat(query) {
  const assistantContent = createMessage("Assistant", "Thinking...");
  let text = "";

  const res = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });

  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let idx = buffer.indexOf("\n");
    while (idx >= 0) {
      const line = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 1);
      idx = buffer.indexOf("\n");
      if (!line) continue;

      const event = JSON.parse(line);
      if (event.type === "meta") {
        renderToolTrace(event.tool_trace);
        renderCitations(event.citations);
      }
      if (event.type === "token") {
        text += event.token;
        assistantContent.textContent = text;
        chatLog.scrollTop = chatLog.scrollHeight;
      }
      if (event.type === "done") {
        assistantContent.textContent = `${text}\n\n${event.latency_ms} ms • ${event.llm.provider}/${event.llm.model} (${event.llm.status})`;
      }
    }
  }
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = chatInput.value.trim();
  if (!query) return;

  createMessage("You", query);
  chatInput.value = "";
  chatInput.focus();

  try {
    await runStreamingChat(query);
    refreshMetrics();
    refreshSystemStatus();
  } catch (err) {
    createMessage("Assistant", `Request failed: ${String(err)}`);
  }
});

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const files = fileInput.files;
  if (!files || files.length === 0) {
    createMessage("Assistant", "Select one or more files before upload.");
    return;
  }

  const form = new FormData();
  for (const f of files) form.append("files", f);

  try {
    const res = await fetch("/api/ingest", { method: "POST", body: form });
    const data = await res.json();
    createMessage(
      "Assistant",
      `Upload complete. Documents: ${data.indexed.documents_indexed}, Chunks: ${data.indexed.chunks_indexed}.`
    );
    fileInput.value = "";
    refreshSystemStatus();
  } catch (err) {
    createMessage("Assistant", `Upload failed: ${String(err)}`);
  }
});

metricsBtn.addEventListener("click", () => {
  refreshMetrics();
  refreshSystemStatus();
});

createMessage("Assistant", "Ready. Upload docs on the left, then ask for analysis/summaries with citations.");
setEmpty(toolTrace, "No tools called yet");
setEmpty(citations, "No citations yet");
refreshMetrics();
refreshSystemStatus();
