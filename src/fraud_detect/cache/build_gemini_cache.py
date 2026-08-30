"""Precomputes Gemini narrative+image analysis for all 100 historical claims,
once, so the 'Browse Existing Claims' demo page never calls the API live
(avoids rate-limit/latency risk during a graded live demo). The 'New Claim'
page still calls Gemini live to demonstrate real multimodal capability.
"""
from __future__ import annotations

import json
import time

import pandas as pd

from fraud_detect.config import CSV_PATH, GEMINI_CACHE_PATH, IMAGES_DIR, RAW_DIR
from fraud_detect.data.build_mapping import build_mapping
from fraud_detect.data.extract_narratives import extract_narratives
from fraud_detect.llm.image_analysis import analyze_image
from fraud_detect.llm.narrative_analysis import analyze_narrative

SLEEP_BETWEEN_CALLS_SECONDS = 1.0


def build_cache() -> dict:
    claims = pd.read_csv(CSV_PATH)
    narratives = extract_narratives().set_index("csv_row_index")
    mapping = build_mapping().set_index("csv_row_index")

    cache: dict[str, dict] = {}
    for csv_row_index in range(len(claims)):
        row = claims.iloc[csv_row_index]
        structured = row.to_dict()
        narrative_text = narratives.loc[csv_row_index, "narrative_text"]
        m = mapping.loc[csv_row_index]

        narrative_result = analyze_narrative(structured, narrative_text)
        time.sleep(SLEEP_BETWEEN_CALLS_SECONDS)

        image_result = None
        if bool(m["has_image"]):
            image_path = RAW_DIR / m["image_path"]
            image_result = analyze_image(str(image_path), structured)
            time.sleep(SLEEP_BETWEEN_CALLS_SECONDS)

        cache[str(csv_row_index)] = {
            "narrative_analysis": narrative_result.model_dump() if narrative_result else None,
            "image_analysis": image_result.model_dump() if image_result else None,
        }
        print(f"  claim {csv_row_index}: narrative={'ok' if narrative_result else 'FAILED'}, "
              f"image={'ok' if image_result else ('n/a' if not m['has_image'] else 'FAILED')}")

    return cache


def main() -> None:
    cache = build_cache()
    GEMINI_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GEMINI_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)
    n_narrative_ok = sum(1 for v in cache.values() if v["narrative_analysis"])
    n_image_ok = sum(1 for v in cache.values() if v["image_analysis"])
    print(f"Cached {len(cache)} claims -> {GEMINI_CACHE_PATH}")
    print(f"  narrative analyses: {n_narrative_ok}/100, image analyses: {n_image_ok}/26")


if __name__ == "__main__":
    main()
