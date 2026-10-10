import json
from datetime import date
from types import SimpleNamespace as NS

import jsonschema
import pytest

from parlwatch.research.agent_io import (
    AgentOutput,
    build_input,
    example_output,
    mark_done,
    merge,
    response_format,
    strict_schema,
)
from parlwatch.research.checkpoints import make_checkpoints
from parlwatch.research.mistral_agent import parse_response, resolve_version, run_checkpoint
from parlwatch.research.schema import Check, Claim, Finding, Research, Topic


def research() -> Research:
    return Research(
        meeting_uid="m1", title="Hearing", meeting_date="2026-05-12", researched_on="2026-10-09", checkpoints=make_checkpoints(date(2026, 5, 12)),
        topics=[Topic(id="t1", title="T", why_it_matters="w", before=[Finding(date="2026-05", summary="b")])],
        claims=[Claim(id="C1", speaker="A", time="00:01:00", text="x is 12", kind="figure", topic="t1",
                      checks=[Check(checkpoint="at_meeting", verdict="supported", checked_on="2026-10-09", evidence="ok")]),
                Claim(id="C2", speaker="B", time="00:02:00", text="y", kind="forecast", topic="t1")])


def good_output(r: Research, **over) -> dict:
    o = example_output(r, "6m", date(2026, 11, 12))
    o["claim_checks"][0].update(verdict="outdated", verdict_changed=True, confidence="high", evidence="Now 21.",
                                sources=[{"title": "P", "url": "https://example.org/a", "tier": "primary", "basis": "page_content", "published": "2026-09-08"}])
    o.update(over)
    return o


def test_schema_is_strict_and_valid():
    s = strict_schema(AgentOutput)
    jsonschema.Draft202012Validator.check_schema(s)
    text = json.dumps(s)
    assert "$ref" not in text and "$defs" not in text and '"default"' not in text

    def objs(n):
        if isinstance(n, dict):
            if n.get("type") == "object":
                yield n
            for v in n.values():
                yield from objs(v)
        elif isinstance(n, list):
            for v in n:
                yield from objs(v)

    for o in objs(s):
        assert o["additionalProperties"] is False and set(o["required"]) == set(o["properties"])
    rf = response_format()
    assert rf["type"] == "json_schema" and rf["json_schema"]["strict"] is True and rf["json_schema"]["schema_definition"] == s


def test_example_validates_against_schema_and_pydantic():
    r = research()
    ex = good_output(r)
    jsonschema.validate(ex, strict_schema(AgentOutput))
    AgentOutput.model_validate(ex)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**ex, "extra": 1}, strict_schema(AgentOutput))


def test_build_input_period_and_history():
    r = research()
    r.checkpoints[1].done_on = "2026-10-09"  # 3m done late
    p = build_input(r, "6m", date(2026, 11, 12))
    assert p["period"] == {"from": "2026-10-09", "to": "2026-11-12", "checkpoint_due": "2026-11-12"}
    assert p["claims"][0]["previous_checks"][0]["verdict"] == "supported" and p["claims"][1]["previous_checks"] == []
    assert build_input(research(), "3m", date(2026, 8, 12))["period"]["from"] == "2026-05-12"


def test_merge_appends_flags_changes_and_rejects_bad_checks():
    r = research()
    out = AgentOutput.model_validate(good_output(r))
    rep = merge(r, out, "6m", 2, date(2026, 11, 12))
    assert rep["applied"] == ["C1", "C2"] and rep["changed"] == [{"claim": "C1", "from": "supported", "to": "outdated", "agent_said_changed": True}]
    c1 = r.claim("C1")
    assert [k.checkpoint for k in c1.checks] == ["at_meeting", "6m"] and c1.checks[0].verdict == "supported"  # append-only
    assert c1.checks[-1].by == "mistral-agent" and c1.checks[-1].agent_version == 2 and c1.checks[-1].sources[0].basis == "page_content"
    mark_done(r, "6m", date(2026, 11, 12), rep)
    assert next(c for c in r.checkpoints if c.label == "6m").done_on == "2026-11-12"

    r2 = research()  # verdict needing a source without one, an unknown claim, a missing claim
    bad = good_output(r2)
    bad["claim_checks"][0]["sources"] = []
    bad["claim_checks"].append({**bad["claim_checks"][1], "claim_id": "ZZ"})
    del bad["claim_checks"][1]
    rep2 = merge(r2, AgentOutput.model_validate(bad), "6m", None, date(2026, 11, 12))
    assert {x["item"] for x in rep2["rejected"]} == {"C1", "ZZ"} and rep2["missing"] == ["C2"] and rep2["applied"] == []
    mark_done(r2, "6m", date(2026, 11, 12), rep2)
    assert next(c for c in r2.checkpoints if c.label == "6m").done_on is None  # stays open when incomplete

    wrong = good_output(research(), meeting_uid="other")
    assert merge(research(), AgentOutput.model_validate(wrong), "6m", 1, date(2026, 11, 12))["rejected"][0]["item"] == "output"


