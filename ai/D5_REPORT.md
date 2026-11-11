# D5 报告：前端 AI 面板 + SSE 流式

## 结论

16 个页面都接入了悬浮 AI 面板：

- 右下角「问小白」→ 打开面板
- 输入问题 → `POST /chat/stream` SSE 流式回答
- 回答下方展示可点击的「依据」引用，直接打开对应菜谱/步骤
- API 不可用时给出明确提示，原站点不受影响
- 640px 以下变成底部抽屉，输入框 16px 防 iOS 聚焦缩放

## 前端

| 文件 | 作用 |
|---|---|
| `assets/ai-assistant.js` | 面板 DOM、SSE 解析、引用渲染、错误处理、移动端 |
| `assets/ai-assistant.css` | 面板样式、桌面悬浮、移动端底部抽屉、reduced-motion |
| 16 个 HTML | 在 `</body>` 前加入 `ai-assistant.js`（菜谱页用 `../assets/`） |

功能细节：

- SSE 用 `fetch + ReadableStream`，不是 EventSource（需要 POST）。
- 支持 `event: meta / citations / token / done / error`。
- 引用 chip：`第 N 步 · 菜名`、`用料 · 菜名`、`菜名`，新标签打开。
- Enter 发送，Shift+Enter 换行；中文输入法 composition 不误发。
- 关闭面板会 abort 当前请求；错误显示“API 未启动”的排查提示。
- 深链：`?ai=1` 打开面板，`&q=问题` 可直接发问；`&nostream=1` 走非流式 `/chat`，用于截图或旧浏览器兜底。
- 流式结束后会移除正文里的 `[C1]` 标记，只保留下方引用 chip，阅读更干净。

## 服务端 SSE

- stdlib：`ai/dev_server.py` 新增 `POST /chat/stream`，返回 `text/event-stream`；工具/拒答每 8 个字符一个 `token` 事件。
- FastAPI：`ai/app.py` 新增 `StreamingResponse` 版本，事件协议一致；D6 后真实 LLM 路径直接透传 token。
- 事件顺序：`meta` → `citations` → 多个 `token` → `done`。
- 实测 `curl`：`meta:1 / citations:1 / token:25 / done:1`，Content-Type 为 `text/event-stream; charset=utf-8`。

## 验证

- `node --check assets/ai-assistant.js` 通过。
- 16 个页面均包含 AI 脚本，无重复。
- 桌面 1365px、移动 500px 截图检查：面板、输入框、引用、建议问题均可用。
- 24 个 Python unittest 保持通过。
- SSE 实测拿到完整 `done` 事件。

## 限制

- 工具/拒答路径是“先算完答案，再按 8 字符切片”；D6 已把真实 LLM 路径改成 token 级流式，事件协议不变。
- FastAPI 版仍未在本机启动（缺 fastapi/uvicorn）；stdlib SSE 已实测。
- API 默认 `http://127.0.0.1:8000`；部署时在页面设置 `window.XIAOBAI_AI_API`。
- 面板不持久化对话；服务端目前忽略 `history`，多轮上下文留给 D6。
- 没有做语音输入、图片上传、Markdown 渲染（回答用纯文本 + 引用 chip，避免 XSS）。

## 下一步 D6

扩到 40 题，评 LLM 的引用正确率/拒答率，做 Prompt v2 和错误分析；同时决定是否把真实 LLM 调用改为 token 级流式。
