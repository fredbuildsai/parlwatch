"""Post-processing of raw ASR segments: drop hallucinations, fix proper names, merge into sentences."""

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from parlwatch.asr.backends.base import AsrSegment

# Whisper invents these over silence/music (training-data artefacts). Matched on the whole segment text.
_HALLUCINATIONS = re.compile(
    r"^\W*(sous-?titr\w*.*|sous-?titres? (réalisés?|par|de la communauté).*|amara\.org.*|merci d'avoir regardé.*|"
    r"n'oubliez pas de vous abonner.*|à bientôt pour une prochaine vidéo.*|\.{2,}|…+)\W*$", re.I)
_NO_LETTERS = re.compile(r"^[\W_]*$")


def drop_hallucinations(segs: list[AsrSegment]) -> tuple[list[AsrSegment], list[AsrSegment]]:
    kept, dropped = [], []
    for s in segs:
        (dropped if _NO_LETTERS.match(s.text) or _HALLUCINATIONS.match(s.text.strip()) else kept).append(s)
    return kept, dropped


# ---- names -------------------------------------------------------------------------------------------------------
_TITLES = {"m", "mme", "mmes", "mm", "dr", "pr", "me"}
_WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:[-'’][A-Za-zÀ-ÖØ-öø-ÿ]+)*")


def _fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))


def name_vocabulary(speaker_names: list[str], extra_terms: list[str] = ()) -> list[str]:
    """Surnames/given names from 'M. Arthur Mensch'-style entries (+ extra terms such as company names)."""
    vocab: list[str] = []
    for n in speaker_names:
        for w in _WORD.findall(n):
            if _fold(w) not in _TITLES and len(w) >= 4:
                vocab.append(w)
    return sorted(set(vocab) | set(extra_terms))


@dataclass
class Correction:
    start_s: float
    before: str
    after: str
    score: float


def correct_names(segs: list[AsrSegment], vocab: list[str], min_ratio: float = 0.84,
                  ) -> tuple[list[AsrSegment], list[Correction]]:
    """Replace capitalised words that are a near-miss of a known name (Mench->Mensch, Herblain-Stoupe->Herblin-Stoop).

    Only capitalised words of >= 5 letters with the same first letter qualify, to avoid rewriting ordinary words;
    every change is returned so it can be reviewed.
    """
    fvocab = {v: _fold(v) for v in vocab}
    exact = set(fvocab.values())
    log: list[Correction] = []

    def fix(m: re.Match, seg_start: float) -> str:
        w = m.group(0)
        fw = _fold(w)
        if len(w) < 5 or not w[0].isupper() or fw in exact:
            return w
        best, score = None, 0.0
        for v, fv in fvocab.items():
            if fv[0] != fw[0] or abs(len(fv) - len(fw)) > 3:
                continue
            r = SequenceMatcher(None, fw, fv).ratio()
            if r > score:
                best, score = v, r
        if best and score >= min_ratio:
            log.append(Correction(seg_start, w, best, round(score, 2)))
            return best
        return w

    out = [AsrSegment(s.start_s, s.end_s, _WORD.sub(lambda m, s=s: fix(m, s.start_s), s.text), s.words) for s in segs]
    return out, log


_FIXED = [(re.compile(r"\bOVH ?[Cc]loud\b"), "OVHcloud"), (re.compile(r"\bMistral AI\b", re.I), "Mistral AI")]


def fix_known_terms(segs: list[AsrSegment]) -> list[AsrSegment]:
    def f(t: str) -> str:
        for pat, rep in _FIXED:
            t = pat.sub(rep, t)
        return t

    return [AsrSegment(s.start_s, s.end_s, f(s.text), s.words) for s in segs]


# ---- sentences ---------------------------------------------------------------------------------------------------
@dataclass
class Utterance:
    start_s: float
    end_s: float
    text: str


_END = re.compile(r"[.?!…»\"”]\s*$")


def merge_sentences(segs: list[AsrSegment], max_gap_s: float = 3.0, max_chars: int = 700) -> list[Utterance]:
    """Join Whisper's short phrase-level segments into sentences (a long pause or a very long run also closes one)."""
    out: list[Utterance] = []
    cur: list[AsrSegment] = []

    def flush() -> None:
        if cur:
            out.append(Utterance(cur[0].start_s, cur[-1].end_s, " ".join(s.text.strip() for s in cur).strip()))
            cur.clear()

    for s in segs:
        if cur and s.start_s - cur[-1].end_s > max_gap_s:
            flush()
        cur.append(s)
        if _END.search(s.text) or sum(len(x.text) for x in cur) > max_chars:
            flush()
    flush()
    return out
