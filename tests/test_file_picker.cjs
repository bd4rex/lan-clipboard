const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const { File } = require("node:buffer");
const { test } = require("node:test");
const vm = require("node:vm");

const source = readFileSync(join(__dirname, "../static/app.js"), "utf8");

class Element {
  constructor() {
    this.listeners = new Map();
    this.dataset = {};
    this.files = [];
    this.attributes = {};
    this.textContent = "";
    this.disabled = false;
    this.classList = { add() {}, remove() {}, toggle() {} };
  }
  set value(value) {
    this._value = value;
    if (value === "") this.files = [];
  }
  get value() { return this._value || ""; }
  click() { this.clickCount = (this.clickCount || 0) + 1; }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener(name, callback) {
    const listeners = this.listeners.get(name) || [];
    listeners.push(callback);
    this.listeners.set(name, listeners);
  }
  async emit(name, event = {}) {
    for (const listener of this.listeners.get(name) || []) {
      await listener({ preventDefault() {}, ...event });
    }
  }
}

function setup({ legacyFilters = false } = {}) {
  const elements = new Map();
  const get = (selector) => {
    if (!legacyFilters && ["#documentInput", "#chooseFileBtn", "#fileType"].includes(selector)) return null;
    if (!elements.has(selector)) elements.set(selector, new Element());
    return elements.get(selector);
  };
  const uploads = [];
  class XHR extends Element {
    constructor() {
      super();
      this.upload = new Element();
      this.headers = {};
    }
    open(method, path) { this.method = method; this.path = path; }
    setRequestHeader(name, value) { this.headers[name] = value; }
    getResponseHeader() { return "application/json"; }
    send(form) { this.form = form; uploads.push(this); }
    async finish(status = 201, body = {}) {
      this.status = status;
      this.responseText = JSON.stringify(body);
      await this.emit("load");
    }
  }
  const context = vm.createContext({
    document: { querySelector: get, querySelectorAll: () => [] },
    localStorage: { getItem: () => "", setItem() {} },
    window: { matchMedia: () => ({ matches: false }) },
    Headers, FormData, TextEncoder,
    XMLHttpRequest: XHR,
    // Leave the startup config request pending; each test controls config and uploads.
    fetch: () => new Promise(() => {}),
    setTimeout() {}, clearTimeout() {}, setInterval() {},
  });
  vm.runInContext(source, context);
  vm.runInContext(`
    loadConfig = async () => {};
    refreshItems = async () => {};
    state.config = { maxUploadBytes: 1024, csrfToken: "test-csrf" };
  `, context);
  get("#fileTtl").value = "1800";
  return {
    get, uploads,
    async choose(id, files) {
      const input = get(id);
      input.files = files;
      await input.emit("change");
    },
    selected: () => Array.from(vm.runInContext("state.selectedFiles", context)),
    submit: () => get("#uploadForm").emit("submit"),
  };
}

test("unrestricted picker replaces selection and accepts unknown and extensionless types", async () => {
  const app = setup();
  const doc = new File(["document"], "report.docx");
  await app.choose("#fileInput", [doc]);
  assert.deepEqual(app.selected(), [doc]);
  const files = [new File(["a"], "custom.xyz"), new File(["b"], "README")];
  await app.choose("#fileInput", files);
  assert.deepEqual(app.selected(), files);
  assert.match(app.get("#selectedFiles").textContent, /custom.xyz.*README/);
});

test("previous HTML keeps its optional choose button functional during a static update", async () => {
  const app = setup({ legacyFilters: true });
  await app.get("#chooseFileBtn").emit("click");
  assert.equal(app.get("#fileInput").clickCount, 1);
  assert.equal(app.get("#documentInput").clickCount, undefined);
  app.get("#fileType").value = "documents";
  await app.get("#chooseFileBtn").emit("click");
  assert.equal(app.get("#documentInput").clickCount, 1);
  app.get("#fileType").value = "all";
  await app.get("#chooseFileBtn").emit("click");
  assert.equal(app.get("#fileInput").clickCount, 2);
});

test("previous HTML can change its optional filter without clearing the pending batch", async () => {
  const app = setup({ legacyFilters: true });
  const file = new File(["binary"], "custom.xyz");
  await app.choose("#fileInput", [file]);
  app.get("#fileType").value = "documents";
  await app.get("#fileType").emit("change");
  await app.choose("#documentInput", []);
  assert.deepEqual(app.selected(), [file]);
});

