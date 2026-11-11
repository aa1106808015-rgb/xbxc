#!/usr/bin/env python3
"""D1: BM25 retrieval baseline for the 30-question set.

No LLM, no embeddings. The point is to get a repeatable number before
adding FastAPI / RAG / Agent code.
"""
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHUNKS_PATH = ROOT / "ai" / "data" / "chunks.jsonl"
QUESTIONS_PATH = ROOT / "ai" / "eval" / "questions.jsonl"
REPORT_PATH = ROOT / "ai" / "eval" / "report.md"

K1 = 1.5
B = 0.75
TOP_K = 3


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def tokenize(text: str):
    """CJK character bigrams + ASCII words. Works without a tokenizer dependency."""
    text = text.lower()
    ascii_tokens = re.findall(r"[a-z0-9]+", text)
    chars = "".join(re.findall(r"[\u4e00-\u9fff]", text))
    bigrams = [chars[i:i + 2] for i in range(max(0, len(chars) - 1))]
    return ascii_tokens + bigrams


class BM25:
    def __init__(self, docs):
        self.docs = docs
        self.doc_tokens = [tokenize(d) for d in docs]
        self.doc_len = [len(t) for t in self.doc_tokens]
        self.avgdl = sum(self.doc_len) / max(1, len(self.doc_len))
        self.tf = [Counter(t) for t in self.doc_tokens]
        df = Counter()
        for tokens in self.doc_tokens:
            df.update(set(tokens))
        n = len(docs)
        self.idf = {
            term: math.log(1 + (n - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

    def score(self, query: str, index: int):
        q = Counter(tokenize(query))
        tf = self.tf[index]
        dl = self.doc_len[index]
        total = 0.0
        for term, qf in q.items():
            if term not in tf:
                continue
            freq = tf[term]
            denom = freq + K1 * (1 - B + B * dl / max(1e-9, self.avgdl))
            total += self.idf.get(term, 0.0) * (freq * (K1 + 1) / denom) * qf
        return total

    def search(self, query: str, k: int = TOP_K):
        scored = [(self.score(query, i), i) for i in range(len(self.docs))]
        scored.sort(key=lambda x: (-x[0], x[1]))
        return scored[:k]


def main() -> None:
    chunks = load_jsonl(CHUNKS_PATH)
    questions = load_jsonl(QUESTIONS_PATH)
    bm25 = BM25([c["text"] for c in chunks])

    answerable = [q for q in questions if q["answerable"]]
    refusal = [q for q in questions if not q["answerable"]]

    per_intent = defaultdict(lambda: {"n": 0, "recipe_hits": 0, "step_n": 0, "step_hits": 0})
    rows = []
    rr_total = 0.0
    recipe_hits_at_1 = 0
    step_hits_at_1 = 0
    failures = []

    for q in answerable:
        hits = bm25.search(q["question"], TOP_K)
        expected = set(q["expected_recipe_ids"])
        top_meta = [(score, chunks[i]["metadata"], chunks[i]["text"][:80]) for score, i in hits]
        recipe_hit = any(meta["recipe_id"] in expected for _, meta, _ in top_meta)
        top1_hit = bool(top_meta) and top_meta[0][1]["recipe_id"] in expected
        recipe_hits_at_1 += int(top1_hit)

        rr = 0.0
        for rank, (_, meta, _) in enumerate(top_meta, start=1):
            if meta["recipe_id"] in expected:
                rr = 1.0 / rank
                break
        rr_total += rr

        step_hit = None
        step_hit_at_1 = None
        if q["expected_step"] is not None:
            step_hit = any(
                meta["type"] == "step"
                and meta["recipe_id"] in expected
                and meta["step_index"] == q["expected_step"]
                for _, meta, _ in top_meta
            )
            step_hit_at_1 = bool(
                top_meta
                and top_meta[0][1]["type"] == "step"
                and top_meta[0][1]["recipe_id"] in expected
                and top_meta[0][1]["step_index"] == q["expected_step"]
            )
            step_hits_at_1 += int(step_hit_at_1)

        stat = per_intent[q["intent"]]
        stat["n"] += 1
        stat["recipe_hits"] += int(recipe_hit)
        if step_hit is not None:
            stat["step_n"] += 1
            stat["step_hits"] += int(step_hit)

        if not recipe_hit or (step_hit is False):
            failures.append((q, top_meta, recipe_hit, step_hit))

        rows.append((q, top_meta, recipe_hit, step_hit))

    recipe_recall = sum(r[2] for r in rows) / max(1, len(rows))
    recipe_recall_at_1 = recipe_hits_at_1 / max(1, len(rows))
    mrr = rr_total / max(1, len(rows))
    step_total = sum(1 for r in rows if r[3] is not None)
    step_recall = sum(1 for r in rows if r[3]) / max(1, step_total)
    step_recall_at_1 = step_hits_at_1 / max(1, step_total)

    lines = []
    lines.append("# D1 检索基线报告\n")
    lines.append("## 数据\n")
    lines.append(f"- 菜谱：9 道（55 个步骤，51 条用料）\n")
    lines.append(f"- 切块：{len(chunks)} 个（recipe / step / ingredients）\n")
    lines.append(f"- 评测题：{len(questions)} 道（可回答 {len(answerable)}，拒答 {len(refusal)}）\n")
    lines.append(f"- 检索：BM25（k1={K1}, b={B}, top_k={TOP_K}），CJK 二元切分 + 英文词\n")
    lines.append("\n## 总体\n")
    lines.append(f"- **Recall@{TOP_K}（可回答问题）**：{recipe_recall:.1%}（{sum(r[2] for r in rows)}/{len(rows)}）\n")
    lines.append(f"- **Recall@1（可回答问题）**：{recipe_recall_at_1:.1%}（{recipe_hits_at_1}/{len(rows)}）\n")
    lines.append(f"- **MRR**：{mrr:.3f}\n")
    lines.append(f"- **步骤命中率 @{TOP_K}（6 道步骤题）**：{step_recall:.1%}（{sum(1 for r in rows if r[3])}/{step_total}）\n")
    lines.append(f"- **步骤命中率 @1（6 道步骤题）**：{step_recall_at_1:.1%}（{step_hits_at_1}/{step_total}）\n")
    lines.append("\n> 9 道菜的食材区分度较高，recipe-level Recall 已接近饱和；D3/D6 应重点看步骤命中率与最终回答质量。\n")
    lines.append("\n## 分类\n")
    lines.append("| 意图 | 题数 | Recall@3 | 步骤命中 |\n")
    lines.append("|---|---:|---:|---:|\n")
    for intent in ["find_recipe", "step_qa", "scaling", "shopping"]:
        stat = per_intent[intent]
        step_text = "—"
        if stat["step_n"]:
            step_text = f"{stat['step_hits']}/{stat['step_n']}"
        lines.append(f"| {intent} | {stat['n']} | {stat['recipe_hits']}/{stat['n']} | {step_text} |\n")

    lines.append("\n## 失败样例（用于 D3 检索优化）\n")
    if failures:
        for q, top_meta, recipe_hit, step_hit in failures:
            lines.append(f"### {q['id']} {q['intent']}：{q['question']}\n")
            lines.append(f"- 期望菜谱：{q['expected_recipe_ids']}；期望步骤：{q['expected_step']}\n")
            lines.append(f"- 检索结果：\n")
            for score, meta, excerpt in top_meta:
                lines.append(f"  - {score:.2f} | {meta['recipe_name']} | {meta['type']} {meta.get('step_index') or ''} | {excerpt}\n")
            lines.append(f"- 命中：菜谱={recipe_hit}，步骤={step_hit}\n\n")
    else:
        lines.append("无失败样例。\n")

    lines.append("\n## 拒答题（D1 不计入 Recall）\n")
    lines.append(f"拒答题 {len(refusal)} 道，留给 D2/D6 的 LLM 拒答评测。D1 只记录检索最高分，不做对错判断。\n")
    for q in refusal:
        hits = bm25.search(q["question"], 1)
        score, idx = hits[0]
        meta = chunks[idx]["metadata"]
        lines.append(f"- {q['id']} {q['question']} → top1={meta['recipe_name']}（{score:.2f}）\n")

    lines.append("\n## 下一步\n")
    lines.append("- D3 用 Embedding + 混合检索重跑同一套题，对比 Recipe Recall@1 与步骤命中率。\n")
    lines.append("- 目标：步骤命中率 @3 从当前基线提升到 ≥90%（40 题版本），Recipe Recall@1 保持 ≥95%。\n")

    REPORT_PATH.write_text("".join(lines), encoding="utf-8")

    summary = {
        "chunks": len(chunks),
        "questions": len(questions),
        "answerable": len(answerable),
        "recall_at_3": round(recipe_recall, 4),
        "recall_at_1": round(recipe_recall_at_1, 4),
        "mrr": round(mrr, 4),
        "step_recall_at_3": round(step_recall, 4),
        "step_recall_at_1": round(step_recall_at_1, 4),
        "by_intent": {k: dict(v) for k, v in per_intent.items()},
        "failures": len(failures),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
