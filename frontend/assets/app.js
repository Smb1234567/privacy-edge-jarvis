const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const toolTrace = document.getElementById("tool-trace");
const citations = document.getElementById("citations");
const metrics = document.getElementById("metrics");
const metricsBtn = document.getElementById("metrics-btn");
const template = document.getElementById("msg-template");

function addMessage(role, content) {
  const node = template.content.cloneNode(true);
  node.querySelector(".role").textContent = role;
  node.querySelector(".content").textContent = content;
  const msg = node.querySelector(".msg");
  if (role === "Assistant") msg.classList.add("assistant");
  chatLog.appendChild(node);
  chatLog.scrollTop = chatLog.scrollHeight;
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

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = chatInput.value.trim();
  if (!query) return;

  addMessage("You", query);
  chatInput.value = "";

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    const data = await res.json();
    addMessage("Assistant", `${data.answer}\n\nLatency: ${data.latency_ms} ms`);
    renderStack(toolTrace, data.tool_trace, "No tools called");
    renderStack(citations, data.citations, "No citations returned");
    refreshMetrics();
  } catch (err) {
    addMessage("Assistant", `Request failed: ${String(err)}`);
  }
});

metricsBtn.addEventListener("click", refreshMetrics);

addMessage("Assistant", "Ready. Upload documents via /api/ingest, then ask grounded questions.");
refreshMetrics();
