# 小白学菜 · AI 层

D1 数据与检索基线；D2 `/chat` + Prompt v1 + 引用；D3 混合检索；D4 四个工具；D5 前端 AI 面板 + SSE。

## 目录

```
ai/
├── app.py                 # FastAPI: /health, /tools, /chat, /chat/stream
├── dev_server.py          # 零依赖 stdlib 版 API（含 SSE，当前可跑）
├── core.py                # 检索 -> 工具/LLM/Mock -> 引用
├── agent.py               # D4 工具路由
├── tools.py               # 四个工具 + JSON Schema
├── embeddings.py          # 本地字符 2/3-gram TF-IDF embedding
├── hybrid.py              # BM25 + embedding + 步骤重排
├── llm.py                 # OpenAI 兼容客户端（DeepSeek/OpenAI）
├── prompts.py             # Prompt v1
├── retrieval.py           # BM25 检索
├── requirements.txt       # FastAPI / uvicorn
├── .env.example           # Key / Base URL / 模型配置示例
├── data/
│   ├── recipes.json       # 9 道菜，55 步，51 条用料
│   └── chunks.jsonl       # 73 个检索块：9 recipe + 55 step + 9 ingredients
├── eval/
│   ├── build_questions.py # 生成 30 题（5 类 × 6）
│   ├── questions.jsonl    # 30 题，24 道可回答 + 6 道拒答
│   ├── run_baseline.py    # BM25 检索基线
│   ├── run_hybrid.py      # D3 混合检索对比评测
│   ├── report.md          # D1 基线报告
│   └── hybrid_report.md   # D3 混合检索报告
├── scripts/
│   ├── export_recipes.py  # data/recipes.js -> recipes.json
│   └── build_chunks.py    # recipes.json -> chunks.jsonl
└── tests/
    ├── test_core.py       # 6 个无 LLM 冒烟测试
    ├── test_hybrid.py     # Q07/Q11/Q10 回归
    ├── test_tools.py      # D4 四个工具
    └── test_llm_mode.py   # 本地 mock LLM 端点验证 LLM 模式

assets/
├── ai-assistant.js        # D5 面板、SSE 解析、引用渲染
└── ai-assistant.css       # 桌面悬浮 + 移动端底部抽屉
```

## 运行

在仓库根目录执行：

```bash
python ai/scripts/export_recipes.py
python ai/scripts/build_chunks.py
python ai/eval/build_questions.py
python ai/eval/run_baseline.py
```

Windows PowerShell 如遇中文乱码，先设置：

```powershell
$env:PYTHONIOENCODING="utf-8"
```

## D2 服务（/chat，非流式）

D2 的目标不是“接个模型”，而是跑通：**问题 → 检索 3 个片段 → Prompt v1 → 回答 + 引用编号**。没有 API Key 时自动走 Mock，方便先验证链路。

### 零依赖启动（当前机器可直接跑）

```bash
python -m ai.dev_server --port 8000
```

```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"麻婆豆腐的豆腐为什么要先用盐水焯？"}'
```

返回示例（Mock）：

```json
{
  "answer": "麻婆豆腐 第 2 步「盐水里焯豆腐 1 分钟」：... 判断标准：... [C1]",
  "citations": [{"id": "C1", "type": "step", "step_index": 2, "recipe_name": "麻婆豆腐", "url": "recipes/mapo-doufu.html"}],
  "mode": "mock",
  "usage": {}
}
```

### FastAPI 启动（目标实现）

```bash
pip install -r ai/requirements.txt
uvicorn ai.app:app --reload --port 8000
```

当前机器没有安装 FastAPI/uvicorn，所以 **FastAPI 版只做了静态检查，未实际启动**；上面的 stdlib 版已实测 `/health` 和 `/chat`。

### 配置真实模型

复制 `ai/.env.example` 为 `.env`，或直接设环境变量：

