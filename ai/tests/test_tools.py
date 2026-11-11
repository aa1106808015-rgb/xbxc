#!/usr/bin/env python3
"""D4 tool tests: search / step / scaling / shopping list."""
import unittest

from ai.tools import (
    TOOL_SCHEMAS,
    ToolError,
    build_shopping_list,
    get_step,
    scale_servings,
    search_recipes,
    target_servings,
)


class ToolTest(unittest.TestCase):
    def test_scale_fanqie_to_four(self):
        r = scale_servings("fanqie", 4)
        self.assertEqual(r["base_servings"], 2)
        self.assertEqual(r["target_servings"], 4)
        self.assertEqual(r["factor"], 2.0)
        by_name = {i["name"]: i for i in r["ingredients"]}
        self.assertEqual(by_name["鸡蛋"]["scaled"], "6 个")
        self.assertEqual(by_name["番茄"]["scaled"], "4 个（约 600 克）")
        self.assertEqual(by_name["白糖"]["scaled"], "1 – 2 小勺")

    def test_scale_tang_down(self):
        r = scale_servings("tang", 2)
        by_name = {i["name"]: i for i in r["ingredients"]}
        self.assertEqual(r["factor"], 0.667)
        self.assertEqual(by_name["冬瓜"]["scaled"], "270 克（去皮后）")
        self.assertEqual(by_name["小葱"]["scaled"], "1.5 根")

    def test_target_servings(self):
        self.assertEqual(target_servings("两人份的番茄鸡蛋，改做四人份"), 4)
        self.assertEqual(target_servings("3 人份改成 2 人份"), 2)

    def test_shopping_list_groups(self):
        r = build_shopping_list(["mapo", "fanqie"], {"mapo": 3, "fanqie": 4})
        self.assertEqual(r["recipe_count"], 2)
        self.assertEqual(r["item_count"], 12)
        self.assertEqual(r["groups"][0]["servings"], 3)
        self.assertEqual(r["groups"][0]["recipe_name"], "麻婆豆腐")

    def test_get_step(self):
        r = get_step("mapo", 2)
        self.assertEqual(r["step_index"], 2)
        self.assertIn("盐水", r["title"])
        self.assertIn("完整", r["check"])

    def test_search_recipes(self):
        r = search_recipes("番茄鸡蛋", 1)
        self.assertEqual(r["results"][0]["id"], "fanqie")

    def test_invalid_recipe(self):
        with self.assertRaises(ToolError):
            scale_servings("nope", 2)
        with self.assertRaises(ToolError):
            get_step("mapo", 99)

    def test_tool_schemas(self):
        names = {t["name"] for t in TOOL_SCHEMAS}
        self.assertEqual(names, {"search_recipes", "get_step", "scale_servings", "build_shopping_list"})


if __name__ == "__main__":
    unittest.main()
