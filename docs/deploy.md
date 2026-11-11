# 部署：Docker + GitHub Actions

## 这套部署长什么样

```text
GitHub Pages（静态站）  ──HTTPS──►  Render / Fly / VPS（Docker 里的 FastAPI）
         │                                      │
         └── ai-config.js 里的 API 地址          └── LLM API（Key 只在服务端）
```

- 前端：16 个 HTML + assets，部署到 GitHub Pages。
- 后端：`ai/` FastAPI，构建成 Docker 镜像。
- 环境变量：Key、模型、CORS、限流全部由部署平台注入，**不进镜像、不进 Git**。

## 1. 本地 Docker

```bash
docker build -t xbxc-ai .
docker run --rm -p 8000:8000 --env-file ai/.env xbxc-ai
curl http://127.0.0.1:8000/health
```

本机实测（Docker Desktop 4.99 + Hyper-V 后端）镜像 236 MB，容器 healthy，`/health` 返回 `llm_configured: true`。

如果 Docker Hub 拉不动基础镜像：

```bash
docker pull docker.m.daocloud.io/library/python:3.12-slim
docker tag docker.m.daocloud.io/library/python:3.12-slim python:3.12-slim
docker build -t xbxc-ai .
```

或者用 Compose：

```bash
docker compose --env-file ai/.env up -d --build
docker compose ps
```

`docker-compose.yml` 会从 shell/`.env` 读取：

| 变量 | 默认 | 说明 |
|---|---|---|
| `LLM_API_KEY` | 空 | 真实 Key；空则 Mock |
| `LLM_BASE_URL` | `https://api.deepseek.com` | OpenAI 兼容地址 |
| `LLM_MODEL` | `deepseek-chat` | 模型 ID |
| `ALLOWED_ORIGINS` | 本地 8765 | 前端 Origin 白名单 |
| `RATE_LIMIT_PER_MINUTE` | `30` | 每 IP 每分钟请求数 |

## 2. GitHub Actions

### CI：`.github/workflows/ci.yml`

每次 push / PR：

1. 安装 `ai/requirements.txt`
2. 跑 30 个 unittest
3. 跑 D6 工具路径 40 题评测
4. 跑 D3 混合检索回归
5. `node --check`
6. `docker build`（不 push）

### 部署：`.github/workflows/deploy.yml`

push 到 `master/main` 时：

1. 测试
2. 构建并推送 GHCR：`ghcr.io/<owner>/<repo>:master`
3. 如果配置了 `RENDER_DEPLOY_HOOK`，触发 Render 重新部署
4. 如果配置了仓库变量 `AI_API_BASE`，构建 `_site` 并部署 GitHub Pages

#### 需要配置的 GitHub Secrets / Variables

| 类型 | 名称 | 用途 |
|---|---|---|
| Secret | `RENDER_DEPLOY_HOOK` | Render 的 Deploy Hook URL，可选 |
| Variable | `AI_API_BASE` | 后端公网地址，例如 `https://xbxc-ai.onrender.com` |

`AI_API_BASE` 会在 Pages 构建时写入 `_site/assets/ai-config.js`：

```js
window.XIAOBAI_AI_API = "https://xbxc-ai.onrender.com";
```

本地开发仍用 `assets/ai-config.js` 里的 `http://127.0.0.1:8000`。

#### 开启 Pages

仓库 Settings → Pages → Build and deployment → Source 选 **GitHub Actions**。

## 3. Render（推荐，最省事）

仓库根目录有 `render.yaml`，可以直接 New → Blueprint 连接仓库；也可以手动建 Web Service。

手动步骤：

1. Render → New → Web Service → 连接仓库。
2. Runtime 选 **Docker**，Dockerfile 用 `./Dockerfile`。
3. Health Check Path 填 `/health`。
4. 环境变量：

```text
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
ALLOWED_ORIGINS=https://<你的用户名>.github.io
RATE_LIMIT_PER_MINUTE=30
```

5. 创建 Deploy Hook，把 URL 存到 GitHub Secret `RENDER_DEPLOY_HOOK`。
6. 把 Render 公网地址存到 GitHub Variable `AI_API_BASE`。
7. 重新跑 Deploy workflow；Pages 部署完成后打开 `https://<你的用户名>.github.io/<repo>/`。

> 如果使用自定义域名，`ALLOWED_ORIGINS` 改成 `https://你的域名`；多个 Origin 用逗号分隔。

## 4. Fly.io / VPS（可选）

GHCR 镜像可以直接跑：

```bash
docker pull ghcr.io/<owner>/<repo>:master
docker run -d --name xbxc-ai --restart unless-stopped \
  -p 8000:8000 \
  -e LLM_API_KEY=sk-... \
  -e LLM_BASE_URL=https://api.deepseek.com \
  -e LLM_MODEL=deepseek-chat \
  -e ALLOWED_ORIGINS=https://<你的用户名>.github.io \
  ghcr.io/<owner>/<repo>:master
```

前面加 Nginx/Caddy 做 HTTPS 反代；CORS 的 `ALLOWED_ORIGINS` 必须是最终前端域名。

## 5. 验证

```bash
curl https://<api-domain>/health
# {"ok":true,"llm_configured":true,...}

curl -X POST https://<api-domain>/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"番茄炒蛋","use_tools":false}'
# mode: "llm"
```

浏览器打开 Pages 站点，右下角「问小白」应能流式回答；Network 里 `/chat/stream` 来自 Render 域名。

## 6. 安全边界

- `LLM_API_KEY` 只放 Render/VPS 的 Secret/环境变量；不要放 GitHub Variable，不要放 Pages。
- `.env` 已被 `ai/.gitignore` 忽略；`.dockerignore` 也排除了 `ai/.env`。
- `ALLOWED_ORIGINS` 只填正式前端域名；不要用 `*`。
- HTTPS 由 Render/VPS 提供；本地 `http://127.0.0.1` 只用于开发。
- 限流是单进程内存版；多实例部署要换 Redis/网关限流。
- 公开部署前确认菜谱图片版权（现有部分图片来自下厨房）。
