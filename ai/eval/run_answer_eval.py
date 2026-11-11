#!/usr/bin/env python3
"""D6: answer-level evaluation on 40 questions.

Checks the tool-grounded path by default (no API key needed):
- citation present / correct recipe / correct step / coverage
- refusal behavior for out-of-scope questions

Run:
  python -m ai.eval.run_answer_eval
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from ai.core import answer_question

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS_PATH = ROOT / "ai" / "eval" / "questions40.jsonl"


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate(questions, use_llm=False, use_tools=True):
    rows = []
    stats = defaultdict(lambda: {"n": 0, "answers": 0, "citation_ok": 0, "refusal_n": 0, "refusal_ok": 0})
    for q in questions:
        r = answer_question(q["question"], use_llm=use_llm, use_tools=use_tools)
        expected = set(q["expected_recipe_ids"])
        cites = r.get("citations", [])
        cited_ids = [c["recipe_id"] for c in cites]
        precision = (sum(1 for c in cited_ids if c in expected) / len(cited_ids)) if cited_ids else 0.0
        coverage = len(set(cited_ids) & expected) / len(expected) if expected else 0.0

        if q["answerable"]:
            step_ok = True
            if q["expected_step"] is not None:
                step_ok = any(
                    c.get("type") == "step"
                    and c.get("recipe_id") in expected
                    and c.get("step_index") == q["expected_step"]
                    for c in cites
                )
            citation_ok = bool(cites) and precision == 1.0 and coverage == 1.0 and step_ok
            st = stats[q["intent"]]
            st["n"] += 1
            st["answers"] += 1
            st["citation_ok"] += int(citation_ok)
            rows.append({
                "q": q, "r": r, "citation_ok": citation_ok,
                "precision": precision, "coverage": coverage, "step_ok": step_ok,
            })
        else:
            refusal_ok = r.get("mode") == "refusal" and not cites
            st = stats[q["intent"]]
            st["n"] += 1
            st["refusal_n"] += 1
            st["refusal_ok"] += int(refusal_ok)
            rows.append({"q": q, "r": r, "refusal_ok": refusal_ok})

    answer_rows = [r for r in rows if "citation_ok" in r]
    refusal_rows = [r for r in rows if "refusal_ok" in r]
    llm_rows = [r for r in answer_rows if r["r"].get("mode") == "llm"]
    return {
        "rows": rows,
        "stats": {k: dict(v) for k, v in stats.items()},
        "citation_accuracy": sum(r["citation_ok"] for r in answer_rows) / max(1, len(answer_rows)),
        "citation_precision": sum(r["precision"] for r in answer_rows) / max(1, len(answer_rows)),
        "citation_coverage": sum(r["coverage"] for r in answer_rows) / max(1, len(answer_rows)),
        "llm_citation_accuracy": sum(r["citation_ok"] for r in llm_rows) / max(1, len(llm_rows)),
        "llm_answers": len(llm_rows),
        "refusal_rate": sum(r["refusal_ok"] for r in refusal_rows) / max(1, len(refusal_rows)),
        "answerable": len(answer_rows),
        "refusal": len(refusal_rows),
        "modes": dict(Counter(r["r"].get("mode", "") for r in rows)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", action="store_true", help="用真实 LLM 回答，并关闭工具路由；需要 LLM_API_KEY")
    args = parser.parse_args()
    use_llm = args.llm
    use_tools = not args.llm

    questions = load_jsonl(QUESTIONS_PATH)
    assert len(questions) == 40, len(questions)
    result = evaluate(questions, use_llm=use_llm, use_tools=use_tools)
    report_path = ROOT / "ai" / "eval" / ("answer_report_llm.md" if use_llm else "answer_report.md")

    lines = []
    lines.append("# D6 回答级评测报告（40 题）\n")
    lines.append("## 口径\n")
    lines.append(f"- 运行模式：`use_llm={use_llm}`，`use_tools={use_tools}`。\n")
    if not use_llm:
        lines.append("- 走工具/拒答的确定路径，不需要 API Key。\n")
        lines.append("- 这评的是工具/路由与引用格式，不是第三方 LLM 的生成质量。\n")
    else:
        lines.append("- 真实 LLM 回答，工具路由关闭；需要配置 LLM_API_KEY。\n")
    lines.append("- 引用正确：引用存在、所有引用菜谱都在期望集合内、覆盖全部期望菜谱；步骤题还要求引用命中正确步骤。\n")
    lines.append("- 拒答正确：`mode=\"refusal\"` 且没有引用。\n")

    lines.append("\n## 总体\n")
    lines.append(f"- 可回答题：{result['answerable']} 道\n")
    lines.append(f"- 拒答题：{result['refusal']} 道\n")
    lines.append(f"- **引用正确率**：{result['citation_accuracy']:.1%}\n")
    lines.append(f"- **引用精确率**：{result['citation_precision']:.1%}\n")
    lines.append(f"- **引用覆盖率**：{result['citation_coverage']:.1%}\n")
    lines.append(f"- **拒答率**：{result['refusal_rate']:.1%}\n")
    lines.append(f"- 模式分布：{result['modes']}\n")
    if use_llm:
        lines.append(f"- **真实 LLM 引用正确率**：{result['llm_citation_accuracy']:.1%}（{result['llm_answers']}/{result['answerable']} 道实际走 LLM）\n")

    lines.append("\n## 分类\n")
    lines.append("| 意图 | 题数 | 引用正确 | 拒答正确 |\n")
    lines.append("|---|---:|---:|---:|\n")
    for intent in ["find_recipe", "step_qa", "scaling", "shopping", "refusal"]:
        s = result["stats"][intent]
        cite = f"{s['citation_ok']}/{s['answers']}" if s["answers"] else "—"
        ref = f"{s['refusal_ok']}/{s['refusal_n']}" if s["refusal_n"] else "—"
        lines.append(f"| {intent} | {s['n']} | {cite} | {ref} |\n")

    failures = [r for r in result["rows"] if not (r.get("citation_ok") or r.get("refusal_ok"))]
    lines.append("\n## 失败样例\n")
    if failures:
        for r in failures:
            q, a = r["q"], r["r"]
            lines.append(f"### {q['id']} {q['intent']}：{q['question']}\n")
            lines.append(f"- 期望：{q['expected_recipe_ids']} 第 {q['expected_step']} 步；可回答={q['answerable']}\n")
            lines.append(f"- 实际：mode={a.get('mode')}；引用={[(c.get('recipe_id'), c.get('type'), c.get('step_index')) for c in a.get('citations', [])]}\n")
            lines.append(f"- 回答：{a.get('answer', '')[:240]}\n\n")
    else:
        lines.append("无失败样例。\n")

    lines.append("\n## Prompt v2\n")
    lines.append("- 版本号：`v2`；规则见 `ai/prompts.py`。\n")
    lines.append("- 加强：强制引用、无依据拒答、最多 3 个引用、含糊问题只追问一次、禁止暴露内部工具名。\n")

    report_path.write_text("".join(lines), encoding="utf-8")
    print(json.dumps({
        "questions": len(questions),
        "answerable": result["answerable"],
        "refusal": result["refusal"],
        "citation_accuracy": round(result["citation_accuracy"], 4),
        "citation_precision": round(result["citation_precision"], 4),
        "citation_coverage": round(result["citation_coverage"], 4),
        "llm_citation_accuracy": round(result["llm_citation_accuracy"], 4),
        "llm_answers": result["llm_answers"],
        "refusal_rate": round(result["refusal_rate"], 4),
        "modes": result["modes"],
        "failures": len(failures),
    }, ensure_ascii=False, indent=2))
    print(f"wrote {report_path}")


if __name__ == "__main__":
    main()
