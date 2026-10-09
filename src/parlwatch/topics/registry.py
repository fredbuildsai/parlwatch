"""Topic registry backed by configs/topics.yaml. Any topic can be added; terms live per language."""

from pathlib import Path

import yaml

from parlwatch.screen.keywords import Matcher


class TopicRegistry:
    def __init__(self, path: Path):
        self.path = path
        self.data = yaml.safe_load(path.read_text()) if path.exists() else {}
        self.data.setdefault("topics", {})

    def save(self) -> None:
        self.path.write_text(yaml.safe_dump(self.data, allow_unicode=True, sort_keys=False))

    def names(self) -> list[str]:
        return list(self.data["topics"])

    def add(self, name: str, label: str, lang: str, terms: list[str]) -> None:
        t = self.data["topics"].setdefault(name, {"label": label, "terms": {}, "generated": {}})
        t["label"] = label or t["label"]
        t.setdefault("terms", {})[lang] = sorted(set(t["terms"].get(lang, []) + terms))

    def terms(self, name: str, lang: str, include_unreviewed: bool = False) -> list[str]:
        t = self.data["topics"][name]
        out = list(t.get("terms", {}).get(lang, []))
        gen = (t.get("generated") or {}).get(lang) or {}
        if gen and (gen.get("reviewed") or include_unreviewed):
            out += gen.get("terms", [])
        return sorted(set(out))

    def matcher(self, name: str, lang: str, include_unreviewed: bool = False) -> Matcher:
        ts = self.terms(name, lang, include_unreviewed)
        if not ts:
            raise KeyError(f"topic {name!r} has no terms for language {lang!r}: run `pw topic translate`")
        return Matcher(tuple(ts))

    def set_generated(self, name: str, lang: str, terms: list[str], model: str) -> None:
        t = self.data["topics"][name]
        t.setdefault("generated", {})[lang] = {"terms": terms, "model": model, "reviewed": False}