class FakeConv:
    def __init__(self, answer):
        self.answer, self.kwargs = answer, None

    def start(self, **kw):
        self.kwargs = kw
        return NS(outputs=[NS(type="tool.execution", content=""), NS(type="message.output", content=[NS(text="```json\n"), NS(text=json.dumps(self.answer)), NS(text="\n```")])], usage=None)


def fake_client(answer, version=2, fail_get=False):
    def get(agent_id):
        if fail_get:
            raise RuntimeError("nope")
        return NS(version=version)

    conv = FakeConv(answer)
    return NS(beta=NS(agents=NS(get=get), conversations=conv)), conv


def test_latest_version_resolved_and_no_completion_args():
    r = research()
    cfg = {"agent_id": "ag_x", "agent_version": "latest", "temperature": 0.2}
    client, conv = fake_client(good_output(r), version=2)
    out, payload, version, _ = run_checkpoint(r, "6m", date(2026, 11, 12), client=client, config=cfg)
    assert version == 2 and conv.kwargs["agent_version"] == 2 and conv.kwargs["agent_id"] == "ag_x"
    assert "completion_args" not in conv.kwargs  # the API rejects completion_args for agent conversations
    assert json.loads(conv.kwargs["inputs"][0]["content"])["checkpoint"] == "6m" and out.claim_checks[0].claim_id == "C1"
    client3, _ = fake_client(good_output(r), version=3)
    assert run_checkpoint(r, "6m", date(2026, 11, 12), client=client3, config=cfg)[2] == 3  # follows the agent's newest version
    client_f, conv_f = fake_client(good_output(r), fail_get=True)
    assert resolve_version(client_f, "ag_x", "latest") is None
    run_checkpoint(r, "6m", date(2026, 11, 12), client=client_f, config=cfg)
    assert "agent_version" not in conv_f.kwargs  # lookup failed: omit it, API default applies
    assert resolve_version(client, "ag_x", 5) == 5  # explicit pin is honoured


def test_parse_response_errors():
    with pytest.raises(ValueError):
        parse_response(NS(outputs=[]))
    with pytest.raises(ValueError):
        parse_response(NS(outputs=[NS(type="message.output", content="no json here")]))


def test_schema_keeps_field_named_title():
    s = strict_schema(AgentOutput)
    src = s["properties"]["claim_checks"]["items"]["properties"]["sources"]["items"]
    assert set(src["properties"]) == {"title", "url", "tier", "basis", "published"} and set(src["required"]) == set(src["properties"])


def test_rate_limit_is_retried_and_raw_response_saved(tmp_path):
    r = research()
    client, conv = fake_client(good_output(r))
    real_start, calls = conv.start, {"n": 0}

    def flaky(**kw):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError('API error occurred: Status 429. Body: {"detail":"Token rate limit reached."}')
        return real_start(**kw)

    conv.start = flaky

    class Resp(NS):
        def model_dump_json(self, indent=None):
            return json.dumps({"outputs": "raw"})

    real = conv.start
    conv.start = lambda **kw: (lambda x: Resp(outputs=x.outputs, usage=None))(real(**kw))
    sink = tmp_path / "raw.json"
    cfg = {"agent_id": "ag_x", "agent_version": 2}
    out = run_checkpoint(r, "6m", date(2026, 11, 12), client=client, config=cfg, raw_sink=sink, wait_s=0, max_attempts=4)[0]
    assert calls["n"] == 3 and out.claim_checks and sink.exists()
    conv.start = lambda **kw: (_ for _ in ()).throw(RuntimeError("Status 500"))
    with pytest.raises(RuntimeError):
        run_checkpoint(r, "6m", date(2026, 11, 12), client=client, config=cfg, wait_s=0)


