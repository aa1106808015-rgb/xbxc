#!/usr/bin/env python3
"""Offline embedding layer for D3.

Default is a local character n-gram TF-IDF embedder: no model download, no API
key, works on the 73 recipe chunks. The `Embedder` interface is intentionally
small so a BGE / OpenAI-compatible embedding provider can replace it later.
"""
import math
import re
from collections import Counter


def char_ngrams(text: str, sizes=(2, 3)):
    text = text.lower()
    tokens = re.findall(r"[a-z0-9]+", text)
    chars = "".join(re.findall(r"[\u4e00-\u9fff]", text))
    for n in sizes:
        tokens.extend(chars[i:i + n] for i in range(max(0, len(chars) - n + 1)))
    return tokens


class LocalCharNgramEmbedder:
    """TF-IDF over CJK 2/3-grams + ASCII words; vectors are L2-normalized dicts."""

    def __init__(self):
        self.idf = {}
        self.dim = 0

    def fit(self, docs):
        df = Counter()
        for doc in docs:
            df.update(set(char_ngrams(doc)))
        n = max(1, len(docs))
        self.idf = {term: math.log((n + 1) / (freq + 1)) + 1.0 for term, freq in df.items()}
        self.dim = len(self.idf)
        return self

    def embed(self, text: str):
        counts = Counter(char_ngrams(text))
        vec = {}
        for term, tf in counts.items():
            idf = self.idf.get(term)
            if idf:
                vec[term] = (1.0 + math.log(tf)) * idf
        norm = math.sqrt(sum(v * v for v in vec.values()))
        if norm:
            for term in vec:
                vec[term] /= norm
        return vec

    @staticmethod
    def cosine(a, b):
        if len(a) > len(b):
            a, b = b, a
        return sum(v * b.get(k, 0.0) for k, v in a.items())


class Embedder:
    """Facade; swap the implementation for a real API/model later."""

    def __init__(self, docs):
        self.impl = LocalCharNgramEmbedder().fit(docs)

    def embed(self, text):
        return self.impl.embed(text)

    def cosine(self, a, b):
        return self.impl.cosine(a, b)
