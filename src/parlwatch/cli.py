import json
from pathlib import Path
from typing import Annotated

import typer
from rich import print
from rich.table import Table

from parlwatch.db.session import init_db
from parlwatch.settings import get_settings, load_env
from parlwatch.topics.registry import TopicRegistry

app = typer.Typer(no_args_is_help=True, help="ParlWatch: parliament meetings -> topic stance database")
topic_app = typer.Typer(no_args_is_help=True, help="Manage search topics (any topic, any language)")
app.add_typer(topic_app, name="topic")
research_app = typer.Typer(no_args_is_help=True, help="Context before/after a meeting and claim checks at 3/6/12 months")
app.add_typer(research_app, name="research")


def _registry() -> TopicRegistry:
    return TopicRegistry(get_settings().configs_dir / "topics.yaml")


@app.callback()
def _main() -> None:
    load_env()


@app.command()
def init() -> None:
    """Create the database tables."""
    init_db()
    print(f"[green]ok[/green] database at {get_settings().database_url}")


@topic_app.command("add")
def topic_add(
    name: Annotated[str, typer.Argument(help="short id, e.g. nuclear")],
    terms: Annotated[list[str], typer.Argument(help="seed search terms")],
    lang: Annotated[str, typer.Option(help="language of the seed terms")] = "en",
    label: Annotated[str, typer.Option(help="human label")] = "",
) -> None:
    """Add a topic (or more seed terms to one). Translate afterwards with `pw topic translate`."""
    reg = _registry()
    reg.add(name, label or name, lang, terms)
    reg.save()
    print(f"[green]ok[/green] topic {name!r} \\[{lang}]: {', '.join(reg.terms(name, lang))}")


@topic_app.command("list")
def topic_list() -> None:
    reg = _registry()
    t = Table("topic", "language", "terms", "status")
    for name in reg.names():
        d = reg.data["topics"][name]
        for lang, ts in d.get("terms", {}).items():
            t.add_row(name, lang, ", ".join(ts), "seed")
        for lang, g in (d.get("generated") or {}).items():
            t.add_row(name, lang, ", ".join(g["terms"]), "reviewed" if g.get("reviewed") else "[yellow]generated, unreviewed[/yellow]")
    print(t)


@topic_app.command("translate")
def topic_translate(name: str, lang: Annotated[str, typer.Option(help="target language: fr de nl es")]) -> None:
    """LLM-translate/expand a topic's terms into LANG. Result is stored unreviewed."""
    from parlwatch.llm import get_router
    from parlwatch.topics.translate import translate_terms

    reg = _registry()
    d = reg.data["topics"][name]
    terms, model = translate_terms(get_router(), d["label"], d.get("terms", {}), lang)
    reg.set_generated(name, lang, terms, model)
    reg.save()
    print(f"[green]ok[/green] {len(terms)} {lang} terms from {model} (unreviewed): {', '.join(terms)}")
    print(f"Review/edit configs/topics.yaml, then `pw topic approve {name} --lang {lang}`")


@topic_app.command("approve")
def topic_approve(name: str, lang: Annotated[str, typer.Option()]) -> None:
    reg = _registry()
    reg.data["topics"][name]["generated"][lang]["reviewed"] = True
    reg.save()
    print(f"[green]ok[/green] {name} \\[{lang}] approved")


@app.command()
def transcribe(
    url: Annotated[str, typer.Argument(help="AN video page url")],
    quant: Annotated[str, typer.Option(help="whisper quantization: q4 | q8")] = "q8",
    keep_audio: Annotated[bool, typer.Option(help="keep the downloaded mp3")] = False,
) -> None:
    """Download a French Assemblée video's audio and transcribe it locally."""
    from parlwatch.pipeline import process_video

    out = process_video(url, get_settings().data_dir / "meetings", quant=quant, keep_audio=keep_audio)
    print(f"[green]ok[/green] {out}")


def _saved_version(d: Path, stem: str) -> int | None:
    f = d / "agent_runs" / f"{stem}_agent.json"
    return json.loads(f.read_text()).get("agent_version") if f.exists() else None


