#!/usr/bin/env python3
"""D4 tools: search_recipes / get_step / scale_servings / build_shopping_list.

The recipe amounts are free text, so scaling parses numbers in the text and
marks the result as approximate. No LLM is involved here.
"""
import json
import math
import re
from pathlib import Path

from .hybrid import HybridRetriever
from .retrieval import load_chunks

ROOT = Path(__file__).resolve().parents[1]
RECIPES_PATH = ROOT / "ai" / "data" / "recipes.json"

RECIPES = {r["id"]: r for r in json.loads(RECIPES_PATH.read_text(encoding="utf-8"))}
_RETRIEVER = HybridRetriever(load_chunks())


class ToolError(ValueError):
    pass


# ---------- servings ----------

_CN_NUM = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def parse_number(token: str) -> int:
    if token.isdigit():
        return int(token)
    if token in _CN_NUM:
        return _CN_NUM[token]
    raise ToolError(f"不认识的数字：{token}")


def base_servings(recipe: dict) -> int:
    text = recipe["servings"]
    m = re.search(r"(\d+)\s*[–\-]\s*(\d+)\s*人份", text)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*人份", text)
    if m:
        return int(m.group(1))
    raise ToolError(f"无法解析份量：{text}")


def target_servings(question: str):
    values = [parse_number(x) for x in re.findall(r"(\d+|[一二两三四五六七八九十])\s*人份", question)]
    if not values:
        return None
    return values[-1]


# ---------- amount scaling ----------

_NUM_RE = re.compile(r"(\d+)\s*/\s*(\d+)|\d+(?:\.\d+)?")


