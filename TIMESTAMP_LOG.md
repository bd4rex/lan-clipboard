# Timestamp Log / 时间戳日志

这个文件提供 git 历史之外的第二条时间线。后期如果在不同仓库、不同电脑、不同部署机器之间切换，可以用它记录“这次到底从哪里来、传到了哪里、包含了什么、不包含什么”。

This file is `TIMESTAMP_LOG.md`: a second timeline beside git history. Use it when the project moves between repositories, computers, or deployment machines, especially when you need to know what was copied, what was excluded, and which version was involved.

## 新增记录模板 / Entry Template

每次跨仓库、跨电脑或跨部署环境操作后，追加一条：

Append a new entry after each cross-repository, cross-computer, or deployment-environment operation:

```text
### YYYY-MM-DD HH:MM:SS TZ

- 事件 / Event:
- 操作电脑/环境 / Machine or environment:
- 仓库 / Repository:
- 分支 / Branch:
- 提交 / Commit:
- 上传/同步范围 / Uploaded or synced scope:
- 未包含内容 / Excluded content:
- 脱敏结论 / Sanitization result:
- 验证命令 / Validation commands:
- 部署目标说明 / Deployment target description:
- 备注 / Notes:
```

部署目标说明只写泛化描述，不写真实 IP、用户名、密码。

Deployment target descriptions should stay generic. Do not include real IP addresses, usernames, or passwords.

## 记录 / Entries

### 2026-06-03 10:17:13 CST

- 事件 / Event: 首次发布到 GitHub。Initial GitHub publication.
- 操作电脑/环境 / Machine or environment: 本地工作站，具体路径不写入仓库。Local workstation; the exact path is not recorded in the repository.
- 仓库 / Repository: `https://github.com/bd4rex/lan-clipboard`
- 发布时可见性 / Visibility at publication: private
- 分支 / Branch: `main`
- 发布前提交 / Commit before docs expansion: `57725ab`
- 上传范围 / Uploaded scope:
  - `.gitignore`
  - `README.md`
  - `server.py`
  - `static/app.js`
  - `static/index.html`
  - `static/styles.css`
- 未包含内容 / Excluded content:
  - `data/`
  - SQLite 运行数据库 / runtime SQLite database
  - 上传文件 / uploaded files
  - 服务日志 / server logs
  - PID 文件 / PID files
  - Python 缓存 / Python cache files
  - 本地 `.env` / local `.env`
- 脱敏结论 / Sanitization result:
  - 未有意发布真实密码、令牌、私有部署 IP、内部服务器用户名或个人机器绝对路径。No real password, token, private deployment IP, internal server username, or personal-machine absolute path was intentionally published.
  - README 中的本机路径示例已改为通用 clone/run 说明。README workstation-specific examples were changed to generic clone/run instructions.
- 验证命令 / Validation:
  - `python3 -m py_compile server.py`
  - `node --check static/app.js`
- 备注 / Notes:
  - 本项目作为 `lan-clipboard` 子目录独立建仓发布。The project was published as an independent repository from the `lan-clipboard` subdirectory.
  - 父级工作区包含多个无关项目，不能作为发布范围。The parent workspace contains unrelated projects and should not be used as the publish scope.

### 2026-06-03 10:17:13 CST 文档补齐 / Documentation Pass

- 事件 / Event: 补齐介绍、部署文档、开发过程文档、脱敏记录和 `TIMESTAMP_LOG`。Added public-facing overview, deployment guide, development notes, sanitization review, and `TIMESTAMP_LOG`.
- 仓库 / Repository: `https://github.com/bd4rex/lan-clipboard`
- 分支 / Branch: `main`
- 基于提交 / Based on commit: `57725ab`
- 上传范围 / Uploaded scope:
  - `README.md`
  - `DEPLOYMENT.md`
  - `DEVELOPMENT.md`
  - `SANITIZATION.md`
  - `TIMESTAMP_LOG.md`
- 运行数据包含 / Runtime data included: 否 / no
- 脱敏结论 / Sanitization result:
  - 文档使用占位符表示主机、用户、路径和访问码。Documentation uses placeholders for hosts, users, paths, and access codes.
  - 真实部署信息不写入仓库。Real deployment details are intentionally omitted.
