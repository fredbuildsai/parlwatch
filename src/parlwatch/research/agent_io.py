"""Contract between ParlWatch and the Mistral research agent: instructions, input message, response format, and a guarded merge.

Single source of truth: `INSTRUCTIONS` and `AgentOutput` here generate the files in docs/mistral-agent/ (see scripts/build_agent_files.py),
so the text pasted into Mistral Studio, the schema it enforces and the parser in this repository cannot drift apart.
"""

import copy
import json
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

from parlwatch.research.checkpoints import add_months
from parlwatch.research.schema import Check, Finding, Research, Source

AgentVerdict = Literal["supported", "partly_supported", "contradicted", "outdated", "unverifiable", "pending"]
NEEDS_SOURCE = {"supported", "partly_supported", "contradicted", "outdated"}


# ------------------------------------------------------------------------------------------------ response format
class AgentSource(BaseModel):
    title: str = Field(description="page or document title")
    url: str = Field(description="URL exactly as returned by the search tool; never invented")
    tier: Literal["primary", "secondary", "weak"]
    basis: Literal["page_content", "search_result_text", "search_snippet"] = Field(description="how much of the source you actually saw")
    published: str = Field(description="publication date YYYY-MM-DD, or empty string if unknown")


class ClaimCheckOut(BaseModel):
    claim_id: str = Field(description="id of the claim from the input")
    verdict: AgentVerdict
    previous_verdict: str = Field(description="verdict of the latest previous check, or 'none'")
    verdict_changed: bool
    confidence: Literal["high", "medium", "low"]
    evidence: str = Field(description="1 to 3 sentences, max 70 words, English; show arithmetic for figures")
    sources: list[AgentSource] = Field(description="max 3; required unless the verdict is unverifiable or pending")
    next_step: str = Field(description="one short sentence on what to check next time, or empty string")


class TopicUpdateOut(BaseModel):
    topic_id: str
    date: str = Field(description="date of the development, YYYY-MM-DD or YYYY-MM")
    summary: str = Field(description="what happened, one or two sentences, English")
    sources: list[AgentSource]


class UnresolvedOut(BaseModel):
    item: str = Field(description="claim id, queue item or topic")
    reason: str


class AgentOutput(BaseModel):
    meeting_uid: str = Field(description="copied from the input")
    checkpoint: Literal["3m", "6m", "12m"] = Field(description="copied from the input")
    checked_on: str = Field(description="today's date from the input, YYYY-MM-DD")
    claim_checks: list[ClaimCheckOut] = Field(description="exactly one entry per claim in the input")
    topic_updates: list[TopicUpdateOut] = Field(description="significant developments within the period, max 3 per topic")
    queue_additions: list[str] = Field(description="new things worth researching later, short strings")
    unresolved: list[UnresolvedOut]
    summary: str = Field(description="3 to 5 sentences for the human reviewer: what changed, what is resolved, what is uncertain")


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """JSON Schema for strict structured output: references inlined, every property required, no extra properties, no defaults/titles."""
    raw = model.model_json_schema()
    defs = raw.pop("$defs", {})

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(copy.deepcopy(defs[node["$ref"].split("/")[-1]]))
            # "title"/"default" are removed only as schema keywords; inside `properties` they can be real field names (a source's title)
            out = {k: (({n: walk(v2) for n, v2 in v.items()}) if k == "properties" else walk(v))
                   for k, v in node.items() if not (k in ("title", "default") and not isinstance(v, dict))}
            if out.get("type") == "object" and "properties" in out:
                out["required"] = list(out["properties"])
                out["additionalProperties"] = False
            return out
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(raw)


def response_format() -> dict[str, Any]:
    """The `response_format` value for Mistral's completion_args (also the JSON Schema to paste in Mistral Studio)."""
    return {"type": "json_schema", "json_schema": {"name": "followup_check", "schema_definition": strict_schema(AgentOutput), "strict": True}}


# ------------------------------------------------------------------------------------------------ input message
def build_input(r: Research, checkpoint: str, today: date) -> dict[str, Any]:
    """The JSON the agent receives. `period.from` is the day after the previous done checkpoint, or the meeting date."""
    meeting = date.fromisoformat(r.meeting_date)
    done = [date.fromisoformat(c.done_on) for c in r.checkpoints if c.done_on and c.label != checkpoint]
    since = max([meeting, *done])

    def fin(f: Finding) -> dict[str, Any]:
        return {"date": f.date, "summary": f.summary, "sources": [{"title": s.title, "url": s.url} for s in f.sources]}

    return {
        "task": "followup_check", "today": today.isoformat(), "checkpoint": checkpoint,
        "period": {"from": since.isoformat(), "to": today.isoformat(),
                   "checkpoint_due": next(c.due for c in r.checkpoints if c.label == checkpoint)},
        "meeting": {"uid": r.meeting_uid, "title": r.title, "date": r.meeting_date, "quote_language": "fr"},
        "topics": [{"id": t.id, "title": t.title, "why_it_matters": t.why_it_matters,
                    "before": [fin(f) for f in t.before], "after": [fin(f) for f in t.after]} for t in r.topics],
        "claims": [{"id": c.id, "speaker": c.speaker, "time": c.time, "kind": c.kind, "text": c.text, "quote_fr": c.quote_fr, "topic": c.topic,
                    "previous_checks": [{"checkpoint": k.checkpoint, "verdict": k.verdict, "checked_on": k.checked_on, "evidence": k.evidence}
                                        for k in c.checks], "next_step": c.next_step} for c in r.claims],
        "queue": r.queue,
    }


