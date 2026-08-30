"""Multimodal Gemini call: damage severity/plausibility assessment.

Scope is deliberately corrected relative to Instructions_Set_Images.docx,
which assumed images were structured report-card screenshots with visible
checkboxes. The actual images are real accident-scene/damage photographs, so
this asks Gemini to assess visual damage plausibility, not read data fields.
"""
from __future__ import annotations

from pathlib import Path

from fraud_detect.llm.gemini_client import call_gemini_json
from fraud_detect.llm.schemas import ImageAnalysis
from fraud_detect.llm.system_prompt import BASE_SYSTEM_PROMPT

PROMPT = """This is a photograph related to an insurance claim (an accident scene and/or vehicle damage).

Claimed accident context (JSON): {structured_json}

Assess the visible damage severity and whether it looks plausible given the claimed context. \
Note any specific visual inconsistencies (e.g. damage that looks staged, damage inconsistent with the \
claimed impact type, or an image that doesn't match the claimed vehicle).

Respond with JSON matching this schema:
{{"damage_severity_estimate": "Minor|Moderate|Severe", "plausibility_notes": "...", "visual_red_flags": ["..."]}}

If there are no red flags, return an empty list."""


def _load_image_bytes(image_path: str | Path) -> tuple[bytes, str]:
    path = Path(image_path)
    data = path.read_bytes()
    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return data, mime


def analyze_image(image_path: str | Path | None, structured: dict) -> ImageAnalysis | None:
    if not image_path:
        return None
    import json

    try:
        data, mime = _load_image_bytes(image_path)
        prompt = PROMPT.format(structured_json=json.dumps(structured, default=str))
        image_part = {"mime_type": mime, "data": data}
        result = call_gemini_json([prompt, image_part], BASE_SYSTEM_PROMPT)
        return ImageAnalysis(**result)
    except Exception:  # noqa: BLE001 - graceful degradation
        return None


def analyze_image_bytes(image_bytes: bytes, mime_type: str, structured: dict) -> ImageAnalysis | None:
    """For images uploaded live through the app (not read from disk)."""
    import json

    try:
        prompt = PROMPT.format(structured_json=json.dumps(structured, default=str))
        image_part = {"mime_type": mime_type, "data": image_bytes}
        result = call_gemini_json([prompt, image_part], BASE_SYSTEM_PROMPT)
        return ImageAnalysis(**result)
    except Exception:  # noqa: BLE001 - graceful degradation
        return None
