import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import BaseModel, Field

from bot.core.bot import SupportBot

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _build_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY is not set")
        sys.exit(1)
    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


_client: Optional[OpenAI] = None
_model: Optional[str] = None
_judge_model: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _client, _model, _judge_model
    _client = _build_client()
    _model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
    _judge_model = os.environ.get("JUDGE_MODEL", _model)
    logger.info("AcmeCorp Support Bot API started. Model=%s JudgeModel=%s", _model, _judge_model)
    yield
    logger.info("AcmeCorp Support Bot API shutting down.")


app = FastAPI(
    title="AcmeCorp Support Bot",
    description="Customer support bot with prompt injection defenses.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

_sessions: dict[str, SupportBot] = {}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="default")
    hardened: bool = Field(default=True, description="Enable all defense layers")


class ChatResponse(BaseModel):
    reply: str
    blocked: bool
    block_reason: str | None = None
    session_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    session_key = f"{request.session_id}:{request.hardened}"

    if session_key not in _sessions:
        _sessions[session_key] = SupportBot(
            client=_client,
            model=_model,
            judge_model=_judge_model,
            use_input_filter=request.hardened,
            use_llm_judge=request.hardened,
        )

    bot = _sessions[session_key]

    try:
        result = bot.chat(request.message)
    except Exception as exc:
        logger.exception("Unexpected error during bot.chat: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")

    return ChatResponse(
        reply=result.content,
        blocked=result.blocked,
        block_reason=result.block_reason,
        session_id=request.session_id,
    )


@app.delete("/chat/{session_id}")
def reset_session(session_id: str):
    removed = []
    for key in list(_sessions.keys()):
        if key.startswith(f"{session_id}:"):
            del _sessions[key]
            removed.append(key)
    if not removed:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"reset": removed}


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