```bash
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

- 有 Key：`/chat` 走真实 LLM，Prompt 要求每个结论标 `[C1]` 引用；解析失败或请求失败会自动回退 Mock，并在 `warning` 里说明。
- 无 Key：`mode="mock"`，从检索片段抽取回答，用于验证链路。
- 范围外问题（维修、卡路里、过敏、空气炸锅等）：`mode="refusal"`，不返回引用。

### D2 已验证

- [x] `GET /health` 返回 `ok=true`，无 Key 时 `llm_configured=false`
- [x] `POST /chat` 对找菜、步骤、采购、拒答四类问题返回正确形状
- [x] 引用包含 `chunk_id / recipe_id / step_index / url`
- [x] 7 个 `unittest` 冒烟测试全通过
- [x] LLM 模式通过本地 mock 端点验证（请求体、usage、`[C1]` 解析）
- [x] 无 Key 时 Mock 可跑，不阻塞 D3/D5
- [ ] 真实第三方 LLM API 未测（需要 Key）

### D2 已知限制

- D5 已加 `/chat/stream` SSE；当前 D2 的 `/chat` 仍是非流式。
- 份量换算已在 D4 接 `scale_servings`，现在直接算；采购清单接 `build_shopping_list`。
- 步骤题在 D3 已修复 Q07/Q11；Q10 的 Top1 仍是用料块，但正确步骤已在 Top3。
- FastAPI 版未在本机运行；代码已写好，装依赖后即可启动。

## D3 混合检索（已完成）

### 方法

- BM25（CJK 二元切分） + 本地字符 2/3-gram TF-IDF embedding，融合权重 `0.55 / 0.45`
- 厨艺同义词查询扩展：蛋液、响边、收汁、焯水、出水等
- 步骤意图重排：标题/正文覆盖度 + 菜谱锚点
- `/chat` 已切换到 `HybridRetriever`，D2 接口不变

### 结果（同一套 30 题，top_k=3）

| 指标 | D1 BM25 | D3 Hybrid | 变化 |
|---|---:|---:|---:|
| Recipe Recall@1 | 95.8% | 95.8% | 0 |
| Recipe Recall@3 | 100% | 100% | 0 |
| MRR | 0.979 | 0.979 | 0 |
| 步骤命中率 @1 | 50.0% | 83.3% | +33.3% |
| **步骤命中率 @3** | **66.7%** | **100%** | **+33.3%** |

- Q07：Top1 从“菜谱/凉拌黄瓜”变为番茄炒蛋第 2 步「打蛋液」。
- Q11：Top1 从“菜谱/第 1 步”变为冬瓜丸子汤第 4 步「水烧到响边」。
- 失败样例：0。

### 运行

```bash
python -m ai.eval.run_hybrid
python -m unittest discover -s ai/tests -v
```

> 本地 embedding 是字符 n-gram TF-IDF，不是神经语义模型；接口在 `ai/embeddings.py`，后续可替换成 BGE/OpenAI embedding，用同一套题复测。

## D4 四个工具（已完成）

| 工具 | 作用 |
|---|---|
| `search_recipes` | 找菜：菜谱 id、名称、时间、份量、链接 |
| `get_step` | 取第 N 步：做法、判断标准、时间 |
| `scale_servings` | 份量换算：原文 → 目标份量，按克/毫升/个/勺四舍五入 |
| `build_shopping_list` | 采购清单：支持多道菜、按菜谱分组 |

`/chat` 对工具类问题返回 `mode="tool"` 和 `tool` 字段；`GET /tools` 返回四份 JSON Schema，后续 LLM function calling 可直接使用。

实测：

- 番茄炒蛋 2 → 4 人份：鸡蛋 `3 个 → 6 个`，番茄 `2 个（约 300 克）→ 4 个（约 600 克）`。
- 麻婆豆腐 + 番茄炒蛋采购清单：按菜谱分组输出。
- 冬瓜丸子汤第 4 步：`get_step` 返回“水烧到响边”的做法与判断标准。
- 18 个 unittest 全通过。

限制：用量原文是自由文本，缩放是数值估算；“适量/几滴/可选”不缩放；采购清单不做跨菜同名合并；目前是确定性工具路由，LLM function calling 还没接。

## D5 前端 AI 面板（已完成）

- 16 个页面都加了悬浮「问小白」按钮，右下角打开面板。
- `POST /chat/stream` SSE：`meta → citations → token × N → done`。
- 回答下方「依据」chip 直接打开对应菜谱/步骤；引用来自 D4 工具结果。
- 640px 以下变底部抽屉，输入框 16px 防 iOS 聚焦缩放；`prefers-reduced-motion` 关闭动画。
- API 不可用时给出排查提示，原站点不受影响。
- 深链：`?ai=1` 打开面板，`&q=问题` 直接发问；`&nostream=1` 走非流式兜底。

启动：

```bash
# 终端 1：API
python -m ai.dev_server --port 8000

