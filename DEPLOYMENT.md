# 部署文档 / Deployment Guide

本文档只记录通用部署方式。不要把真实服务器 IP、用户名、密码、内网路径或 SSH 命令写进仓库。

This guide describes generic deployment only. Do not commit real server IP addresses, usernames, passwords, private paths, or SSH commands to the repository.

## 环境要求 / Requirements

- Python 3.10 或更新版本 / Python 3.10 or newer
- 一台同内网可访问的机器 / A LAN-accessible machine
- 足够的硬盘空间，用于保存硬盘落盘文件 / Enough disk space for disk-backed uploads
- 防火墙允许访问所选端口 / Firewall access to the selected port

项目不需要第三方 Python 包。

No third-party Python package is required.

## 直接运行 / Basic Run

```bash
git clone https://github.com/bd4rex/lan-clipboard.git
cd lan-clipboard
python3 server.py --host 0.0.0.0 --port 8765
```

内网其他电脑访问 / LAN clients can open:

```text
http://SERVER_LAN_IP:8765
```

## 推荐 `.env` / Recommended `.env`

在部署机器上创建本地 `.env` 文件。`.env` 已加入 `.gitignore`，不要提交。

Create a local `.env` file on the server. `.env` is ignored by git and should not be committed.

```bash
HOST=0.0.0.0
PORT=8765
ACCESS_CODE=
MAX_UPLOAD_MB=5120
MAX_TEXT_MB=2
DEFAULT_TTL_HOURS=0.5
MAX_ITEMS=200
MEMORY_STORE_ENABLED=1
MEMORY_RESERVE_MB=1024
MEMORY_STORE_MAX_MB=0
MEMORY_SAFETY_MULTIPLIER=1.25
DISK_RESERVE_MB=1024
CLEANUP_INTERVAL_SECONDS=60
ORPHAN_GRACE_SECONDS=300
DOWNLOAD_TOKEN_TTL_SECONDS=300
CORS_ALLOWED_ORIGINS=
```

启动 / Start:

```bash
set -a
source .env
set +a
python3 server.py --host "$HOST" --port "$PORT"
```

## 用户级 systemd 服务 / systemd User Service

创建 `~/.config/systemd/user/lan-clipboard.service`：

Create `~/.config/systemd/user/lan-clipboard.service`:

```ini
[Unit]
Description=LAN Clipboard Web
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/lan-clipboard
EnvironmentFile=/path/to/lan-clipboard/.env
ExecStart=/usr/bin/python3 -u /path/to/lan-clipboard/server.py --host ${HOST} --port ${PORT}
Restart=always
RestartSec=3
StandardOutput=append:/path/to/lan-clipboard/data/server.log
StandardError=append:/path/to/lan-clipboard/data/server.log

[Install]
WantedBy=default.target
```

启用并启动 / Enable and start:

```bash
systemctl --user daemon-reload
systemctl --user enable --now lan-clipboard.service
systemctl --user status lan-clipboard.service
```

如果用户退出登录后服务也退出，需要由管理员开启 linger。

If the service exits after the user logs out, enable linger from an administrator account:

```bash
sudo loginctl enable-linger USERNAME
```

## 反向代理注意事项 / Reverse Proxy Notes

如果前面加 Nginx、Caddy、Apache 或其他反向代理，代理层的上传限制必须大于或等于 `MAX_UPLOAD_MB`。例如应用允许 5GB，但代理只允许 100MB，上传仍然会失败。

If you put the app behind Nginx, Caddy, Apache, or another reverse proxy, make sure the proxy upload limit is at least as large as `MAX_UPLOAD_MB`. A 5GB app limit will still fail if the reverse proxy only accepts 100MB.

## 硬盘空间提示 / Disk Space Warnings

应用会读取 `data/` 所在文件系统的容量，并在 `/api/config` 返回总量、剩余空间、系统预留空间和可用于落盘的空间。

The app checks the filesystem that contains `data/` and returns total, free, reserved, and usable disk capacity from `/api/config`.

