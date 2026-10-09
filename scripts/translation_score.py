"""Score translation outputs on the sample: figures kept, names kept, chrF agreement with Claude's and with the consensus."""
import json
import re
import statistics
from pathlib import Path

from sacrebleu.metrics import CHRF

D = Path("docs/pilot-2026-10/translation-test")
S = {str(p["n"]): p for p in json.loads((D / "sample_fr.json").read_text())}
O = {s: json.loads((D / f"out_{s}.json").read_text()) for s in ("claude", "nemotron", "gemma", "argos", "mymemory")}
chrf = CHRF()


def nums(t: str) -> set[str]:
    return {m.replace(",", ".") for m in re.findall(r"\d+(?:[.,]\d+)?", t)}


def names(t: str) -> set[str]:
    toks = re.findall(r"(?<![.?!]\s)(?<!^)\b([A-Z][A-Za-zéèÉ]{2,})\b", t)
    return {w.lower() for w in toks if w not in ("IA",)} - {"monsieur", "madame", "merci"}


rows = {}
for s, o in O.items():
    tr = o["translations"]
    n_ok = n_all = m_ok = m_all = 0
    for k, p in S.items():
        e = tr.get(k, "")
        for x in nums(p["fr"]):
            n_all += 1
            n_ok += x in nums(e)
        for x in names(p["fr"]):
            m_all += 1
            m_ok += x in e.lower()
    others = [x for x in ("nemotron", "argos", "mymemory", "claude") if x != s]
    cons = []
    for k in S:
        e = tr.get(k)
        if e:
            cons.append(statistics.mean(chrf.sentence_score(e, [O[x]["translations"][k]]).score for x in others if k in O[x]["translations"]))
    vs_claude = [chrf.sentence_score(tr[k], [O["claude"]["translations"][k]]).score for k in S if k in tr] if s != "claude" else []
    rows[s] = dict(done=f"{len(tr)}/30", secs=o.get("seconds"), figures=f"{n_ok}/{n_all}", names=f"{m_ok}/{m_all}",
                   chrf_vs_claude=round(statistics.mean(vs_claude), 1) if vs_claude else None, chrf_vs_others=round(statistics.mean(cons), 1))
for s, r in rows.items():
    print(f"{s:9s}", r)
json.dump(rows, open(D / "scores.json", "w"), indent=1)
