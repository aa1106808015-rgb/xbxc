# D4 报告：四个工具接上

## 结论

`/chat` 不再“说需要工具”，而是真的调用四个工具：

- `search_recipes`：找菜
- `get_step`：取某道菜的第 N 步
- `scale_servings`：按目标份量算用量
- `build_shopping_list`：生成采购清单（支持多道菜）

新增 `GET /tools` 返回 JSON Schema，后续 LLM function calling 可直接用。

## 工具行为

| 工具 | 输入 | 输出 |
|---|---|---|
| `search_recipes` | `query`, `limit` | 菜谱 id、名称、时间、份量、链接、导语 |
| `get_step` | `recipe_id`, `step_index` | 标题、做法、判断标准、时间、总步数 |
| `scale_servings` | `recipe_id`, `target_servings` | 基准份量、目标份量、倍数、每条用料的原文与缩放值 |
| `build_shopping_list` | `recipe_ids[]`, `servings_map` | 按菜谱分组的采购清单 |

## 实测

### 份量换算：番茄炒蛋 2 → 4 人份（×2）

```text
番茄炒蛋：2 → 4 人份（×2.0）
- 番茄：2 个（约 300 克） → 4 个（约 600 克）
- 鸡蛋：3 个 → 6 个
- 小葱：1 根 → 2 根
- 盐：约 1/2 小勺 → 约 1 小勺
- 白糖：1/2 – 1 小勺 → 1 – 2 小勺
- 食用油：约 2 汤匙 → 约 4 汤匙
```

### 采购清单：麻婆豆腐 + 番茄炒蛋

按菜谱分组输出，同名食材不跨菜合并，避免单位不同误加。

### 步骤：冬瓜丸子汤第 4 步

`get_step("tang", 4)` 返回“水烧到响边”的做法、判断标准和时间。

## 已验证

- **18 个 unittest 全部通过**：D2/D3 回归 + D4 工具测试。
- `/tools` 返回 4 个工具的 JSON Schema。
- `/chat` 实测：
  - 份量题 → `mode="tool"`, `tool="scale_servings"`，鸡蛋 3 → 6 个。
  - 采购题 → `mode="tool"`, `tool="build_shopping_list"`，多菜分组。
  - 步骤题 → `mode="tool"`, `tool="get_step"`，引用正确步骤。
  - 找菜 → `mode="tool"`, `tool="search_recipes"`。

## 限制

- 菜谱用量是自由文本（如“1/2 – 1 小勺”“半根”“几滴”），缩放按数字比例估算，并按克/毫升/个/勺做四舍五入；不是结构化单位换算。
- “适量/几滴/可选”保持原样，不缩放。
- 采购清单按菜谱分组，不做跨菜同名合并（单位不同，合并容易错）。
- 目前是确定性工具路由；LLM function calling 还没接，但 `TOOL_SCHEMAS` 已准备好。
- FastAPI 版仍未在本机启动（缺依赖）；stdlib 版已实测。

## 下一步 D5

把 `/chat` 接到前端 AI 面板：SSE 流式、引用展示、加载/错误状态、手机宽度适配；原静态站保留降级。
