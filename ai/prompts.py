"""Prompt v1: grounded recipe assistant with explicit citation labels."""

SYSTEM_PROMPT = """你是「小白学菜」的菜谱助手，服务对象是完全没有下过厨的新手。

规则：
1. 只能依据下面给出的菜谱片段回答，不要用模型常识补菜谱里没有的步骤、用量或判断标准。
2. 每个关键结论后面标注来源，例如 [C1]；引用必须来自给定片段，不要编造编号。
3. 如果片段不足以回答，直接说「菜谱里没有找到依据」，并建议用户换个问法或回到菜谱页。
4. 不提供医疗、过敏安全保证、营养热量、电器维修等菜谱范围外的结论。
5. 回答用中文，短句，先给结论，再给判断标准或步骤；不要写“根据上下文”这类空话。
6. 涉及份量换算时，只说明按比例缩放；具体数字由工具计算，不要心算后编造。
"""


def build_context(hits):
    blocks = []
    for i, hit in enumerate(hits, start=1):
        meta = hit["metadata"]
        if meta["type"] == "step":
            kind = f"步骤 {meta['step_index']}"
        elif meta["type"] == "ingredients":
            kind = "用料清单"
        else:
            kind = "菜谱概览"
        blocks.append(
            f"[C{i}] 菜谱：{meta['recipe_name']}｜{kind}\n{hit['text']}"
        )
    return "\n\n".join(blocks)


def build_messages(question: str, hits):
    context = build_context(hits)
    user = (
        f"用户问题：{question}\n\n"
        f"可用菜谱片段：\n{context}\n\n"
        "请只根据以上片段回答；每个关键结论标注 [C1] 这样的来源编号。"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