# ------------------------------------------------------------------------------------------------ guarded merge
def _src(s: AgentSource, today: str) -> Source:
    note = {"page_content": "page content read", "search_result_text": "search result text only", "search_snippet": "search snippet only"}[s.basis]
    return Source(title=s.title, url=s.url, tier=s.tier, accessed=today, note=f"{note} (by mistral-agent)", basis=s.basis, published=s.published)


def merge(r: Research, out: AgentOutput, checkpoint: str, agent_version: int | None, today: date) -> dict[str, Any]:
    """Append the agent's checks to `r` (in place). Append-only; each check is validated and rejected with a reason if it fails.

    Rejected: unknown claim id; duplicate claim id; a verdict that needs a source but has none, or a source URL that is not http(s);
    a topic update dated in the future. `verdict_changed` is recomputed from the record, not trusted. Claims the agent skipped are reported.
    """
    t = today.isoformat()
    report: dict[str, Any] = {"applied": [], "rejected": [], "changed": [], "missing": [], "topics_added": 0}
    if out.meeting_uid != r.meeting_uid or out.checkpoint != checkpoint:
        report["rejected"].append({"item": "output", "reason": f"output is for {out.meeting_uid}/{out.checkpoint}, expected {r.meeting_uid}/{checkpoint}"})
        return report
    seen: set[str] = set()
    known = {c.id: c for c in r.claims}
    for ck in out.claim_checks:
        why = None
        if ck.claim_id not in known:
            why = "unknown claim id"
        elif ck.claim_id in seen:
            why = "duplicate claim id"
        elif ck.verdict in NEEDS_SOURCE and not ck.sources:
            why = f"verdict '{ck.verdict}' without a source"
        elif any(not s.url.startswith(("http://", "https://")) for s in ck.sources):
            why = "source without a valid URL"
        elif not ck.evidence.strip():
            why = "empty evidence"
        if why:
            report["rejected"].append({"item": ck.claim_id, "reason": why})
            continue
        seen.add(ck.claim_id)
        claim = known[ck.claim_id]
        prev = claim.checks[-1].verdict if claim.checks else "none"
        claim.checks.append(Check(checkpoint=checkpoint, verdict=ck.verdict, checked_on=t, evidence=ck.evidence, sources=[_src(s, t) for s in ck.sources],
                                  confidence=ck.confidence, by="mistral-agent", agent_version=agent_version))
        if ck.next_step:
            claim.next_step = ck.next_step
        report["applied"].append(ck.claim_id)
        if prev != ck.verdict and prev != "none":
            report["changed"].append({"claim": ck.claim_id, "from": prev, "to": ck.verdict, "agent_said_changed": ck.verdict_changed})
    report["missing"] = [c for c in known if c not in seen and c not in {x["item"] for x in report["rejected"]}]
    topics = {x.id: x for x in r.topics}
    for tu in out.topic_updates:
        try:
            ok = tu.topic_id in topics and (tu.date[:10] <= t) and bool(tu.summary.strip())
        except Exception:
            ok = False
        if ok:
            topics[tu.topic_id].after.append(Finding(date=tu.date, summary=tu.summary, sources=[_src(s, t) for s in tu.sources]))
            report["topics_added"] += 1
        else:
            report["rejected"].append({"item": f"topic:{tu.topic_id}", "reason": "unknown topic, future date or empty summary"})
    r.queue += [q for q in out.queue_additions if q not in r.queue]
    return report


def mark_done(r: Research, checkpoint: str, today: date, report: dict[str, Any]) -> None:
    """Close the checkpoint only if every claim got an accepted check; otherwise leave it open."""
    cp = next(c for c in r.checkpoints if c.label == checkpoint)
    if not report["missing"] and not [x for x in report["rejected"] if not x["item"].startswith("topic:")]:
        cp.done_on = today.isoformat()
        late = (today - date.fromisoformat(cp.due)).days
        cp.note = f"done by mistral-agent, {late} days after the due date" if late > 0 else "done by mistral-agent"
    else:
        cp.note = f"mistral-agent run {today.isoformat()} incomplete: {len(report['missing'])} claim(s) missing, {len(report['rejected'])} rejected"


def window_months(checkpoint: str) -> int:
    return {"3m": 3, "6m": 6, "12m": 12}[checkpoint]


def due_date(meeting_date: date, checkpoint: str) -> date:
    return add_months(meeting_date, window_months(checkpoint))


def example_output(r: Research, checkpoint: str, today: date) -> dict[str, Any]:
    """A valid sample answer built from the record (used in docs/tests)."""
    return json.loads(AgentOutput(
        meeting_uid=r.meeting_uid, checkpoint=checkpoint, checked_on=today.isoformat(),
        claim_checks=[ClaimCheckOut(claim_id=c.id, verdict="pending", previous_verdict=c.checks[-1].verdict if c.checks else "none",
                                    verdict_changed=False, confidence="low", evidence="No new evidence found in the period.", sources=[], next_step="")
                      for c in r.claims],
        topic_updates=[], queue_additions=[], unresolved=[], summary="Example only.").model_dump_json())
