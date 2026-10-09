"""Research record: context before a meeting, claim checks, and follow-ups at 3/6/12 months.

One `research.json` per meeting. It is deliberately plain data so that any researcher (a person, Claude Code, or later an automated
searcher) can add checks, and so that every verdict carries its evidence, sources and the date it was checked.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

# supported: evidence agrees | partly_supported: roughly right but a detail is off | contradicted: evidence disagrees
# outdated: was right when said, superseded since | unverifiable: no public evidence found | pending: outcome not yet knowable
# not_checked: queued, nobody has looked yet
Verdict = Literal["supported", "partly_supported", "contradicted", "outdated", "unverifiable", "pending", "not_checked"]
Tier = Literal["primary", "secondary", "weak"]  # primary = official/original; secondary = reputable press, law firms; weak = aggregators, blogs
CheckpointLabel = Literal["at_meeting", "3m", "6m", "12m"]
ClaimKind = Literal["figure", "forecast", "policy_position", "fact", "opinion"]


class Source(BaseModel):
    title: str
    url: str
    tier: Tier
    accessed: str  # ISO date
    note: str = ""
    basis: Literal["page_content", "search_result_text", "search_snippet", "unspecified"] = "unspecified"  # how much of the source was seen
    published: str = ""  # ISO date of the source when known


class Finding(BaseModel):
    date: str  # ISO date or "2026-05" / "2025" when only that is known
    summary: str
    sources: list[Source] = Field(default_factory=list)


class Topic(BaseModel):
    id: str
    title: str
    why_it_matters: str
    before: list[Finding] = Field(default_factory=list)  # what the meeting builds on
    after: list[Finding] = Field(default_factory=list)  # what happened since


class Check(BaseModel):
    checkpoint: CheckpointLabel
    verdict: Verdict
    checked_on: str
    evidence: str
    sources: list[Source] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low", "unrated"] = "unrated"
    by: str = ""  # who did the check, e.g. "claude-code" or "mistral-agent"
    agent_version: int | None = None  # version of the Mistral agent that produced it, for traceability


class Claim(BaseModel):
    id: str
    speaker: str
    time: str  # hh:mm:ss in the recording
    text: str  # the assertion, in English
    quote_fr: str = ""
    kind: ClaimKind
    topic: str = ""
    checks: list[Check] = Field(default_factory=list)
    next_step: str = ""  # what to look at next time


class Checkpoint(BaseModel):
    label: CheckpointLabel
    due: str  # ISO date
    done_on: str | None = None
    note: str = ""


class Research(BaseModel):
    meeting_uid: str
    title: str
    meeting_date: str
    researched_on: str
    method: str = "manual research by Claude Code with web search, protocol v0 (see docs/research-feature.md)"
    checkpoints: list[Checkpoint] = Field(default_factory=list)
    topics: list[Topic] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    queue: list[str] = Field(default_factory=list)  # things noticed but not yet researched

    def claim(self, claim_id: str) -> Claim:
        return next(c for c in self.claims if c.id == claim_id)


def today_iso() -> str:
    return date.today().isoformat()