# 终端 2：站点
python -m http.server 8765

# 浏览器
http://127.0.0.1:8765/?ai=1
```

部署时在页面里设置 `window.XIAOBAI_AI_API = "https://你的-api"`；默认是 `http://127.0.0.1:8000`。

实测：`node --check assets/ai-assistant.js` 通过；16 页脚本无重复；桌面/移动截图检查；SSE `curl` 拿到 `meta:1 / citations:1 / token:25 / done:1`；18 个 Python 测试保持通过。

限制：当前是“先算完答案再按 8 字符切片流式输出”，不是 LLM token 级流式；FastAPI SSE 版未在本机启动（缺依赖），stdlib SSE 已实测。

## D1 当前基线

- 菜谱：9 道 / 55 步 / 51 条用料
- 检索块：73 个（recipe / step / ingredients）
- 评测题：30 道（24 可回答 + 6 拒答）
- 检索：BM25，CJK 二元切分 + 英文词，`k1=1.5, b=0.75, top_k=3`
- **Recipe Recall@3：100%**
- **Recipe Recall@1：95.8%**
- **MRR：0.979**
- **步骤命中率 @3：66.7%（4/6）**
- **步骤命中率 @1：50.0%（3/6）**

> 9 道菜的食材区分度高，recipe-level 已经接近饱和。D1 真正有意义的信号是**步骤命中率**：用户问“第几步/怎么判断”时，能不能把正确的步骤块排进前三。

## 字段说明

`questions.jsonl` 每行：

```json
{
  "id": "Q07",
  "intent": "step_qa",
  "question": "炒鸡蛋时，蛋液要搅到什么程度，下锅才不会一块白一块黄？",
  "answerable": true,
  "expected_recipe_ids": ["fanqie"],
  "expected_step": 2,
  "reference_answer": "蛋液里没有整块蛋黄，提起来是流畅的一条线；水不用多，小半勺。",
  "notes": "步骤 2，间接描述"
}
```

- `intent`：`find_recipe` / `step_qa` / `scaling` / `shopping` / `refusal`
- `expected_recipe_ids`：允许多个（一题多解时都算命中）
- `expected_step`：步骤题填 1–N，其他填 `null`
- `answerable=false` 的题不参与 D1 Recall，留给 D2/D6 评拒答

`chunks.jsonl` 每个块都带 metadata：

```json
{"chunk_id": "step:mapo:2", "metadata": {"recipe_id": "mapo", "type": "step", "step_index": 2, ...}}
```

## D1 完成标准

- [x] `recipes.json` 9 道菜 / 55 步 / 51 条用料
- [x] `chunks.jsonl` 73 块，recipe / step / ingredients 三类齐全
- [x] `questions.jsonl` 30 题，5 类各 6 题
- [x] `run_baseline.py` 一条命令跑出 Recall / MRR / 步骤命中率
- [x] `report.md` 记录基线、失败样例、拒答题最高分
- [x] 当前基线已记录：Recipe R@3 100%，Step R@3 66.7%

## 下一步

D6 扩到 40 题，评 LLM 的引用正确率、拒答率和首 token 延迟，做 Prompt v2 与错误分析；同时决定是否把真实 LLM 调用改成 token 级流式。
