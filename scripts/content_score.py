"""Content-level ASR score vs an EDITED reference (compte rendu / SRT): bag-of-content-words recall/precision.
Content word = >=5 letters or any number token; accent/case folded. Robust to the editing that makes WER meaningless."""
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path


def toks(s: str) -> Counter:
    s = "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))
    return Counter(t for t in re.findall(r"[a-z0-9]+", s) if len(t) >= 5 or t.isdigit())


ref = toks(Path("data/spike/ref.txt").read_text())
print(f"reference content tokens: {sum(ref.values())} ({len(ref)} distinct)")
for f in sys.argv[1:]:
    hyp = toks(Path(f).read_text())
    common = sum((ref & hyp).values())
    print(f"{Path(f).stem:22s} recall {common / sum(ref.values()):.3f}  precision {common / sum(hyp.values()):.3f}  hyp_tokens {sum(hyp.values())}")
