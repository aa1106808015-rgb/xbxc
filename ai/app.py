#!/usr/bin/env python3
"""D2 FastAPI service: POST /chat (non-streaming) + GET /health.

Run:
  uvicorn ai.app:app --reload --port 8000
"""
import asyncio
import json
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .core import answer_question
from .llm import llm_status
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


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(3, ge=1, le=5)
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
    result = answer_question(req.message, top_k=req.top_k, use_llm=True)
    return {
        "answer": result["answer"],
        "citations": result["citations"],
        "mode": result["mode"],
        "tool": result.get("tool", ""),
        "usage": result.get("usage", {}),
        "warning": result.get("warning", ""),
    }


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    result = answer_question(req.message, top_k=req.top_k, use_llm=True)

    async def generate():
        yield _sse("meta", {"mode": result.get("mode", ""), "tool": result.get("tool", "")})
        yield _sse("citations", {"citations": result.get("citations", [])})
        answer = result.get("answer", "")
        for i in range(0, len(answer), 8):
            yield _sse("token", {"text": answer[i:i + 8]})
            await asyncio.sleep(0.012)
        yield _sse("done", {"mode": result.get("mode", ""), "tool": result.get("tool", "")})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
