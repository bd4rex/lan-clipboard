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

清空全部运行数据 / Clear all runtime data:

```bash
systemctl --user stop lan-clipboard.service
rm -rf data/
systemctl --user start lan-clipboard.service
```
