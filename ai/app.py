#!/usr/bin/env python3
"""D2 FastAPI service: POST /chat (non-streaming) + GET /health.

Run:
  uvicorn ai.app:app --reload --port 8000
"""
import json
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .core import answer_question, stream_answer
from .llm import llm_status
from .security import RateLimiter, origin_allowed
from .tools import TOOL_SCHEMAS

app = FastAPI(title="小白学菜 AI 助手", version="0.2.0")

_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://127.0.0.1:8765,http://localhost:8765,http://127.0.0.1:5500,http://localhost:5500",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_LIMITER = RateLimiter(int(os.getenv("RATE_LIMIT_PER_MINUTE", "30")), 60)


@app.middleware("http")
async def security_guard(request: Request, call_next):
    if request.url.path in ("/chat", "/chat/stream"):
        origin = request.headers.get("origin")
        if origin and not origin_allowed(origin):
            return JSONResponse({"error": "origin not allowed"}, status_code=403)
        key = request.client.host if request.client else "unknown"
        allowed, retry_after = _LIMITER.allow(key)
        if not allowed:
            return JSONResponse(
                {"error": "too many requests"},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
    return await call_next(request)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(3, ge=1, le=5)
    use_tools: bool = True
    history: list[dict] = Field(default_factory=list)


@app.get("/health")
def health():
    status = llm_status()
    return {
        "ok": True,
        "service": "xbxc-ai",
        "llm_configured": status["configured"],
        "model": status["model"],
        "base_url": status["base_url"],
    }


@app.get("/tools")
def tools():
    return {"tools": TOOL_SCHEMAS}


@app.post("/chat")
def chat(req: ChatRequest):
    result = answer_question(req.message, top_k=req.top_k, use_llm=True, use_tools=req.use_tools)
    return {
        "answer": result["answer"],
        "citations": result["citations"],
        "mode": result["mode"],
        "tool": result.get("tool", ""),
        "prompt_version": result.get("prompt_version", ""),
        "usage": result.get("usage", {}),
        "warning": result.get("warning", ""),
    }


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    def generate():
        for event, payload in stream_answer(req.message, top_k=req.top_k, use_tools=req.use_tools):
            yield _sse(event, payload)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
