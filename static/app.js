const state = {
  accessCode: localStorage.getItem("lanClipboardAccessCode") || "",
  config: null,
  busy: false,
  toastTimer: null,
};

const $ = (selector) => document.querySelector(selector);
const itemsEl = $("#items");
const textInput = $("#textInput");
const textCount = $("#textCount");
const textForm = $("#textForm");
const uploadForm = $("#uploadForm");
const fileInput = $("#fileInput");
const dropZone = $("#dropZone");
const selectedFiles = $("#selectedFiles");
const fileHint = $("#fileHint");
const uploadButton = $("#uploadForm button[type='submit']");
const accessCodeInput = $("#accessCode");
const codeBox = $("#codeBox");
const serverMeta = $("#serverMeta");
const syncState = $("#syncState");
const toast = $("#toast");

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("is-visible");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.remove("is-visible"), 2200);
}

function bytes(value) {
  if (!Number.isFinite(value)) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let size = value;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  const digits = unit === 0 ? 0 : size >= 10 ? 1 : 2;
  return `${size.toFixed(digits)} ${units[unit]}`;
}

function formatTime(seconds) {
  if (!seconds) return "不自动删除";
  return new Date(seconds * 1000).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return "不自动删除";
  if (seconds % 86400 === 0) return `${seconds / 86400} 天`;
  if (seconds % 3600 === 0) return `${seconds / 3600} 小时`;
  if (seconds % 60 === 0) return `${seconds / 60} 分钟`;
  return `${seconds} 秒`;
}

function ttlFrom(selectId) {
  return Number($(selectId).value || 0);
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.accessCode) headers.set("X-Access-Code", state.accessCode);
  const response = await fetch(path, { ...options, headers });
  const contentType = response.headers.get("Content-Type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (response.status === 401) {
    codeBox.classList.add("is-visible");
    accessCodeInput.focus();
  }
  if (!response.ok) {
    throw new Error(payload.error || `请求失败: ${response.status}`);
  }
  return payload;
}

async function loadConfig() {
  state.config = await api("/api/config");
  if (state.config.requiresAccessCode || state.accessCode) {
    codeBox.classList.add("is-visible");
  }
  fileHint.textContent = `单次上传上限 ${bytes(state.config.maxUploadBytes)}`;
  serverMeta.textContent = `最多保留 ${state.config.maxItems} 条，默认 ${formatDuration(state.config.defaultTtlSeconds)}`;
}

function uploadFormData(path, form, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", path);
    if (state.accessCode) xhr.setRequestHeader("X-Access-Code", state.accessCode);
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) onProgress(event.loaded, event.total);
    });
    xhr.addEventListener("load", () => {
      const contentType = xhr.getResponseHeader("Content-Type") || "";
      const payload = contentType.includes("application/json") ? JSON.parse(xhr.responseText || "{}") : xhr.responseText;
      if (xhr.status === 401) {
        codeBox.classList.add("is-visible");
        accessCodeInput.focus();
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(payload);
      } else {
        reject(new Error(payload.error || `上传失败: ${xhr.status}`));
      }
    });
    xhr.addEventListener("error", () => reject(new Error("上传失败，请检查网络")));
    xhr.addEventListener("abort", () => reject(new Error("上传已取消")));
    xhr.send(form);
  });
}

async function refreshItems() {
  if (state.busy) return;
  syncState.textContent = "同步中";
  try {
    const data = await api("/api/items");
    renderItems(data.items || []);
    syncState.textContent = `已同步 ${new Date().toLocaleTimeString("zh-CN", { hour12: false })}`;
  } catch (error) {
    syncState.textContent = "同步失败";
    showToast(error.message);
  }
}

function renderItems(items) {
  itemsEl.replaceChildren();
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "暂无内容";
    itemsEl.append(empty);
    return;
  }

  for (const item of items) {
    const card = document.createElement("article");
    card.className = "item";
    card.dataset.id = item.id;

    const head = document.createElement("div");
    head.className = "item-head";

    const meta = document.createElement("div");
    meta.className = "item-meta";
    const badge = document.createElement("span");
    badge.className = `badge ${item.kind === "file" ? "file" : ""}`;
    badge.textContent = item.kind === "file" ? "文件" : "文本";
    const created = document.createElement("span");
    created.textContent = `发布 ${formatTime(item.createdAt)}`;
    const expires = document.createElement("span");
    expires.textContent = `保留 ${formatTime(item.expiresAt)}`;
    meta.append(badge, created, expires);
    if (item.kind === "file") {
      const storage = document.createElement("span");
      storage.textContent = item.storageBackend === "memory" ? "内存" : "硬盘";
      meta.append(storage);
    }

    const actions = document.createElement("div");
    actions.className = "item-actions";

    if (item.kind === "text") {
      const copyBtn = document.createElement("button");
      copyBtn.type = "button";
      copyBtn.textContent = "复制";
      copyBtn.addEventListener("click", () => copyText(item.content || ""));
      actions.append(copyBtn);
    } else {
      const downloadBtn = document.createElement("button");
      downloadBtn.type = "button";
      downloadBtn.textContent = "下载";
      downloadBtn.addEventListener("click", () => downloadFile(item));
      actions.append(downloadBtn);
    }

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "delete-btn";
    deleteBtn.textContent = "删除";
    deleteBtn.addEventListener("click", () => deleteItem(item.id));
    actions.append(deleteBtn);
    head.append(meta, actions);
    card.append(head);

    if (item.kind === "text") {
      const body = document.createElement("pre");
      body.className = "text-body";
      body.textContent = item.content || "";
      card.append(body);
    } else {
      const body = document.createElement("div");
      body.className = "file-body";
      const name = document.createElement("div");
      name.className = "file-name";
      name.textContent = item.filename || "download";
      const size = document.createElement("div");
      size.className = "file-size";
      size.textContent = bytes(item.size || 0);
      body.append(name, size);
      card.append(body);
    }
    itemsEl.append(card);
  }
}

