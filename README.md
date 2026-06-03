# 内网中转站

一个轻量的局域网页面，用来在不同电脑之间临时传递文本和文件。后端只用 Python 标准库。文件上传会自动判断可用内存：内存充足时临时保存在内存中，内存不足时边接收边写入 `data/uploads/`。

## 启动

```bash
cd lan-clipboard
python3 server.py --host 0.0.0.0 --port 8765
```

启动后，其他内网电脑访问：

```text
http://这台电脑的内网IP:8765
```

## 可选配置

```bash
ACCESS_CODE=your-access-code MAX_UPLOAD_MB=5120 DEFAULT_TTL_HOURS=0.5 python3 server.py --host 0.0.0.0 --port 8765
```

常用环境变量：

- `ACCESS_CODE`: 访问码；不设置则内网直接可用。
- `MAX_UPLOAD_MB`: 单次上传大小上限，默认 `50`。例如 `5120` 表示约 5GB。
- `MAX_TEXT_MB`: 单条文本大小上限，默认 `2`。
- `DEFAULT_TTL_HOURS`: 默认保留小时数，默认 `0.5`，也就是 30 分钟。
- `MAX_ITEMS`: 最多保留条数，默认 `200`。
- `MEMORY_STORE_ENABLED`: 是否启用内存优先存储，默认 `1`。
- `MEMORY_RESERVE_MB`: 至少保留给系统的可用内存，默认 `1024`。
- `MEMORY_STORE_MAX_MB`: 允许进入内存的单次上传上限，默认 `0` 表示不单独限制，由可用内存决定。
- `MEMORY_SAFETY_MULTIPLIER`: 内存判断安全系数，默认 `1.25`。
- `PORT`: 端口，默认 `8765`。
- `HOST`: 监听地址，默认 `0.0.0.0`。

## 数据位置

- 文本和索引：`data/clipboard.sqlite`
- 上传文件：内存充足时在服务进程内存中；否则在 `data/uploads/`

删除 `data/` 会清空全部历史内容。

内存中的文件重启后会自动失效；适合临时中转。需要重启后仍可下载的大文件，会在内存不足时自动落到硬盘。

## 内网访问注意

如果其他电脑打不开，优先检查这台机器的防火墙是否允许 Python/端口 `8765` 被局域网访问。
