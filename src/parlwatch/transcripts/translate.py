"""Machine translation of sentences and analyses with the free LLM router.

Chosen by the pilot translation test (docs/pilot-2026-10/translation-test): Nemotron via the router made no meaning errors on
30 sentences, vs 6 for MyMemory and 7 for Argos; local gemma4:e4b failed to return all sentences. Every batch is validated:
all numbered sentences must come back, otherwise the call is retried/failed over; sentences whose figures look changed are flagged for review.
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor

LANGS = {"fr": "French", "en": "English", "de": "German", "nl": "Dutch", "es": "Spanish"}

PROMPT = """Translate these {src} sentences, taken from a parliamentary hearing (speech-recognition output) or an analysis of it, into {tgt}.
Be faithful: keep the spoken register, proper nouns, acronyms, quotation marks and all figures exactly; do not correct, summarise,
explain or add anything. Resolve obvious speech-recognition slips only when the intended word is unambiguous (e.g. "circonception" = constituency).
Translate every numbered sentence. Reply with ONLY a JSON object {{"1": "...", "2": "..."}} keyed by the sentence numbers.

{lines}"""


_NUM = re.compile(r"\d+(?:[ \u00a0\u202f.,]\d{3})+|\d+(?:[.,]\d+)?")


def _nums(t: str) -> set[str]:
    """Figures as digit strings, ignoring thousands/decimal separators ('1 000' = '1,000' = '1.000'; '0,65' = '0.65')."""
    return {re.sub(r"\D", "", m) for m in _NUM.findall(t)}


def figure_flags(src: list[str], out: list[str]) -> list[int]:
    """Indices of sentences whose figures may have changed. Lenient: '50' is satisfied by '2050' (horizon 50 -> 2050), and a
    figure the translator wrote as a word cannot be checked, so it is flagged for review rather than rejected."""
    flags = []
    for i, (a, b) in enumerate(zip(src, out, strict=True)):
        have = _nums(b)
        if any(f not in have and not any(h.endswith(f) for h in have) for f in _nums(a)):
            flags.append(i)
    return flags


_FR_STOP = re.compile(r"\b(le|la|les|des|une|est|pour|dans|vous|nous|qui|que|donc|mais|c'est|j'ai|il y a)\b", re.I)


def looks_untranslated(src: str, out: str) -> bool:
    """The model sometimes copies a French sentence back (verified: 11 of 564 in one hearing)."""
    same = out.strip().lower() == src.strip().lower() and len(src.split()) > 3
    return same or len(_FR_STOP.findall(out)) >= 3


def _validator(src_batch: list[str]):
    def validate(text: str) -> dict[str, str]:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise ValueError("no JSON object")
        d = json.loads(m.group(0))
        missing = [str(i + 1) for i in range(len(src_batch)) if not str(d.get(str(i + 1), "")).strip()]
        if missing:
            raise ValueError(f"missing sentences {missing}")
        return d

    return validate


def translate_texts(router, texts: list[str], src: str = "fr", tgt: str = "en", batch: int = 12, workers: int = 2,
                    route: str = "translate") -> tuple[list[str], list[int]]:
    """Returns (translations, indices of sentences whose figures should be reviewed)."""
    out = [""] * len(texts)
    chunks = [(i, texts[i:i + batch]) for i in range(0, len(texts), batch)]

    def run(c: tuple[int, list[str]]) -> None:
        i, b = c
        lines = "\n".join(f"{k + 1}. {t}" for k, t in enumerate(b))
        res = router.complete(route, [{"role": "user", "content": PROMPT.format(src=LANGS[src], tgt=LANGS[tgt], lines=lines)}],
                              temperature=0.1, max_tokens=6000, validate=_validator(b))
        d = _validator(b)(res.text)
        for k in range(len(b)):
            out[i + k] = str(d[str(k + 1)]).strip()

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(run, chunks))
    for _ in range(2):  # second pass: re-translate only what came back untranslated, in small batches
        bad = [i for i, (a, b) in enumerate(zip(texts, out, strict=True)) if looks_untranslated(a, b)]
        if not bad:
            break
        redo = translate_texts_once(router, [texts[i] for i in bad], src, tgt, route)
        for i, t in zip(bad, redo, strict=True):
            out[i] = t
    return out, figure_flags(texts, out)


def translate_texts_once(router, texts: list[str], src: str, tgt: str, route: str) -> list[str]:
    out = []
    for i in range(0, len(texts), 4):
        b = texts[i:i + 4]
        lines = "\n".join(f"{k + 1}. {t}" for k, t in enumerate(b))
        res = router.complete(route, [{"role": "user", "content": PROMPT.format(src=LANGS[src], tgt=LANGS[tgt], lines=lines)
                                       + f"\nEvery sentence MUST be rewritten in {LANGS[tgt]}; do not return the {LANGS[src]} text."}],
                              temperature=0.3, max_tokens=3000, validate=_validator(b), use_cache=False)
        d = _validator(b)(res.text)
        out += [str(d[str(k + 1)]).strip() for k in range(len(b))]
    return out


def translate_analysis(router, a: dict, src: str = "fr", tgt: str = "en") -> dict:
    """Translate the free-text fields of an analysis dict (summary, takeaways, Q&A, positions); structure is kept."""
    import copy

    b = copy.deepcopy(a)
    refs: list[tuple[object, object]] = []  # (container, key)
    if b.get("overall"):
        o = b["overall"]
        for k in ("summary", "ai_stance_overview"):
            refs.append((o, k))
        for lst in ("key_takeaways", "open_questions"):
            refs += [(o[lst], i) for i in range(len(o[lst]))]
    for q in b["qa"]:
        refs += [(q, k) for k in ("question", "answer") if q.get(k)]
    for p in b["positions"]:
        refs += [(p, k) for k in ("claim", "quote", "target") if p.get(k)]
    refs += [(r, "window_summary") for r in b.get("parts", []) if r.get("window_summary")]
    new, flags = translate_texts(router, [c[k] for c, k in refs], src, tgt)
    for (c, k), t in zip(refs, new, strict=True):
        c[k] = t
    b["translation_flags"] = [{"field": str(refs[i][1]), "text": new[i]} for i in flags]
    return b