- 验证命令 / Validation planned:
  - `python3 -m py_compile server.py`
  - `node --check static/app.js`
  - `SANITIZATION.md` 中的 `rg` 扫描 / `rg` scan from `SANITIZATION.md`

### 2026-06-04 17:05:27 CST 磁盘扩容与容量提示 / Disk Expansion and Capacity Warning

- 事件 / Event: 将部署机器可用 LVM 空间并入根文件系统，并加入硬盘容量提示和上传前容量保护。Expanded the deployment machine root filesystem with available LVM space, then added disk-capacity warnings and pre-upload disk-capacity protection.
- 操作电脑/环境 / Machine or environment: 本地工作站 + 内网部署机器；真实地址和用户名不写入仓库。Local workstation plus LAN deployment host; real address and username are not recorded in the repository.
- 仓库 / Repository: `https://github.com/bd4rex/lan-clipboard`
- 分支 / Branch: `main`
- 基于提交 / Based on commit: `a9ee166`
- 上传/同步范围 / Uploaded or synced scope:
  - `server.py`
  - `static/app.js`
  - `static/index.html`
  - `static/styles.css`
  - `README.md`
  - `DEPLOYMENT.md`
  - `DEVELOPMENT.md`
  - `TIMESTAMP_LOG.md`
- 未包含内容 / Excluded content:
  - `data/`
  - 运行数据库、上传文件、服务日志和本地 `.env`。Runtime database, uploaded files, service logs, and local `.env`.
- 脱敏结论 / Sanitization result: 本次记录不包含真实内网 IP、用户名、密码、令牌或上传内容。This entry does not include real LAN IPs, usernames, passwords, tokens, or uploaded content.
- 验证命令 / Validation commands:
  - `python3 -m py_compile server.py`
  - `node --check static/app.js`
  - `GET /api/config`
- 部署目标说明 / Deployment target description: 内网 Python 标准库服务，监听端口由部署环境 `.env` 指定。LAN Python standard-library service; listen port is defined by the deployment `.env`.
- 备注 / Notes: `DISK_RESERVE_MB` 默认保留 1GB 系统空间；当可落盘空间不足一个单次上传上限时页面显示提示，上传无法落盘时返回 `507 Insufficient Storage`。`DISK_RESERVE_MB` keeps 1GB for the system by default; the UI warns when usable disk space is below one upload limit, and uploads that cannot fit return `507 Insufficient Storage`.

### 2026-07-10 14:45:51 CST P1/P2 审查修复 / P1 and P2 Review Fixes

- 事件 / Event: 修复代码审查发现的全部 P1/P2 问题。Fixed all P1 and P2 findings from the code review.
- 操作电脑/环境 / Machine or environment: 本地工作站 + 泛化内网部署机器；真实地址和用户名不写入仓库。Local workstation plus a generic LAN deployment host; real addresses and usernames are not recorded.
- 仓库 / Repository: `https://github.com/bd4rex/lan-clipboard`
- 分支 / Branch: `main`
- 基于提交 / Based on commit: `51f5cb9`
- 上传/同步范围 / Uploaded or synced scope:
  - `server.py`
  - `static/app.js`
  - `static/index.html`
  - `tests/test_server.py`
  - `README.md`
  - `DEPLOYMENT.md`
  - `DEVELOPMENT.md`
  - `SANITIZATION.md`
  - `TIMESTAMP_LOG.md`
- 主要修复 / Main fixes:
  - 写接口 CSRF 保护和默认关闭通配符 CORS。CSRF protection for writes and wildcard CORS disabled by default.
  - 内存/硬盘并发容量预留。Atomic in-flight memory and disk capacity reservations.
  - 周期性过期清理和孤儿文件回收。Scheduled expiry cleanup and orphan-file reclamation.
  - 短时文件下载令牌及日志查询参数脱敏。Short-lived file download tokens and query-parameter log redaction.
  - HTTP Range 断点续传。HTTP Range support for resumable downloads.
  - 页面默认保留时间与服务器配置同步。UI retention defaults synchronized with server configuration.
