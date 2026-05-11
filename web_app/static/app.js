let activeArchive = null;
let activeFigure = "graph";

const archiveList = document.getElementById("archiveList");
const statusText = document.getElementById("statusText");
const runForm = document.getElementById("runForm");
const runButton = document.getElementById("runButton");
const pdfFrame = document.getElementById("pdfFrame");
const figureImage = document.getElementById("figureImage");
const pdfDownload = document.getElementById("pdfDownload");
const graphDownload = document.getElementById("graphDownload");
const keywordsDownload = document.getElementById("keywordsDownload");
const chatMessages = document.getElementById("chatMessages");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const activeArchiveLabel = document.getElementById("activeArchiveLabel");
const settingsForm = document.getElementById("settingsForm");
const apiUrlInput = document.getElementById("apiUrlInput");
const modelInput = document.getElementById("modelInput");
const apiKeyInput = document.getElementById("apiKeyInput");
const settingsStatus = document.getElementById("settingsStatus");
const dateDaysInput = document.getElementById("dateDaysInput");
const allDatesInput = document.getElementById("allDatesInput");

function archiveFileUrl(archiveId, filename) {
  return `/api/archives/${encodeURIComponent(archiveId)}/file/${encodeURIComponent(filename)}`;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }
  return data;
}

function archiveTitle(archive) {
  return archive.query || archive.id;
}

function archiveDateLabel(archive) {
  if (archive.date_label) return `查询 ${archive.date_label}`;
  if (archive.date_start && archive.date_end && archive.date_start !== "all") {
    return `查询 ${archive.date_start} 至 ${archive.date_end}`;
  }
  if (archive.date_range) return `查询 ${archive.date_range}`;
  return "查询时间未知";
}

function setText(node, value) {
  node.textContent = value || "";
}

async function loadArchives(selectFirst = false) {
  const data = await fetchJson("/api/archives");
  archiveList.innerHTML = "";
  data.archives.forEach((archive) => {
    const item = document.createElement("button");
    item.className = "archive-item";
    if (activeArchive && archive.id === activeArchive.id) item.classList.add("active");

    const title = document.createElement("span");
    const range = document.createElement("small");
    const id = document.createElement("small");
    setText(title, archiveTitle(archive));
    setText(range, archiveDateLabel(archive));
    setText(id, archive.id);
    item.append(title, range, id);
    item.addEventListener("click", () => selectArchive(archive.id));
    archiveList.appendChild(item);
  });
  if (selectFirst && data.archives.length) {
    await selectArchive(data.archives[0].id);
  }
}

async function loadSettings() {
  const settings = await fetchJson("/api/settings");
  apiUrlInput.value = settings.api_url || "";
  modelInput.value = settings.model || "gpt-5.4";
  apiKeyInput.value = "";
  settingsStatus.textContent = settings.has_api_key
    ? "已保存 API Key"
    : "未保存 API Key，聊天将使用本地文件检索";
}

async function selectArchive(archiveId) {
  const data = await fetchJson(`/api/archives/${encodeURIComponent(archiveId)}`);
  activeArchive = data.metadata;
  activeArchiveLabel.textContent = `${archiveTitle(activeArchive)}\n${archiveDateLabel(activeArchive)}`;
  renderDownloads();
  renderChat(data.chat.messages || []);
  await loadArchives(false);
}

function renderDownloads() {
  const files = activeArchive.files || {};
  setDownload(pdfDownload, files.report_pdf, "下载 PDF");
  setDownload(graphDownload, files.keyword_graph, "下载图谱");
  setDownload(keywordsDownload, files.top_keywords, "下载关键词图");

  if (files.report_pdf) {
    pdfFrame.src = archiveFileUrl(activeArchive.id, files.report_pdf);
  } else {
    pdfFrame.removeAttribute("src");
  }
  updateFigure();
}

