#!/usr/bin/env python3
"""D3: evaluate hybrid retrieval (BM25 + local embedding + step rerank) on the 30-question set."""
import json
from collections import defaultdict
from pathlib import Path

from ai.hybrid import HybridRetriever, expand_query, is_step_query
from ai.retrieval import BM25

ROOT = Path(__file__).resolve().parents[2]
CHUNKS_PATH = ROOT / "ai" / "data" / "chunks.jsonl"
QUESTIONS_PATH = ROOT / "ai" / "eval" / "questions.jsonl"
REPORT_PATH = ROOT / "ai" / "eval" / "hybrid_report.md"
TOP_K = 3


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate(search, questions):
    stats = defaultdict(lambda: {"n": 0, "r1": 0, "r3": 0, "step_n": 0, "s1": 0, "s3": 0})
    rr_total = 0.0
    rows = []
    for q in questions:
        if not q["answerable"]:
            continue
        hits = search(q["question"], TOP_K)
        metas = [h["metadata"] for h in hits]
        expected = set(q["expected_recipe_ids"])
        r1 = bool(metas) and metas[0]["recipe_id"] in expected
        r3 = any(m["recipe_id"] in expected for m in metas)
        rr = 0.0
        for rank, m in enumerate(metas, 1):
            if m["recipe_id"] in expected:
                rr = 1.0 / rank
                break
        rr_total += rr

        s1 = s3 = None
        if q["expected_step"] is not None:
            s1 = bool(metas) and metas[0]["type"] == "step" and metas[0]["recipe_id"] in expected and metas[0]["step_index"] == q["expected_step"]
            s3 = any(
                m["type"] == "step" and m["recipe_id"] in expected and m["step_index"] == q["expected_step"]
                for m in metas
            )

        st = stats[q["intent"]]
        st["n"] += 1
        st["r1"] += int(r1)
        st["r3"] += int(r3)
        if s3 is not None:
            st["step_n"] += 1
            st["s1"] += int(s1)
            st["s3"] += int(s3)
        rows.append((q, hits, r1, r3, s1, s3))

    n = len(rows)
    step_n = sum(1 for r in rows if r[5] is not None)
    return {
        "n": n,
        "r1": sum(r[2] for r in rows) / max(1, n),
        "r3": sum(r[3] for r in rows) / max(1, n),
        "mrr": rr_total / max(1, n),
        "s1": sum(1 for r in rows if r[4]) / max(1, step_n),
        "s3": sum(1 for r in rows if r[5]) / max(1, step_n),
        "step_n": step_n,
        "by_intent": {k: dict(v) for k, v in stats.items()},
        "rows": rows,
    }


def main():
    chunks = load_jsonl(CHUNKS_PATH)
    questions = load_jsonl(QUESTIONS_PATH)
    bm25 = BM25(chunks)
    hybrid = HybridRetriever(chunks)

    base = evaluate(lambda q, k: bm25.search(q, k), questions)
    hyb = evaluate(lambda q, k: hybrid.search(q, k), questions)

    lines = []
    lines.append("# D3 混合检索报告\n")
    lines.append("## 方法\n")
    lines.append("- 基线：BM25（CJK 二元切分）\n")
    lines.append("- D3：BM25 + 本地字符 2/3-gram TF-IDF embedding，融合权重 0.55 / 0.45\n")
    lines.append("- 查询扩展：蛋液、响边、收汁、焯水、出水等厨艺同义词\n")
    lines.append("- 步骤意图重排：标题/正文覆盖度 + 菜谱锚点加分\n")
    lines.append(f"- 评测：同一套 30 题，top_k={TOP_K}；只统计 24 道可回答题\n")

    lines.append("\n## 总体对比\n")
    lines.append("| 指标 | D1 BM25 | D3 Hybrid | 变化 |\n")
    lines.append("|---|---:|---:|---:|\n")
    def delta(a, b, pct=True):
        d = b - a
        return f"{d:+.1%}" if pct else f"{d:+.3f}"
    lines.append(f"| Recipe Recall@1 | {base['r1']:.1%} | {hyb['r1']:.1%} | {delta(base['r1'], hyb['r1'])} |\n")
    lines.append(f"| Recipe Recall@3 | {base['r3']:.1%} | {hyb['r3']:.1%} | {delta(base['r3'], hyb['r3'])} |\n")
    lines.append(f"| MRR | {base['mrr']:.3f} | {hyb['mrr']:.3f} | {hyb['mrr']-base['mrr']:+.3f} |\n")
    lines.append(f"| 步骤命中率 @1 | {base['s1']:.1%} | {hyb['s1']:.1%} | {delta(base['s1'], hyb['s1'])} |\n")
    lines.append(f"| **步骤命中率 @3** | **{base['s3']:.1%}** | **{hyb['s3']:.1%}** | **{delta(base['s3'], hyb['s3'])}** |\n")

    lines.append("\n## 分类（D3）\n")
    lines.append("| 意图 | 题数 | R@1 | R@3 | 步骤@3 |\n")
    lines.append("|---|---:|---:|---:|---:|\n")
    for intent in ["find_recipe", "step_qa", "scaling", "shopping"]:
        s = hyb["by_intent"][intent]
        step = f"{s['s3']}/{s['step_n']}" if s["step_n"] else "—"
        lines.append(f"| {intent} | {s['n']} | {s['r1']}/{s['n']} | {s['r3']}/{s['n']} | {step} |\n")

    lines.append("\n## 步骤题明细\n")
    lines.append("| 题号 | 问题 | 期望 | D3 Top1 | 步骤@3 |\n")
    lines.append("|---|---|---|---|---|\n")
    for q, hits, r1, r3, s1, s3 in hyb["rows"]:
        if q["intent"] != "step_qa":
            continue
        top = hits[0]["metadata"]
        top_text = f"{top['recipe_name']} {top['type']} {top.get('step_index') or ''}"
        lines.append(f"| {q['id']} | {q['question']} | {q['expected_recipe_ids']} 第{q['expected_step']}步 | {top_text} | {'✓' if s3 else '✗'} |\n")

    failures = [r for r in hyb["rows"] if not r[3] or r[5] is False]
    lines.append("\n## 失败样例\n")
    if failures:
        for q, hits, r1, r3, s1, s3 in failures:
            lines.append(f"### {q['id']} {q['intent']}：{q['question']}\n")
            for h in hits:
                m = h["metadata"]
                lines.append(f"- {h.get('hybrid', h.get('score', 0)):.3f} | {m['recipe_name']} | {m['type']} {m.get('step_index') or ''}\n")
            lines.append("\n")
    else:
        lines.append("无失败样例。\n")

    lines.append("\n## 结论\n")
    lines.append(f"- 步骤命中率 @3：{base['s3']:.1%} → {hyb['s3']:.1%}。\n")
    lines.append(f"- Recipe Recall@1：{base['r1']:.1%} → {hyb['r1']:.1%}。\n")
    lines.append("- 本地 embedding 不是语义模型；它的价值是补足 BM25 对字符重叠/同义表达的盲区。\n")
    lines.append("- 下一步可把 `Embedder` 换成 BGE/OpenAI embedding，接口不变，再用同一套题复测。\n")

    REPORT_PATH.write_text("".join(lines), encoding="utf-8")
    summary = {
        "baseline": {k: base[k] for k in ("r1", "r3", "mrr", "s1", "s3")},
        "hybrid": {k: hyb[k] for k in ("r1", "r3", "mrr", "s1", "s3")},
        "failures": len(failures),
        "by_intent": hyb["by_intent"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
