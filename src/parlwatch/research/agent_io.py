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
from parlwatch.research.coverage import coverage
from parlwatch.research.schema import DIMENSIONS, Check, Finding, Research, Source, Topic

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
    sources: list[AgentSource] = Field(description="max 3, URLs returned by your search in this run; required for a new or changed verdict other than unverifiable or pending; empty for an unchanged verdict")
    next_step: str = Field(description="one short sentence on what to check next time, or empty string")


class TopicUpdateOut(BaseModel):
    topic_id: str
    date: str = Field(description="date of the development, YYYY-MM-DD or YYYY-MM")
    summary: str = Field(description="what happened, one or two sentences, English")
    sources: list[AgentSource]


DimensionName = Literal["supply", "demand", "regulation", "finance", "energy_resources", "geopolitics_security", "technology"]


class FindingOut(BaseModel):
    date: str = Field(description="date of the development, YYYY-MM-DD or YYYY-MM; the system files it as before/after the meeting by this date")
    summary: str = Field(description="what happened or what was the situation, one or two sentences, English")
    sources: list[AgentSource]


class NewTopicOut(BaseModel):
    id: str = Field(description="short unique snake_case id, not already used by an existing topic")
    title: str
    dimension: DimensionName
    why_it_matters: str = Field(description="one sentence: how this context bears on what was said in the hearing")
    findings: list[FindingOut] = Field(description="2 to 6 findings: the situation before the meeting and, if any, developments since")


class CoverageNote(BaseModel):
    dimension: DimensionName
    status: Literal["covered", "not_relevant", "not_researched"]
    note: str = Field(description="why: what covers it, why it does not apply to this hearing, or why it was not researched (for example search budget)")


class UnresolvedOut(BaseModel):
    item: str = Field(description="claim id, queue item or topic")
    reason: str


class AgentOutput(BaseModel):
    meeting_uid: str = Field(description="copied from the input")
    checkpoint: Literal["3m", "6m", "12m"] = Field(description="copied from the input")
    checked_on: str = Field(description="today's date from the input, YYYY-MM-DD")
    claim_checks: list[ClaimCheckOut] = Field(description="exactly one entry per claim in the input")
    topic_updates: list[TopicUpdateOut] = Field(description="significant developments within the period, max 3 per topic")
    new_topics: list[NewTopicOut] = Field(description="topics for context dimensions the record does not cover yet (see input.coverage); may be empty")
    coverage_notes: list[CoverageNote] = Field(description="one entry per context dimension: covered, not relevant to this hearing, or not researched")
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
def build_input(r: Research, checkpoint: str, today: date, since: date | None = None, blind: bool = False,
                max_web_searches: int | None = None, max_page_fetches: int | None = None, claim_ids: list[str] | None = None,
                context_scan: bool = True) -> dict[str, Any]:
    """The JSON the agent receives. `period.from` is the latest done checkpoint, or the meeting date; `since` overrides it
    (e.g. an independent re-check of the whole period since the meeting)."""
    meeting = date.fromisoformat(r.meeting_date)
    done = [date.fromisoformat(c.done_on) for c in r.checkpoints if c.done_on and c.label != checkpoint]
    since = since or max([meeting, *done])
    # blind = an independent second opinion: the agent sees the claims but NOT our earlier verdicts, evidence, sources or hints
    # (otherwise it tends to repeat them).

    def fin(f: Finding) -> dict[str, Any]:
        return {"date": f.date, "summary": f.summary, "sources": [{"title": s.title, "url": s.url} for s in f.sources]}

    return {
        "task": "followup_check", "today": today.isoformat(), "checkpoint": checkpoint,
        "period": {"from": since.isoformat(), "to": today.isoformat(),
                   "checkpoint_due": next(c.due for c in r.checkpoints if c.label == checkpoint)},
        "meeting": {"uid": r.meeting_uid, "title": r.title, "date": r.meeting_date, "quote_language": "fr"},
        "topics": [{"id": t.id, "title": t.title, "why_it_matters": t.why_it_matters,
                    "before": [] if blind else [fin(f) for f in t.before], "after": [] if blind else [fin(f) for f in t.after]} for t in r.topics],
        "claims": [{"id": c.id, "speaker": c.speaker, "time": c.time, "kind": c.kind, "text": c.text, "quote_fr": c.quote_fr, "topic": c.topic,
                    "previous_checks": [] if blind else [{"checkpoint": k.checkpoint, "verdict": k.verdict, "checked_on": k.checked_on,
                                                          "evidence": k.evidence} for k in c.checks],
                    "next_step": "" if blind else c.next_step} for c in r.claims if claim_ids is None or c.id in claim_ids],
        "queue": [] if blind else r.queue,
        **({"context_dimensions": DIMENSIONS,
            "coverage": [{"dimension": c["dimension"], "status": c["status"], "topics": c["topics"]} for c in coverage(r)]} if context_scan else
           {"note": "This task covers only the claims listed. Do the claim checks; leave topic_updates, new_topics and coverage_notes empty."}),
        **({"mode": "blind: earlier verdicts are deliberately withheld; judge each claim from scratch"} if blind else {}),
        **({"limits": {k: v for k, v in (("max_web_searches", max_web_searches), ("max_page_fetches", max_page_fetches)) if v}}
           if (max_web_searches or max_page_fetches) else {}),
    }