function setDownload(link, filename, label) {
  if (!activeArchive || !filename) {
    link.hidden = true;
    link.href = "#";
    return;
  }
  link.hidden = false;
  link.textContent = label;
  link.href = archiveFileUrl(activeArchive.id, filename);
  link.download = filename;
}

function updateFigure() {
  if (!activeArchive) return;
  const files = activeArchive.files || {};
  const filename = activeFigure === "graph" ? files.keyword_graph : files.top_keywords;
  if (filename) {
    figureImage.src = archiveFileUrl(activeArchive.id, filename);
    figureImage.hidden = false;
  } else {
    figureImage.removeAttribute("src");
    figureImage.hidden = true;
  }
}

function renderChat(messages) {
  chatMessages.innerHTML = "";
  messages.forEach((message) => appendMessage(message.role, message.content));
}

function appendMessage(role, content) {
  const node = document.createElement("div");
  node.className = `message ${role === "user" ? "user" : "assistant"}`;
  node.textContent = content;
  chatMessages.appendChild(node);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function currentDateRange() {
  if (allDatesInput.checked) return "all";
  const days = Math.max(1, Math.min(3650, Number(dateDaysInput.value || 7)));
  dateDaysInput.value = String(days);
  return `last ${days} days`;
}

runForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    query: document.getElementById("queryInput").value,
    date_range: currentDateRange(),
    max_results: Number(document.getElementById("maxResultsInput").value),
    top_k: Number(document.getElementById("topKInput").value),
  };
  runButton.disabled = true;
  statusText.textContent = `正在检索 arXiv、排序并生成 PDF（${payload.date_range}）...`;
  try {
    const data = await fetchJson("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    activeArchive = data.archive.metadata;
    statusText.textContent = `完成：${archiveTitle(activeArchive)}，${archiveDateLabel(activeArchive)}`;
    await loadArchives(false);
    await selectArchive(activeArchive.id);
  } catch (error) {
    statusText.textContent = `运行失败：${error.message}`;
  } finally {
    runButton.disabled = false;
  }
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!activeArchive) {
    statusText.textContent = "请先运行或选择一个归档。";
    return;
  }
  const message = chatInput.value.trim();
  if (!message) return;
  chatInput.value = "";
  appendMessage("user", message);
  appendMessage("assistant", "正在阅读归档文件并回答...");
  try {
    const data = await fetchJson("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ archive_id: activeArchive.id, message }),
    });
    renderChat(data.messages);
  } catch (error) {
    renderChat([{ role: "assistant", content: `对话失败：${error.message}` }]);
  }
});

settingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  settingsStatus.textContent = "正在保存设置...";
  try {
    const settings = await fetchJson("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        api_url: apiUrlInput.value,
        model: modelInput.value,
        api_key: apiKeyInput.value,
      }),
    });
    apiKeyInput.value = "";
    settingsStatus.textContent = settings.has_api_key
      ? "设置已保存，聊天将使用模型接口"
      : "设置已保存，但未填写 API Key";
  } catch (error) {
    settingsStatus.textContent = `保存失败：${error.message}`;
  }
});

allDatesInput.addEventListener("change", () => {
  dateDaysInput.disabled = allDatesInput.checked;
});

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    activeFigure = button.dataset.image;
    updateFigure();
  });
});

document.getElementById("newRunButton").addEventListener("click", () => {
  activeArchive = null;
  activeArchiveLabel.textContent = "未选择归档";
  chatMessages.innerHTML = "";
  pdfFrame.removeAttribute("src");
  figureImage.removeAttribute("src");
  [pdfDownload, graphDownload, keywordsDownload].forEach((link) => (link.hidden = true));
  statusText.textContent = "准备新实验";
});

loadSettings().catch((error) => {
  settingsStatus.textContent = `加载设置失败：${error.message}`;
});

loadArchives(true).catch((error) => {
  statusText.textContent = `加载归档失败：${error.message}`;
});
