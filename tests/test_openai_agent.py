import json
from datetime import date

from test_agent import good_output, research  # noqa: F401  (shared fixtures)

from parlwatch.research.agent_io import merge
from parlwatch.research.openai_agent import make_tool_functions, run_checkpoint_oa
from parlwatch.websearch.base import Ledger, Page, SearchError, SearchResult

CFG = {"model": "nvidia/nemotron-x:free", "max_web_searches": 2, "max_page_fetches": 1, "fetch_chars": 500}


class FakeSearcher:
    def __init__(self):
        self.calls = []

    def search(self, query, kind="web", region="wt-wt", recent="any", max_results=6):
        self.calls.append((query, kind, region, recent))
        if query == "boom":
            raise SearchError("DuckDuckGo search failed", retryable=True)
        return [SearchResult("Official", "https://real.example/a", "snip", "2026-09-08")] if query != "none" else []


def fake_fetch(url, max_chars=6000):
    if "bad" in url:
        raise SearchError("HTTP 404")
    return Page(url=url, title="T", date="2026-09-08", text="Body text " * 10, truncated=False)


def test_tools_enforce_budgets_record_everything_and_mark_untrusted():
    led = Ledger(2, 1)
    fns = make_tool_functions(led, FakeSearcher(), 500, fake_fetch)
    assert json.loads(fns["web_search"]("q1"))[0]["url"] == "https://real.example/a"
    assert fns["web_search"]("boom").startswith("ERROR")           # a failed search still costs budget
    assert "budget exhausted" in fns["web_search"]("q3") and len(led.searches) == 2
    page = fns["fetch_page"]("https://real.example/a")
    assert page.startswith("PAGE (untrusted web content") and "Body text" in page and "DATE: 2026-09-08" in page
    assert "budget exhausted" in fns["fetch_page"]("https://other.example") and len(led.fetches) == 1
    assert led.fetched_urls() == {"https://real.example/a"}
    led2 = Ledger(5, 5)
    f2 = make_tool_functions(led2, FakeSearcher(), 500, fake_fetch)
    assert f2["web_search"]("none").startswith("No results")
    assert f2["fetch_page"]("https://bad.example").startswith("ERROR: HTTP 404") and led2.fetches[0]["ok"] is False


def src(url, basis="page_content"):
    return {"title": "P", "url": url, "tier": "primary", "basis": basis, "published": "2026-09-08"}


def test_run_with_fake_runner_checks_pages_and_downgrades_unfetched_claims():
    r = research()
    sent = {}

    def runner(instructions, fns, cfg, messages):
        sent["instructions"], sent["tools"], sent["payload"] = instructions, set(fns), json.loads(messages[0]["content"])
        fns["web_search"]("ovhcloud")
        fns["fetch_page"]("https://real.example/a")
        o = good_output(r)
        o["claim_checks"][0]["sources"] = [src("https://real.example/a")]                       # fetched: page_content stays
        o["claim_checks"][1].update(verdict="partly_supported", verdict_changed=False, confidence="high",
                                    sources=[src("https://real.example/b")])                     # searched? no -> must be dropped
        return "Sure.\n" + json.dumps(o), {"requests": 3, "input_tokens": 10, "output_tokens": 5, "total_tokens": 15}, []

    res = run_checkpoint_oa(r, "6m", date(2026, 11, 12), CFG, runner=runner, searcher=FakeSearcher(), fetcher=fake_fetch)
    assert "TOOLS (this deployment)" in sent["instructions"] and sent["tools"] == {"web_search", "fetch_page"}
    assert sent["payload"]["limits"] == {"max_web_searches": 2, "max_page_fetches": 1}
    assert len(res.ledger.searches) == 1 and res.ledger.fetched_urls() == {"https://real.example/a"}
    rep = merge(r, res.output, "6m", None, date(2026, 11, 12), res.ledger.seen_urls(), "openai-agents:nemotron", res.ledger.fetched_urls())
    assert rep["urls_dropped"] == [{"where": "C2", "url": "https://real.example/b"}]
    assert [x["item"] for x in rep["rejected"]] == ["C2"] and rep["applied"] == ["C1"]  # a new verdict whose only URL was invented is rejected
    c1 = r.claim("C1").checks[-1]
    assert c1.by == "openai-agents:nemotron" and c1.sources[0].basis == "page_content"


def test_unfetched_page_content_claim_is_downgraded():
    r = research()

    def runner(instructions, fns, cfg, messages):
        fns["web_search"]("q")  # result URL https://real.example/a is seen but never fetched
        o = good_output(r)
        o["claim_checks"][0]["sources"] = [src("https://real.example/a", "page_content")]
        return json.dumps(o), {}, []

    res = run_checkpoint_oa(r, "6m", date(2026, 11, 12), CFG, runner=runner, searcher=FakeSearcher(), fetcher=fake_fetch)
    rep = merge(r, res.output, "6m", None, date(2026, 11, 12), res.ledger.seen_urls(), "x", res.ledger.fetched_urls())
    s = r.claim("C1").checks[-1].sources[0]
    assert s.basis == "search_snippet" and "NOT fetched" in s.note and rep["basis_downgraded"] == [{"where": "C1", "url": "https://real.example/a"}]


