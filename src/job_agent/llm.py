"""Model factory. Gemini free tier by default; each model has its own free quota."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODELS = ["gemini-3.1-flash-lite", "gemini-3.5-flash"]


def get_llm(model: str | None = None):
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model or os.getenv("LLM_MODEL", DEFAULT_MODEL),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        timeout=60,
        max_retries=1,
    )


def get_llm_chain() -> list:
    """Main model first, then fallbacks (used when a model hits its free quota)."""
    names = [os.getenv("LLM_MODEL", DEFAULT_MODEL), *FALLBACK_MODELS]
    seen: list[str] = []
    for n in names:
        if n not in seen:
            seen.append(n)
    return [get_llm(n) for n in seen]
