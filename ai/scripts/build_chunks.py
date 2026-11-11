#!/usr/bin/env python3
"""D1: turn recipes into small retrieval chunks (recipe / step / ingredient list)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "ai" / "data" / "recipes.json"
OUT = ROOT / "ai" / "data" / "chunks.jsonl"


def ingredient_text(recipe: dict) -> str:
    lines = []
    for item in recipe["ingredients"]:
        lines.append(f"- {item['name']} {item['amount']}（{item['why']}）")
    return "\n".join(lines)


def main() -> None:
    recipes = json.loads(SRC.read_text(encoding="utf-8"))
    chunks = []

    for recipe in recipes:
        meta = {
            "recipe_id": recipe["id"],
            "recipe_name": recipe["name"],
            "url": recipe["url"],
            "level": recipe["level"],
            "tags": recipe["tags"],
        }

        recipe_text = (
            f"{recipe['name']}\n"
            f"别名：{'、'.join(recipe.get('aliases', []))}\n"
            f"标签：{'、'.join(recipe['tags'])}\n"
            f"难度：{recipe['difficulty']}；时间：{recipe['time']}；份量：{recipe['servings']}；成本：{recipe['cost']}\n"
            f"导语：{recipe['lead']}\n"
            f"用料：\n{ingredient_text(recipe)}"
        )
        chunks.append(
            {
                "chunk_id": f"recipe:{recipe['id']}",
                "text": recipe_text,
                "metadata": {**meta, "type": "recipe", "step_index": None},
            }
        )

        for index, step in enumerate(recipe["steps"], start=1):
            step_text = (
                f"{recipe['name']} 第 {index} 步：{step['title']}\n"
                f"做法：{step['text']}\n"
                f"判断标准：{step['check']}\n"
                f"时间：{step['time']}"
            )
            chunks.append(
                {
                    "chunk_id": f"step:{recipe['id']}:{index}",
                    "text": step_text,
                    "metadata": {
                        **meta,
                        "type": "step",
                        "step_index": index,
                        "step_title": step["title"],
                    },
                }
            )

        chunks.append(
            {
                "chunk_id": f"ingredients:{recipe['id']}",
                "text": f"{recipe['name']} 用料清单\n{ingredient_text(recipe)}",
                "metadata": {**meta, "type": "ingredients", "step_index": None},
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    print(f"wrote {OUT} chunks={len(chunks)}")
    print(f"recipe={sum(c['metadata']['type']=='recipe' for c in chunks)} "
          f"step={sum(c['metadata']['type']=='step' for c in chunks)} "
          f"ingredients={sum(c['metadata']['type']=='ingredients' for c in chunks)}")


if __name__ == "__main__":
    main()
