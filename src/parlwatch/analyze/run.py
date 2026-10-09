"""Map-reduce analysis of a cleaned hearing: Q&A pairs, positions (quotes verified verbatim), summary."""

import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from llmrouter_free import json_schema_response_format, json_validator

from parlwatch.analyze.schemas import Overall, WindowOut
from parlwatch.pipeline import hms

SUBTOPICS = ("regulation, sovereignty, compute_infrastructure, open_source, funding_investment, energy, "
             "jobs_skills, copyright_data, security, public_procurement, competition, other")

MAP_PROMPT = """You analyse a transcript excerpt of a French National Assembly hearing, to study what politicians and witnesses
say about artificial intelligence, cloud and the digital economy.

HEARING: {context}
DATE: {date}
PARTICIPANTS (exact spellings): {participants}
OFFICIAL ORDER OF INTERVENTIONS from the Assembly's video index (a speaker may take several turns; some turns can be merged
or missing): {order}

The transcript comes from speech recognition WITHOUT speaker labels. Identify speakers ONLY from explicit cues in the text
("La parole est à Mme X", "Merci Madame X", "Monsieur le Président", the witness answering) combined with the official order.
Consecutive questions with no hand-over cue come from the SAME person: never spread them across different people. A name
from the participant list may be used only when a cue supports it; otherwise write "Unknown deputy" or "Unknown". Never invent names.
The witness is the person the hearing was convened for; the chair opens, gives the floor and may ask the first questions.
Recognition errors exist; interpret them sensibly but never alter a quote.

TRANSCRIPT EXCERPT (each line starts with its [hh:mm:ss] time):
{text}

Return JSON with:
- qa: up to 10 substantive questions that START in this excerpt, each with its answer. Questions are often asked in a block,
  then the witness speaks (an opening statement, then answers). Pair EACH question with the part of the answer that addresses
  it, even if that comes minutes later: `answer` = a paraphrase in French, at most 60 words, specific to THAT question, never
  a copy of the transcript or the same answer for several questions. `answer_time` = where that answer starts. If the answer is
  not in the excerpt, set answered=false and answer="". Times are plain hh:mm:ss without brackets. Skip procedure and thanks.
  ai_relevant is true when the exchange concerns AI, algorithms, data or computing power; subtopics from: {subtopics}.
- positions: up to 8 clear positions on AI, cloud/data centres, digital sovereignty or digital regulation, by the witness or a
  deputy (not procedural remarks, not facts about the company's history). Say what it is about in `target` and the speaker's
  stance towards it. `claim` is your own one-sentence paraphrase; `quote` is copied VERBATIM from the excerpt (max 35 words).
- window_summary: 3-5 sentences in French.
If the excerpt has nothing substantive, return empty lists."""

REDUCE_PROMPT = """Below are summaries and extracted items from consecutive parts of one French National Assembly hearing.

HEARING: {context}
DATE: {date}

PART SUMMARIES:
{summaries}

KEY POSITIONS (speaker | stance | subtopic | claim):
{positions}

Write, in French: `summary` (150-250 words: who was heard, the main themes, the tone), `key_takeaways` (5-8 specific,
informative bullets with concrete facts/figures where given), `open_questions` (up to 6 questions raised but left unanswered
or contested), `ai_stance_overview` (3-5 sentences on how the witness and the deputies position themselves on AI).
Stick to what is in the material; do not add outside knowledge."""


