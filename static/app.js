const state = {
  accessCode: localStorage.getItem("lanClipboardAccessCode") || "",
  config: null,
  busy: false,
  toastTimer: null,
  serverTimeOffsetSeconds: 0,
};

const $ = (selector) => document.querySelector(selector);
const appShell = $(".app-shell");
const itemsEl = $("#items");
const textInput = $("#textInput");
const textCount = $("#textCount");
const textForm = $("#textForm");
const textTtl = $("#textTtl");
const uploadForm = $("#uploadForm");
const fileInput = $("#fileInput");
const fileTtl = $("#fileTtl");
const dropZone = $("#dropZone");
const selectedFiles = $("#selectedFiles");
const fileHint = $("#fileHint");
const uploadButton = $("#uploadForm button[type='submit']");
const accessCodeInput = $("#accessCode");
const codeBox = $("#codeBox");
const serverMeta = $("#serverMeta");
const syncState = $("#syncState");
const diskWarning = $("#diskWarning");
const toast = $("#toast");
const mobileViewButtons = [...document.querySelectorAll(".mobile-view-switch button[data-mobile-view]")];

function setMobileView(view) {
  if (!appShell || !["feed", "text", "file"].includes(view)) return;
  appShell.dataset.mobileView = view;
  mobileViewButtons.forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.mobileView === view));
  });
}

function showRecentContentOnMobile() {
  if (window.matchMedia("(max-width: 820px)").matches) {
    setMobileView("feed");
  }
}

mobileViewButtons.forEach((button) => {
  button.addEventListener("click", () => setMobileView(button.dataset.mobileView));
});

setMobileView("feed");

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

function formatCountdown(seconds) {
  const remaining = Math.max(0, Math.ceil(seconds));
  if (remaining <= 0) return "等待清理";

  const days = Math.floor(remaining / 86400);
  const hours = Math.floor((remaining % 86400) / 3600);
  const minutes = Math.floor((remaining % 3600) / 60);
  const secs = remaining % 60;
  const twoDigits = (value) => String(value).padStart(2, "0");
  if (days > 0) return `剩余 ${days} 天 ${twoDigits(hours)}:${twoDigits(minutes)}:${twoDigits(secs)}`;
  if (hours > 0) return `剩余 ${twoDigits(hours)}:${twoDigits(minutes)}:${twoDigits(secs)}`;
  return `剩余 ${twoDigits(minutes)}:${twoDigits(secs)}`;
}

function updateCountdowns() {
  const now = Date.now() / 1000 + state.serverTimeOffsetSeconds;
  document.querySelectorAll(".expiry-countdown").forEach((countdown) => {
    const expiresAt = Number(countdown.dataset.expiresAt || 0);
    if (!expiresAt) {
      countdown.textContent = "长期保留";
      countdown.classList.remove("is-expired");
      countdown.setAttribute("aria-label", "文件不自动删除");
      return;
    }

    const remaining = expiresAt - now;
    const formatted = formatCountdown(remaining);
    countdown.textContent = formatted;
    countdown.classList.toggle("is-expired", remaining <= 0);
    countdown.setAttribute(
      "aria-label",
      remaining > 0 ? `距离文件自动删除还有 ${formatted.replace("剩余 ", "")}` : "文件正在等待自动清理",
    );
  });
}

function applyDefaultTtl(select, seconds) {
  const value = String(seconds > 0 ? Math.round(seconds) : 0);
  select.querySelectorAll("option.server-default").forEach((option) => option.remove());
  let option = [...select.options].find((candidate) => candidate.value === value);
  if (!option) {
    option = document.createElement("option");
    option.className = "server-default";
    option.value = value;
    option.textContent = `默认 ${formatDuration(Number(value))}`;
    select.prepend(option);
  }
  select.value = value;
}

function updateDiskWarning(config) {
  if (!diskWarning || !config) return;
  const free = Number(config.diskFreeBytes);
  const reserve = Number(config.diskReserveBytes || 0);
  const usable = Number(config.diskUsableBytes);
  const maxUpload = Number(config.maxUploadBytes || 0);
  let message = "";

  if (Number.isFinite(usable) && usable <= 0) {
    message = `硬盘空间不足：剩余 ${bytes(free)}，已低于系统预留 ${bytes(reserve)}。请删除旧文件、等待自动清理，或扩容后再上传。`;
  } else if (Number.isFinite(usable) && maxUpload > 0 && usable < maxUpload) {
    message = `硬盘空间偏低：可用于落盘约 ${bytes(usable)}，低于单次上传上限 ${bytes(maxUpload)}。大文件可能会失败。`;
  }

  diskWarning.textContent = message;
  diskWarning.hidden = !message;
}