- 未包含内容 / Excluded content: `data/`、本地 `.env`、上传文件、数据库、日志和缓存。`data/`, local `.env`, uploads, databases, logs, and caches.
- 脱敏结论 / Sanitization result: 不包含真实内网 IP、用户名、密码、访问码或运行时令牌。No real LAN IPs, usernames, passwords, access codes, or runtime tokens are included.
- 验证命令 / Validation commands:
  - `python3 -m py_compile server.py`
  - `node --check static/app.js`
  - `python3 -m unittest discover -s tests -v`
  - 浏览器同源写入、默认保留时间和下载验证 / browser verification for same-origin writes, retention defaults, and downloads
- 部署目标说明 / Deployment target description: 现有内网用户级 systemd 服务，端口由部署环境 `.env` 指定。Existing LAN user-level systemd service; port is defined by the deployment `.env`.

### 2026-07-10 15:08:01 CST 移动端 UI 修复 / Mobile UI Fixes

- 事件 / Event: 修复 UI 检查发现的移动端内容顺序、键盘焦点和触控尺寸问题。Fixed mobile content order, keyboard focus, and touch-target issues found during the UI review.
- 操作电脑/环境 / Machine or environment: 本地工作站 + 泛化内网部署机器；真实地址和用户名不写入仓库。Local workstation plus a generic LAN deployment host; real addresses and usernames are not recorded.
- 仓库 / Repository: `https://github.com/bd4rex/lan-clipboard`
- 分支 / Branch: `main`
- 基于提交 / Based on commit: `d65bc89`
- 上传/同步范围 / Uploaded or synced scope: `static/index.html`、`static/styles.css`、`static/app.js`、`README.md`、`DEVELOPMENT.md`、`TIMESTAMP_LOG.md`。
- 主要修复 / Main fixes:
  - 移动端默认展示最近内容，并提供文本、文件发布视图切换。Mobile screens show recent content first and provide text/file publishing views.
  - 发布成功后自动返回最近内容。Successful sends return to the recent-content view.
  - 补充可见键盘焦点，并将移动端操作控件提高到至少 `44px`。Added visible keyboard focus and raised mobile controls to at least `44px`.
  - 降低移动端清空按钮的视觉强调。Reduced the visual emphasis of the mobile clear action.
- 未包含内容 / Excluded content: `data/`、本地 `.env`、上传文件、数据库、日志、截图和测试缓存。`data/`, local `.env`, uploads, databases, logs, screenshots, and test caches.
- 脱敏结论 / Sanitization result: 不包含真实内网 IP、用户名、密码、访问码或运行时数据。No real LAN IPs, usernames, passwords, access codes, or runtime data are included.
- 验证命令 / Validation commands:
  - `git diff --check`
  - `node --check static/app.js`
  - `python3 -m py_compile server.py`
  - `python3 -m unittest discover -s tests -v`
  - `1280x720`、`390x844`、`320x568` 浏览器布局和交互检查 / browser layout and interaction checks
- 部署目标说明 / Deployment target description: 现有内网用户级 systemd 服务，端口由部署环境 `.env` 指定。Existing LAN user-level systemd service; port is defined by the deployment `.env`.

### 2026-07-19 10:33:22 CST 文件自动删除倒计时 / File Auto-Deletion Countdown

