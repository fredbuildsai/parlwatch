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


def test_latest_version_resolved_and_response_format_enforced():
    r = research()
    cfg = {"agent_id": "ag_x", "agent_version": "latest", "temperature": 0.2}
    client, conv = fake_client(good_output(r), version=2)
    out, payload, version, _ = run_checkpoint(r, "6m", date(2026, 11, 12), client=client, config=cfg)
    assert version == 2 and conv.kwargs["agent_version"] == 2 and conv.kwargs["agent_id"] == "ag_x"
    assert conv.kwargs["completion_args"]["response_format"]["json_schema"]["strict"] is True
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