- `DISK_RESERVE_MB` 默认 `1024`，表示至少给系统留出 1GB。`DISK_RESERVE_MB` defaults to `1024`, keeping at least 1GB free for the operating system.
- 如果可用于落盘的空间低于 `MAX_UPLOAD_MB`，页面顶部会显示提示。If usable disk space is below `MAX_UPLOAD_MB`, the UI shows a warning banner.
- 如果本次上传预计超过可用于落盘的空间，服务端会拒绝上传并返回 `507 Insufficient Storage`。If an upload would exceed usable disk space, the server rejects it with `507 Insufficient Storage`.
- 当 `diskUsableBytes <= 0` 或上传返回 `507` 时，页面会弹出硬盘空间提示框；关闭后不会随每次轮询重复弹出。When `diskUsableBytes <= 0` or an upload returns `507`, the page opens a disk-capacity modal; dismissal prevents it from reopening on every poll.
- 正在进行的上传会先预留容量；多个并发请求不能重复使用同一份可用空间。In-flight uploads reserve capacity so concurrent requests cannot claim the same free space.
- 页面每 10 秒刷新一次磁盘状态，因此其他电脑上传导致的空间变化也会自动反映在已打开页面中。The UI refreshes disk status every ten seconds, so space changes caused by uploads from other computers appear on already-open pages.
- 正在写入但尚未提交数据库的硬盘文件不会被孤儿清理任务删除。Disk files that are still being written and not yet committed to SQLite are excluded from orphan cleanup.

## 写接口与下载安全 / Write and Download Security

- 页面先从 `GET /api/config` 获取 CSRF 令牌，所有 `POST` 和 `DELETE` 请求必须携带 `X-CSRF-Token`。The UI obtains a CSRF token from `GET /api/config`; every `POST` and `DELETE` request must send `X-CSRF-Token`.
- 默认不返回通配符 CORS。确实需要跨站 API 时，用 `CORS_ALLOWED_ORIGINS` 配置完整来源，例如 `http://intranet.example:8080`。Wildcard CORS is disabled. Configure exact origins through `CORS_ALLOWED_ORIGINS` only when cross-origin API access is required.
- 启用 `ACCESS_CODE` 后，文件列表返回短时、文件级下载令牌，不会把访问码放进下载 URL。With `ACCESS_CODE` enabled, item listings return short-lived per-file download tokens instead of placing the access code in download URLs.
- 请求日志会脱敏 `code`、`token` 和 `expires` 查询参数。Request logs redact `code`, `token`, and `expires` query parameters.
- 服务重启后，已打开页面如使用了旧 CSRF 令牌，会自动获取新令牌并重试一次写请求。After a service restart, an open page that sends a stale CSRF token automatically fetches the new token and retries the write once.

脚本或其他 API 客户端执行写操作时，应先请求 `/api/config`，再把返回的 `csrfToken` 放入 `X-CSRF-Token` 请求头。

Scripts and API clients should fetch `/api/config` first and send its `csrfToken` value in the `X-CSRF-Token` header for write requests.

## 常用运维命令 / Operations

查看状态 / Check status:

```bash
systemctl --user status lan-clipboard.service
```

重启 / Restart:

```bash
systemctl --user restart lan-clipboard.service
```

停止 / Stop:

```bash
systemctl --user stop lan-clipboard.service
```

查看日志 / Follow logs:

```bash
tail -f data/server.log
```

## 数据备份与清理 / Backup and Cleanup

运行数据位于 `data/`。

Runtime state is in `data/`.

- `data/clipboard.sqlite`: 文本和文件索引 / text and file metadata
- `data/uploads/`: 硬盘落盘文件 / disk-backed uploaded files
- 内存文件：只存在当前服务进程中，服务重启后失效 / memory-backed uploads exist only inside the current server process and disappear on restart

服务每隔 `CLEANUP_INTERVAL_SECONDS` 主动删除过期内容，并清理超过 `ORPHAN_GRACE_SECONDS` 且没有数据库记录的孤儿文件。启动时也会执行一次清理；当前进程正在写入的上传路径会被排除。

The service actively removes expired items every `CLEANUP_INTERVAL_SECONDS` and deletes unreferenced files older than `ORPHAN_GRACE_SECONDS`. Cleanup also runs once at startup and excludes upload paths currently being written by the process.

清空全部运行数据 / Clear all runtime data:

```bash
systemctl --user stop lan-clipboard.service
rm -rf data/
systemctl --user start lan-clipboard.service
```
