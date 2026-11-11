# D8 报告：Docker + GitHub Actions + 环境变量部署

## 结论

D8 的部署骨架已完成：

- `Dockerfile`：Python 3.12 + FastAPI/uvicorn，非 root 用户，`/health` 健康检查
- `docker-compose.yml`：本地一键起 API，从环境变量读 Key/模型/CORS/限流
- `.github/workflows/ci.yml`：测试 + 40 题评测 + 检索回归 + JS 检查 + Docker build
- `.github/workflows/deploy.yml`：测试 → 推 GHCR → Render Deploy Hook → GitHub Pages
- `assets/ai-config.js`：前端 API 地址；本地默认 8000，Pages 构建时用 `AI_API_BASE` 覆盖
- `docs/deploy.md`：Render / Fly / VPS / Pages 的完整步骤

> 本机 Docker 已安装并完成 **build + run + /health 验证**；GitHub Actions 仍未实际触发（没有 push / 云端凭据）。

## 产物

| 文件 | 作用 |
|---|---|
| `Dockerfile` | API 镜像，`uvicorn ai.app:app --host 0.0.0.0 --port 8000` |
| `.dockerignore` | 排除 `.env`、前端、图片、缓存、文档 |
| `docker-compose.yml` | 本地 API + 环境变量 |
| `.github/workflows/ci.yml` | PR/push 测试与镜像构建 |
| `.github/workflows/deploy.yml` | GHCR 镜像 + Render + Pages |
| `assets/ai-config.js` | 前端 API 地址配置 |
| `docs/deploy.md` | 部署手册 |

## 环境变量

| 变量 | 放哪里 | 说明 |
|---|---|---|
| `LLM_API_KEY` | Render/VPS Secret | 真实 Key，空则 Mock |
| `LLM_BASE_URL` | Render/VPS 环境变量 | 默认 `https://api.deepseek.com` |
| `LLM_MODEL` | Render/VPS 环境变量 | 默认 `deepseek-chat` |
| `ALLOWED_ORIGINS` | Render/VPS 环境变量 | 正式前端域名，逗号分隔 |
| `RATE_LIMIT_PER_MINUTE` | Render/VPS 环境变量 | 默认 30 |
| `RENDER_DEPLOY_HOOK` | GitHub Secret | 可选，触发 Render 重新部署 |
| `AI_API_BASE` | GitHub Variable | 后端公网地址，写入 Pages 的 `ai-config.js` |

## 本地验证

```text
30 个 unittest 通过
node --check assets/ai-assistant.js 通过
16 个页面都加载 ai-config.js + ai-assistant.js
Docker Desktop 4.99.0 / Engine 29.9.3（Hyper-V 后端）
xbxc-ai:latest 236 MB，容器 healthy
GET /health -> {"ok":true,"llm_configured":true,...}
POST /chat  -> mode="llm", prompt_version="v2", citations=3
```

实际执行：

```bash
docker build -t xbxc-ai .
docker run -d --name xbxc-ai --env-file ai/.env -p 8000:8000 xbxc-ai
docker ps
```

本机 Docker Hub 直连不稳，先用镜像站拉基础镜像再打 tag：

```bash
docker pull docker.m.daocloud.io/library/python:3.12-slim
docker tag docker.m.daocloud.io/library/python:3.12-slim python:3.12-slim
docker build -t xbxc-ai .
```

复验脚本：`scripts/docker_verify.ps1`（启动 Docker Desktop → build → run → 等 `/health`）。

## 部署顺序（Render + Pages）

1. Render 建 Docker Web Service，Health Check `/health`。
2. 配环境变量：`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`、`ALLOWED_ORIGINS`。
3. Render 创建 Deploy Hook，存到 GitHub Secret `RENDER_DEPLOY_HOOK`。
4. Render 公网地址存到 GitHub Variable `AI_API_BASE`。
5. 仓库 Settings → Pages → Source 选 GitHub Actions。
6. push `master`，Deploy workflow 构建 GHCR、触发 Render、部署 Pages。

## 安全

- `.env` 被 `.gitignore` 和 `.dockerignore` 双重排除，不会进镜像。
- Key 只放 Render/VPS Secret；GitHub Pages 产物只有 `ai-config.js` 里的 API 地址，没有 Key。
- `ALLOWED_ORIGINS` 只填正式前端域名，不要用 `*`。
- GHCR 镜像默认私有/需权限；Render Deploy Hook 是 Secret。

## 限制

- 本机用 Hyper-V 后端；WSL2 的 Linux 组件下载约 712 MB 且被限速，未使用 WSL2 路径。
- 本机 Docker Hub 直连失败，基础镜像通过 `docker.m.daocloud.io` 镜像站拉取并打 tag；CI 里没有这个前置步骤，GitHub Actions 网络正常时不需要。
- `docker compose up` 未单独执行；已用等价的 `docker run` 验证镜像。
- 未实际触发 GitHub Actions；workflow YAML 需要第一次 push 后在 Actions 页面验证。
- Render 免费实例会休眠，首次请求可能慢。
- 限流仍是单进程内存版；多实例需要 Redis/网关。
- 公开部署前确认菜谱图片版权。

## 下一步

真正执行一次部署：Render 建服务 → 配 Secret/Variable → push → 看 Actions 日志 → 用 Pages 打开 AI 面板，确认 `/chat/stream` 命中公网 API。