- 事件 / Event: 在已上传文件卡片中增加实时自动删除倒计时。Added a live auto-deletion countdown to uploaded-file cards.
- 操作电脑/环境 / Machine or environment: 本地工作站 + 泛化内网部署机器；真实地址和用户名不写入仓库。Local workstation plus a generic LAN deployment host; real addresses and usernames are not recorded.
- 仓库 / Repository: `https://github.com/bd4rex/lan-clipboard`
- 分支 / Branch: `main`
- 基于提交 / Based on commit: `878215d`
- 上传/同步范围 / Uploaded or synced scope: `static/app.js`、`static/styles.css`、`static/index.html`、`README.md`、`DEVELOPMENT.md`、`SANITIZATION.md`、`TIMESTAMP_LOG.md`。
- 主要修复 / Main fixes:
  - 文件倒计时每秒更新，并按分钟、小时和天数自适应显示。File countdowns update every second and adapt across minute, hour, and day ranges.
  - 倒计时优先使用 API 服务器时间，并以 HTTP `Date` 响应头兼容校准，避免不同电脑的本机时钟偏差且支持无重启前端热更新。Countdowns prefer API server time and fall back to the HTTP `Date` response header, avoiding client clock drift while supporting restart-free frontend updates.
  - 不自动删除的文件显示“长期保留”。Files without automatic deletion show long-term retention.
  - 倒计时归零后显示“等待清理”，实际删除仍由后端清理任务负责。Expired countdowns show pending cleanup while actual deletion remains the backend cleanup worker's responsibility.
  - 桌面和窄屏布局均保留稳定尺寸，长文件名不会挤压倒计时。Desktop and narrow-screen layouts preserve stable sizing without long filenames squeezing the countdown.
- 未包含内容 / Excluded content: `data/`、本地 `.env`、上传文件、数据库、日志、截图和测试缓存。`data/`, local `.env`, uploads, databases, logs, screenshots, and test caches.
- 脱敏结论 / Sanitization result: 不包含真实内网 IP、用户名、密码、访问码或运行时数据。No real LAN IPs, usernames, passwords, access codes, or runtime data are included.
- 验证命令 / Validation commands:
  - `git diff --check`
  - `node --check static/app.js`
  - `python3 -m py_compile server.py`
  - `python3 -m unittest discover -s tests -v`
  - `1280x720` 和 `320x568` 浏览器布局及实时递减检查 / browser layout and live decrement checks
- 部署目标说明 / Deployment target description: 现有内网用户级 systemd 服务，端口由部署环境 `.env` 指定。Existing LAN user-level systemd service; port is defined by the deployment `.env`.

### 2026-07-19 10:51:55 CST 文件保存时间延长 / File Retention Extension

- 事件 / Event: 在文件倒计时旁增加保存时间增量选择和延长操作。Added retention-increment selection and an extend action beside file countdowns.
- 操作电脑/环境 / Machine or environment: 本地工作站 + 泛化内网部署机器；真实地址和用户名不写入仓库。Local workstation plus a generic LAN deployment host; real addresses and usernames are not recorded.
- 仓库 / Repository: `https://github.com/bd4rex/lan-clipboard`
- 分支 / Branch: `main`
- 基于提交 / Based on commit: `a14c7aa`
- 上传/同步范围 / Uploaded or synced scope: `server.py`、`static/app.js`、`static/index.html`、`static/styles.css`、`tests/test_server.py`、`README.md`、`DEVELOPMENT.md`、`SANITIZATION.md`、`TIMESTAMP_LOG.md`。
- 主要修复 / Main fixes:
  - 文件可增加 `30 分钟`、`2 小时`、`8 小时` 或 `24 小时`。Files can be extended by 30 minutes, 2 hours, 8 hours, or 24 hours.
  - 增量累加到现有到期时间，最长保留一年。Extensions are added to the existing expiry, with a one-year maximum retention horizon.
  - 长期保留文件不显示延长操作，已过期文件不能复活。Permanent files do not show extension controls, and expired files cannot be revived.
  - 延长接口使用现有访问码和 CSRF 保护。The extension endpoint uses the existing access-code and CSRF protections.
  - 桌面端保持紧凑单行，窄屏使用两行 `44px` 控件布局。Desktop keeps a compact single row, while narrow screens use a two-row layout with `44px` controls.
- 未包含内容 / Excluded content: `data/`、本地 `.env`、上传文件、数据库、日志、截图和测试缓存。`data/`, local `.env`, uploads, databases, logs, screenshots, and test caches.
- 脱敏结论 / Sanitization result: 不包含真实内网 IP、用户名、密码、访问码或运行时数据。No real LAN IPs, usernames, passwords, access codes, or runtime data are included.
- 验证命令 / Validation commands:
  - `git diff --check`
  - `node --check static/app.js`
  - `python3 -m py_compile server.py`
  - `python3 -m unittest discover -s tests -v`
  - `1280x720` 和 `320x568` 浏览器布局及真实延长操作检查 / browser layout and live extension checks
