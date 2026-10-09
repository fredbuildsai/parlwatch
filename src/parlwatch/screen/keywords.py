"""Deterministic keyword matching for topic terms.

- phrases match accent- and case-insensitively on word boundaries ("intelligence artificielle");
- acronyms (all caps, <= 5 chars: "IA", "KI", "AI Act" keeps its caps part) match case-sensitively, so
  "IA" does not fire inside "Silvia" or on Spanish "ia".
"""

import re
import unicodedata
from dataclasses import dataclass


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def is_acronym(term: str) -> bool:
    letters = [c for c in term if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters) and len(letters) <= 5


@dataclass(frozen=True)
class Matcher:
    terms: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "_patterns", [(t, self._compile(t)) for t in self.terms])

    @staticmethod
    def _compile(term: str) -> re.Pattern:
        if is_acronym(term):
            return re.compile(rf"(?<!\w){re.escape(term)}(?!\w)")
        return re.compile(rf"(?<!\w){re.escape(fold(term))}(?!\w)")

    def find(self, text: str) -> dict[str, int]:
        """term -> number of occurrences (only terms that occur)."""
        folded = fold(text)
        hits: dict[str, int] = {}
        for term, pat in self._patterns:  # type: ignore[attr-defined]
            n = len(pat.findall(text if is_acronym(term) else folded))
            if n:
                hits[term] = n
        return hits

    def score(self, text: str) -> float:
        """Distinct terms weigh most, repeats add diminishing credit."""
        return sum(1.0 + min(n - 1, 4) * 0.25 for n in self.find(text).values())
