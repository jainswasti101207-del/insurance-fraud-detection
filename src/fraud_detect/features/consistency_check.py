"""Deterministic structured-vs-narrative contradiction detector (Instructions_Set_Reports.docx §21).

This is the auditable baseline; llm/narrative_analysis.py provides a secondary,
complementary Gemini-based check. Agreement between the two raises confidence
in a detected contradiction; the deterministic result here never depends on
the LLM being available.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

POLICE_ABSENT_RE = re.compile(
    r"no (?:formal |official )?police report|neither[^.]{0,40}police report", re.IGNORECASE
)
POLICE_PRESENT_RE = re.compile(r"police report (?:was|were|has been) filed", re.IGNORECASE)
WITNESS_ABSENT_RE = re.compile(
    r"no (?:external )?witness|nor (?:were|was)[^.]{0,20}witness", re.IGNORECASE
)
WITNESS_PRESENT_RE = re.compile(r"witness(?:es)? (?:was|were) present", re.IGNORECASE)


@dataclass
class Contradiction:
    field: str
    structured_value: str
    narrative_signal: str
    detail: str


def _narrative_police_status(text: str) -> str | None:
    if POLICE_ABSENT_RE.search(text):
        return "No"
    if POLICE_PRESENT_RE.search(text):
        return "Yes"
    return None


def _narrative_witness_status(text: str) -> str | None:
    if WITNESS_ABSENT_RE.search(text):
        return "No"
    if WITNESS_PRESENT_RE.search(text):
        return "Yes"
    return None


def check_consistency(structured: dict, narrative_text: str) -> list[Contradiction]:
    contradictions: list[Contradiction] = []

    narrative_police = _narrative_police_status(narrative_text)
    structured_police = str(structured.get("PoliceReportFiled", "")).strip()
    if narrative_police is not None and structured_police and narrative_police != structured_police:
        contradictions.append(
            Contradiction(
                field="PoliceReportFiled",
                structured_value=structured_police,
                narrative_signal=narrative_police,
                detail=(
                    f"Spreadsheet says PoliceReportFiled={structured_police} but the narrative "
                    f"describes a police report as {'filed' if narrative_police == 'Yes' else 'not filed'}."
                ),
            )
        )

    narrative_witness = _narrative_witness_status(narrative_text)
    structured_witness = str(structured.get("WitnessPresent", "")).strip()
    if narrative_witness is not None and structured_witness and narrative_witness != structured_witness:
        contradictions.append(
            Contradiction(
                field="WitnessPresent",
                structured_value=structured_witness,
                narrative_signal=narrative_witness,
                detail=(
                    f"Spreadsheet says WitnessPresent={structured_witness} but the narrative "
                    f"describes a witness as {'present' if narrative_witness == 'Yes' else 'not present'}."
                ),
            )
        )

    make = str(structured.get("Make", ""))
    if make and make.lower() not in narrative_text.lower():
        contradictions.append(
            Contradiction(
                field="Make",
                structured_value=make,
                narrative_signal="not mentioned",
                detail=f"Spreadsheet lists Make={make} but the narrative does not mention this vehicle make.",
            )
        )

    area = str(structured.get("AccidentArea", "")).strip()
    if area and area.lower() not in narrative_text.lower():
        contradictions.append(
            Contradiction(
                field="AccidentArea",
                structured_value=area,
                narrative_signal="not mentioned",
                detail=f"Spreadsheet lists AccidentArea={area} but the narrative does not use this term.",
            )
        )

    return contradictions