async function copyText(content) {
  try {
    await navigator.clipboard.writeText(content);
    showToast("已复制");
  } catch {
    const area = document.createElement("textarea");
    area.value = content;
    document.body.append(area);
    area.select();
    document.execCommand("copy");
    area.remove();
    showToast("已复制");
  }
}

function downloadFile(item) {
  const url = new URL(item.downloadUrl, window.location.href);
  if (state.accessCode) url.searchParams.set("code", state.accessCode);

  const link = document.createElement("a");
  link.href = url.toString();
  link.download = item.filename || "download";
  link.rel = "noopener";
  document.body.append(link);
  link.click();
  link.remove();
  showToast("已开始下载");
}

async function deleteItem(id) {
  try {
    await api(`/api/items/${encodeURIComponent(id)}`, { method: "DELETE" });
    showToast("已删除");
    await refreshItems();
  } catch (error) {
    showToast(error.message);
  }
}

textInput.addEventListener("input", () => {
  textCount.textContent = bytes(new TextEncoder().encode(textInput.value).length);
});

textForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const content = textInput.value;
  if (!content.trim()) {
    showToast("文本不能为空");
    return;
  }
  try {
    state.busy = true;
    await api("/api/text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, expiresInSeconds: ttlFrom("#textTtl") }),
    });
    textInput.value = "";
    textCount.textContent = "0 B";
    showToast("已发送");
  } catch (error) {
    showToast(error.message);
  } finally {
    state.busy = false;
    await refreshItems();
  }
});

function updateSelectedFiles() {
  const files = [...fileInput.files];
  selectedFiles.textContent = files.length
    ? files.map((file) => `${file.name} (${bytes(file.size)})`).join("，")
    : "未选择文件";
}

fileInput.addEventListener("change", updateSelectedFiles);

for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("is-dragging");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("is-dragging");
  });
}

dropZone.addEventListener("drop", (event) => {
  if (event.dataTransfer.files.length) {
    fileInput.files = event.dataTransfer.files;
    updateSelectedFiles();
  }
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const files = [...fileInput.files];
  if (!files.length) {
    showToast("请选择文件");
    return;
  }
  if (state.config && files.some((file) => file.size > state.config.maxUploadBytes)) {
    showToast("有文件超过大小限制");
    return;
  }
  const totalSize = files.reduce((sum, file) => sum + file.size, 0);
  if (state.config && totalSize > state.config.maxUploadBytes) {
    showToast("单次上传总大小超过限制");
    return;
  }
  const form = new FormData();
  files.forEach((file) => form.append("file", file));
  form.append("expiresInSeconds", ttlFrom("#fileTtl"));
  try {
    state.busy = true;
    uploadButton.disabled = true;
    await uploadFormData("/api/upload", form, (loaded, total) => {
      const percent = Math.round((loaded / total) * 100);
      selectedFiles.textContent = `上传中 ${percent}% · ${bytes(loaded)} / ${bytes(total)}`;
    });
    fileInput.value = "";
    updateSelectedFiles();
    showToast("已上传");
  } catch (error) {
    showToast(error.message);
  } finally {
    uploadButton.disabled = false;
    state.busy = false;
    await refreshItems();
  }
});

$("#refreshBtn").addEventListener("click", refreshItems);

$("#clearBtn").addEventListener("click", async () => {
  if (!confirm("清空所有内容？")) return;
  try {
    await api("/api/clear", { method: "POST" });
    showToast("已清空");
    await refreshItems();
  } catch (error) {
    showToast(error.message);
  }
});

accessCodeInput.value = state.accessCode;
accessCodeInput.addEventListener("input", () => {
  state.accessCode = accessCodeInput.value.trim();
  localStorage.setItem("lanClipboardAccessCode", state.accessCode);
});

loadConfig()
  .then(refreshItems)
  .catch((error) => showToast(error.message));

setInterval(refreshItems, 3000);
