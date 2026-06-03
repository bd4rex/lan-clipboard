# 开发过程文档 / Development Notes

## 项目结构 / Project Shape

```text
server.py             Python 标准库 HTTP 服务和 API / Python standard-library HTTP server and API
static/index.html     页面结构 / UI shell
static/app.js         前端交互 / frontend behavior
static/styles.css     页面样式 / UI styling
docs/                 项目文档 / project documentation
data/                 运行数据，已忽略 / runtime data, ignored by git
```

## 设计目标 / Design Goals

这个工具最初目标是解决同一内网不同电脑之间的临时文本和文件中转问题。

This tool was built to move temporary text and files between computers on the same LAN.

- 部署简单，尽量不引入依赖。Simple deployment with minimal dependencies.
- 在可信内网内快速可用。Fast to use in a trusted LAN.
- 支持大文件，但不把大文件默认读进内存。Support large files without loading disk-backed uploads fully into memory.
- 页面直接进入使用界面，不做营销页。Open directly into the usable app rather than a landing page.
- 运行数据和代码分离，方便发布到 GitHub。Keep runtime data separate from code for safe publishing.

## 后端接口 / API

服务提供 / The server exposes:

- `GET /`: 页面 / UI.
- `GET /api/config`: 前端配置、大小限制、默认保留时间 / frontend limits and defaults.
- `GET /api/items`: 当前内容列表 / current item list.
- `POST /api/text`: 新增文本 / create a text snippet.
- `POST /api/upload`: 上传文件 / upload files.
- `GET /download/<id>`: 下载文件 / download a file.
- `DELETE /api/items/<id>`: 删除单条内容 / delete one item.
- `POST /api/clear`: 清空全部内容 / clear all items.
- `GET /health`: 健康检查 / health check.

## 存储模型 / Storage Model

SQLite 只保存元数据。文件内容有两种后端：

SQLite stores metadata only. File content has two storage backends:

- `memory`: 文件保存在当前服务进程内存里，重启后失效。Files live in the running process and disappear on restart.
- `disk`: 文件流式写入 `data/uploads/`。Files are streamed to `data/uploads/`.

服务启动时会清理数据库里旧的 `memory` 文件记录，避免出现“列表里有但下载不到”的假记录。

On startup, stale `memory` file records are removed from SQLite so the list does not show files that no longer exist.

## 内存/硬盘自动策略 / Memory-or-Disk Strategy

上传时按以下条件判断是否进入内存：

Uploads use memory when all of these are true:

- `MEMORY_STORE_ENABLED` 已启用。`MEMORY_STORE_ENABLED` is enabled.
- 请求大小没有超过 `MAX_UPLOAD_MB`。The request is within `MAX_UPLOAD_MB`.
- `MEMORY_STORE_MAX_MB` 未设置，或请求大小没有超过该值。`MEMORY_STORE_MAX_MB` is unset or large enough.
- 当前可用内存扣除已有内存文件后，仍能保留 `MEMORY_RESERVE_MB`。Available memory minus current memory-backed files can still preserve `MEMORY_RESERVE_MB`.
- 剩余可用内存大于请求大小乘以 `MEMORY_SAFETY_MULTIPLIER`。Remaining available memory is larger than request size times `MEMORY_SAFETY_MULTIPLIER`.

不满足时自动走硬盘流式写入。

Otherwise, uploads are streamed to disk.

## 大文件上传 / Large Uploads

`POST /api/upload` 使用自定义 multipart 读取流程：

`POST /api/upload` uses a custom multipart reader:

- 请求体按行读取。The request body is read incrementally.
- 硬盘路径边收边写，不把完整文件放入内存。Disk-backed uploads are written while being received.
- 内存路径只在存储策略允许时使用。Memory-backed uploads are used only when the storage strategy allows it.
- 文件大小超过限制会中止并清理已写入的临时文件。Oversized uploads are rejected and partial files are cleaned up.

## 前端行为 / Frontend Behavior

- 文本和文件表单各自有保留时间选择。Text and file forms each have a retention selector.
- 默认选中 `30 分钟`。Default selection is `30 分钟`.
- 上传使用 `XMLHttpRequest`，用于显示进度。Uploads use `XMLHttpRequest` for progress reporting.
- 下载使用原生 `<a download>` 触发，避免大文件先被 `fetch` 读进浏览器内存。Downloads use native `<a download>` behavior to avoid preloading large files into browser memory.
- 文件卡片会显示存储后端：`内存` 或 `硬盘`。File cards show `内存` or `硬盘` for the storage backend.

## 本地检查 / Local Checks

提交前运行 / Run before committing:

```bash
python3 -m py_compile server.py
node --check static/app.js
```

可选冒烟测试 / Optional smoke test:

```bash
python3 server.py --host 127.0.0.1 --port 8765
curl -fsS http://127.0.0.1:8765/health
```

## 提交前规则 / Sensitive Data Rules

不要提交 / Do not commit:

- `.env`
- `data/`
- 上传文件 / uploaded files
- 日志 / logs
- 本地或内网 IP / local or private deployment IPs
- 用户名、密码、令牌 / usernames, passwords, tokens
- 带真实主机和凭据的 SSH/SCP/expect 命令 / SSH/SCP/expect commands with real hosts or credentials
- 个人电脑绝对路径 / personal-machine absolute paths

文档里用 `SERVER_LAN_IP`、`USERNAME`、`/path/to/lan-clipboard` 这类占位符。

Use placeholders such as `SERVER_LAN_IP`, `USERNAME`, and `/path/to/lan-clipboard` in docs.

## 发布流程 / Release Workflow

1. 运行本地检查。Run local checks.
2. 按 `docs/SANITIZATION.md` 复扫脱敏。Run the sanitization scan from `docs/SANITIZATION.md`.
3. 更新 `docs/RELEASE_TRACKING.md`。Update `docs/RELEASE_TRACKING.md`.
4. 只暂存本项目文件。Stage only intended project files.
5. 提交并推送到 GitHub。Commit and push to GitHub.