- 部署目标说明 / Deployment target description: 现有内网用户级 systemd 服务，端口由部署环境 `.env` 指定。Existing LAN user-level systemd service; port is defined by the deployment `.env`.

### 2026-07-20 14:07:31 CST 审查问题修复 / Review Finding Fixes

- 事件 / Event: 修复慢速多文件上传、延长控件自动重置、服务重启令牌恢复和跨电脑磁盘告警刷新问题。Fixed slow multi-file upload cleanup, retention-control reset, restart token recovery, and cross-device disk-warning refresh issues.
- 操作电脑/环境 / Machine or environment: 本地工作站隔离测试环境；真实地址和用户名不写入仓库。Local workstation and isolated test environment; real addresses and usernames are not recorded.
- 仓库 / Repository: `https://github.com/bd4rex/lan-clipboard`
- 分支 / Branch: `main`
- 基于提交 / Based on commit: `edebbeb`
- 当前状态 / Current status: 本地修复和验证已完成，尚未提交、推送或部署。Local fixes and validation are complete; not yet committed, pushed, or deployed.
- 上传/同步范围 / Upload or sync scope: `server.py`、`static/app.js`、`static/index.html`、`tests/test_server.py`、`README.md`、`DEVELOPMENT.md`、`DEPLOYMENT.md`、`TIMESTAMP_LOG.md`。
- 主要修复 / Main fixes:
  - 上传中的硬盘路径在整批请求完成前免受孤儿文件清理。Active disk upload paths are protected from orphan cleanup until the full request completes.
  - 最近内容未变化时不重建控件，并在必要重建时保留延长时长选择。Unchanged feeds keep their existing controls, and necessary rebuilds preserve retention-extension selections.
  - 旧 CSRF 令牌触发一次配置刷新和自动重试，普通写请求和文件上传均覆盖。A stale CSRF token triggers one configuration refresh and automatic retry for regular writes and uploads.
  - 页面每 10 秒刷新磁盘状态，且不重置用户当前表单保留时间。Disk status refreshes every ten seconds without resetting current form retention selections.
- 未包含内容 / Excluded content: `data/`、本地 `.env`、上传文件、数据库、日志、浏览器缓存和测试临时目录。`data/`, local `.env`, uploads, databases, logs, browser caches, and temporary test directories.
- 脱敏结论 / Sanitization result: 不包含真实内网 IP、用户名、密码、访问码、运行时令牌或上传内容。No real LAN IPs, usernames, passwords, access codes, runtime tokens, or uploaded content are included.
- 验证命令 / Validation commands:
  - `git diff --check`
  - `python3 -m py_compile server.py`
  - `node --check static/app.js`
  - `python3 -m unittest discover -s tests -v`，13 项通过 / 13 tests passed
  - 浏览器验证延长选择保持、旧令牌一次性恢复、10 秒磁盘状态刷新和 `390x844` 无横向溢出 / browser verification for retained extension selection, one-time stale-token recovery, ten-second disk refresh, and no horizontal overflow at `390x844`
- 部署目标说明 / Deployment target description: 本条仅记录本地修复；服务器与 GitHub 状态需在后续同步时另记。This entry records local fixes only; server and GitHub states must be recorded separately when synchronized.

### 2026-07-20 14:16:29 CST 审查修复发布 / Review Fix Release

