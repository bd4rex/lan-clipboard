# 开发过程文档 / Development Notes

## 项目结构 / Project Shape

```text
server.py             Python 标准库 HTTP 服务和 API / Python standard-library HTTP server and API
static/index.html     页面结构 / UI shell
static/app.js         前端交互 / frontend behavior
static/styles.css     页面样式 / UI styling
tests/test_server.py  后端回归测试 / backend regression tests
DEPLOYMENT.md         部署文档 / deployment guide
DEVELOPMENT.md        开发过程文档 / development notes
SANITIZATION.md       脱敏检查记录 / sanitization review
TIMESTAMP_LOG.md      时间戳日志 / timestamp log
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
- `GET /api/config`: 前端配置、大小限制、默认保留时间、内存和硬盘容量状态 / frontend limits, defaults, memory state, and disk-capacity state.
- `GET /api/items`: 当前内容列表和服务器时间，用于统一倒计时基准 / current item list and server time for a shared countdown clock.
- `POST /api/text`: 新增文本 / create a text snippet.
- `POST /api/upload`: 上传文件 / upload files.
- `POST /api/items/<id>/extend`: 按固定增量延长文件保存时间 / extend file retention by an allowed increment.
- `GET /download/<id>`: 下载文件 / download a file.
- `DELETE /api/items/<id>`: 删除单条内容 / delete one item.
- `POST /api/clear`: 清空全部内容 / clear all items.
- `GET /health`: 健康检查 / health check.

所有写接口要求 `X-CSRF-Token`，令牌由同源页面通过 `/api/config` 获取。默认不开放跨站 API。

All write endpoints require `X-CSRF-Token`, obtained by the same-origin UI from `/api/config`. Cross-origin API access is disabled by default.

## 存储模型 / Storage Model

SQLite 只保存元数据。文件内容有两种后端：

SQLite stores metadata only. File content has two storage backends:

- `memory`: 文件保存在当前服务进程内存里，重启后失效。Files live in the running process and disappear on restart.
- `disk`: 文件流式写入 `data/uploads/`。Files are streamed to `data/uploads/`.

服务启动时会清理数据库里旧的 `memory` 文件记录，避免出现“列表里有但下载不到”的假记录。

On startup, stale `memory` file records are removed from SQLite so the list does not show files that no longer exist.

后台清理线程按 `CLEANUP_INTERVAL_SECONDS` 周期删除过期记录和文件，并回收超过保护时间的孤儿文件。

A background cleanup thread removes expired records and files on the `CLEANUP_INTERVAL_SECONDS` schedule and reclaims orphan files after their grace period.

## 内存/硬盘自动策略 / Memory-or-Disk Strategy

上传时按以下条件判断是否进入内存：

Uploads use memory when all of these are true:

- `MEMORY_STORE_ENABLED` 已启用。`MEMORY_STORE_ENABLED` is enabled.
- 请求大小没有超过 `MAX_UPLOAD_MB`。The request is within `MAX_UPLOAD_MB`.
- `MEMORY_STORE_MAX_MB` 未设置，或请求大小没有超过该值。`MEMORY_STORE_MAX_MB` is unset or large enough.
- 当前可用内存扣除已有内存文件后，仍能保留 `MEMORY_RESERVE_MB`。Available memory minus current memory-backed files can still preserve `MEMORY_RESERVE_MB`.
- 剩余可用内存大于请求大小乘以 `MEMORY_SAFETY_MULTIPLIER`。Remaining available memory is larger than request size times `MEMORY_SAFETY_MULTIPLIER`.
- 当前没有其他上传预留掉同一份容量。No in-flight upload has already reserved the same capacity.

不满足时自动走硬盘流式写入。

Otherwise, uploads are streamed to disk.

## 硬盘容量保护 / Disk Capacity Protection

硬盘落盘前会检查 `data/` 所在文件系统：

Before disk-backed writes, the server checks the filesystem that contains `data/`:

- `diskFreeBytes`: 文件系统实际剩余空间。Actual free filesystem space.
- `diskReserveBytes`: 按 `DISK_RESERVE_MB` 保留给系统的空间。Space reserved for the system through `DISK_RESERVE_MB`.
- `diskUsableBytes`: `diskFreeBytes - diskReserveBytes`，小于 0 时按 0 处理。`diskFreeBytes - diskReserveBytes`, floored at 0.
- `diskReservedBytes`: 正在上传但尚未完成的落盘预留。Disk capacity reserved by in-flight uploads.
- `diskWarning`: 当 `diskUsableBytes` 低于 `MAX_UPLOAD_MB` 时为 `true`，前端显示提示。`true` when `diskUsableBytes` is below `MAX_UPLOAD_MB`, which makes the UI show a warning.

如果本次上传无法放入可用落盘空间，后端返回 `507 Insufficient Storage`，前端用 toast 展示错误。

If an upload cannot fit into usable disk space, the backend returns `507 Insufficient Storage` and the frontend displays the error in a toast.

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
- 下载支持单区间 HTTP Range，返回 `206 Partial Content`，可用于断点续传。Downloads support single HTTP byte ranges with `206 Partial Content` for resume support.
- 启用访问码时，列表返回短时文件令牌；访问码不会进入下载 URL。When an access code is enabled, item listings return short-lived file tokens and the access code is not placed in download URLs.
- 页面会根据 `/api/config.defaultTtlSeconds` 选中真实默认保留时间；自定义值会动态加入下拉框。The UI selects the real default retention from `/api/config.defaultTtlSeconds`, adding a custom option when needed.
- 文件卡片会显示存储后端：`内存` 或 `硬盘`。File cards show `内存` or `硬盘` for the storage backend.
- 有到期时间的文件卡片优先以 `/api/items.serverTime` 为时间基准，并兼容使用 HTTP `Date` 响应头校准，每秒更新自动删除倒计时；不自动删除时显示长期保留，归零后显示等待清理。File cards prefer `/api/items.serverTime` as their clock source, fall back to the HTTP `Date` response header for calibration, and update the auto-deletion countdown every second; permanent files show long-term retention, and expired files show pending cleanup.
- 有到期时间的文件可以在卡片中选择固定增量并延长；增量累加到原到期时间，最长保留一年。Expiring files can be extended from their cards using fixed increments; the increment is added to the existing expiry, with a one-year maximum retention horizon.
- 窄屏使用“最近内容 / 发文本 / 发文件”分段切换，发送成功后自动回到最近内容。Narrow screens use a segmented switch for recent content, text, and files, returning to recent content after a successful send.
- 键盘焦点始终可见，移动端操作控件的最小触控高度为 `44px`。Keyboard focus remains visible, and mobile controls use a minimum `44px` touch height.

## 本地检查 / Local Checks

提交前运行 / Run before committing:

```bash
python3 -m py_compile server.py
node --check static/app.js
python3 -m unittest discover -s tests -v
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
2. 按 `SANITIZATION.md` 复扫脱敏。Run the sanitization scan from `SANITIZATION.md`.
3. 更新 `TIMESTAMP_LOG.md`。Update `TIMESTAMP_LOG.md`.
4. 只暂存本项目文件。Stage only intended project files.
5. 提交并推送到 GitHub。Commit and push to GitHub.