# ------------------------------------------------------------------------------------------------ guarded merge
def _src(s: AgentSource, today: str, by: str = "mistral-agent", note_extra: str = "", basis: str | None = None) -> Source:
    basis = basis or s.basis
    note = {"page_content": "page content read", "search_result_text": "search result text only", "search_snippet": "search snippet only"}[basis]
    return Source(title=s.title, url=s.url, tier=s.tier, accessed=today, note=f"{note}{note_extra} (by {by})", basis=basis, published=s.published)


def norm_url(u: str) -> str:
    return u.split("#")[0].rstrip("/").lower()


def record_urls(r: Research) -> set[str]:
    """Every URL already in the record (these are sent to the agent as context)."""
    urls = {norm_url(x.url) for t in r.topics for f in t.before + t.after for x in f.sources}
    return urls | {norm_url(x.url) for c in r.claims for k in c.checks for x in k.sources}


def merge(r: Research, out: AgentOutput, checkpoint: str, agent_version: int | None, today: date,
          seen_urls: set[str] | None = None, by: str = "mistral-agent", fetched_urls: set[str] | None = None) -> dict[str, Any]:
    """Append the agent's checks to `r` (in place). Append-only; each check is validated and rejected with a reason if it fails.

    Rejected: unknown claim id; duplicate claim id; a policy position or opinion given a true/false verdict; a forecast judged supported or contradicted; a new or changed verdict that needs a source but has none retrieved in this run, or a
    source URL that is not http(s); a topic update dated in the future. An UNCHANGED verdict with no new evidence is accepted as 'carried forward'.
    When `seen_urls` (URLs present in the agent's own search results) is given, a cited URL not in it is dropped: URLs already in the record were
    only given to the agent as context and are kept but marked 'not retrieved in this run'; any other URL is treated as invented and dropped.
    When `fetched_urls` (pages whose content was really read) is given, a source claiming basis 'page_content' that was not fetched is downgraded.
    `verdict_changed` is recomputed from the record, not trusted. Claims the agent skipped are reported.
    """
    t = today.isoformat()
    report: dict[str, Any] = {"applied": [], "rejected": [], "changed": [], "missing": [], "topics_added": 0, "carried_forward": [],
                              "urls_dropped": [], "urls_not_retrieved": []}
    prior = record_urls(r)
    if out.meeting_uid != r.meeting_uid or out.checkpoint != checkpoint:
        report["rejected"].append({"item": "output", "reason": f"output is for {out.meeting_uid}/{out.checkpoint}, expected {r.meeting_uid}/{checkpoint}"})
        return report
    seen: set[str] = set()
    known = {c.id: c for c in r.claims}
    def vet(sources: list[AgentSource], where: str) -> tuple[list[Source], int]:
        """Sources to keep, and how many were retrieved in this run (all count when seen_urls is not given)."""
        kept, fresh = [], 0
        for x in sources:
            if not x.url.startswith(("http://", "https://")):
                continue
            n = norm_url(x.url)
            if seen_urls is None or n in seen_urls:
                if fetched_urls is not None and x.basis == "page_content" and n not in fetched_urls:
                    kept.append(_src(x, t, by, "; claimed full page but it was NOT fetched, downgraded", "search_snippet"))
                    report.setdefault("basis_downgraded", []).append({"where": where, "url": x.url})
                else:
                    kept.append(_src(x, t, by))
                fresh += 1
            elif n in prior:
                src = _src(x, t, by)
                src.note = f"URL taken from the earlier record; NOT retrieved in this run ({by})"
                src.basis = "unspecified"
                kept.append(src)
                report["urls_not_retrieved"].append({"where": where, "url": x.url})
            else:
                report["urls_dropped"].append({"where": where, "url": x.url})
        return kept, fresh

    for ck in out.claim_checks:
        why = None
        if ck.claim_id not in known:
            why = "unknown claim id"
        elif ck.claim_id in seen:
            why = "duplicate claim id"
        elif not ck.evidence.strip():
            why = "empty evidence"
        elif known[ck.claim_id].kind in ("policy_position", "opinion") and ck.verdict not in ("pending", "unverifiable"):
            why = f"a {known[ck.claim_id].kind} cannot be judged true or false; it stays pending (rule enforced in code)"
        elif known[ck.claim_id].kind == "forecast" and ck.verdict in ("supported", "contradicted"):
            why = "a forecast cannot be judged before its date; leave it pending for a human decision (rule enforced in code)"
        if why:
            report["rejected"].append({"item": ck.claim_id, "reason": why})
            continue
        claim = known[ck.claim_id]
        prev = claim.checks[-1].verdict if claim.checks else "none"
        kept, fresh = vet(ck.sources, ck.claim_id)
        carried = False
        if ck.verdict in NEEDS_SOURCE and fresh == 0:
            if ck.verdict == prev:
                carried = True  # unchanged verdict, no new evidence: carry it forward
            else:
                report["rejected"].append({"item": ck.claim_id, "reason": f"new/changed verdict '{ck.verdict}' without a source retrieved in this run"})
                continue
        seen.add(ck.claim_id)
        evidence = ck.evidence
        if carried:
            evidence = "[carried forward, no new evidence in this run] " + evidence
            report["carried_forward"].append(ck.claim_id)
        claim.checks.append(Check(checkpoint=checkpoint, verdict=ck.verdict, checked_on=t, evidence=evidence, sources=kept,
                                  confidence=ck.confidence, by=by, agent_version=agent_version))
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
            topics[tu.topic_id].after.append(Finding(date=tu.date, summary=tu.summary, sources=vet(tu.sources, f"topic:{tu.topic_id}")[0]))
            report["topics_added"] += 1
        else:
            report["rejected"].append({"item": f"topic:{tu.topic_id}", "reason": "unknown topic, future date or empty summary"})
    existing = {x.id for x in r.topics}
    meeting_d = r.meeting_date
    report["new_topics"], report["new_topics_rejected"] = [], []
    for nt in out.new_topics:
        if nt.id in existing or not nt.id.strip() or not nt.title.strip() or nt.dimension not in DIMENSIONS:
            report["new_topics_rejected"].append({"item": nt.id, "reason": "duplicate id, empty, or unknown dimension"})
            continue
        topic = Topic(id=nt.id, title=nt.title, dimension=nt.dimension, why_it_matters=nt.why_it_matters)
        for f in nt.findings:
            if not f.summary.strip() or f.date[:10] > t:
                continue  # empty or dated in the future
            fin = Finding(date=f.date, summary=f.summary, sources=vet(f.sources, f"newtopic:{nt.id}")[0])
            (topic.before if f.date[:10] <= meeting_d else topic.after).append(fin)  # filed by date, not by the agent's say-so
        if not (topic.before or topic.after):
            report["new_topics_rejected"].append({"item": nt.id, "reason": "no valid findings"})
            continue
        r.topics.append(topic)
        existing.add(nt.id)
        report["new_topics"].append(nt.id)
    for cn in out.coverage_notes:
        if cn.status == "not_relevant" and cn.dimension not in {x.dimension for x in r.topics}:
            r.dimension_notes[cn.dimension] = f"not relevant: {cn.note} (by {by}, {t})"
    r.queue += [q for q in out.queue_additions if q not in r.queue]
    return report


