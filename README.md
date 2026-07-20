# LAN Clipboard / 内网中转站

一个轻量的局域网页面，用来在同一内网的不同电脑之间临时传递文本和文件。后端只使用 Python 标准库，前端是普通 HTML/CSS/JavaScript，适合部署在一台内网服务器、办公室电脑或临时中转机上。

LAN Clipboard is a lightweight local-network web tool for moving short text and temporary files between computers on the same LAN. It uses only the Python standard library on the backend and plain HTML/CSS/JavaScript on the frontend.

## 功能 / Features

- 文本临时中转：粘贴、发布、复制。
- 文件临时中转：上传、列表、下载、删除。
- 文件卡片实时显示自动删除倒计时，并区分长期保留和等待清理状态。
- 可按 `30 分钟`、`2 小时`、`8 小时` 或 `24 小时` 延长文件保存时间。
- 移动端使用“最近内容 / 发文本 / 发文件”视图切换，默认优先展示最近内容。
- 默认保留 30 分钟，并保留 `2 小时`、`8 小时`、`24 小时`、`不自动删除` 选项。
- 支持大文件上传，上传上限可配置。
- 自动存储策略：内存足够时存在服务进程内存中，内存不足时流式写入硬盘。
- 并发上传会预留内存或硬盘容量，避免多个请求重复使用同一份可用空间。
- 正在写入硬盘的文件会受到清理保护，慢速多文件上传不会被误判为孤儿文件。
- 后台定时删除过期内容和孤儿文件；硬盘可用空间耗尽或上传返回 `507` 时显示顶部告警并弹出提示框。
- 大文件下载支持 HTTP Range 和断点续传。
- 写操作带 CSRF 保护，访问码下载使用短时文件令牌。
- 页面会定时刷新磁盘状态，并在服务重启导致安全令牌变化时自动恢复写操作。
- 可选访问码，适合小范围可信内网使用。
- 无第三方 Python 依赖。

- Share text snippets across computers on the same network.
- Upload, list, download, and delete temporary files.
- File cards show a live auto-deletion countdown, including permanent-retention and pending-cleanup states.
- File retention can be extended by 30 minutes, 2 hours, 8 hours, or 24 hours.
- Mobile view switching for recent content, text sending, and file uploads, with recent content shown first.
- Default retention is 30 minutes, with options for 2 hours, 8 hours, 24 hours, or no automatic deletion.
- Configurable large-file upload support.
- Automatic storage strategy: keep files in process memory when enough memory is available, otherwise stream them to disk.
- Concurrent uploads reserve memory or disk capacity so requests cannot claim the same free space.
- Active disk writes are protected from orphan cleanup so slow multi-file uploads are not removed mid-request.
- Background cleanup removes expired items and orphan files; exhausted disk capacity or a `507` upload response triggers both a warning banner and a modal alert.
- HTTP Range support for resumable large-file downloads.
- CSRF protection for writes and short-lived per-file download tokens when an access code is enabled.
- The UI refreshes disk status periodically and automatically recovers write requests after a server restart rotates the CSRF token.
- Optional access code for small trusted LAN deployments.
- No third-party Python package is required.

## 快速启动 / Quick Start

```bash
git clone https://github.com/bd4rex/lan-clipboard.git
cd lan-clipboard
python3 server.py --host 0.0.0.0 --port 8765
```

同一内网的其他电脑访问：

Open the page from another device on the same LAN:

```text
http://SERVER_LAN_IP:8765
```

## 常用配置 / Configuration

示例 / Example:

```bash
ACCESS_CODE=your-access-code MAX_UPLOAD_MB=5120 DEFAULT_TTL_HOURS=0.5 python3 server.py --host 0.0.0.0 --port 8765
```

常用环境变量 / Common environment variables:

- `ACCESS_CODE`: 可选访问码；为空则内网直接访问。Optional access code; leave empty for open LAN access.
- `MAX_UPLOAD_MB`: 单次上传大小上限，默认 `50`。Upload size limit per request. Default: `50`.
- `MAX_TEXT_MB`: 单条文本大小上限，默认 `2`。Text size limit per item. Default: `2`.
- `DEFAULT_TTL_HOURS`: 默认保留小时数，默认 `0.5`。Default retention in hours. Default: `0.5`.
- `MAX_ITEMS`: 最多保留条数，默认 `200`。Maximum number of retained items. Default: `200`.
- `MEMORY_STORE_ENABLED`: 是否启用内存优先存储，默认 `1`。Enable memory-first file storage. Default: `1`.
- `MEMORY_RESERVE_MB`: 至少给系统预留的可用内存，默认 `1024`。Keep at least this much available memory for the system. Default: `1024`.
- `MEMORY_STORE_MAX_MB`: 允许进入内存的单次上传上限，默认 `0`，表示只按可用内存判断。Maximum upload size allowed for memory storage. Default: `0`, meaning no separate cap beyond available memory.
- `MEMORY_SAFETY_MULTIPLIER`: 内存判断安全系数，默认 `1.25`。Safety multiplier for memory decisions. Default: `1.25`.
- `DISK_RESERVE_MB`: 至少给系统预留的可用硬盘空间，默认 `1024`。Keep at least this much free disk space for the system. Default: `1024`.
- `CLEANUP_INTERVAL_SECONDS`: 后台清理间隔，默认 `60` 秒。Background cleanup interval. Default: `60` seconds.
- `ORPHAN_GRACE_SECONDS`: 孤儿文件删除前的保护时间，默认 `300` 秒。Grace period before orphan-file deletion. Default: `300` seconds.
- `DOWNLOAD_TOKEN_TTL_SECONDS`: 文件下载令牌有效期，默认 `300` 秒。Per-file download token lifetime. Default: `300` seconds.
- `CORS_ALLOWED_ORIGINS`: 可选跨站来源白名单，逗号分隔；默认不允许跨站 API。Optional comma-separated cross-origin allowlist; cross-origin API access is disabled by default.
- `HOST`: 监听地址，默认 `0.0.0.0`。Listen address. Default: `0.0.0.0`.
- `PORT`: 监听端口，默认 `8765`。Listen port. Default: `8765`.

## 数据位置 / Data

- SQLite 元数据 / SQLite metadata: `data/clipboard.sqlite`
- 硬盘文件 / Disk-backed uploads: `data/uploads/`
- 内存文件 / Memory-backed uploads: 只保存在当前运行中的服务进程里 / kept only inside the running server process

`data/` 目录已加入 `.gitignore`，不会提交到 GitHub。

The `data/` directory is intentionally ignored by git.

## 测试 / Tests

```bash
python3 -m unittest discover -s tests -v
```

## 文档 / Documentation

- [部署文档 / Deployment Guide](./DEPLOYMENT.md)
- [开发过程文档 / Development Notes](./DEVELOPMENT.md)
- [脱敏检查记录 / Sanitization Review](./SANITIZATION.md)
- [时间戳日志 / TIMESTAMP_LOG](./TIMESTAMP_LOG.md)

## 使用边界 / Intended Use

这个项目面向可信内网临时中转。如果要暴露到公网，请放在 HTTPS、认证、反向代理和合理上传限制之后使用。

This project is designed for trusted local networks. If you expose it outside a LAN, put it behind HTTPS, authentication, and a real reverse proxy with request-size limits that match your intended upload size.
