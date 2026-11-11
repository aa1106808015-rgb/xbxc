# 当前限制与解除方法

> 状态截至 D8：真实 DeepSeek Key 已配置，API 正常，30 个测试通过；Docker/云端部署尚未实际执行。

## P0：会阻塞“真正上线”的限制

| 限制 | 现状/证据 | 影响 | 解除方法 |
|---|---|---|---|
| **本机没有 Docker** | `docker` 命令不存在；Dockerfile 只做了静态检查 | 无法本地验证镜像，部署前可能踩坑 | 安装 Docker Desktop（Windows 开 WSL2）→ `docker build -t xbxc-ai .` → `docker run --env-file ai/.env -p 8000:8000 xbxc-ai` → 打开 `/health` |
| **FastAPI 版没实际跑过** | 本机没有 fastapi/uvicorn；一直用零依赖 stdlib 版 | 生产入口 `uvicorn ai.app:app` 未验证 | 建 venv：`python -m venv .venv` → `.venv\Scripts\pip install -r ai/requirements.txt` → `.venv\Scripts\uvicorn ai.app:app --port 8000` |
| **GitHub 没 push** | 本地 `master` 领先 `origin/master` 2 个提交；D8 仍未提交 | GitHub Actions / Pages / Render 都不会触发 | 配好代理或 SSH over 443，`git add . && git commit`，`git push origin master`；先确认 `git remote -v` |
| **没有真正部署** | 没有 Render/VPS/Pages 实例 | 只有本地 `127.0.0.1`，别人打不开 | 按 `docs/deploy.md`：Render Blueprint 建 Docker 服务 → 配 `LLM_API_KEY`/`ALLOWED_ORIGINS` → GitHub Secret `RENDER_DEPLOY_HOOK` → Variable `AI_API_BASE` → Pages Source 选 GitHub Actions |
| **菜谱图片版权** | 部分步骤图来自下厨房；产品文档已标为上线硬阻塞 | 公开部署可能侵权 | 换成自己拍/授权图，或先只保留文字步骤；上线前逐张确认授权 |

## P1：影响 AI 质量与可信度

| 限制 | 现状/证据 | 影响 | 解除方法 |
|---|---|---|---|
| **本地 embedding 不是语义模型** | `ai/embeddings.py` 是字符 2/3-gram TF-IDF | 同义改写、跨表达召回有限 | 换 `BAAI/bge-small-zh-v1.5`（sentence-transformers）或 OpenAI embedding；接口已在 `Embedder`，换实现后用 30/40 题复测 |
| **只有 9 道菜 / 55 步** | `ai/data/recipes.json` | 语料小，recipe-level 100% 容易饱和，开放域不足 | 扩到 30–50 道菜；保持“菜谱/步骤/用料”切块与 metadata；补难例、同义表达、多菜问题 |
| **40 题仍偏小，只测了一个模型** | 真实 LLM 引用正确率 96.9%（31/32），仅 DeepSeek 一轮 | 不能代表其他模型/版本；统计置信度低 | 扩到 100–200 题；加人工 1–5 分有用性评分；换 `deepseek-reasoner`、`gpt-4o-mini` 等复测 |
| **Q37 多菜采购在 LLM-only 路径失败** | 模型没有合并清单上下文，选择安全拒答 | 真实 LLM 引用正确率被拉到 96.9% | 多菜/份量/步骤强制走工具：在 router 里把 `shopping` 意图固定到 `build_shopping_list`；或把工具结果放进 LLM 上下文再让模型总结 |
| **Q10 步骤 Top1 仍是用料块** | 步骤 @3 100%，但 @1 83.3% | 前端可能先展示用料而不是步骤 | 在 UI 上按 `type=step` 优先展示；或加 step-aware rerank 权重 |
| **份量用量是自由文本** | “1/2–1 小勺”“半根”“几滴”靠正则估算 | 缩放是近似值，不是严格单位换算 | 给 `ingredients` 补 `amountValue/unit` 结构化字段；用统一单位表和取整规则；保留原文兜底 |
| **没有回答质量的人工评分** | 只评引用/拒答/路由 | 可能出现“引用对但答得不好” | 加 5 分制有用性/可读性评分；双人盲评 50 条；把差例入库 |

## P2：安全、稳定性与产品体验

| 限制 | 现状/证据 | 影响 | 解除方法 |
|---|---|---|---|
| **没有登录/鉴权** | API 公开可调；CORS 只防浏览器 | 公开部署后可能被刷、Key 成本失控 | 加 API Token/JWT；或 Cloudflare Access / 反向代理 Basic Auth；个人演示至少加访问口令 |
| **限流是单进程内存版** | `ai/security.py` RateLimiter | 多 worker/重启重置；代理后 IP 可能不准 | 生产换 Redis 滑动窗口/网关限流；配置可信 `X-Forwarded-For` |
| **Prompt 注入检测是关键词** | `security.py` 的 pattern 列表 | 变体可能绕过 | Prompt v2 规则 + 拒答是第二层；加 LLM 输入分类器/更强 guard；记录注入尝试 |
| **SSE 工具路径是切片，不是模型 token** | 工具/拒答先算完整答案再切 8 字符 | 首 token 延迟对工具题不重要，但不是真流式 | 保持现状即可；真实 LLM 路径已经是 token 级；若要统一，可把工具结果也做成流式 JSON 事件 |
| **没有对话持久化** | `history` 只传给服务端、不落库 | 刷新即丢失；多轮上下文有限 | 若要保留，加会话表 + 过期清理；或明确“不保存”，保持隐私优势 |
| **手机端只用无头 Chrome 截图验证** | 未上真机 | iOS Safari 的 100vh/输入缩放/安全区可能不同 | 用 iPhone Safari + Android Chrome 真机走一遍：打开面板、输入、滚动、关闭、断网 |
| **Render 免费实例会休眠** | 免费 plan | 首次请求慢，用户体验差 | 升 paid 实例，或用 Fly/VPS 常驻；加首屏 loading/超时提示 |
| **API 地址要手工配** | Pages 构建用 `AI_API_BASE` 写入 `ai-config.js` | 配错就请求 localhost | CI 里加校验：`AI_API_BASE` 必须 `https://` 且可访问 `/health`，否则 Pages job 失败 |

## 建议的最短解除顺序

1. **安装 Docker**，本地 `docker build` + `docker run` 验证镜像和 `/health`。
2. **提交 D8 并 push**，让 GitHub Actions 第一次真正跑起来。
3. **Render 建服务**，配 `LLM_API_KEY`、`ALLOWED_ORIGINS`；拿到公网 `/health`。
4. **配 `AI_API_BASE` + Pages**，用手机打开 Pages 面板确认 `/chat/stream` 命中公网 API。
5. **修 Q37**：多菜采购强制走 `build_shopping_list`。
6. **换 BGE/OpenAI embedding**，用 40 题复测步骤 @3 和引用正确率。
7. **加访问控制 + Redis 限流**，再考虑公开分享链接。
8. **处理图片版权**，这是公开上线前必须解决的非技术问题。

## 不建议现在做

- 不要先上多 Agent 框架/复杂向量数据库；9 道菜的语料不值得。
- 不要微调模型；当前问题主要是检索和工具路由，不是模型知识。
- 不要为了“真流式”把工具结果也交给模型重写，数字容易错。
- 不要在没有鉴权的情况下把 API 直接公开到互联网。
