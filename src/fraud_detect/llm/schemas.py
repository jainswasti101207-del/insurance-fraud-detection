"""Pydantic models for structured Gemini JSON outputs."""
from __future__ import annotations

from pydantic import BaseModel, Field


class NarrativeAnalysis(BaseModel):
    summary: str = Field(description="1-3 sentence factual summary of the narrative.")
    contradictions: list[str] = Field(
        default_factory=list,
        description="Specific disagreements between the narrative and the structured claim fields provided, if any.",
    )
    notable_facts: list[str] = Field(
        default_factory=list, description="Facts from the narrative relevant to fraud risk (evidence, delays, history)."
    )


class ImageAnalysis(BaseModel):
    damage_severity_estimate: str = Field(description="One of: Minor, Moderate, Severe.")
    plausibility_notes: str = Field(description="Whether the visible damage looks consistent with the claimed accident description.")
    visual_red_flags: list[str] = Field(default_factory=list, description="Specific visual inconsistencies, if any. Empty list if none.")


class WhyReportSections(BaseModel):
    top_reasons: list[str] = Field(default_factory=list, description="3-5 reasons, each stating a FACT and why it matters.")
    narrative_evidence: str = Field(default="", description="Facts from the narrative report, not invented.")
    what_to_check: list[str] = Field(default_factory=list, description="Concrete, specific investigation actions, not generic advice.")
