#!/usr/bin/env python3
"""D2 zero-dependency dev server (stdlib only).

The FastAPI app in ai/app.py is the target implementation. This server lets
you test /chat immediately on a machine where FastAPI/uvicorn are not installed.

Run:
  python -m ai.dev_server --port 8000
"""
import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .core import answer_question
from .llm import llm_status
from .tools import TOOL_SCHEMAS


class Handler(BaseHTTPRequestHandler):
    server_version = "XiaobaiAI/0.3"
    protocol_version = "HTTP/1.1"

    def _send(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
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
        path = self.path.split("?")[0].rstrip("/")
        if path not in ("/chat", "/chat/stream"):
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            message = str(payload.get("message", "")).strip()
            if not message:
                raise ValueError("message is empty")
            if len(message) > 500:
                raise ValueError("message is too long (max 500)")
            result = answer_question(
                message,
                top_k=int(payload.get("top_k", 3)),
                use_llm=True,
            )
            if path == "/chat/stream":
                self._stream_result(result)
                return
            self._send(200, {
                "answer": result["answer"],
                "citations": result["citations"],
                "mode": result["mode"],
                "tool": result.get("tool", ""),
                "usage": result.get("usage", {}),
                "warning": result.get("warning", ""),
            })
        except (ValueError, json.JSONDecodeError) as exc:
            self._send(400, {"error": str(exc)})
        except Exception as exc:  # keep the dev server alive
            self._send(500, {"error": f"internal error: {exc}"})

    def _stream_result(self, result):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.close_connection = True

        def event(name, payload):
            data = json.dumps(payload, ensure_ascii=False)
            self.wfile.write(f"event: {name}\ndata: {data}\n\n".encode("utf-8"))
            self.wfile.flush()

        try:
            event("meta", {"mode": result.get("mode", ""), "tool": result.get("tool", "")})
            event("citations", {"citations": result.get("citations", [])})
            answer = result.get("answer", "")
            for i in range(0, len(answer), 8):
                event("token", {"text": answer[i:i + 8]})
                time.sleep(0.012)
            event("done", {"mode": result.get("mode", ""), "tool": result.get("tool", "")})
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