- 事件 / Event: 将审查修复提交到 GitHub，并部署到现有内网服务。Committed the review fixes to GitHub and deployed them to the existing LAN service.
- 操作电脑/环境 / Machine or environment: 本地工作站 + 泛化内网部署机器；真实地址、用户名和凭据不写入仓库。Local workstation plus a generic LAN deployment host; real addresses, usernames, and credentials are not recorded.
- 仓库 / Repository: `https://github.com/bd4rex/lan-clipboard`
- 分支 / Branch: `main`
- 发布提交 / Released commit: `865da7b`
- GitHub 状态 / GitHub status: `main` 已推送。`main` pushed successfully.
- 服务器状态 / Server status: 代码已更新，用户级服务为 `active`，继续监听端口 `8765`。Code updated; the user-level service is `active` and continues to listen on port `8765`.
- 数据保护 / Data protection: 重启前将 2 个内存文件共 `203675042` 字节迁移到硬盘，逐个校验大小并建立 SQLite 与源代码备份；重启后 2/2 文件再次通过校验。Before restart, two memory-backed files totaling `203675042` bytes were migrated to disk, byte-checked, and protected by SQLite and source backups; 2/2 files passed post-restart verification.
- 线上配置 / Live configuration: 单次上传上限 `10737418240` 字节（10 GiB），默认保留 `1800` 秒，清理周期 `60` 秒，磁盘告警为关闭状态。Upload limit `10737418240` bytes (10 GiB), default retention `1800` seconds, cleanup interval `60` seconds, and no active disk warning.
- 验证 / Verification:
  - 远端 13 项自动化测试全部通过。All 13 remote automated tests passed.
  - 健康检查成功，Range 下载返回 `206`。Health check passed and a Range download returned `206`.
  - 本地、GitHub 发布提交和服务器的 `server.py`、`static/app.js`、`static/index.html` 哈希一致。Local, GitHub release commit, and server hashes match for `server.py`, `static/app.js`, and `static/index.html`.
  - 线上浏览器确认 `+24 小时` 选择跨自动同步保持原值且节点未被替换。The live browser confirmed that the `+24 hours` selection survives automatic sync without replacing its control node.
  - `390x844` 线上页面无横向溢出。The live page has no horizontal overflow at `390x844`.
  - 既有其他服务端口保持监听，未做配置修改。Existing unrelated service ports remain listening and were not reconfigured.
- 未包含内容 / Excluded content: 运行数据库、上传文件、备份文件、`.env`、日志、真实内网地址、用户名、密码和令牌。Runtime databases, uploads, backups, `.env`, logs, real LAN addresses, usernames, passwords, and tokens are excluded.
- 当前状态 / Current status: 功能代码和本条时间戳记录均已在 GitHub 与服务器同步。Both the feature code and this timestamp entry are synchronized to GitHub and the server.

### 2026-07-20 14:25:28 CST 硬盘满盘弹框 / Disk Capacity Modal

- 事件 / Event: 在原有硬盘告警横幅之外增加满盘模态提示框，并同步 GitHub 与内网服务。Added a disk-capacity modal alongside the existing warning banner and synchronized it to GitHub and the LAN service.
- 操作电脑/环境 / Machine or environment: 本地工作站 + 泛化内网部署机器；真实地址、用户名和凭据不写入仓库。Local workstation plus a generic LAN deployment host; real addresses, usernames, and credentials are not recorded.
- 仓库 / Repository: `https://github.com/bd4rex/lan-clipboard`
- 分支 / Branch: `main`
- 功能提交 / Feature commit: `c315a9f`
- 触发条件 / Triggers: `diskUsableBytes <= 0` 的定时状态检查，或写请求返回 `507 Insufficient Storage`。Periodic status checks with `diskUsableBytes <= 0`, or a write request returning `507 Insufficient Storage`.
- 交互行为 / Interaction: 弹框显示硬盘剩余、可用于落盘和系统预留；关闭后同一满盘状态不随每次轮询重复弹出，新的 `507` 失败仍会强制提示。The modal shows free, usable, and reserved capacity; dismissal suppresses repeated polling alerts for the same full state, while a new `507` failure still forces an alert.
- 服务器发布 / Server release: 静态文件热更新，服务进程未重启且 PID 保持不变，端口继续为 `8765`。Static assets were hot-updated without restarting the service; its PID remained unchanged and the port remains `8765`.
- 线上配置 / Live configuration: 单次上传上限 `10737418240` 字节（10 GiB），默认保留 `1800` 秒，当前磁盘告警为关闭状态。Upload limit `10737418240` bytes (10 GiB), default retention `1800` seconds, and no current disk warning.
- 验证 / Verification:
  - `git diff --check`、`node --check static/app.js`、`python3 -m py_compile server.py` 均通过。All static checks passed.
  - 13 项自动化测试全部通过。All 13 automated tests passed.
  - 浏览器验证首次满盘自动弹出、关闭后 10 秒轮询不重复、`507` 上传失败强制再次弹出。Browser verification covered the initial full-disk alert, no repeat after a ten-second poll, and forced reopening after a `507` upload failure.
  - 桌面和 `390x844` 手机布局已检查，手机页面无横向溢出。Desktop and `390x844` mobile layouts were checked with no mobile horizontal overflow.
  - 服务器静态文件哈希与本地一致，健康检查成功，既有其他服务端口保持监听。Server asset hashes match local files, health checks passed, and existing unrelated service ports remain listening.
