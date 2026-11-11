#!/usr/bin/env python3
"""Minimal OpenAI-compatible chat client (stdlib only).

Works with DeepSeek / OpenAI-compatible endpoints:
  LLM_API_KEY=...
  LLM_BASE_URL=https://api.deepseek.com
  LLM_MODEL=deepseek-chat
"""
import json
import os
import urllib.error
import urllib.request
from pathlib import Path


def _load_dotenv():
    """Load ai/.env (preferred), then repo-root .env. Existing env wins."""
    here = Path(__file__).resolve().parent
    candidates = [here / ".env", here.parent / ".env"]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


class LLMNotConfigured(RuntimeError):
    pass


class LLMError(RuntimeError):
    pass


def _first_env(*names):
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return ""


def _endpoint(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


class LLMClient:
    def __init__(self):
        self.api_key = _first_env("LLM_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY")
        self.base_url = _first_env("LLM_BASE_URL") or "https://api.deepseek.com"
        self.model = _first_env("LLM_MODEL") or "deepseek-chat"
        self.timeout = float(os.getenv("LLM_TIMEOUT", "30"))

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def complete(self, messages, temperature=0.2, max_tokens=600) -> dict:
        if not self.api_key:
            raise LLMNotConfigured("LLM_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY is not set")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        req = urllib.request.Request(
            _endpoint(self.base_url),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise LLMError(f"LLM HTTP {exc.code}: {body}") from exc
        except Exception as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Unexpected LLM response shape") from exc
        return {
            "text": content.strip(),
            "usage": data.get("usage", {}),
            "model": data.get("model", self.model),
        }

    def stream_complete(self, messages, temperature=0.1, max_tokens=600):
        """Yield content deltas from an OpenAI-compatible streaming response."""
        if not self.api_key:
            raise LLMNotConfigured("LLM_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY is not set")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        req = urllib.request.Request(
            _endpoint(self.base_url),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "text/event-stream",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                for raw in resp:
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    try:
                        delta = obj["choices"][0].get("delta", {}).get("content", "")
                    except (KeyError, IndexError, TypeError):
                        continue
                    if delta:
                        yield delta
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise LLMError(f"LLM HTTP {exc.code}: {body}") from exc
        except Exception as exc:
            raise LLMError(f"LLM stream failed: {exc}") from exc


def llm_status() -> dict:
    client = LLMClient()
    return {
        "configured": client.configured,
        "base_url": client.base_url,
        "model": client.model,
    }