def _norm(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()


def verify_quote(quote: str, lines: list[str], threshold: float = 0.88) -> bool:
    """True when the quote appears (near-)verbatim in the excerpt: exact after normalisation, or fuzzy match on 1-3 lines."""
    q = _norm(quote)
    if len(q) < 12:
        return False
    flat = _norm(" ".join(lines))
    if q in flat:
        return True
    for i in range(len(lines)):
        for n in (1, 2, 3):
            cand = _norm(" ".join(lines[i:i + n]))
            if cand and SequenceMatcher(None, q, cand[:len(q) + 40]).ratio() >= threshold:
                return True
            if SequenceMatcher(None, q, cand).ratio() >= threshold:
                return True
    return False


def make_windows(sentences: list[dict], start_s: float, end_s: float, max_chars: int = 18000) -> list[list[dict]]:
    sel = [s for s in sentences if start_s <= s["start_s"] <= end_s]
    wins, cur, size = [], [], 0
    for s in sel:
        n = len(s["text"]) + 12
        if cur and size + n > max_chars:
            wins.append(cur)
            cur, size = [], 0
        cur.append(s)
        size += n
    if cur:
        wins.append(cur)
    return wins


def _line(s: dict) -> str:
    return f"[{hms(s['start_s'])}] {s['text']}"


@dataclass
class Ctx:
    router: object
    context: str
    date: str
    participants: list[str]
    order: str = "(not available)"


def _content_words(t: str) -> set[str]:
    return {w for w in _norm(t).split() if len(w) >= 5}


def locate(text: str, win: list[dict], after_s: float = 0.0, min_overlap: float = 0.5, span: int = 3) -> float | None:
    """Start time of the 1-3 consecutive sentences whose content words best cover `text` (None if below min_overlap)."""
    want = _content_words(text)
    if len(want) < 3:
        return None
    best, best_t = 0.0, None
    for i, s in enumerate(win):
        if s["start_s"] < after_s:
            continue
        if not (want & _content_words(s["text"])):
            continue  # the match must begin on a sentence that itself shares words with the text
        have = _content_words(" ".join(x["text"] for x in win[i:i + span]))
        score = len(want & have) / len(want)
        if score > best:
            best, best_t = score, s["start_s"]
    return best_t if best >= min_overlap else None


def role_of(label: str) -> str:
    low = label.lower()
    if "rapporteur" in low:
        return "rapporteur"
    if "président" in low:
        return "chair"
    return "deputy"


_TITLE = re.compile(r"^(m|mme|mmes|mm|dr|pr|me)\.?\s+", re.I)


def canonical_name(name: str, participants: list[str], min_ratio: float = 0.8) -> str:
    """Snap 'Mme Valérie Rossier, députée' to the official participant spelling 'Mme Valérie Rossi' when close enough."""
    bare = _TITLE.sub("", name.split(",")[0]).strip()
    if not bare or bare.lower().startswith("unknown"):
        return name
    best, score = None, 0.0
    for p in participants:
        r = SequenceMatcher(None, _norm(bare), _norm(_TITLE.sub("", p))).ratio()
        if r > score:
            best, score = p, r
    return best if best and score >= min_ratio else name.split(",")[0].strip()


def canonicalize(a: dict, participants: list[str]) -> dict:
    for q in a["qa"]:
        q["asker"], q["answerer"] = canonical_name(q["asker"], participants), canonical_name(q["answerer"], participants)
    for p in a["positions"]:
        p["speaker"] = canonical_name(p["speaker"], participants)
    return a


def _clean_time(t: str) -> str:
    m = re.search(r"\d{1,3}:\d{2}:\d{2}", t or "")
    return m.group(0) if m else ""


def analyse_window(ctx: Ctx, win: list[dict]) -> dict:
    lines = [_line(s) for s in win]
    prompt = MAP_PROMPT.format(context=ctx.context, date=ctx.date, participants="; ".join(ctx.participants), order=ctx.order,
                               text="\n".join(lines), subtopics=SUBTOPICS)
    res = ctx.router.complete("analyze", [{"role": "user", "content": prompt}], temperature=0.2, max_tokens=7000,
                              validate=json_validator(WindowOut),
                              response_format=json_schema_response_format(WindowOut, strict=False))
    out = json_validator(WindowOut)(res.text)
    plain = [s["text"] for s in win]
    positions = []
    for p in out.positions:
        d = p.model_dump()
        d["quote_verified"] = verify_quote(p.quote, plain)
        positions.append(d)
    qa = [q.model_dump() for q in out.qa]
    for q in qa:
        q["time_model"] = _clean_time(q["time"])
        t = locate(q["question"], win, min_overlap=0.5, span=2)
        q["time"] = hms(t) if t is not None else q["time_model"]
        q["time_located"] = t is not None
        q["answer_time"] = ""
        if q["answered"] and q["answer"].strip():
            qs = t if t is not None else 0.0
            at = locate(q["answer"], win, after_s=qs, min_overlap=0.3, span=4)
            q["answer_time"] = hms(at) if at is not None else ""
        else:
            q["answer"], q["answered"] = "", False
        if q["asker_role"] in ("deputy", "other"):
            q["asker_role"] = role_of(q["asker"])
    for d in positions:
        d["time"] = _clean_time(d["time"])
    return {"from": hms(win[0]["start_s"]), "to": hms(win[-1]["end_s"]), "model": res.model, "qa": qa,
            "positions": positions, "window_summary": out.window_summary}


def analyse(router, sentences: list[dict], start_s: float, end_s: float, context: str, date: str,
            participants: list[str], workers: int = 2, order: str = "(not available)") -> dict:
    ctx = Ctx(router, context, date, participants, order)
    wins = make_windows(sentences, start_s, end_s)
    results, failures = [None] * len(wins), []

    def run(i: int) -> None:
        try:
            results[i] = analyse_window(ctx, wins[i])
        except Exception as e:  # keep going: report the window as failed rather than losing the whole run
            failures.append({"window": i, "from": hms(wins[i][0]["start_s"]), "error": f"{type(e).__name__}: {e}"[:300]})

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(run, range(len(wins))))
    ok = [r for r in results if r]
    positions = [p for r in ok for p in r["positions"]]
    reduce_prompt = REDUCE_PROMPT.format(
        context=context, date=date,
        summaries="\n".join(f"- [{r['from']}-{r['to']}] {r['window_summary']}" for r in ok),
        positions="\n".join(f"{p['speaker']} | {p['stance']} | {p['subtopic']} | {p['claim']}" for p in positions[:60]))
    overall = None
    if ok:
        res = router.complete("analyze", [{"role": "user", "content": reduce_prompt}], temperature=0.2, max_tokens=4000,
                              validate=json_validator(Overall),
                              response_format=json_schema_response_format(Overall, strict=False))
        overall = json_validator(Overall)(res.text).model_dump()
    return canonicalize({"context": context, "date": date, "range": [hms(start_s), hms(end_s)], "windows": len(wins), "failed_windows": failures,
            "overall": overall, "qa": [dict(q, window=i) for i, r in enumerate(results) if r for q in r["qa"]],
            "positions": positions, "parts": [{k: r[k] for k in ("from", "to", "model", "window_summary")} for r in ok]}, participants)