function ttlFrom(selectId) {
  return Number($(selectId).value || 0);
}

function calibrateServerTime(serverTime, requestedAt, receivedAt) {
  if (!Number.isFinite(serverTime)) return;
  state.serverTimeOffsetSeconds = serverTime - (requestedAt + receivedAt) / 2;
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const method = String(options.method || "GET").toUpperCase();
  if (state.accessCode) headers.set("X-Access-Code", state.accessCode);
  if (!["GET", "HEAD", "OPTIONS"].includes(method) && state.config?.csrfToken) {
    headers.set("X-CSRF-Token", state.config.csrfToken);
  }
  const requestedAt = Date.now() / 1000;
  const response = await fetch(path, { ...options, headers });
  const receivedAt = Date.now() / 1000;
  const responseDate = Date.parse(response.headers.get("Date") || "") / 1000;
  calibrateServerTime(responseDate, requestedAt, receivedAt);
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
  applyDefaultTtl(textTtl, state.config.defaultTtlSeconds);
  applyDefaultTtl(fileTtl, state.config.defaultTtlSeconds);
  updateDiskWarning(state.config);
}

function uploadFormData(path, form, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", path);
    if (state.accessCode) xhr.setRequestHeader("X-Access-Code", state.accessCode);
    if (state.config?.csrfToken) xhr.setRequestHeader("X-CSRF-Token", state.config.csrfToken);
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
    const requestedAt = Date.now() / 1000;
    const data = await api("/api/items");
    const receivedAt = Date.now() / 1000;
    const serverTime = Number(data.serverTime);
    calibrateServerTime(serverTime, requestedAt, receivedAt);
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
      const details = document.createElement("div");
      details.className = "file-details";
      const size = document.createElement("div");
      size.className = "file-size";
      size.textContent = bytes(item.size || 0);
      const countdown = document.createElement("span");
      countdown.className = "expiry-countdown";
      countdown.dataset.expiresAt = String(item.expiresAt || 0);
      countdown.title = "自动删除倒计时";
      details.append(size, countdown);
      if (item.expiresAt) {
        const extension = document.createElement("div");
        extension.className = "expiry-extension";
        const extensionSelect = document.createElement("select");
        extensionSelect.setAttribute("aria-label", `延长 ${item.filename || "文件"} 的保存时间`);
        for (const [seconds, label] of [
          [1800, "+30 分钟"],
          [7200, "+2 小时"],
          [28800, "+8 小时"],
          [86400, "+24 小时"],
        ]) {
          const option = document.createElement("option");
          option.value = String(seconds);
          option.textContent = label;
          extensionSelect.append(option);
        }
        const extendButton = document.createElement("button");
        extendButton.type = "button";
        extendButton.textContent = "延长";
        extendButton.addEventListener("click", () => {
          extendFile(item.id, Number(extensionSelect.value), extendButton);
        });
        extension.append(extensionSelect, extendButton);
        details.append(extension);
      }
      body.append(name, details);
      card.append(body);
    }
    itemsEl.append(card);
  }
  updateCountdowns();
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
    await loadConfig();
    await refreshItems();
  } catch (error) {
    showToast(error.message);
  }
}

async function extendFile(id, seconds, button) {
  button.disabled = true;
  try {
    await api(`/api/items/${encodeURIComponent(id)}/extend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seconds }),
    });
    showToast(`已延长 ${formatDuration(seconds)}`);
    await refreshItems();
  } catch (error) {
    showToast(error.message);
    button.disabled = false;
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
    showRecentContentOnMobile();
  } catch (error) {
    showToast(error.message);
  } finally {
    state.busy = false;
    await loadConfig();
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
    showRecentContentOnMobile();
  } catch (error) {
    showToast(error.message);
  } finally {
    uploadButton.disabled = false;
    state.busy = false;
    await loadConfig();
    await refreshItems();
  }
});

$("#refreshBtn").addEventListener("click", async () => {
  await loadConfig();
  await refreshItems();
});

$("#clearBtn").addEventListener("click", async () => {
  if (!confirm("清空所有内容？")) return;
  try {
    await api("/api/clear", { method: "POST" });
    showToast("已清空");
    await loadConfig();
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
setInterval(updateCountdowns, 1000);
