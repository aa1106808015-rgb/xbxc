#!/usr/bin/env python3
"""D1: export the JS recipe data to a clean JSON file for the AI layer."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "recipes.js"
OUT = ROOT / "ai" / "data" / "recipes.json"


def main() -> None:
    src = SRC.read_text(encoding="utf-8")
    match = re.search(r"window\.XIAOBAI_RECIPES\s*=\s*(\[.*\]);?\s*$", src, re.S)
    if not match:
        raise SystemExit("Cannot find window.XIAOBAI_RECIPES in data/recipes.js")
    recipes = json.loads(match.group(1))

    dishes = len(recipes)
    steps = sum(len(r["steps"]) for r in recipes)
    ingredients = sum(len(r["ingredients"]) for r in recipes)
    if (dishes, steps, ingredients) != (9, 55, 51):
        raise SystemExit(
            f"Unexpected counts: dishes={dishes}, steps={steps}, ingredients={ingredients}"
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(recipes, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"dishes={dishes} steps={steps} ingredients={ingredients}")


if __name__ == "__main__":
    main()
