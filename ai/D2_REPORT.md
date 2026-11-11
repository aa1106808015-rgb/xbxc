# D2 报告：/chat + Prompt v1 + 引用

## 结论

D2 链路已跑通：**问题 → BM25 检索 3 个片段 → Prompt v1 → LLM / Mock → 回答 + 引用编号**。没有 API Key 时自动走 Mock，不阻塞 D3/D5。

## 已实现

| 文件 | 作用 |
|---|---|
| `ai/app.py` | FastAPI：`GET /health`、`POST /chat` |
| `ai/dev_server.py` | 零依赖 stdlib 版 `/chat`，当前机器可直接跑 |
| `ai/core.py` | 检索、Prompt、LLM/Mock、引用组装、拒答 |
| `ai/llm.py` | OpenAI 兼容客户端（DeepSeek/OpenAI，stdlib） |
| `ai/prompts.py` | Prompt v1：只依据菜谱片段、强制 `[C1]` 引用、无依据拒答 |
| `ai/retrieval.py` | BM25 检索（CJK 二元切分） |
| `ai/tests/test_core.py` | 6 个无 LLM 冒烟测试 |
| `ai/tests/test_llm_mode.py` | 本地 mock LLM 端点，验证 LLM 模式与 usage |

## 接口

`GET /health`：

```json
{"ok": true, "service": "xbxc-ai", "llm_configured": false, "model": "deepseek-chat"}
```

`POST /chat`：

```json
{"message": "麻婆豆腐的豆腐为什么要先用盐水焯？", "top_k": 3}
```

返回：

```json
{
  "answer": "麻婆豆腐 第 2 步「盐水里焯豆腐 1 分钟」：... [C1]",
  "citations": [{"id": "C1", "chunk_id": "step:mapo:2", "type": "step", "step_index": 2, "recipe_name": "麻婆豆腐", "url": "recipes/mapo-doufu.html"}],
  "mode": "mock",
  "usage": {}
}
```

## 已验证

- 7 个 `unittest` 全部通过：找菜、步骤、采购、份量、拒答、引用字段、LLM 模式。
- `GET /health` 返回 200，无 Key 时 `llm_configured=false`。
- `POST /chat` 实测：
  - 步骤题 → 引用 `step:mapo:2`，答案含判断标准。
  - 找菜 → 推荐番茄炒蛋，引用菜谱块。
  - 采购 → 返回麻婆豆腐用料清单。
  - 燃气灶维修 → `mode="refusal"`，不返回引用。
- LLM 模式用本地 mock OpenAI 兼容端点验证：请求路径 `/v1/chat/completions`、模型名、`usage` 与 `[C1]` 引用解析均通过。
- `ai/app.py` 等文件通过 `py_compile` 语法检查。

## 未完成 / 限制

- 当前机器没装 FastAPI/uvicorn，所以 **FastAPI 版未实际启动**；stdlib 版已实测。装依赖后 `uvicorn ai.app:app` 即可。
- 没有真实 API Key，**第三方 LLM API 未测**；LLM 客户端/Prompt/引用解析已用本地 mock 端点验证。
- D2 的 `/chat` 仍是非流式；D5 已加 `/chat/stream` SSE 和前端面板。
- D2 当时份量换算只回复“需要工具”；D4 已接 `scale_servings` / `build_shopping_list`，现在直接算（见 `D4_REPORT.md`）。
- D2 当时用 BM25，Q07/Q11 步骤题会错；D3 已把 `/chat` 切到 `HybridRetriever`，两题 Top1 已修正（见 `D3_REPORT.md`）。

## 启动

```bash
# 零依赖（现在就能跑）
python -m ai.dev_server --port 8000

# FastAPI（装依赖后）
pip install -r ai/requirements.txt
uvicorn ai.app:app --reload --port 8000
```

```powershell
# 测试
$env:PYTHONIOENCODING="utf-8"
python -m unittest ai.tests.test_core -v
```

## 下一步 D3

用 Embedding + 混合检索重跑 D1 的 30 题，目标：步骤命中率 @3 从 66.7% → ≥90%，Recipe Recall@1 ≥95%。
