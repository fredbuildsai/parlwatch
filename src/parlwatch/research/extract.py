"""Propose checkable claims from a cleaned hearing transcript (candidates for the research step; a person or researcher confirms)."""

import re

from llmrouter_free import json_schema_response_format, json_validator
from pydantic import BaseModel, Field

from parlwatch.analyze.run import make_windows, verify_quote
from parlwatch.pipeline import hms
from parlwatch.research.schema import ClaimKind


class Candidate(BaseModel):
    speaker: str = Field(description="who says it; a name from the participant list or 'Unknown'")
    time: str = Field(description="hh:mm:ss copied from the line where the statement is made")
    claim: str = Field(description="the assertion in English, one sentence, self-contained")
    quote_fr: str = Field(description="VERBATIM excerpt (max 30 words) from the transcript")
    kind: ClaimKind
    how_to_check: str = Field(description="what source would confirm or refute it (e.g. company results, official statistics, EU text)")


class Candidates(BaseModel):
    candidates: list[Candidate] = Field(default_factory=list)


PROMPT = """From this excerpt of a French parliamentary hearing, list the statements worth FACT-CHECKING later: specific figures, dated or
sourced facts, comparisons, and forecasts that can be confirmed or refuted by public evidence (company results, official statistics,
laws and EU texts, announced projects). Skip procedure, greetings, rhetorical questions and pure opinions that no evidence could settle
(you may keep an important policy position as kind=policy_position). Prefer statements that state a number, a date or a causal claim.

HEARING: {context}
PARTICIPANTS: {participants}

EXCERPT (lines start with [hh:mm:ss]):
{text}

Return JSON {{"candidates": [...]}} with at most 8 items. `quote_fr` must be copied verbatim from a single line; `time` is that line's time."""


def extract_candidates(router, sentences: list[dict], start_s: float, end_s: float, context: str, participants: list[str]) -> list[dict]:
    out = []
    for win in make_windows(sentences, start_s, end_s, max_chars=14000):
        text = "\n".join(f"[{hms(s['start_s'])}] {s['text']}" for s in win)
        res = router.complete("analyze", [{"role": "user", "content": PROMPT.format(context=context, participants="; ".join(participants), text=text)}],
                              temperature=0.2, max_tokens=4000, validate=json_validator(Candidates),
                              response_format=json_schema_response_format(Candidates, strict=False))
        plain = [s["text"] for s in win]
        for c in json_validator(Candidates)(res.text).candidates:
            d = c.model_dump()
            d["quote_verified"] = verify_quote(c.quote_fr, plain)
            d["time"] = (re.search(r"\d{1,3}:\d{2}:\d{2}", d["time"]) or [""])[0] if re.search(r"\d{1,3}:\d{2}:\d{2}", d["time"]) else ""
            out.append(d)
    return out