def _hms_to_s(v: str) -> float:
    parts = [float(x) for x in v.split(":")]
    return sum(p * 60**i for i, p in enumerate(reversed(parts)))


@app.command()
def clean(uid: Annotated[str, typer.Argument(help="meeting folder name under data/meetings")]) -> None:
    """Drop ASR hallucinations, fix names from the portal speaker list, merge into sentences."""
    from parlwatch.transcripts.postprocess import postprocess

    stats = postprocess(get_settings().data_dir / "meetings" / uid)
    print(f"[green]ok[/green] {stats}")


@app.command()
def analyze(
    uid: Annotated[str, typer.Argument()],
    start: Annotated[str, typer.Option("--from", help="hh:mm:ss")] = "00:00:00",
    end: Annotated[str, typer.Option("--to", help="hh:mm:ss")] = "99:00:00",
    context: Annotated[str, typer.Option(help="what this hearing is; defaults to the portal title")] = "",
    label: Annotated[str, typer.Option(help="suffix for output files")] = "",
    max_windows: Annotated[int, typer.Option(help="debug: analyse only the first N windows")] = 0,
) -> None:
    """Extract Q&A, positions (quotes verified) and a summary from a cleaned transcript."""
    import json
    import re

    from parlwatch.analyze.run import analyse, load_sentences, make_windows, to_markdown
    from parlwatch.llm import get_router

    d = get_settings().data_dir / "meetings" / uid
    meta = json.loads((d / "meta.json").read_text())
    date = (m := re.search(r"(\d{4})(\d{2})(\d{2})\d{6}\.mp3", meta.get("audio_url") or "")) and "-".join(m.groups()) or "?"
    sentences = load_sentences(d)
    a, b = _hms_to_s(start), _hms_to_s(end)
    if max_windows:
        b = make_windows(sentences, a, b)[max_windows - 1][-1]["start_s"]
    seq = [c["label"].strip() for c in meta["chapters"] if c["type"] == "Intervention"]
    order = " → ".join(f"{i + 1}. {x}" for i, x in enumerate(seq)) or "(not available)"
    res = analyse(get_router(), sentences, a, b, context or meta["title"], date, list(meta["speakers"].values()), order=order)
    suffix = f"_{label}" if label else ""
    (d / f"analysis{suffix}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    (d / f"brief{suffix}.md").write_text(to_markdown(res, context or meta["title"]))
    print(f"[green]ok[/green] {res['windows']} windows, {len(res['qa'])} Q&A, {len(res['positions'])} positions, "
          f"{len(res['failed_windows'])} failed -> {d / f'brief{suffix}.md'}")


@app.command()
def translate(
    uid: Annotated[str, typer.Argument()],
    start: Annotated[str, typer.Option("--from", help="hh:mm:ss")] = "00:00:00",
    end: Annotated[str, typer.Option("--to", help="hh:mm:ss")] = "99:00:00",
    label: Annotated[str, typer.Option(help="analysis label to translate too (e.g. full, mistral); empty = transcript only")] = "",
    title: Annotated[str, typer.Option(help="brief title (English)")] = "",
    lang: Annotated[str, typer.Option(help="target language")] = "en",
) -> None:
    """Machine-translate the cleaned transcript (and an analysis/brief) with the free LLM router."""
    import json

    from parlwatch.analyze.run import to_markdown
    from parlwatch.llm import get_router
    from parlwatch.pipeline import hms
    from parlwatch.transcripts.translate import translate_analysis, translate_texts

    d = get_settings().data_dir / "meetings" / uid
    router = get_router()
    a_s, b_s = _hms_to_s(start), _hms_to_s(end)
    sents = [x for x in json.loads((d / "sentences.json").read_text()) if a_s <= x["start_s"] <= b_s]
    tr, flags = translate_texts(router, [x["text"] for x in sents], "fr", lang)
    (d / f"transcript_{lang}_flags.json").write_text(json.dumps([{"t": hms(sents[i]["start_s"]), "fr": sents[i]["text"], lang: tr[i]} for i in flags],
                                                                ensure_ascii=False, indent=1))
    (d / f"transcript_{lang}.txt").write_text("\n".join(f"[{hms(x['start_s'])}] {t}" for x, t in zip(sents, tr, strict=True)))
    print(f"[green]ok[/green] {len(sents)} sentences -> transcript_{lang}.txt ({len(flags)} flagged for figure review)")
    if label:
        a = json.loads((d / f"analysis_{label}.json").read_text())
        en = translate_analysis(router, a, "fr", lang)
        (d / f"analysis_{label}_{lang}.json").write_text(json.dumps(en, ensure_ascii=False, indent=1))
        (d / f"brief_{label}_{lang}.md").write_text(to_markdown(en, title or a["context"], lang))
        print(f"[green]ok[/green] brief_{label}_{lang}.md")


@research_app.command("init")
def research_init(uid: str, meeting_date: Annotated[str, typer.Option("--date", help="meeting date YYYY-MM-DD")], title: Annotated[str, typer.Option()] = "") -> None:
    """Create research.json with the 3/6/12-month checkpoints (add topics/claims by hand or with Claude Code)."""
    from datetime import date as _d

    from parlwatch.research.checkpoints import make_checkpoints
    from parlwatch.research.schema import Research, today_iso

    d = get_settings().data_dir / "meetings" / uid
    if (d / "research.json").exists():
        raise typer.BadParameter("research.json already exists")
    r = Research(meeting_uid=uid, title=title or uid, meeting_date=meeting_date, researched_on=today_iso(),
                 checkpoints=make_checkpoints(_d.fromisoformat(meeting_date)))
    (d / "research.json").write_text(r.model_dump_json(indent=1))
    print(f"[green]ok[/green] {d / 'research.json'}")


@research_app.command("due")
def research_due(today: Annotated[str, typer.Option(help="override today's date, YYYY-MM-DD")] = "") -> None:
    """List follow-up checkpoints that are due (or coming up) across all meetings."""
    from datetime import date as _d

    from parlwatch.research.checkpoints import due_checkpoints, upcoming
    from parlwatch.research.schema import Research

    t = _d.fromisoformat(today) if today else _d.today()
    tb = Table("meeting", "checkpoint", "due", "state")
    for f in sorted((get_settings().data_dir / "meetings").glob("*/research.json")):
        r = Research.model_validate_json(f.read_text())
        for c in due_checkpoints(r, t):
            tb.add_row(r.title[:60], c.label, c.due, f"[red]due ({(t - _d.fromisoformat(c.due)).days} days ago)[/red]")
        for c in upcoming(r, t):
            tb.add_row(r.title[:60], c.label, c.due, f"in {(_d.fromisoformat(c.due) - t).days} days")
    print(tb)


@research_app.command("coverage")
def research_coverage(uid: Annotated[str, typer.Argument(help="meeting folder; omit for all meetings")] = "") -> None:
    """Show which context dimensions (supply, demand, regulation, finance, energy, geopolitics, technology) are researched for a meeting."""
    from parlwatch.research.coverage import coverage
    from parlwatch.research.schema import Research

    base = get_settings().data_dir / "meetings"
    files = [base / uid / "research.json"] if uid else sorted(base.glob("*/research.json"))
    for f in files:
        r = Research.model_validate_json(f.read_text())
        tb = Table("dimension", "status", "topics", "before", "after", title=r.title[:70])
        for c in coverage(r):
            col = {"covered": "green", "partial": "yellow", "missing": "red", "not_relevant": "dim"}[c["status"]]
            tb.add_row(c["dimension"], f"[{col}]{c['status']}[/{col}]", ", ".join(c["topics"]) or "-", str(c["findings_before"]), str(c["findings_after"]))
        print(tb)


@research_app.command("render")
def research_render(uid: str) -> None:
    """Render research.json to research.md."""
    from parlwatch.research.render import to_markdown
    from parlwatch.research.schema import Research

    d = get_settings().data_dir / "meetings" / uid
    (d / "research.md").write_text(to_markdown(Research.model_validate_json((d / "research.json").read_text())))
    print(f"[green]ok[/green] {d / 'research.md'}")


@research_app.command("agent")
def research_agent(
    uid: str,
    checkpoint: Annotated[str, typer.Option(help="3m | 6m | 12m")],
    apply: Annotated[bool, typer.Option(help="write the checks into research.json (default: dry run, nothing is changed)")] = False,
    today: Annotated[str, typer.Option(help="override today's date, YYYY-MM-DD")] = "",
    from_raw: Annotated[str, typer.Option("--from-raw", help="re-parse a saved *_raw_response.json instead of calling the agent")] = "",
    since: Annotated[str, typer.Option(help="start of the period to examine, YYYY-MM-DD (default: latest done checkpoint)")] = "",
    blind: Annotated[bool, typer.Option(help="withhold our earlier verdicts: an independent second opinion. Never applied; reports agreement")] = False,
    backend: Annotated[str, typer.Option(help="mistral = Mistral Studio agent; openai = OpenAI Agents SDK + Nemotron + DuckDuckGo (this package)")] = "mistral",
) -> None:
    """Run a follow-up checkpoint through a research agent. Dry run unless --apply; the raw answer is always saved."""
    import copy
    import json
    from datetime import date as _d

    from parlwatch.research.agent_io import mark_done, merge
    from parlwatch.research.mistral_agent import run_checkpoint
    from parlwatch.research.render import to_markdown
    from parlwatch.research.schema import Research

    t = _d.fromisoformat(today) if today else _d.today()
    if blind and apply:
        raise typer.BadParameter("--blind is a second opinion for comparison and is never applied")
    d = get_settings().data_dir / "meetings" / uid
    r = Research.model_validate_json((d / "research.json").read_text())
    if checkpoint not in {c.label for c in r.checkpoints}:
        raise typer.BadParameter(f"unknown checkpoint {checkpoint!r}")
    runs = d / "agent_runs"
    runs.mkdir(exist_ok=True)
    stem = f"{t.isoformat()}_{checkpoint}"
    if backend not in ("mistral", "openai"):
        raise typer.BadParameter("backend must be mistral or openai")
    since_d = _d.fromisoformat(since) if since else None
    fetched_urls: set[str] | None = None
    by = "mistral-agent"
    if backend == "openai":
        from parlwatch.research.agent_io import build_input
        from parlwatch.research.openai_agent import load_config as oa_config
        from parlwatch.research.openai_agent import run_checkpoint_oa
        from parlwatch.websearch.base import Ledger

        trace = runs / f"{stem}_oa_trace.json"
        cfg = oa_config()
        by, version = f"openai-agents:{cfg['model'].split('/')[-1].split(':')[0]}", None
        if from_raw:
            from parlwatch.research.mistral_agent import parse_text

            tr = json.loads(Path(from_raw).read_text())
            out, usage, payload = parse_text(tr["final_text"]), str(tr["usage"]), build_input(r, checkpoint, t, since_d, blind)
            led = Ledger()
            led.searches, led.fetches = tr["ledger"]["searches"], tr["ledger"]["fetches"]
        else:
            res = run_checkpoint_oa(r, checkpoint, t, cfg, since_d, blind, trace_sink=trace)
            out, payload, usage, led = res.output, res.payload, str(res.usage), res.ledger
        seen_urls, fetched_urls = led.seen_urls(), led.fetched_urls()
        print(f"web searches: {len(led.searches)} · pages fetched: {sum(f['ok'] for f in led.fetches)} of {len(led.fetches)} attempts")
    else:
        if from_raw:
            from parlwatch.research.agent_io import build_input
            from parlwatch.research.mistral_agent import parse_raw_file

            meta_f = Path(from_raw.replace("_raw_response", "_run_meta"))
            meta_run = json.loads(meta_f.read_text()) if meta_f.exists() else {}
            out, usage = parse_raw_file(Path(from_raw)), "re-parsed from saved response"
            payload = build_input(r, checkpoint, t, since_d, blind)
            version = meta_run.get("agent_version")
        else:
            out, payload, version, usage = run_checkpoint(r, checkpoint, t, raw_sink=runs / f"{stem}_raw_response.json", since=since_d, blind=blind)
        from parlwatch.research.mistral_agent import urls_in_search

        raw_path = Path(from_raw) if from_raw else runs / f"{stem}_raw_response.json"
        seen_urls = urls_in_search(json.loads(raw_path.read_text())) if raw_path.exists() else None
    work = r if apply else copy.deepcopy(r)
    if apply:
        (runs / f"{stem}_research_before.json").write_text(r.model_dump_json(indent=1))
    report = merge(work, out, checkpoint, version, t, seen_urls, by, fetched_urls)
    mark_done(work, checkpoint, t, report)
    (runs / f"{stem}_agent.json").write_text(json.dumps(
        {"backend": backend, "by": by, "agent_version": version, "usage": str(usage), "input": payload, "output": out.model_dump(), "merge_report": report}, ensure_ascii=False, indent=1))
    tb = Table("claim", "applied", "note")
    for c in report["applied"]:
        tb.add_row(c, "yes", "")
    for x in report["rejected"]:
        tb.add_row(x["item"], "[red]rejected[/red]", x["reason"])
    for c in report["missing"]:
        tb.add_row(c, "[yellow]missing[/yellow]", "the agent returned no check for this claim")
    print(tb)
    if report["carried_forward"]:
        print(f"carried forward (unchanged, no new evidence): {', '.join(report['carried_forward'])}")
    for u in report["urls_dropped"]:
        print(f"[red]dropped a URL not found in the agent's search results[/red] ({u['where']}): {u['url']}")
    if report.get("basis_downgraded"):
        print(f"[yellow]{len(report['basis_downgraded'])} source(s) claimed a full page read that the agent never fetched: downgraded[/yellow]")
    if report["urls_not_retrieved"]:
        print(f"[yellow]{len(report['urls_not_retrieved'])} cited URL(s) came from the earlier record, not from this run's search[/yellow]")
    if blind:
        same = [c for c in out.claim_checks if c.claim_id in {x.id for x in r.claims} and r.claim(c.claim_id).checks and r.claim(c.claim_id).checks[-1].verdict == c.verdict]
        total = [c for c in out.claim_checks if c.claim_id in {x.id for x in r.claims} and r.claim(c.claim_id).checks]
        print(f"[bold]blind comparison[/bold]: agent agrees with our latest verdict on {len(same)} of {len(total)} claims")
        for c in total:
            mine = r.claim(c.claim_id).checks[-1].verdict
            if mine != c.verdict:
                print(f"  {c.claim_id}: ours {mine} | agent {c.verdict} ({c.confidence}): {c.evidence[:160]}")
    for ch in report["changed"]:
        print(f"[bold]verdict changed[/bold] {ch['claim']}: {ch['from']} -> {ch['to']}")
    print(f"{by} · agent version: {version} · topic updates: {report['topics_added']} · summary:\n{out.summary}")
    if apply:
        (d / "research.json").write_text(r.model_dump_json(indent=1))
        (d / "research.md").write_text(to_markdown(r))
        print(f"[green]applied[/green] research.json and research.md updated (previous copy in {runs}/{stem}_research_before.json)")
    else:
        print("[yellow]dry run[/yellow]: nothing changed. Review the saved answer, then rerun with --apply.")


@research_app.command("extract")
def research_extract(uid: str, start: Annotated[str, typer.Option("--from")] = "00:00:00", end: Annotated[str, typer.Option("--to")] = "99:00:00",
                     context: Annotated[str, typer.Option()] = "") -> None:
    """Ask the LLM to propose checkable claims (candidates.json); a person confirms which to research."""
    import json

    from parlwatch.llm import get_router
    from parlwatch.research.extract import extract_candidates

    d = get_settings().data_dir / "meetings" / uid
    meta = json.loads((d / "meta.json").read_text())
    c = extract_candidates(get_router(), json.loads((d / "sentences.json").read_text()), _hms_to_s(start), _hms_to_s(end),
                           context or meta["title"], list(meta["speakers"].values()))
    (d / "research_candidates.json").write_text(json.dumps(c, ensure_ascii=False, indent=1))
    print(f"[green]ok[/green] {len(c)} candidates ({sum(x['quote_verified'] for x in c)} with verbatim quotes)")


if __name__ == "__main__":
    app()