- 数据影响 / Data impact: 未重启服务、未修改数据库或现有上传文件。The service was not restarted, and no database or existing upload was modified.
- 未包含内容 / Excluded content: 运行数据库、上传文件、备份文件、`.env`、日志、真实内网地址、用户名、密码和令牌。Runtime databases, uploads, backups, `.env`, logs, real LAN addresses, usernames, passwords, and tokens are excluded.
- 当前状态 / Current status: 功能与本条记录均纳入本次 GitHub 和服务器同步范围。Both the feature and this entry are included in the current GitHub and server synchronization scope.

### 2026-09-06 23:42:16 CST 再审查问题修复 / Follow-up Review Fixes

- 事件 / Event: 修复重新审查确认的 3 项 P1 和 2 项 P2 问题，并增加回归测试。Fixed the three P1 and two P2 findings confirmed by the follow-up review and added regression coverage.
- 操作电脑/环境 / Machine or environment: 本地工作站隔离测试环境；真实地址、用户名和凭据不写入仓库。Isolated tests on a local workstation; real addresses, usernames, and credentials are not recorded.
- 仓库 / Repository: `https://github.com/bd4rex/lan-clipboard`
- 分支 / Branch: `main`
- 基于提交 / Based on commit: `d62f719`
- 修改范围 / Changed files: `server.py`, `tests/test_server.py`, `README.md`, `DEVELOPMENT.md`, `TIMESTAMP_LOG.md`.
- 主要修复 / Main fixes:
  - multipart 解析跨分块保留字节，并验证完整分隔行，内存和硬盘上传下载保持一致。Multipart parsing preserves bytes across chunks and validates complete delimiter lines for both storage backends.
  - 清理和删除先取得 SQLite 写锁，再读取元数据，与延期操作串行化。Cleanup and deletion acquire the SQLite write lock before reading metadata, serializing them with extensions.
  - HTTP 成功和错误响应均在数据库事务结束、连接关闭后发送。Successful and error HTTP responses are sent after the database transaction ends and its connection closes.
  - 中断、超限和满盘异常清理当前残片及同批文件，并释放预留容量。Interrupted, oversized, and disk-full uploads clean the current partial file and earlier batch files and release reservations.
  - 同秒记录按插入顺序稳定排序；超过保留条数上限的批量上传整批拒绝，不淘汰已有内容。Same-second items use stable insertion ordering; batches exceeding the retention cap are rejected without evicting existing items.
- 验证 / Verification:
  - `python3 -m unittest discover -s tests -v`: 28 项测试全部通过，包含内存和硬盘路径及跨分块子用例。All 28 tests passed, including both storage backends and chunk-boundary subcases.
  - 5 组核心回归测试在基准提交上均能检出旧问题，在修复版本上通过。All five core regression groups detect their original bugs on the baseline and pass with the fixes.
  - 真实慢接收客户端复验中，另一客户端发布文本返回 `201`，不再因列表响应持锁而超时。With a real slow-reading client, another client's text submission returned `201` without timing out on the list response's database lock.
  - `python3 -m py_compile server.py tests/test_server.py`, `node --check static/app.js`, `git diff --check` 均通过。All syntax and diff checks passed.
- 数据影响 / Data impact: 无数据库结构迁移，未操作现有运行数据，也未修改部署环境中的容量和保留时间配置。No database schema migration, existing runtime-data changes, or deployed capacity/retention configuration changes.
- 未包含内容 / Excluded content: 运行数据库、上传文件、`.env`、日志、测试临时目录、真实部署地址、用户名、密码和令牌。Runtime databases, uploads, `.env`, logs, temporary test directories, real deployment addresses, usernames, passwords, and tokens are excluded.
- 当前状态 / Current status: 本地修复与验证完成，尚未提交、推送 GitHub 或部署服务器；后续发布需另记时间戳。Local fixes and validation are complete; not yet committed, pushed to GitHub, or deployed. A later release must have its own timestamp entry.

