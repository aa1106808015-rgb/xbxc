#!/usr/bin/env python3
"""D2 LLM-mode test with a local OpenAI-compatible mock endpoint."""
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ai.core import answer_question


class MockLLMHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        assert self.path == "/v1/chat/completions", self.path
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        assert payload["model"] == "mock-model"
        body = json.dumps({
            "model": "mock-model",
            "choices": [{"message": {"content": "麻婆豆腐 第 2 步：盐水焯 1 分钟。[C1]"}}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class LLMModeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MockLLMHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        os.environ["LLM_API_KEY"] = "test-key"
        os.environ["LLM_BASE_URL"] = f"http://127.0.0.1:{cls.port}/v1"
        os.environ["LLM_MODEL"] = "mock-model"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        for key in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
            os.environ.pop(key, None)

    def test_llm_mode_and_usage(self):
        r = answer_question("麻婆豆腐的豆腐为什么要先用盐水焯？", use_llm=True, use_tools=False)
        self.assertEqual(r["mode"], "llm")
        self.assertIn("[C1]", r["answer"])
        self.assertEqual(r["usage"]["total_tokens"], 30)
        self.assertEqual(r["citations"][0]["step_index"], 2)


if __name__ == "__main__":
    unittest.main()
