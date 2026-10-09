"""LLM translation/expansion of topic search terms into a parliament's language."""

import json
import re

LANG_NAMES = {"fr": "French", "de": "German", "nl": "Dutch", "es": "Spanish", "en": "English"}

PROMPT = """You help build keyword searches over parliamentary meeting agendas and transcripts in {language}.
Topic: "{label}".
Known search terms (other languages): {known}.
Return the terms and short phrases that politicians, ministers and agenda writers in {language} actually use
for this topic, including the common acronym, official institutional names and widely used English loanwords.
Prefer specific multi-word phrases over generic single words; skip words so common they cause false matches.
Reply with ONLY a JSON array of 8 to 25 strings."""


def parse_terms(text: str) -> list[str]:
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        raise ValueError(f"no JSON array in: {text[:200]}")
    terms = json.loads(m.group(0))
    out = [t.strip() for t in terms if isinstance(t, str) and t.strip()]
    if not out:
        raise ValueError("empty term list")
    return out


def translate_terms(router, label: str, known: dict[str, list[str]], lang: str) -> tuple[list[str], str]:
    known_s = "; ".join(f"{k}: {', '.join(v)}" for k, v in known.items() if v) or "none"
    messages = [{"role": "user", "content": PROMPT.format(language=LANG_NAMES.get(lang, lang), label=label, known=known_s)}]
    res = router.complete("translate", messages, temperature=0.2, max_tokens=800, validate=lambda t: parse_terms(t))
    return parse_terms(res.text), res.model