def test_parse_text_takes_first_json_and_ignores_fenced_duplicate_and_thinking():
    from parlwatch.research.mistral_agent import parse_text

    ex = json.dumps(good_output(research()))
    out = parse_text("Here you go.\n" + ex + "\n```json\n" + ex + "\n```")
    assert out.claim_checks[0].claim_id == "C1" and out.checkpoint == "6m"
    with pytest.raises(ValueError):
        parse_text("no braces at all")
    resp = NS(outputs=[NS(type="message.output", content=[NS(type="thinking", thinking="hmm", text=None), NS(type="text", text=ex)]),
                       NS(type="message.output", content=[NS(type="thinking", thinking="x", text=None)])])
    assert parse_response(resp).claim_checks  # empty-text trailing message is skipped


def src(url, **kw):
    return {"title": "P", "url": url, "tier": "primary", "basis": "page_content", "published": "2026-09-08", **kw}


def test_merge_grounds_urls_and_carries_forward_unchanged_verdicts():
    r = research()
    r.claim("C1").checks[0].sources = []
    r.topics[0].before[0].sources = []
    from parlwatch.research.schema import Source
    r.claim("C1").checks[0].sources = [Source(title="old", url="https://old.example/page/", tier="secondary", accessed="2026-10-09")]
    o = good_output(r)
    o["claim_checks"][0].update(verdict="supported", verdict_changed=False, sources=[src("https://old.example/page"), src("https://invented.example/x")])
    o["claim_checks"][1].update(verdict="partly_supported", verdict_changed=False, sources=[src("https://real.example/a")])
    rep = merge(r, AgentOutput.model_validate(o), "6m", 2, date(2026, 11, 12), seen_urls={"https://real.example/a"})
    assert rep["carried_forward"] == ["C1"]                                    # unchanged verdict, only a URL from the record -> carried forward
    assert rep["urls_dropped"] == [{"where": "C1", "url": "https://invented.example/x"}]
    assert rep["urls_not_retrieved"] == [{"where": "C1", "url": "https://old.example/page"}]
    c1 = r.claim("C1").checks[-1]
    assert c1.evidence.startswith("[carried forward") and c1.sources[0].basis == "unspecified" and "NOT retrieved" in c1.sources[0].note
    assert r.claim("C2").checks[-1].sources[0].url == "https://real.example/a"
    # a NEW verdict backed only by an unretrieved or invented URL is rejected
    r2 = research()
    o2 = good_output(r2)  # C1 supported -> outdated with a source that is not in the search results
    rep2 = merge(r2, AgentOutput.model_validate(o2), "6m", 2, date(2026, 11, 12), seen_urls={"https://other.example"})
    assert {"item": "C1", "reason": "new/changed verdict 'outdated' without a source retrieved in this run"} in rep2["rejected"]


def test_build_input_since_override():
    r = research()
    r.checkpoints[0].done_on = "2026-10-09"
    assert build_input(r, "3m", date(2026, 10, 9))["period"]["from"] == "2026-10-09"
    assert build_input(r, "3m", date(2026, 10, 9), since=date(2026, 5, 12))["period"]["from"] == "2026-05-12"


def test_blind_input_withholds_history_and_limits_are_sent():
    r = research()
    r.claim("C1").next_step = "look at X"
    b = build_input(r, "3m", date(2026, 10, 9), since=date(2026, 5, 12), blind=True, max_web_searches=12)
    assert all(c["previous_checks"] == [] and c["next_step"] == "" for c in b["claims"])
    assert b["topics"][0]["before"] == [] and b["queue"] == [] and "blind" in b["mode"] and b["limits"] == {"max_web_searches": 12}
    n = build_input(r, "3m", date(2026, 10, 9))
    assert n["claims"][0]["previous_checks"] and "mode" not in n and "limits" not in n