LABELS = {
    "fr": dict(summary="Résumé", takeaways="Points clés", stance="Positionnement sur l'IA", open="Questions ouvertes",
               qa="Questions / réponses", positions="Positions", cols="| temps | qui | sujet / cible / attitude | position | citation |",
               unanswered="*(réponse hors de cette fenêtre)*", unverified=" ⚠ non vérifiée", ai=" · IA",
               head="*{date} · transcription {a}–{b} · analyse automatique, à vérifier avant citation*"),
    "en": dict(summary="Summary", takeaways="Key takeaways", stance="Position on AI", open="Open questions",
               qa="Questions and answers", positions="Positions", cols="| time | who | topic / target / stance | position | quote |",
               unanswered="*(answer outside this window)*", unverified=" ⚠ unverified", ai=" · AI",
               head="*{date} · transcript {a}–{b} · automatic analysis, machine-translated from French, verify before quoting*"),
}


def to_markdown(a: dict, title: str, lang: str = "fr") -> str:
    L = LABELS[lang]
    o = a["overall"] or {}
    md = [f"# {title}", L["head"].format(date=a["date"], a=a["range"][0], b=a["range"][1]), ""]
    if o:
        md += [f"## {L['summary']}", o["summary"], "", f"## {L['takeaways']}", *[f"- {t}" for t in o["key_takeaways"]], "",
               f"## {L['stance']}", o["ai_stance_overview"], "", f"## {L['open']}", *[f"- {t}" for t in o["open_questions"]], ""]
    md += [f"## {L['qa']}", ""]
    for q in a["qa"]:
        tag = L["ai"] if q["ai_relevant"] else ""
        ans = f"**{q['answerer']}** [{q['answer_time'] or '?'}] : {q['answer']}" if q.get("answered", True) and q["answer"] else L["unanswered"]
        md += [f"**[{q['time']}] {q['asker']}** ({q['asker_role']}){tag}", f"> {q['question']}", "", ans, ""]
    md += [f"## {L['positions']}", "", L["cols"], "|---|---|---|---|---|"]
    for p in a["positions"]:
        mark = "" if p["quote_verified"] else L["unverified"]
        md.append(f"| {p['time']} | {p['speaker']} | {p['subtopic']} / {p.get('target', '')} / {p['stance']} | {p['claim']} | « {p['quote']} »{mark} |")
    if a["failed_windows"]:
        md += ["", f"*{len(a['failed_windows'])} window(s) failed and are missing: {a['failed_windows']}*"]
    return "\n".join(md)


def load_sentences(meeting_dir: Path) -> list[dict]:
    return json.loads((meeting_dir / "sentences.json").read_text())
