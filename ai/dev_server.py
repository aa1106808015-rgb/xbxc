#!/usr/bin/env python3
"""D2 zero-dependency dev server (stdlib only).

The FastAPI app in ai/app.py is the target implementation. This server lets
you test /chat immediately on a machine where FastAPI/uvicorn are not installed.

Run:
  python -m ai.dev_server --port 8000
"""
import argparse
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .core import answer_question, stream_answer
from .llm import llm_status
from .security import RateLimiter, origin_allowed
from .tools import TOOL_SCHEMAS

LIMITER = RateLimiter(int(os.getenv("RATE_LIMIT_PER_MINUTE", "30")), 60)


class Handler(BaseHTTPRequestHandler):
    server_version = "XiaobaiAI/0.4"
    protocol_version = "HTTP/1.1"

    def _cors_origin(self):
        origin = self.headers.get("Origin", "")
        if origin and not origin_allowed(origin):
            return None
        return origin or ""

    def _send(self, status, payload, headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        origin = self._cors_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        origin = self._cors_origin()
        if origin is None:
            self._send(403, {"error": "origin not allowed"})
            return
        self.send_response(204)
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        if self._cors_origin() is None:
            self._send(403, {"error": "origin not allowed"})
            return
        if self.path.rstrip("/") in ("/health", ""):
            status = llm_status()
            self._send(200, {
                "ok": True,
                "service": "xbxc-ai",
                "llm_configured": status["configured"],
                "model": status["model"],
                "base_url": status["base_url"],
            })
            return
        if self.path.rstrip("/") == "/tools":
            self._send(200, {"tools": TOOL_SCHEMAS})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if self._cors_origin() is None:
            self._send(403, {"error": "origin not allowed"})
            return
        path = self.path.split("?")[0].rstrip("/")
        if path not in ("/chat", "/chat/stream"):
            self._send(404, {"error": "not found"})
            return
        allowed, retry_after = LIMITER.allow(self.client_address[0])
        if not allowed:
            self._send(429, {"error": "too many requests"}, {"Retry-After": str(retry_after)})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            message = str(payload.get("message", "")).strip()
            if not message:
                raise ValueError("message is empty")
            if len(message) > 500:
                raise ValueError("message is too long (max 500)")
            top_k = int(payload.get("top_k", 3))
            use_tools = bool(payload.get("use_tools", True))
            if path == "/chat/stream":
                self._stream_events(stream_answer(message, top_k=top_k, use_tools=use_tools))
                return
            result = answer_question(message, top_k=top_k, use_llm=True, use_tools=use_tools)
            self._send(200, {
                "answer": result["answer"],
                "citations": result["citations"],
                "mode": result["mode"],
                "tool": result.get("tool", ""),
                "prompt_version": result.get("prompt_version", ""),
                "usage": result.get("usage", {}),
                "warning": result.get("warning", ""),
            })
        except (ValueError, json.JSONDecodeError) as exc:
            self._send(400, {"error": str(exc)})
        except Exception as exc:  # keep the dev server alive
            self._send(500, {"error": f"internal error: {exc}"})

    def _stream_events(self, events):
        origin = self._cors_origin()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.close_connection = True

        def event(name, payload):
            data = json.dumps(payload, ensure_ascii=False)
            self.wfile.write(f"event: {name}\ndata: {data}\n\n".encode("utf-8"))
            self.wfile.flush()

        try:
            for name, payload in events:
                event(name, payload)
                if name == "token":
                    time.sleep(0.012)
        except (BrokenPipeError, ConnectionResetError):
            return

    def log_message(self, fmt, *args):
        print("[ai] " + fmt % args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"xbxc-ai listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