def _fmt(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    if abs(value * 2 - round(value * 2)) < 1e-6:
        return f"{value:.1f}"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _round_to(value: float, step: float) -> float:
    return math.floor(value / step + 0.5) * step


def _polish_amount(text: str) -> str:
    """Make scaled numbers readable: 267 g, 1.5 roots, 0.75 spoon."""
    text = re.sub(r"(?<=\d)(?=[\u4e00-\u9fff])", " ", text)

    def repl(m):
        num = float(m.group(1))
        unit = m.group(2)
        if unit in ("克", "毫升"):
            if num >= 100:
                num = _round_to(num, 10)
            elif num >= 10:
                num = _round_to(num, 5)
            else:
                num = _round_to(num, 0.5)
        elif unit in ("个", "根", "瓣", "片", "朵", "盒", "罐", "块", "小块", "杯", "汤匙", "小勺"):
            num = _round_to(num, 0.25) if num < 1 else _round_to(num, 0.5)
        return f"{_fmt(num)} {unit}"

    return re.sub(
        r"(\d+(?:\.\d+)?)\s*(克|毫升|个|根|瓣|片|朵|盒|罐|小块|块|杯|汤匙|小勺)",
        repl,
        text,
    )


def scale_amount_text(amount: str, factor: float) -> str:
    if not factor or abs(factor - 1) < 1e-9:
        return amount
    text = amount.replace("半", "__HALF__")

    def repl(m):
        if m.group(1):
            value = int(m.group(1)) / int(m.group(2))
        else:
            value = float(m.group())
        return _fmt(value * factor)

    text = _NUM_RE.sub(repl, text)
    text = text.replace("__HALF__", _fmt(0.5 * factor))
    return _polish_amount(text)


def scale_servings(recipe_id: str, target: int = None) -> dict:
    if recipe_id not in RECIPES:
        raise ToolError(f"没有这道菜：{recipe_id}")
    recipe = RECIPES[recipe_id]
    base = base_servings(recipe)
    target = base if target is None else int(target)
    if target <= 0 or target > 20:
        raise ToolError("目标份量需在 1–20 人份之间")
    factor = target / base
    items = []
    warnings = []
    for item in recipe["ingredients"]:
        scaled = scale_amount_text(item["amount"], factor)
        if scaled == item["amount"] and not re.search(r"\d|半", item["amount"]):
            warnings.append(f"{item['name']} 是「{item['amount']}」，没有可缩放数字，保持原样")
        items.append({
            "name": item["name"],
            "original": item["amount"],
            "scaled": scaled,
        })
    return {
        "recipe_id": recipe_id,
        "recipe_name": recipe["name"],
        "base_servings": base,
        "target_servings": target,
        "factor": round(factor, 3),
        "ingredients": items,
        "warnings": warnings,
        "note": "用量原文是自由文本，数字按比例估算；“适量/几滴/可选”不缩放，咸淡请尝味调整。",
    }


# ---------- tools ----------

def search_recipes(query: str, limit: int = 3) -> dict:
    if not query.strip():
        raise ToolError("query is empty")
    limit = max(1, min(int(limit), 5))
    hits = _RETRIEVER.search(query, limit * 4)
    seen = set()
    results = []
    for hit in hits:
        meta = hit["metadata"]
        rid = meta["recipe_id"]
        if rid in seen:
            continue
        seen.add(rid)
        recipe = RECIPES.get(rid, {})
        results.append({
            "id": rid,
            "name": meta["recipe_name"],
            "time": recipe.get("time", ""),
            "servings": recipe.get("servings", ""),
            "url": meta["url"],
            "why": recipe.get("lead", ""),
        })
        if len(results) >= limit:
            break
    return {"query": query, "results": results}


def get_step(recipe_id: str, step_index: int = None) -> dict:
    if recipe_id not in RECIPES:
        raise ToolError(f"没有这道菜：{recipe_id}")
    recipe = RECIPES[recipe_id]
    steps = recipe["steps"]
    if step_index is None:
        return {
            "recipe_id": recipe_id,
            "recipe_name": recipe["name"],
            "steps": [
                {"index": i, "title": s["title"], "time": s["time"]}
                for i, s in enumerate(steps, start=1)
            ],
        }
    step_index = int(step_index)
    if step_index < 1 or step_index > len(steps):
        raise ToolError(f"{recipe['name']} 只有 1–{len(steps)} 步")
    step = steps[step_index - 1]
    return {
        "recipe_id": recipe_id,
        "recipe_name": recipe["name"],
        "step_index": step_index,
        "total_steps": len(steps),
        "title": step["title"],
        "text": step["text"],
        "check": step["check"],
        "time": step["time"],
        "url": recipe["url"],
    }


def build_shopping_list(recipe_ids, servings_map=None) -> dict:
    if isinstance(recipe_ids, str):
        recipe_ids = [recipe_ids]
    recipe_ids = list(dict.fromkeys(recipe_ids))
    if not recipe_ids:
        raise ToolError("至少给一个 recipe_id")
    servings_map = servings_map or {}
    groups = []
    item_count = 0
    for rid in recipe_ids:
        target = servings_map.get(rid)
        scaled = scale_servings(rid, target)
        groups.append({
            "recipe_id": rid,
            "recipe_name": scaled["recipe_name"],
            "servings": scaled["target_servings"],
            "items": scaled["ingredients"],
        })
        item_count += len(scaled["ingredients"])
    return {
        "groups": groups,
        "recipe_count": len(groups),
        "item_count": item_count,
        "note": "按菜谱分组列出；同名食材没有跨菜合并，避免单位不同误加。",
    }


TOOL_SCHEMAS = [
    {
        "name": "search_recipes",
        "description": "按食材、时间、口味或场景找菜；返回菜谱 id、名称、时间、份量。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_step",
        "description": "读取某道菜的第 N 步，包含做法、判断标准、时间。",
        "parameters": {
            "type": "object",
            "properties": {
                "recipe_id": {"type": "string"},
                "step_index": {"type": "integer", "minimum": 1},
            },
            "required": ["recipe_id", "step_index"],
        },
    },
    {
        "name": "scale_servings",
        "description": "把一道菜的用量按目标份量等比缩放；返回每一条用料的原文与缩放值。",
        "parameters": {
            "type": "object",
            "properties": {
                "recipe_id": {"type": "string"},
                "target_servings": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["recipe_id", "target_servings"],
        },
    },
    {
        "name": "build_shopping_list",
        "description": "按菜谱生成采购清单；可选传入每道菜的目标份量。",
        "parameters": {
            "type": "object",
            "properties": {
                "recipe_ids": {"type": "array", "items": {"type": "string"}},
                "servings_map": {"type": "object", "additionalProperties": {"type": "integer"}},
            },
            "required": ["recipe_ids"],
        },
    },
]
