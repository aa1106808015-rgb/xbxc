#!/usr/bin/env python3
"""D7 security helpers: origin allowlist, rate limit, injection guard, redaction."""
import os
import re
import threading
import time
from collections import defaultdict, deque

DEFAULT_ORIGINS = "http://127.0.0.1:8765,http://localhost:8765,http://127.0.0.1:5500,http://localhost:5500"

INJECTION_PATTERNS = (
    "忽略之前", "忽略以上", "忽略所有指令", "忽略规则", "ignore previous",
    "ignore all previous", "system prompt", "系统提示", "开发者模式", "developer mode",
    "jailbreak", "越狱", "打印你的提示", "泄露提示", "reveal your prompt",
    "act as", "你现在是", "绕过规则", "bypass",
)


def allowed_origins():
    raw = os.getenv("ALLOWED_ORIGINS", DEFAULT_ORIGINS)
    return {item.strip() for item in raw.split(",") if item.strip()}


def origin_allowed(origin: str) -> bool:
    """No Origin (curl/server-to-server) is allowed; browser origins must be allowlisted."""
    if not origin:
        return True
    return origin in allowed_origins()


def is_prompt_injection(text: str) -> bool:
    lowered = (text or "").lower()
    return any(p.lower() in lowered for p in INJECTION_PATTERNS)


_SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_-]{6,}|Bearer\s+[A-Za-z0-9._-]{8,})")


def redact_secrets(text: str) -> str:
    return _SECRET_RE.sub("sk-***", text or "")


class RateLimiter:
    """Tiny in-memory sliding-window limiter (per process)."""

    def __init__(self, limit: int = 30, window_seconds: int = 60):
        self.limit = max(1, int(limit))
        self.window = max(1, int(window_seconds))
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str):
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.limit:
                retry = max(1, int(self.window - (now - q[0])))
                return False, retry
            q.append(now)
            return True, 0
