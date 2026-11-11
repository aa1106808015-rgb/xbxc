#!/usr/bin/env python3
"""D2 smoke tests for the no-LLM mock path. No external dependencies."""
import unittest

from ai.core import answer_question


class ChatCoreTest(unittest.TestCase):
    def ask(self, q):
        return answer_question(q, use_llm=False)

    def test_find_recipe(self):
        r = self.ask("冰箱里只剩两个西红柿和三个鸡蛋，15 分钟能做什么？")
        self.assertIn("番茄", r["answer"])
        self.assertTrue(r["citations"])
        self.assertEqual(r["mode"], "tool")
        self.assertEqual(r["tool"], "search_recipes")

    def test_step_question_cites_step(self):
        r = self.ask("麻婆豆腐的豆腐为什么要先用盐水焯？")
        self.assertIn("第 2 步", r["answer"])
        self.assertEqual(r["tool"], "get_step")
        self.assertTrue(any(c["type"] == "step" and c["step_index"] == 2 for c in r["citations"]))

    def test_shopping_list(self):
        r = self.ask("做麻婆豆腐要买哪些材料？")
        self.assertIn("嫩豆腐", r["answer"])
        self.assertEqual(r["tool"], "build_shopping_list")
        self.assertTrue(r["citations"])

    def test_scaling_computes(self):
        r = self.ask("两人份的番茄鸡蛋，改做四人份，鸡蛋要几个？")
        self.assertIn("6 个", r["answer"])
        self.assertIn("2 → 4 人份", r["answer"])
        self.assertEqual(r["tool"], "scale_servings")
        self.assertTrue(r["citations"])

    def test_refusal_has_no_citations(self):
        r = self.ask("帮我修一下家里的燃气灶")
        self.assertEqual(r["mode"], "refusal")
        self.assertEqual(r["citations"], [])
        self.assertIn("超出菜谱", r["answer"])

    def test_citation_shape(self):
        r = self.ask("麻婆豆腐的豆腐为什么要先焯水？")
        self.assertTrue(r["citations"])
        c = r["citations"][0]
        for key in ("id", "chunk_id", "recipe_id", "recipe_name", "url"):
            self.assertIn(key, c)
        self.assertTrue(c["url"].startswith("recipes/"))


if __name__ == "__main__":
    unittest.main()
