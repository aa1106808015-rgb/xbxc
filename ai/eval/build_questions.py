#!/usr/bin/env python3
"""D1: build the 30-question retrieval evaluation set.

30 questions = 5 intents x 6:
find_recipe, step_qa, scaling, shopping, refusal.
Only answerable questions are scored for retrieval in D1; refusal is for the LLM stage.
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ai" / "eval" / "questions.jsonl"

QUESTIONS = [
    # ---------- find_recipe (6) ----------
    dict(id="Q01", intent="find_recipe", question="冰箱里只剩两个西红柿和三个鸡蛋，晚上一个人吃，15 分钟能做什么？",
         answerable=True, expected_recipe_ids=["fanqie"], expected_step=None,
         reference_answer="番茄炒蛋：番茄 + 鸡蛋，15 分钟，2 人份。", notes="食材 + 时间；用别名“西红柿”"),
    dict(id="Q02", intent="find_recipe", question="不想开火，想做个凉菜，家里有黄瓜和木耳",
         answerable=True, expected_recipe_ids=["liangban"], expected_step=None,
         reference_answer="黄瓜拌木耳：凉菜，10 分钟，1–2 人份。", notes="同义表达：不想开火=凉菜"),
    dict(id="Q03", intent="find_recipe", question="下班晚，想用电饭煲一锅出，有腊肠和香菇",
         answerable=True, expected_recipe_ids=["menfan"], expected_step=None,
         reference_answer="电饭煲腊肠焖饭：一锅出，40 分钟。", notes="厨具 + 食材"),
    dict(id="Q04", intent="find_recipe", question="想喝清淡的汤，家里有冬瓜和肉末",
         answerable=True, expected_recipe_ids=["tang"], expected_step=None,
         reference_answer="冬瓜丸子汤：清淡汤品，30 分钟，3 人份。", notes="汤 + 食材"),
    dict(id="Q05", intent="find_recipe", question="减脂期，想要高蛋白、20 分钟内能做的鸡肉",
         answerable=True, expected_recipe_ids=["jixiong"], expected_step=None,
         reference_answer="香煎鸡胸肉：高蛋白/减脂，20 分钟。", notes="目标 + 时间"),
    dict(id="Q06", intent="find_recipe", question="想请客，做一道甜咸口味的鸡翅",
         answerable=True, expected_recipe_ids=["jichi"], expected_step=None,
         reference_answer="可乐鸡翅：甜咸口，35 分钟，适合请客。", notes="场景 + 口味"),

    # ---------- step_qa (6) ----------
    dict(id="Q07", intent="step_qa", question="炒鸡蛋时，蛋液要搅到什么程度，下锅才不会一块白一块黄？",
         answerable=True, expected_recipe_ids=["fanqie"], expected_step=2,
         reference_answer="蛋液里没有整块蛋黄，提起来是流畅的一条线；水不用多，小半勺。", notes="步骤 2，间接描述"),
    dict(id="Q08", intent="step_qa", question="豆腐先用盐水焯一下，是为了什么？",
         answerable=True, expected_recipe_ids=["mapo"], expected_step=2,
         reference_answer="盐水焯 1 分钟，让豆腐紧实一点、不容易碎；用漏勺轻托捞出。", notes="步骤 2 目的"),
    dict(id="Q09", intent="step_qa", question="鸡翅收汁到什么时候该关火？",
         answerable=True, expected_recipe_ids=["jichi"], expected_step=6,
         reference_answer="锅铲划过锅底能留下清晰痕迹，汤汁浓稠发亮，颜色红棕不是黑棕。", notes="步骤 6 判断标准"),
    dict(id="Q10", intent="step_qa", question="青菜下锅前怎么处理，炒的时候才不出水？",
         answerable=True, expected_recipe_ids=["qingcai"], expected_step=1,
         reference_answer="洗菜后甩干并用厨房纸吸掉水珠，盆底无积水、叶面无大颗水珠。", notes="步骤 1 关键点"),
    dict(id="Q11", intent="step_qa", question="下肉丸时，水要烧到什么状态才不容易散？",
         answerable=True, expected_recipe_ids=["tang"], expected_step=4,
         reference_answer="烧到锅边冒小泡、有轻微响声但中间平静（响边），再转小火。", notes="步骤 4 水温"),
    dict(id="Q12", intent="step_qa", question="煎鸡胸肉怎么确认最厚的地方已经熟透？",
         answerable=True, expected_recipe_ids=["jixiong"], expected_step=6,
         reference_answer="关火盖盖焖 2 分钟；开盖表面微泛透明汁水，最厚处无粉红、汁水清澈。", notes="步骤 6 判断标准"),

    # ---------- scaling (6) ----------
    dict(id="Q13", intent="scaling", question="番茄炒蛋是 2 人份，我想做 4 人份，鸡蛋要几个？",
         answerable=True, expected_recipe_ids=["fanqie"], expected_step=None,
         reference_answer="鸡蛋 3 个 → 6 个（2 倍），其余按比例；需要 scale_servings 计算。", notes="2→4 人份"),
    dict(id="Q14", intent="scaling", question="三人份的冬瓜肉丸汤，改做两人份，肉末要减多少？",
         answerable=True, expected_recipe_ids=["tang"], expected_step=None,
         reference_answer="按 2/3 缩放；肉末、冬瓜、淀粉等按比例，需要工具计算。", notes="3→2 人份"),
    dict(id="Q15", intent="scaling", question="两人份的麻婆豆腐，改做三人份，豆瓣酱要加多少？",
         answerable=True, expected_recipe_ids=["mapo"], expected_step=None,
         reference_answer="按 1.5 倍缩放；豆瓣酱等按比例，需要工具计算。", notes="2→3 人份"),
    dict(id="Q16", intent="scaling", question="两人份的可乐鸡翅，改做四人份，可乐和生抽怎么调？",
         answerable=True, expected_recipe_ids=["jichi"], expected_step=None,
         reference_answer="按 2 倍缩放；可乐、生抽等按比例，需要工具计算。", notes="2→4 人份"),
    dict(id="Q17", intent="scaling", question="一人份的腊肠焖饭，改做两人份，米和水怎么变？",
         answerable=True, expected_recipe_ids=["menfan"], expected_step=None,
         reference_answer="米和水按 2 倍；注意电饭煲容量，需要工具计算。", notes="1→2 人份"),
    dict(id="Q18", intent="scaling", question="两人份的拍黄瓜，改做三人份，料汁比例怎么调？",
         answerable=True, expected_recipe_ids=["huanggua"], expected_step=None,
         reference_answer="按 1.5 倍；盐、生抽、醋、糖按比例，需要工具计算。", notes="2→3 人份"),

    # ---------- shopping (6) ----------
    dict(id="Q19", intent="shopping", question="做麻婆豆腐要买哪些材料？",
         answerable=True, expected_recipe_ids=["mapo"], expected_step=None,
         reference_answer="嫩豆腐、猪肉末、郫县豆瓣酱、蒜/姜、淀粉/花椒粉、生抽/糖/小葱。", notes="用料清单"),
    dict(id="Q20", intent="shopping", question="可乐鸡翅的采购清单是什么？",
         answerable=True, expected_recipe_ids=["jichi"], expected_step=None,
         reference_answer="鸡翅中、可乐、姜、料酒、生抽、食用油/白芝麻。", notes="用料清单"),
    dict(id="Q21", intent="shopping", question="冬瓜丸子汤需要哪些食材？",
         answerable=True, expected_recipe_ids=["tang"], expected_step=None,
         reference_answer="冬瓜、猪肉末、姜、小葱、淀粉、盐/白胡椒粉。", notes="用料清单"),
    dict(id="Q22", intent="shopping", question="腊肠焖饭要买什么？",
         answerable=True, expected_recipe_ids=["menfan"], expected_step=None,
         reference_answer="大米、广式腊肠、干香菇、胡萝卜、生抽、食用油/小葱。", notes="用料清单"),
    dict(id="Q23", intent="shopping", question="凉拌木耳黄瓜的调料有哪些？",
         answerable=True, expected_recipe_ids=["liangban"], expected_step=None,
         reference_answer="大蒜、生抽、香醋、白糖/香油。", notes="调料子集"),
    dict(id="Q24", intent="shopping", question="香煎鸡胸肉用哪些调料？",
         answerable=True, expected_recipe_ids=["jixiong"], expected_step=None,
         reference_answer="盐、黑胡椒、生抽、食用油。", notes="调料子集"),

    # ---------- refusal (6) ----------
    dict(id="Q25", intent="refusal", question="帮我修一下家里的燃气灶",
         answerable=False, expected_recipe_ids=[], expected_step=None,
         reference_answer="超出菜谱范围，应明确拒答。", notes="无关领域"),
    dict(id="Q26", intent="refusal", question="番茄炒蛋有多少卡路里？",
         answerable=False, expected_recipe_ids=[], expected_step=None,
         reference_answer="菜谱数据没有营养数据，应说明未覆盖。", notes="数据未覆盖"),
    dict(id="Q27", intent="refusal", question="用空气炸锅做可乐鸡翅要多少度？",
         answerable=False, expected_recipe_ids=[], expected_step=None,
         reference_answer="现有菜谱是煎锅做法，没有空气炸锅参数，应说明未覆盖。", notes="做法未覆盖"),
    dict(id="Q28", intent="refusal", question="我对花生过敏，麻婆豆腐能吃吗？",
         answerable=False, expected_recipe_ids=[], expected_step=None,
         reference_answer="菜谱没有过敏原数据，不能保证安全，应建议核对配料/咨询专业人士。", notes="安全边界"),
    dict(id="Q29", intent="refusal", question="推荐一家附近的餐厅",
         answerable=False, expected_recipe_ids=[], expected_step=None,
         reference_answer="超出菜谱范围，应拒答。", notes="无关领域"),
    dict(id="Q30", intent="refusal", question="把这道菜翻译成英文",
         answerable=False, expected_recipe_ids=[], expected_step=None,
         reference_answer="MVP 不做翻译，应说明范围。", notes="能力边界"),
]


EXTRA_QUESTIONS = [
    dict(id="Q31", intent="find_recipe", question="家里有鸡翅和可乐，想做一个甜咸口的硬菜",
         answerable=True, expected_recipe_ids=["jichi"], expected_step=None,
         reference_answer="可乐鸡翅：甜咸口，35 分钟，适合请客。", notes="食材 + 口味"),
    dict(id="Q32", intent="find_recipe", question="想喝清淡的汤，最好 30 分钟内，有冬瓜和肉末",
         answerable=True, expected_recipe_ids=["tang"], expected_step=None,
         reference_answer="冬瓜丸子汤：清淡汤品，30 分钟。", notes="时间 + 食材"),
    dict(id="Q33", intent="step_qa", question="麻婆豆腐勾芡时，淀粉水分几次淋？",
         answerable=True, expected_recipe_ids=["mapo"], expected_step=5,
         reference_answer="分两次淋入，汤汁变亮、能挂在豆腐上，没有白色淀粉疙瘩。", notes="步骤 5 细节"),
    dict(id="Q34", intent="step_qa", question="煎鸡胸肉翻面时，怎么判断可以翻了？",
         answerable=True, expected_recipe_ids=["jixiong"], expected_step=4,
         reference_answer="贴锅一面金黄、能整块推动；铲不动就再等 30 秒。", notes="步骤 4 判断标准"),
    dict(id="Q35", intent="scaling", question="麻婆豆腐 2 人份改 4 人份，嫩豆腐要几盒？",
         answerable=True, expected_recipe_ids=["mapo"], expected_step=None,
         reference_answer="2 盒（约 800 克），按 2 倍；用工具计算。", notes="2→4 人份"),
    dict(id="Q36", intent="scaling", question="可乐鸡翅 2 人份改 6 人份，鸡翅要几个？",
         answerable=True, expected_recipe_ids=["jichi"], expected_step=None,
         reference_answer="24 个（8 个 × 3），用工具计算。", notes="2→6 人份"),
    dict(id="Q37", intent="shopping", question="番茄炒蛋和麻婆豆腐一起买什么？",
         answerable=True, expected_recipe_ids=["fanqie", "mapo"], expected_step=None,
         reference_answer="番茄炒蛋 + 麻婆豆腐两份采购清单。", notes="多菜采购"),
    dict(id="Q38", intent="shopping", question="凉拌黄瓜的辣椒油是必买还是可选？",
         answerable=True, expected_recipe_ids=["huanggua"], expected_step=None,
         reference_answer="辣椒油标注为可选，不是必买。", notes="optional 字段"),
    dict(id="Q39", intent="refusal", question="帮我算一下这顿饭的蛋白质含量",
         answerable=False, expected_recipe_ids=[], expected_step=None,
         reference_answer="菜谱没有营养数据，应说明未覆盖。", notes="营养数据未覆盖"),
    dict(id="Q40", intent="refusal", question="用微波炉做麻婆豆腐要几分钟？",
         answerable=False, expected_recipe_ids=[], expected_step=None,
         reference_answer="现有菜谱是锅灶做法，没有微波炉参数，应说明未覆盖。", notes="做法未覆盖"),
]


def main() -> None:
    assert len(QUESTIONS) == 30
    assert len(EXTRA_QUESTIONS) == 10
    all_questions = QUESTIONS + EXTRA_QUESTIONS
    counts = Counter(q["intent"] for q in all_questions)
    assert counts == {"find_recipe": 8, "step_qa": 8, "scaling": 8, "shopping": 8, "refusal": 8}, counts
    assert sum(q["answerable"] for q in all_questions) == 32
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for q in QUESTIONS:
            fh.write(json.dumps(q, ensure_ascii=False) + "\n")
    out40 = OUT.with_name("questions40.jsonl")
    with out40.open("w", encoding="utf-8") as fh:
        for q in all_questions:
            fh.write(json.dumps(q, ensure_ascii=False) + "\n")
    print(f"wrote {OUT} questions={len(QUESTIONS)}")
    print(f"wrote {out40} questions={len(all_questions)} answerable={sum(q['answerable'] for q in all_questions)}")
    print(dict(counts))


if __name__ == "__main__":
    main()
