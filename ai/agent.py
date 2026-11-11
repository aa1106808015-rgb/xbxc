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
FIND_MARKERS = ("吃", "喝", "做", "推荐", "菜", "饿", "晚饭", "午饭", "早餐", "请客", "快手", "清淡", "减脂", "一锅出", "凉菜", "汤", "食材", "冰箱", "家里有")


def _anchor(hits):
    """Return (recipe_id, citation_index) for the most likely recipe."""
    for i, hit in enumerate(hits, start=1):
        if hit["metadata"]["type"] == "recipe":
            return hit["metadata"]["recipe_id"], i
    for i, hit in enumerate(hits, start=1):
        return hit["metadata"]["recipe_id"], i
    return None, None


def _mentioned_recipe(question):
    """Prefer an explicitly named recipe/alias over the top retrieval hit."""
    matches = []
    for rid, recipe in RECIPES.items():
        names = [recipe["name"]] + recipe.get("aliases", [])
        for name in names:
            if name and name in question:
                matches.append((len(name), rid))
    return max(matches)[1] if matches else None


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
        recipe_id = _mentioned_recipe(question) or rid
        if target and recipe_id:
            try:
                data = scale_servings(recipe_id, target)
                cite_index = next(
                    (i for i, hit in enumerate(hits, start=1) if hit["metadata"]["recipe_id"] == recipe_id),
                    cite_index,
                )
                return {
                    "answer": _fmt_scaling(data, f"C{cite_index}"),
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
            citation_indices = []
            for item_id in ids:
                found_index = next(
                    (i for i, hit in enumerate(hits, start=1) if hit["metadata"]["recipe_id"] == item_id),
                    None,
                )
                if found_index:
                    citation_indices.append(found_index)
            if not citation_indices:
                citation_indices = [cite_index]
            citations = []
            for i, group in enumerate(data["groups"], start=1):
                recipe = RECIPES.get(group["recipe_id"], {})
                citations.append({
                    "id": f"C{i}",
                    "chunk_id": f"recipe:{group['recipe_id']}",
                    "recipe_id": group["recipe_id"],
                    "recipe_name": group["recipe_name"],
                    "type": "recipe",
                    "step_index": None,
                    "title": group["recipe_name"],
                    "url": recipe.get("url", ""),
                    "score": 0,
                })
            return {
                "answer": _fmt_shopping(data, f"C{citation_indices[0]}"),
                "tool": "build_shopping_list",
                "data": data,
                "citations": citations,
                "citation_index": citation_indices[0],
                "citation_indices": citation_indices,
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

    if rid and any(k in question for k in FIND_MARKERS):
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
