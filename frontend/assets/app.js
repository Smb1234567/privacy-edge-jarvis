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
  const contentEl = node.querySelector(".content");
  chatLog.appendChild(node);
  chatLog.scrollTop = chatLog.scrollHeight;
  return contentEl;
}

function renderStack(container, items, emptyText) {
  container.innerHTML = "";
  if (!items || items.length === 0) {
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = emptyText;
    container.appendChild(p);
    return;
  }

  for (const item of items) {
    const block = document.createElement("div");
    block.className = "trace-item";
    block.textContent = JSON.stringify(item, null, 2);
    container.appendChild(block);
  }
}

async function refreshMetrics() {
  try {
    const res = await fetch("/api/benchmark/metrics");
    const data = await res.json();
    renderStack(metrics, [data], "No metrics yet");
  } catch (err) {
    renderStack(metrics, [{ error: String(err) }], "No metrics yet");
  }
}

async function refreshSystemStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    renderStack(systemStatus, [data], "No status yet");
  } catch (err) {
    renderStack(systemStatus, [{ error: String(err) }], "No status yet");
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

  if (!res.ok || !res.body) {
    throw new Error(`HTTP ${res.status}`);
  }

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
        renderStack(toolTrace, event.tool_trace, "No tools called");
        renderStack(citations, event.citations, "No citations returned");
      }

      if (event.type === "token") {
        text += event.token;
        assistantContent.textContent = text;
        chatLog.scrollTop = chatLog.scrollHeight;
      }

      if (event.type === "done") {
        assistantContent.textContent = `${text}\n\nLatency: ${event.latency_ms} ms\nLLM: ${event.llm.provider}/${event.llm.model} (${event.llm.status})`;
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
    createMessage("Assistant", "Choose one or more files before uploading.");
    return;
  }

  const form = new FormData();
  for (const f of files) form.append("files", f);

  try {
    const res = await fetch("/api/ingest", {
      method: "POST",
      body: form,
    });
    const data = await res.json();
    createMessage("Assistant", `Upload complete. Indexed: ${JSON.stringify(data.indexed)}`);
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

createMessage("Assistant", "Ready. Upload docs, then chat with streaming responses and grounded citations.");
refreshMetrics();
refreshSystemStatus();
