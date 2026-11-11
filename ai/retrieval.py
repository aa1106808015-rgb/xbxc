#!/usr/bin/env python3
"""Small BM25 retriever shared by the D2 service and smoke tests."""
import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = ROOT / "ai" / "data" / "chunks.jsonl"

K1 = 1.5
B = 0.75


def load_chunks(path: Path = CHUNKS_PATH):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def tokenize(text: str):
    """CJK character bigrams + ASCII words, no tokenizer dependency."""
    text = text.lower()
    ascii_tokens = re.findall(r"[a-z0-9]+", text)
    chars = "".join(re.findall(r"[\u4e00-\u9fff]", text))
    bigrams = [chars[i:i + 2] for i in range(max(0, len(chars) - 1))]
    return ascii_tokens + bigrams


class BM25:
    def __init__(self, chunks):
        self.chunks = chunks
        self.doc_tokens = [tokenize(c["text"]) for c in chunks]
        self.doc_len = [len(t) for t in self.doc_tokens]
        self.avgdl = sum(self.doc_len) / max(1, len(self.doc_len))
        self.tf = [Counter(t) for t in self.doc_tokens]
        df = Counter()
        for tokens in self.doc_tokens:
            df.update(set(tokens))
        n = len(chunks)
        self.idf = {
            term: math.log(1 + (n - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

    def score(self, query: str, index: int):
        q = Counter(tokenize(query))
        tf = self.tf[index]
        dl = self.doc_len[index]
        total = 0.0
        for term, qf in q.items():
            if term not in tf:
                continue
            freq = tf[term]
            denom = freq + K1 * (1 - B + B * dl / max(1e-9, self.avgdl))
            total += self.idf.get(term, 0.0) * (freq * (K1 + 1) / denom) * qf
        return total

    def search(self, query: str, k: int = 3):
        scored = [(self.score(query, i), i) for i in range(len(self.chunks))]
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [
            {"score": score, **self.chunks[i]}
            for score, i in scored[:k]
        ]
