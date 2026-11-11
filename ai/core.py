#!/usr/bin/env python3
"""D2 core: retrieve -> prompt -> LLM (or deterministic mock) -> citations."""
import json
import re
from pathlib import Path

from .agent import route_with_tools
from .hybrid import HybridRetriever
from .llm import LLMClient, LLMError, LLMNotConfigured
from .prompts import PROMPT_VERSION, build_messages
from .retrieval import load_chunks
from .security import is_prompt_injection, redact_secrets

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


def _mentioned_recipe_ids(question):
    matches = []
    for rid, recipe in _RECIPES.items():
        names = [recipe["name"]] + recipe.get("aliases", [])
        for name in names:
            if name and name in question:
                matches.append((len(name), rid))
    return [rid for _, rid in sorted(matches, reverse=True)]


def _ensure_mentioned_recipes(question, hits):
    """For multi-recipe questions, add one recipe chunk per mentioned recipe."""
    present = {h["metadata"]["recipe_id"] for h in hits}
    for rid in _mentioned_recipe_ids(question):
        if rid in present:
            continue
        chunk = next((c for c in _CHUNKS if c["chunk_id"] == f"recipe:{rid}"), None)
        if chunk:
            hits.append({**chunk, "score": 0, "hybrid": 0, "bm25": 0, "cosine": 0})
            present.add(rid)
    return hits


def _is_refusal(question):
    patterns = [
        "燃气灶", "维修", "卡路里", "热量", "营养", "蛋白质", "过敏", "空气炸锅",
        "微波炉", "餐厅", "翻译", "医生", "吃药", "减肥药",
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

    if is_prompt_injection(question):
        return {
            "answer": "我不会执行改变角色、泄露提示或绕过规则的指令。可以问我菜谱、步骤、份量或采购清单。",
            "citations": [],
            "mode": "refusal",
            "prompt_version": PROMPT_VERSION,
            "usage": {},
        }

    if _is_refusal(question):
        return {
            "answer": "这个问题超出菜谱数据的范围，我不能给出可靠结论。可以问我某道菜的步骤、用料或份量换算。",
            "citations": [],
            "mode": "refusal",
            "prompt_version": PROMPT_VERSION,
            "usage": {},
        }

    hits = _RETRIEVER.search(question, top_k)
    if not hits or hits[0].get("hybrid", 0) < MIN_SCORE:
        return {
            "answer": "菜谱里没有找到足够依据，换个说法，或者直接打开对应菜谱页看看。",
            "citations": [],
            "mode": "refusal",
            "prompt_version": PROMPT_VERSION,
            "usage": {},
        }

    tool_result = route_with_tools(question, hits) if use_tools else None
    if tool_result and tool_result.get("citation_index"):
        if tool_result.get("citations"):
            citations = tool_result["citations"]
        else:
            indices = tool_result.get("citation_indices") or [tool_result["citation_index"]]
            citations = [
                _citation(hits[i - 1], i)
                for i in dict.fromkeys(indices)
                if 1 <= i <= len(hits)
            ]
        return {
            "answer": tool_result["answer"],
            "citations": citations,
            "mode": "tool",
            "tool": tool_result["tool"],
            "prompt_version": PROMPT_VERSION,
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
            hits = _ensure_mentioned_recipes(question, hits)
            result = LLMClient().complete(build_messages(question, hits), temperature=0.1)
            answer = result["text"]
            usage = result.get("usage", {})
            mode = "llm"
            cited_ids = {int(x) for x in re.findall(r"\[C(\d+)\]", answer)}
        except (LLMNotConfigured, LLMError) as exc:
            warning = redact_secrets(str(exc))
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
        "prompt_version": PROMPT_VERSION,
        "usage": usage,
        "warning": warning,
    }


def _result_events(result):
    """Turn a full result into the D5 SSE event sequence."""
    yield "meta", {
        "mode": result.get("mode", ""),
        "tool": result.get("tool", ""),
        "prompt_version": result.get("prompt_version", PROMPT_VERSION),
    }
    yield "citations", {"citations": result.get("citations", [])}
    answer = result.get("answer", "")
    for i in range(0, len(answer), 8):
        yield "token", {"text": answer[i:i + 8]}
    yield "done", {
        "mode": result.get("mode", ""),
        "tool": result.get("tool", ""),
        "warning": result.get("warning", ""),
    }


def stream_answer(question: str, top_k: int = 3, use_tools: bool = True):
    """SSE-ready event generator.

    Tool/refusal answers are deterministic and chunked. When a real LLM is
    configured, free-form answers stream token-by-token from the provider.
    """
    question = (question or "").strip()
    if not question:
        raise ValueError("question is empty")

    base = answer_question(question, top_k=top_k, use_llm=False, use_tools=use_tools)
    if base.get("mode") in ("tool", "refusal") or not LLMClient().configured:
        yield from _result_events(base)
        return

    hits = _RETRIEVER.search(question, top_k)
    hits = _ensure_mentioned_recipes(question, hits)
    yield "meta", {"mode": "llm", "tool": "", "prompt_version": PROMPT_VERSION}
    yield "citations", {"citations": [_citation(hit, i) for i, hit in enumerate(hits, start=1)]}

    emitted = []
    try:
        for delta in LLMClient().stream_complete(
            build_messages(question, hits),
            temperature=0.1,
        ):
            emitted.append(delta)
            yield "token", {"text": delta}
        yield "done", {"mode": "llm", "tool": "", "warning": ""}
    except (LLMNotConfigured, LLMError) as exc:
        if emitted:
            yield "done", {"mode": "llm", "tool": "", "warning": str(exc)}
            return
        fallback = answer_question(question, top_k=top_k, use_llm=False, use_tools=use_tools)
        yield "citations", {"citations": fallback.get("citations", [])}
        for i in range(0, len(fallback.get("answer", "")), 8):
            yield "token", {"text": fallback["answer"][i:i + 8]}
        yield "done", {"mode": "mock", "tool": "", "warning": str(exc)}
