"""Thin wrapper around google-generativeai with retry/timeout and graceful
degradation - a live graded demo must never crash because of a rate limit or
a missing key."""
from __future__ import annotations

import json
import time

import google.generativeai as genai

from fraud_detect.config import get_api_key

MODEL_NAME = "gemini-2.5-flash"
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 2


class GeminiUnavailable(Exception):
    pass


_configured = False


def _ensure_configured() -> None:
    global _configured
    if _configured:
        return
    api_key = get_api_key()
    if not api_key:
        raise GeminiUnavailable("GEMINI_API_KEY not set")
    genai.configure(api_key=api_key)
    _configured = True


def call_gemini_json(prompt_parts: list, system_instruction: str) -> dict:
    """Calls Gemini with a JSON response format. Returns a dict, or raises
    GeminiUnavailable on any failure after retries - callers must catch this
    and fall back to a deterministic path."""
    try:
        _ensure_configured()
    except GeminiUnavailable:
        raise

    model = genai.GenerativeModel(
        MODEL_NAME,
        system_instruction=system_instruction,
        generation_config=genai.GenerationConfig(response_mime_type="application/json"),
    )

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = model.generate_content(prompt_parts)
            return json.loads(response.text)
        except Exception as exc:  # noqa: BLE001 - any SDK/network/parse failure degrades gracefully
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise GeminiUnavailable(f"Gemini call failed after {MAX_RETRIES + 1} attempts: {last_error}")
