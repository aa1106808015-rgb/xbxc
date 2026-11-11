#!/usr/bin/env python3
"""D6 prompt v2 contract tests."""
import unittest

from ai.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_messages


class PromptV2Test(unittest.TestCase):
    def test_version(self):
        self.assertEqual(PROMPT_VERSION, "v2")

    def test_rules_present(self):
        for phrase in ("只能依据", "菜谱里没有找到依据", "[C1]", "最多引用 3 个"):
            self.assertIn(phrase, SYSTEM_PROMPT)

    def test_messages_include_context_and_question(self):
        hits = [{
            "text": "番茄炒蛋 第 2 步：打蛋液",
            "metadata": {"type": "step", "step_index": 2, "recipe_name": "番茄炒蛋"},
        }]
        messages = build_messages("蛋液怎么打？", hits)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("[C1]", messages[1]["content"])
        self.assertIn("蛋液怎么打", messages[1]["content"])


if __name__ == "__main__":
    unittest.main()