def mark_done(r: Research, checkpoint: str, today: date, report: dict[str, Any]) -> None:
    """Close the checkpoint only if every claim got an accepted check; otherwise leave it open."""
    cp = next(c for c in r.checkpoints if c.label == checkpoint)
    if not report["missing"] and not [x for x in report["rejected"] if not x["item"].startswith("topic:")]:
        cp.done_on = today.isoformat()
        late = (today - date.fromisoformat(cp.due)).days
        cp.note = f"done by agent, {late} days after the due date" if late > 0 else "done by agent"
    else:
        cp.note = f"agent run {today.isoformat()} incomplete: {len(report['missing'])} claim(s) missing, {len(report['rejected'])} rejected"


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
        topic_updates=[], new_topics=[], coverage_notes=[], queue_additions=[], unresolved=[], summary="Example only.").model_dump_json())


def shape_example() -> str:
    """A small, valid example answer (illustrative content) shown to models that do not get schema-constrained decoding."""
    src = AgentSource(title="Official press release", url="https://example.org/press/2026-09-01", tier="primary", basis="page_content", published="2026-09-01")
    out = AgentOutput(
        meeting_uid="<copy from input>", checkpoint="3m", checked_on="<today from input>",
        claim_checks=[
            ClaimCheckOut(claim_id="K1", verdict="partly_supported", previous_verdict="none", verdict_changed=False, confidence="medium",
                          evidence="The ceiling is 180M over 6 years = at most 30M a year, not 40M.", sources=[src], next_step="Look for call-off volumes."),
            ClaimCheckOut(claim_id="K2", verdict="unverifiable", previous_verdict="unverifiable", verdict_changed=False, confidence="low",
                          evidence="No new evidence; no public breakdown by vendor found.", sources=[], next_step="")],
        topic_updates=[TopicUpdateOut(topic_id="ovh", date="2026-09-01", summary="One or two sentences on a development in the period.", sources=[src])],
        new_topics=[NewTopicOut(id="demand", title="Demand for compute", dimension="demand", why_it_matters="One sentence.",
                                findings=[FindingOut(date="2026-04", summary="A dated finding.", sources=[src])])],
        coverage_notes=[CoverageNote(dimension="technology", status="not_relevant", note="The hearing is about procurement, not technology.")],
        queue_additions=["Something worth checking later."], unresolved=[UnresolvedOut(item="K2", reason="No public data.")],
        summary="Three to five sentences for the human reviewer.")
    return out.model_dump_json(indent=1)


