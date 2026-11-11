#!/usr/bin/env python3
"""D3 regression tests: the two baseline step failures must be fixed."""
import unittest

from ai.hybrid import HybridRetriever


class HybridStepTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = HybridRetriever()

    def test_q07_egg_step(self):
        hits = self.r.search("炒鸡蛋时，蛋液要搅到什么程度，下锅才不会一块白一块黄？", 3)
        m = hits[0]["metadata"]
        self.assertEqual((m["recipe_id"], m["type"], m["step_index"]), ("fanqie", "step", 2))

    def test_q11_meatball_water(self):
        hits = self.r.search("下肉丸时，水要烧到什么状态才不容易散？", 3)
        m = hits[0]["metadata"]
        self.assertEqual((m["recipe_id"], m["type"], m["step_index"]), ("tang", "step", 4))

    def test_q10_greens_step_in_top3(self):
        hits = self.r.search("青菜下锅前怎么处理，炒的时候才不出水？", 3)
        self.assertTrue(any(
            h["metadata"]["recipe_id"] == "qingcai"
            and h["metadata"]["type"] == "step"
            and h["metadata"]["step_index"] == 1
            for h in hits
        ))


if __name__ == "__main__":
    unittest.main()
