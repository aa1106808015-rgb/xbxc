#!/usr/bin/env python3
"""D4: deterministic tool router for the four recipe tools.

The LLM can later use TOOL_SCHEMAS for function calling; until then this router
makes /chat actually compute portions and shopping lists.
"""
from .tools import (
    RECIPES,
    ToolError,
    build_shopping_list,
    get_step,
    scale_servings,
    search_recipes,
    target_servings,
)

STEP_MARKERS = ("第", "步", "怎么判断", "什么状态", "为什么", "熟", "出水", "收汁", "火候", "程度", "水温", "下锅", "搅", "散")
SHOPPING_MARKERS = ("买", "材料", "食材", "调料", "清单")
SCALING_MARKERS = ("人份", "改做", "改成", "份量", "倍")


def _anchor(hits):
    """Return (recipe_id, citation_index) for the most likely recipe."""
    for i, hit in enumerate(hits, start=1):
        if hit["metadata"]["type"] == "recipe":
            return hit["metadata"]["recipe_id"], i
    for i, hit in enumerate(hits, start=1):
        return hit["metadata"]["recipe_id"], i
    return None, None


def _fmt_scaling(data, cite):
    lines = [
        f"{data['recipe_name']}：{data['base_servings']} → {data['target_servings']} 人份"
        f"（×{data['factor']}）"
    ]
    for item in data["ingredients"]:
        lines.append(f"- {item['name']}：{item['original']} → {item['scaled']}")
    lines.append(data["note"])
    return "\n".join(lines) + f" [{cite}]"


def _fmt_shopping(data, cite):
    lines = []
    for group in data["groups"]:
        lines.append(f"{group['recipe_name']}（{group['servings']} 人份）：")
        for item in group["items"]:
            lines.append(f"- {item['name']}：{item['scaled']}")
    lines.append(data["note"])
    return "\n".join(lines) + f" [{cite}]"


def route_with_tools(question: str, hits):
    """Return a tool-grounded answer, or None when no tool applies."""
    if not hits:
        return None

    rid, cite_index = _anchor(hits)
    cite = f"C{cite_index}"

    if any(k in question for k in SCALING_MARKERS):
        target = target_servings(question)
        if target and rid:
            try:
                data = scale_servings(rid, target)
                return {
                    "answer": _fmt_scaling(data, cite),
                    "tool": "scale_servings",
                    "data": data,
                    "citation_index": cite_index,
                }
            except ToolError:
                pass

    if any(k in question for k in SHOPPING_MARKERS) and rid:
        try:
            found = search_recipes(question, 3)
            ids = []
            for item in found["results"]:
                names = [item["name"]] + RECIPES.get(item["id"], {}).get("aliases", [])
                if any(name in question for name in names):
                    ids.append(item["id"])
            ids = list(dict.fromkeys(ids)) or [rid]
            data = build_shopping_list(ids)
            cite_index = next(
                (i for i, hit in enumerate(hits, start=1) if hit["metadata"]["recipe_id"] == ids[0]),
                cite_index,
            )
            return {
                "answer": _fmt_shopping(data, f"C{cite_index}"),
                "tool": "build_shopping_list",
                "data": data,
                "citation_index": cite_index,
            }
        except ToolError:
            pass

    if any(k in question for k in STEP_MARKERS):
        for i, hit in enumerate(hits, start=1):
            meta = hit["metadata"]
            if meta["type"] == "step":
                try:
                    data = get_step(meta["recipe_id"], meta["step_index"])
                    answer = (
                        f"{data['recipe_name']} 第 {data['step_index']} 步「{data['title']}」："
                        f"{data['text']} 判断标准：{data['check']} [C{i}]"
                    )
                    return {
                        "answer": answer,
                        "tool": "get_step",
                        "data": data,
                        "citation_index": i,
                    }
                except ToolError:
                    break

    if rid:
        # find_recipe: actually call the search tool, then cite the matching hit
        data = search_recipes(question, 1)
        if not data["results"]:
            return None
        top = data["results"][0]
        for i, hit in enumerate(hits, start=1):
            if hit["metadata"]["recipe_id"] == top["id"]:
                cite_index = i
                cite = f"C{i}"
                break
        answer = (
            f"推荐「{top['name']}」：{top.get('why', '')} "
            f"时间 {top.get('time', '')}，份量 {top.get('servings', '')}。[{cite}]"
        )
        return {
            "answer": answer,
            "tool": "search_recipes",
            "data": data,
            "citation_index": cite_index,
        }

    return None