def compact_errors(exc: Exception, limit: int = 14) -> str:
    """A short, readable list of what is wrong with an answer (pydantic errors are long; models need the paths and the reason)."""
    errs = getattr(exc, "errors", None)
    if not callable(errs):
        return str(exc)[:600]
    lines = [f"- {'.'.join(str(x) for x in e['loc'])}: {e['msg']}" for e in errs()[:limit]]
    more = len(errs()) - limit
    return "\n".join(lines) + (f"\n- ... and {more} more" if more > 0 else "")


def combine_outputs(outs: list[AgentOutput]) -> AgentOutput:
    """Merge the answers of several partial runs (claim batches + a context run) into one."""
    first = outs[0]
    seen_cov: dict[str, CoverageNote] = {}
    for o in outs:
        for cn in o.coverage_notes:
            if cn.dimension not in seen_cov or cn.status != "not_researched":
                seen_cov[cn.dimension] = cn
    return AgentOutput(
        meeting_uid=first.meeting_uid, checkpoint=first.checkpoint, checked_on=first.checked_on,
        claim_checks=[c for o in outs for c in o.claim_checks], topic_updates=[t for o in outs for t in o.topic_updates],
        new_topics=[t for o in outs for t in o.new_topics], coverage_notes=list(seen_cov.values()),
        queue_additions=list(dict.fromkeys(q for o in outs for q in o.queue_additions)), unresolved=[u for o in outs for u in o.unresolved],
        summary=" ".join(o.summary for o in outs if o.summary.strip()))
