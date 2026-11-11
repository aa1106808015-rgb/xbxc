#!/usr/bin/env python3
"""D2 core: retrieve -> prompt -> LLM (or deterministic mock) -> citations."""
import json
import re
from pathlib import Path

from .agent import route_with_tools
from .hybrid import HybridRetriever
from .llm import LLMClient, LLMError, LLMNotConfigured
from .prompts import build_messages
from .retrieval import load_chunks

ROOT = Path(__file__).resolve().parents[1]
RECIPES_PATH = ROOT / "ai" / "data" / "recipes.json"

_CHUNKS = load_chunks()
_RECIPES = {r["id"]: r for r in json.loads(RECIPES_PATH.read_text(encoding="utf-8"))}
_RETRIEVER = HybridRetriever(_CHUNKS)

MIN_SCORE = 0.18


def _kind(meta):
    if meta["type"] == "step":
        return "步骤"
    if meta["type"] == "ingredients":
        return "用料"
    return "菜谱"


def _citation(hit, index):
    meta = hit["metadata"]
    return {
        "id": f"C{index}",
        "chunk_id": hit["chunk_id"],
        "recipe_id": meta["recipe_id"],
        "recipe_name": meta["recipe_name"],
        "type": meta["type"],
        "step_index": meta.get("step_index"),
        "title": meta.get("step_title") or meta["recipe_name"],
        "url": meta["url"],
        "score": round(hit["score"], 3),
    }


def _ingredient_names(recipe_id):
    recipe = _RECIPES.get(recipe_id)
    if not recipe:
        return []
    return [i["name"] for i in recipe["ingredients"]]


def _is_refusal(question):
    patterns = [
        "燃气灶", "维修", "卡路里", "热量", "营养", "过敏", "空气炸锅",
        "餐厅", "翻译", "医生", "吃药", "减肥药",
    ]
    return any(p in question for p in patterns)


def _mock_answer(question, hits):
    top = hits[0]
    meta = top["metadata"]
    recipe = _RECIPES.get(meta["recipe_id"], {})
    cite = "C1"

    if any(k in question for k in ("人份", "改做", "改成", "份量", "倍")):
        return (
            f"「{meta['recipe_name']}」可以按目标份量等比缩放；"
            f"具体数字请查看菜谱用量，或确认目标份量后让我计算。[{cite}]"
        )

    step_pairs = [(i, h) for i, h in enumerate(hits, start=1) if h["metadata"]["type"] == "step"]
    step_hit = step_pairs[0][1] if step_pairs else None
    if step_hit and any(k in question for k in ("第", "步", "怎么判断", "什么状态", "为什么", "熟", "出水", "收汁", "火候")):
        cite = f"C{step_pairs[0][0]}"
        m = step_hit["metadata"]
        r = _RECIPES.get(m["recipe_id"], {})
        step = r.get("steps", [])[m["step_index"] - 1] if r else {}
        return (
            f"{m['recipe_name']} 第 {m['step_index']} 步「{m.get('step_title', '')}」："
            f"{step.get('text', '')} 判断标准：{step.get('check', '')} [{cite}]"
            if step else f"找到 {m['recipe_name']} 的第 {m['step_index']} 步，但步骤正文缺失。[{cite}]"
        )

    if any(k in question for k in ("买", "材料", "食材", "调料", "清单")):
        names = "、".join(_ingredient_names(meta["recipe_id"]))
        return f"「{meta['recipe_name']}」需要：{names}。[{cite}]"

    if top["metadata"]["type"] == "step":
        m = top["metadata"]
        r = _RECIPES.get(m["recipe_id"], {})
        step = r.get("steps", [])[m["step_index"] - 1] if r else {}
        return f"{m['recipe_name']} 第 {m['step_index']} 步：{step.get('text', '')} [{cite}]"

    lead = recipe.get("lead", "")
    return (
        f"推荐「{meta['recipe_name']}」：{lead} "
        f"时间 {recipe.get('time', '')}，份量 {recipe.get('servings', '')}。[{cite}]"
    )


def answer_question(question: str, top_k: int = 3, use_llm: bool = True, use_tools: bool = True) -> dict:
    question = (question or "").strip()
    if not question:
        raise ValueError("question is empty")

    if _is_refusal(question):
        return {
            "answer": "这个问题超出菜谱数据的范围，我不能给出可靠结论。可以问我某道菜的步骤、用料或份量换算。",
            "citations": [],
            "mode": "refusal",
            "usage": {},
        }

    hits = _RETRIEVER.search(question, top_k)
    if not hits or hits[0].get("hybrid", 0) < MIN_SCORE:
        return {
            "answer": "菜谱里没有找到足够依据，换个说法，或者直接打开对应菜谱页看看。",
            "citations": [],
            "mode": "refusal",
            "usage": {},
        }

    tool_result = route_with_tools(question, hits) if use_tools else None
    if tool_result and tool_result.get("citation_index"):
        idx = tool_result["citation_index"]
        return {
            "answer": tool_result["answer"],
            "citations": [_citation(hits[idx - 1], idx)],
            "mode": "tool",
            "tool": tool_result["tool"],
            "data": tool_result.get("data"),
            "usage": {},
            "warning": "",
        }

    mode = "mock"
    usage = {}
    warning = ""
    cited_ids = set()
    answer = ""

    if use_llm and LLMClient().configured:
        try:
            result = LLMClient().complete(build_messages(question, hits))
            answer = result["text"]
            usage = result.get("usage", {})
            mode = "llm"
            cited_ids = {int(x) for x in re.findall(r"\[C(\d+)\]", answer)}
        except (LLMNotConfigured, LLMError) as exc:
            warning = str(exc)
            answer = ""
            mode = "mock"

    if not answer:
        answer = _mock_answer(question, hits)
        cited_ids = {int(x) for x in re.findall(r"\[C(\d+)\]", answer)}

    if not cited_ids:
        cited_ids = {1}

    citations = [
        _citation(hit, i)
        for i, hit in enumerate(hits, start=1)
        if i in cited_ids and i <= len(hits)
    ]
    if not citations and hits:
        citations = [_citation(hits[0], 1)]
    return {
        "answer": answer,
        "citations": citations,
        "mode": mode,
        "usage": usage,
        "warning": warning,
    }
