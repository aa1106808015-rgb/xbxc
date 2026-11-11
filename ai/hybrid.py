#!/usr/bin/env python3
"""D3: hybrid retrieval (BM25 + char n-gram embedding) with step-aware rerank."""
from collections import Counter

from .embeddings import Embedder, char_ngrams
from .retrieval import BM25, load_chunks

STEP_MARKERS = (
    "第", "步", "怎么判断", "什么状态", "为什么", "熟", "出水", "收汁",
    "火候", "程度", "水温", "下锅", "搅", "散", "响边",
)

EXPANSIONS = {
    "蛋液": ["鸡蛋", "搅打", "蛋黄", "打蛋液"],
    "搅": ["搅打", "打蛋液", "蛋黄"],
    "下锅": ["油温", "蛋液", "下锅"],
    "水烧": ["水", "响边", "小泡", "大滚", "水温"],
    "响边": ["小泡", "大滚", "水温"],
    "下肉丸": ["下丸子", "丸子", "散", "水温"],
    "肉丸": ["丸子", "肉馅", "散"],
    "收汁": ["汤汁", "浓稠", "挂", "收汁"],
    "焯": ["焯水", "紧实", "碎", "漏勺"],
    "出水": ["积水", "沥干", "水珠", "出水"],
    "熟": ["粉红", "汁水", "透明", "熟透"],
    "火候": ["油温", "小火", "大火", "火候"],
    "翻面": ["第一面", "金黄", "推动", "翻面"],
    "煎": ["第一面", "第二面", "金黄", "翻面"],
}


def expand_query(query: str) -> str:
    extra = []
    for key, synonyms in EXPANSIONS.items():
        if key in query:
            extra.extend(synonyms)
    if not extra:
        return query
    return query + " " + " ".join(dict.fromkeys(extra))


def is_step_query(query: str) -> bool:
    return any(marker in query for marker in STEP_MARKERS)


def _overlap(query: str, text: str) -> float:
    q = set(char_ngrams(query, (2, 3)))
    if not q:
        return 0.0
    t = set(char_ngrams(text, (2, 3)))
    return len(q & t) / len(q)


class HybridRetriever:
    def __init__(self, chunks=None):
        self.chunks = chunks or load_chunks()
        self.bm25 = BM25(self.chunks)
        self.embedder = Embedder([c["text"] for c in self.chunks])
        self.vectors = [self.embedder.embed(c["text"]) for c in self.chunks]

    def search(self, query: str, k: int = 3):
        expanded = expand_query(query)
        candidates = self.bm25.search(expanded, 25)
        if not candidates:
            return []
        max_bm25 = max(c["score"] for c in candidates) or 1.0
        qv = self.embedder.embed(expanded)

        scored = []
        for cand in candidates:
            idx = next(i for i, c in enumerate(self.chunks) if c["chunk_id"] == cand["chunk_id"])
            cosine = self.embedder.cosine(qv, self.vectors[idx])
            hybrid = 0.55 * (cand["score"] / max_bm25) + 0.45 * cosine
            scored.append({
                **cand,
                "bm25": round(cand["score"], 4),
                "cosine": round(cosine, 4),
                "hybrid": round(hybrid, 4),
            })

        if is_step_query(query):
            anchor = self._anchor_recipe(scored)
            for hit in scored:
                meta = hit["metadata"]
                if meta["type"] != "step":
                    continue
                title_overlap = _overlap(query, meta.get("step_title", ""))
                text_overlap = _overlap(expanded, hit["text"])
                bonus = 0.30 * title_overlap + 0.10 * text_overlap
                if anchor and meta["recipe_id"] == anchor:
                    bonus += 0.10
                hit["hybrid"] = round(hit["hybrid"] + bonus, 4)
                hit["step_bonus"] = round(bonus, 4)
            scored.sort(key=lambda h: (-h["hybrid"], h["chunk_id"]))

        return scored[:k]

    def _anchor_recipe(self, scored):
        for hit in scored:
            if hit["metadata"]["type"] == "recipe":
                return hit["metadata"]["recipe_id"]
        counts = Counter(
            h["metadata"]["recipe_id"]
            for h in scored[:5]
        )
        return counts.most_common(1)[0][0] if counts else None