def test_daily_quota_stops_immediately_without_retry():
    from parlwatch.research.mistral_agent import DailyQuotaExhausted

    r = research()
    client, conv = fake_client(good_output(r))
    calls = {"n": 0}

    class Err(Exception):
        headers = {"x-ratelimit-remaining-web-search-day": "0", "x-ratelimit-remaining-web-search-minute": "2"}

    def start(**kw):
        calls["n"] += 1
        raise Err('Status 429. Body: {"detail":"web_search rate limit reached."}')

    conv.start = start
    with pytest.raises(DailyQuotaExhausted):
        run_checkpoint(r, "6m", date(2026, 11, 12), client=client, config={"agent_id": "a", "agent_version": 2}, wait_s=0, max_attempts=4)
    assert calls["n"] == 1  # no pointless waiting


def test_context_dimensions_in_input_and_new_topics_merge():
    from parlwatch.research.coverage import coverage, gaps
    from parlwatch.research.schema import DIMENSIONS

    r = research()
    r.topics[0].dimension = "supply"
    p = build_input(r, "6m", date(2026, 11, 12))
    assert set(p["context_dimensions"]) == set(DIMENSIONS) and {c["dimension"]: c["status"] for c in p["coverage"]}["supply"] == "covered"
    assert "demand" in gaps(r) and {c["dimension"]: c["status"] for c in coverage(r)}["demand"] == "missing"
    o = good_output(r)
    f = lambda d, s: {"date": d, "summary": s, "sources": [src("https://example.org/a")]}  # noqa: E731
    o["new_topics"] = [
        {"id": "demand", "title": "Compute demand", "dimension": "demand", "why_it_matters": "w", "findings": [f("2026-03", "before"), f("2026-09", "after"), f("2027-01", "future")]},
        {"id": "t1", "title": "dup", "dimension": "supply", "why_it_matters": "w", "findings": [f("2026-03", "x")]},
        {"id": "empty", "title": "nothing", "dimension": "finance", "why_it_matters": "w", "findings": [f("2030-01", "future only")]}]
    o["coverage_notes"] = [{"dimension": "technology", "status": "not_relevant", "note": "hearing is about procurement"}]
    rep = merge(r, AgentOutput.model_validate(o), "6m", 2, date(2026, 11, 12), seen_urls={"https://example.org/a"})
    new = next(t for t in r.topics if t.id == "demand")
    assert rep["new_topics"] == ["demand"] and [x["item"] for x in rep["new_topics_rejected"]] == ["t1", "empty"]
    assert [x.summary for x in new.before] == ["before"] and [x.summary for x in new.after] == ["after"]  # filed by date, future dropped
    assert r.dimension_notes["technology"].startswith("not relevant")
    assert {c["dimension"]: c["status"] for c in coverage(r)}["demand"] == "covered" and "demand" not in gaps(r)


def test_merge_refuses_true_false_verdicts_on_forecasts_and_opinions():
    r = research()
    r.claims.append(Claim(id="C3", speaker="C", time="00:03:00", text="it will never exist", kind="forecast"))
    r.claims.append(Claim(id="C4", speaker="D", time="00:04:00", text="we should do X", kind="policy_position"))
    r.claims.append(Claim(id="C5", speaker="E", time="00:05:00", text="it will be 5 by 2030", kind="forecast"))
    o = good_output(r)
    base = o["claim_checks"][1]
    o["claim_checks"] = [c for c in o["claim_checks"] if c["claim_id"] in ("C1", "C2")]  # the sample already has an entry per claim
    s_ok = [src("https://example.org/a")]
    o["claim_checks"] += [{**base, "claim_id": "C3", "verdict": "contradicted", "sources": s_ok}, {**base, "claim_id": "C4", "verdict": "supported", "sources": s_ok},
                          {**base, "claim_id": "C5", "verdict": "pending", "sources": []}]
    rep = merge(r, AgentOutput.model_validate(o), "6m", 2, date(2026, 11, 12), seen_urls={"https://example.org/a"})
    assert {x["item"] for x in rep["rejected"]} == {"C3", "C4"} and "C5" in rep["applied"]
    assert all("enforced in code" in x["reason"] for x in rep["rejected"])