### 2026-09-07 07:23:13 CST 审查修复合并与部署 / Review Fix Merge and Deployment

- 事件 / Event: 将重新审查的 5 项问题修复合入 GitHub `main`，并部署到现有内网服务。Merged the five follow-up review fixes into GitHub `main` and deployed them to the existing LAN service.
- 操作电脑/环境 / Machine or environment: 本地工作站与泛化内网部署机器；真实地址、用户名和凭据不写入仓库。Local workstation and a generic LAN deployment host; real addresses, usernames, and credentials are not recorded.
- 仓库 / Repository: `https://github.com/bd4rex/lan-clipboard`
- 合并方式 / Merge: `codex/review-fixes-20260907` 快进合并到 `main`，未强制推送。Fast-forwarded `codex/review-fixes-20260907` into `main` without a force push.
- 功能发布提交 / Feature release commit: `085a1f691d6042743df3202f267890ed0db7b3c9`
- 基准提交 / Previous baseline: `d62f719`
- GitHub 状态 / GitHub status: 功能发布提交已推送到 `main`；本条记录作为后续文档提交同步。The feature release commit is pushed to `main`; this entry is synchronized in a follow-up documentation commit.
- 服务器状态 / Server status: 用户级 `lan-clipboard.service` 已重启并保持 `active`，继续监听端口 `8765`。The user-level `lan-clipboard.service` was restarted and is `active`, still listening on port `8765`.
- 数据保护 / Data protection: 切换前备份旧代码、部署配置和 SQLite；数据库及备份完整性检查通过。重启前确认无内存文件和在途上传，未迁移数据库结构或修改已有上传目录。Previous code, deployment configuration, and SQLite were backed up, and integrity checks passed. No memory files or in-flight uploads were present before restart; no schema migration or existing-upload directory replacement was performed.
- 配置保持 / Preserved configuration: 单次上传上限 `10737418240` 字节（10 GiB），默认保留 `1800` 秒，系统磁盘预留 `1073741824` 字节；部署配置文件未修改。Upload limit `10737418240` bytes (10 GiB), default retention `1800` seconds, and disk reserve `1073741824` bytes; the deployment configuration file was unchanged.
- 验证 / Verification:
  - 本地 28 项测试通过；服务器 Python `3.12.3` 在暂存目录和实际安装目录运行的 28 项测试均通过。All 28 local tests passed; all 28 tests also passed under server Python `3.12.3` in both staging and the installed directory.
  - 11 个发布文件的 SHA-256 与功能提交一致；本条文档同步后再次按最终 `main` 校验。SHA-256 values for all 11 release files match the feature commit; the final `main` is checked again after synchronizing this entry.
  - 线上文本发布和文件上传返回 `201`；1 MiB 文件下载大小为 `1048576` 字节，SHA-256 与原始内容一致。Live text creation and file upload returned `201`; a 1 MiB download was exactly `1048576` bytes with the original SHA-256.
  - Range 下载返回 `206`，延期成功增加 `1800` 秒；两条测试内容均已单独删除。A Range download returned `206`, extension added `1800` seconds, and both synthetic test items were individually deleted.
  - 健康检查和 SQLite 完整性检查通过，容量预留归零。Health and SQLite integrity checks passed, with upload reservations back at zero.
- 未包含内容 / Excluded content: 运行数据、部署配置、备份、日志、测试文件、临时发布工具、真实部署地址、用户名、密码和令牌。Runtime data, deployment configuration, backups, logs, test files, temporary release tools, real deployment addresses, usernames, passwords, and tokens are excluded.
- 当前状态 / Current status: 功能代码已在 GitHub 与服务器发布，本条记录随最终文档提交同步；记录自身不回填自己的提交号。Feature code is published to GitHub and the server; this entry is synchronized with the final documentation commit and does not embed its own commit ID.