test("canceling keeps the previous selection and same-file reselection works", async () => {
  const app = setup();
  const file = new File(["pdf"], "report.pdf", { type: "application/pdf" });
  await app.choose("#fileInput", [file]);
  assert.equal(app.get("#fileInput").value, "");
  assert.equal(app.get("#fileInput").files.length, 0);
  await app.choose("#fileInput", []);
  assert.deepEqual(app.selected(), [file]);
  await app.choose("#fileInput", [file]);
  assert.deepEqual(app.selected(), [file]);
});

test("drop accepts any type, replaces the selection, and ignores an empty drop", async () => {
  const app = setup();
  const file = new File(["binary"], "custom.bin");
  await app.get("#dropZone").emit("drop", { dataTransfer: { files: [file] } });
  await app.get("#dropZone").emit("drop", { dataTransfer: { files: [] } });
  assert.deepEqual(app.selected(), [file]);
});

test("upload preserves file bytes, names, TTL and CSRF; locks selection until success", async () => {
  const app = setup();
  const files = [new File(["doc bytes"], "report.pdf"), new File(["zip bytes"], "archive.zip")];
  await app.choose("#fileInput", files);
  const pending = app.submit();
  const upload = app.uploads[0];
  assert.equal(upload.method, "POST");
  assert.equal(upload.path, "/api/upload");
  assert.equal(upload.headers["X-CSRF-Token"], "test-csrf");
  assert.equal(upload.form.get("expiresInSeconds"), "1800");
  assert.deepEqual(upload.form.getAll("file").map((file) => file.name), ["report.pdf", "archive.zip"]);
  assert.equal(await upload.form.get("file").text(), "doc bytes");
  for (const id of ["#fileInput", "#fileTtl"]) assert.equal(app.get(id).disabled, true);
  assert.equal(app.get("#uploadForm").attributes["aria-busy"], "true");
  await app.choose("#fileInput", [new File(["new"], "new.txt")]);
  await app.get("#dropZone").emit("drop", { dataTransfer: { files: [] } });
  await app.submit();
  assert.equal(app.uploads.length, 1);
  assert.deepEqual(app.selected(), files);
  await upload.finish();
  await pending;
  assert.deepEqual(app.selected(), []);
  assert.equal(app.get("#selectedFiles").textContent, "未选择文件");
  for (const id of ["#fileInput", "#fileTtl"]) assert.equal(app.get(id).disabled, false);
  assert.equal(app.get("#uploadForm").attributes["aria-busy"], "false");
});

test("failed upload restores selected names and permits retry without reselection", async () => {
  const app = setup();
  const file = new File(["content"], "retry.txt");
  await app.choose("#fileInput", [file]);
  const pending = app.submit();
  await app.uploads[0].upload.emit("progress", { lengthComputable: true, loaded: 1, total: 2 });
  assert.match(app.get("#selectedFiles").textContent, /50%/);
  await app.uploads[0].emit("error");
  await pending;
  assert.deepEqual(app.selected(), [file]);
  assert.match(app.get("#selectedFiles").textContent, /retry.txt/);
  assert.equal(app.get("#fileInput").disabled, false);
  const retry = app.submit();
  await app.uploads[1].finish();
  await retry;
  assert.deepEqual(app.selected(), []);
});

test("an empty selection is not uploaded", async () => {
  const app = setup();
  await app.submit();
  assert.equal(app.uploads.length, 0);
});

test("per-file and aggregate limits apply to current and previous HTML", async () => {
  for (const [id, legacyFilters] of [["#fileInput", false], ["#documentInput", true]]) {
    const app = setup({ legacyFilters });
    await app.choose(id, [new File([new Uint8Array(1025)], "large.pdf")]);
    await app.submit();
    assert.equal(app.uploads.length, 0);
    await app.choose(id, [new File([new Uint8Array(600)], "a.pdf"), new File([new Uint8Array(600)], "b.pdf")]);
    await app.submit();
    assert.equal(app.uploads.length, 0);
    assert.equal(app.selected().length, 2);
  }
});

test("previous HTML still uploads from its document input during a static update", async () => {
  const app = setup({ legacyFilters: true });
  await app.choose("#documentInput", [new File(["content"], "legacy.txt")]);
  const pending = app.submit();
  await app.uploads[0].finish();
  await pending;
  assert.equal(app.uploads.length, 1);
});