def test_invalid_json_gets_one_repair_turn_and_usage_is_summed(tmp_path):
    r = research()
    calls = []

    def runner(instructions, fns, cfg, messages):
        calls.append((len(fns), messages[-1]["content"][:30]))
        if len(calls) == 1:
            return "I could not produce JSON", {"requests": 1, "input_tokens": 10, "output_tokens": 1, "total_tokens": 11}, [{"role": "assistant", "content": "x"}]
        return json.dumps(good_output(r)), {"requests": 1, "input_tokens": 5, "output_tokens": 2, "total_tokens": 7}, []

    res = run_checkpoint_oa(r, "6m", date(2026, 11, 12), CFG, runner=runner, searcher=FakeSearcher(), fetcher=fake_fetch, trace_sink=tmp_path / "t.json")
    assert res.repaired and res.usage["total_tokens"] == 18 and calls[1][0] == 0 and "not valid" in calls[1][1]  # no tools in the repair turn
    assert json.loads((tmp_path / "t.json").read_text())["repaired"] is True


def test_instructions_carry_a_valid_example_and_repair_gets_compact_errors_and_structured_mode():
    from parlwatch.research.agent_io import AgentOutput, compact_errors, shape_example

    AgentOutput.model_validate_json(shape_example())  # the example shown to the model is itself valid
    r = research()
    seen = {}

    def runner(instructions, fns, cfg, messages):
        seen.setdefault("instr", instructions)
        seen.setdefault("structured", []).append(cfg.get("structured", False))
        if len(seen["structured"]) == 1:
            bad = {"meeting_uid": "m1", "checkpoint": "6m", "checked_on": "2026-11-12", "claim_checks": [{"claim_id": "C1", "verdict": "supported",
                   "evidence": "x", "sources": ["https://a.example"]}], "topic_updates": [{"topic": "t1", "description": "d", "sources": []}]}
            seen["fix_args"] = None
            return json.dumps(bad), {}, [{"role": "assistant", "content": "x"}]
        seen["fix"] = messages[-1]["content"]
        return json.dumps(good_output(r)), {}, []

    res = run_checkpoint_oa(r, "6m", date(2026, 11, 12), CFG, runner=runner, searcher=FakeSearcher(), fetcher=fake_fetch)
    assert res.repaired and seen["structured"] == [False, True]  # the repair turn asks for schema-constrained decoding
    assert "REQUIRED JSON SHAPE" in seen["instr"] and "claim_checks" in seen["instr"]
    assert "topic_updates.0.topic_id: Field required" in seen["fix"] and "claim_checks.0.sources.0" in seen["fix"]
    assert compact_errors(ValueError("plain")) == "plain"


def test_batches_split_claims_each_with_own_budget_and_combine():
    r = research()  # claims C1, C2; context gaps exist (no topic dimension set)
    cfg = {**CFG, "claims_per_run": 1}
    runs = []

    def runner(instructions, fns, cfg_, messages):
        p = json.loads(messages[0]["content"])
        runs.append(([c["id"] for c in p["claims"]], "coverage" in p))
        fns["web_search"]("q")
        o = good_output(r)
        o["claim_checks"] = [c for c in o["claim_checks"] if c["claim_id"] in [x["id"] for x in p["claims"]]]
        o["claim_checks"] = [{**c, "sources": [src("https://real.example/a")] if c["verdict"] == "outdated" else []} for c in o["claim_checks"]]
        return json.dumps(o), {"requests": 1, "input_tokens": 1, "output_tokens": 1, "total_tokens": 2}, []

    res = run_checkpoint_oa(r, "6m", date(2026, 11, 12), cfg, runner=runner, searcher=FakeSearcher(), fetcher=fake_fetch)
    assert runs == [(["C1"], False), (["C2"], False), ([], True)]      # one claim per run, then a context-only run
    assert [c.claim_id for c in res.output.claim_checks] == ["C1", "C2"] and res.usage["total_tokens"] == 6
    assert len(res.ledger.searches) == 3                                # ledgers of the three runs are combined (budget is per run)
    single = run_checkpoint_oa(r, "6m", date(2026, 11, 12), {**CFG}, runner=runner, searcher=FakeSearcher(), fetcher=fake_fetch)
    assert len(single.output.claim_checks) == 2                         # without claims_per_run: one run, as before


def test_budgets_scale_with_the_number_of_claims_in_a_run():
    r = research()
    cfg = {**CFG, "claims_per_run": 2, "searches_per_claim": 4, "fetches_per_claim": 3, "context_searches": 7, "context_fetches": 5}
    seen = []

    def runner(instructions, fns, cfg_, messages):
        p = json.loads(messages[0]["content"])
        seen.append((len(p["claims"]), p["limits"]))
        return json.dumps({**good_output(r), "claim_checks": [c for c in good_output(r)["claim_checks"] if c["claim_id"] in [x["id"] for x in p["claims"]]]}), {}, []

    run_checkpoint_oa(r, "6m", date(2026, 11, 12), cfg, runner=runner, searcher=FakeSearcher(), fetcher=fake_fetch)
    assert seen == [(2, {"max_web_searches": 8, "max_page_fetches": 6}), (0, {"max_web_searches": 7, "max_page_fetches": 5})]
