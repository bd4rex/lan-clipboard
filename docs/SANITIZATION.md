# 脱敏检查记录 / Sanitization Review

本文档记录发布前做过的脱敏检查。

This document records the sanitization checks used before publishing.

## 当前结论 / Current Result

截至 `2026-06-03 10:17:13 CST`，仓库中未发现需要提交清理的真实密码、令牌、私有部署 IP、服务器用户名或个人机器绝对路径。

As of `2026-06-03 10:17:13 CST`, no real password, token, private deployment IP, server username, or machine-specific path was found in the committed project files.

`.gitignore` 已排除运行数据 / `.gitignore` excludes runtime data:

```text
data/
__pycache__/
*.pyc
*.log
*.pid
.env
.DS_Store
```

## 扫描命令 / Scan Command

发布前运行 / Run before release:

```bash
rg -n --hidden \
  --glob '!data/**' \
  --glob '!__pycache__/**' \
  --glob '!.git/**' \
  --glob '!*.pyc' \
  '(password|passwd|secret|token|ACCESS_CODE=.+|172\\.(16|18)\\.|192\\.168\\.|10\\.|/Users/|/home/|gho_|ssh|scp|expect)' .
```

允许出现的命中 / Acceptable matches:

- 前端访问码输入框里的 `type="password"`。`type="password"` in the access-code input.
- `ACCESS_CODE=your-access-code` 这类占位符。Placeholders such as `ACCESS_CODE=your-access-code`.
- 文档里的扫描规则、风险说明、占位路径。Scan rules, risk descriptions, and placeholder paths in documentation.

需要清理的命中 / Matches to remove:

- 真实密码或令牌。Real passwords or tokens.
- 真实内网部署 IP。Real private deployment IP addresses.
- 真实服务器用户名。Real server usernames.
- 包含真实主机或凭据的 SSH/SCP/expect 命令。SSH/SCP/expect commands with real hosts or credentials.
- 个人电脑绝对路径。Personal-machine absolute paths.

## 人工复核记录 / Manual Review Notes

- `data/` 中可能包含 SQLite、上传文件、日志和 PID，已忽略。`data/` may contain SQLite databases, uploads, logs, and PID files; it is ignored.
- `.env` 只应保存在部署机器，已忽略。`.env` should stay on deployment machines only; it is ignored.
- 文档使用占位符，不写真实部署主机。Documentation uses placeholders instead of actual deployment hosts.
- GitHub 仓库地址属于项目坐标，可以保留。The GitHub repository URL is a project coordinate and is safe to keep.
