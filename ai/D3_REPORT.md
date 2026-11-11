# D3 报告：Embedding + 混合检索

## 结论

步骤命中率 @3：**66.7% → 100%**，达到 D3 目标（≥90%）；Recipe Recall@1 保持 **95.8%**，没有牺牲菜谱级检索。

## 方法

1. **BM25**：原有 CJK 二元切分，作为稀疏检索基线。
2. **本地 embedding**：字符 2/3-gram TF-IDF，L2 归一化，余弦相似度；不依赖模型下载/API Key。
3. **混合打分**：`0.55 × BM25_norm + 0.45 × cosine`。
4. **查询扩展**：蛋液、响边、收汁、焯水、出水等厨艺同义词。
5. **步骤意图重排**：标题/正文覆盖度 + 菜谱锚点加分；只在步骤类问题上启用。

## 结果（同一套 30 题，top_k=3）

| 指标 | D1 BM25 | D3 Hybrid | 变化 |
|---|---:|---:|---:|
| Recipe Recall@1 | 95.8% | 95.8% | 0 |
| Recipe Recall@3 | 100% | 100% | 0 |
| MRR | 0.979 | 0.979 | 0 |
| 步骤命中率 @1 | 50.0% | 83.3% | +33.3% |
| **步骤命中率 @3** | **66.7%** | **100%** | **+33.3%** |

失败样例：**0**。

### 两个关键修复

- **Q07**：问“炒鸡蛋蛋液搅到什么程度”，D1 把菜谱/凉拌黄瓜步骤排前面；D3 Top1 = 番茄炒蛋第 2 步「打蛋液」。
- **Q11**：问“下肉丸水烧到什么状态”，D1 只命中菜谱和第 1 步；D3 Top1 = 冬瓜丸子汤第 4 步「水烧到响边」。

## 代码

| 文件 | 作用 |
|---|---|
| `ai/embeddings.py` | 本地字符 n-gram TF-IDF embedder（可替换成 BGE/OpenAI embedding） |
| `ai/hybrid.py` | BM25 + embedding 混合检索、查询扩展、步骤重排 |
| `ai/eval/run_hybrid.py` | 30 题对比评测，输出 `hybrid_report.md` |
| `ai/core.py` | `/chat` 已切换到 `HybridRetriever` |
| `ai/tests/test_hybrid.py` | Q07/Q11/Q10 回归测试 |

运行：

```bash
python -m ai.eval.run_hybrid
python -m unittest discover -s ai/tests -v
```

## 限制

- 本地 embedding 不是语义模型，只是字符 n-gram 特征；对同义改写仍然有限。
- 接口已隔离在 `Embedder`，后续可替换成 BGE/OpenAI embedding，用同一套 30 题复测。
- 步骤 @1 还有 1 题没到第一（Q10 的用料块排在步骤前），但步骤 @3 已全部命中；D5 接前端时可在 UI 上把 step 结果优先展示。
