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
