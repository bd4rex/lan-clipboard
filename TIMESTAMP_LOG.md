# TIMESTAMP_LOG / 时间戳日志

这个文件提供 git 历史之外的第二条时间线。后期如果在不同仓库、不同电脑、不同部署机器之间切换，可以用它记录“这次到底从哪里来、传到了哪里、包含了什么、不包含什么”。

This file is the `TIMESTAMP_LOG`: a second timeline beside git history. Use it when the project moves between repositories, computers, or deployment machines, especially when you need to know what was copied, what was excluded, and which version was involved.

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
  - `docs/DEPLOYMENT.md`
  - `docs/DEVELOPMENT.md`
  - `docs/SANITIZATION.md`
  - `docs/TIMESTAMP_LOG.md`
- 运行数据包含 / Runtime data included: 否 / no
- 脱敏结论 / Sanitization result:
  - 文档使用占位符表示主机、用户、路径和访问码。Documentation uses placeholders for hosts, users, paths, and access codes.
  - 真实部署信息不写入仓库。Real deployment details are intentionally omitted.
- 验证命令 / Validation planned:
  - `python3 -m py_compile server.py`
  - `node --check static/app.js`
  - `docs/SANITIZATION.md` 中的 `rg` 扫描 / `rg` scan from `docs/SANITIZATION.md`
