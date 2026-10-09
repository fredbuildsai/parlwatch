"""Translate the 30-sentence sample with several free systems and save one JSON per system. usage: translation_test.py <system>
systems: nemotron | gemma | argos | mymemory   (claude's file is written by hand)"""
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

D = Path("docs/pilot-2026-10/translation-test")
sample = json.loads((D / "sample_fr.json").read_text())
system = sys.argv[1]

PROMPT = """Translate these French sentences, taken from a National Assembly hearing (speech-recognition output), into English.
Be faithful: keep the spoken register, proper nouns, acronyms and all figures exactly; do not correct, summarise, explain or add anything.
Translate every numbered sentence. Reply with ONLY a JSON object {{"1": "...", "2": "..."}} keyed by the sentence numbers.

{lines}"""


def llm(route: str) -> dict[str, str]:
    from parlwatch.llm import get_router
    router, out = get_router(), {}
    for i in range(0, len(sample), 10):
        batch = sample[i:i + 10]
        lines = "\n".join(f"{p['n']}. {p['fr']}" for p in batch)
        res = router.complete(route, [{"role": "user", "content": PROMPT.format(lines=lines)}], temperature=0.1, max_tokens=3000,
                              validate=lambda t: json.loads(re.search(r"\{.*\}", t, re.S).group(0)), use_cache=False)
        out.update({k: v for k, v in json.loads(re.search(r"\{.*\}", res.text, re.S).group(0)).items()})
    return out


def argos() -> dict[str, str]:
    code = ("import json,sys,argostranslate.translate as t;S=json.load(open(sys.argv[1]));"
            "print(json.dumps({str(p['n']):t.translate(p['fr'],'fr','en') for p in S}))")
    py = "/private/tmp/claude-501/-Users-fred-Documents-Work-AI-fredbuildsai/e92dfede-62be-4f94-bcb4-f90218f21ba4/scratchpad/argos/.venv/bin/python"
    return json.loads(subprocess.run([py, "-c", code, str(D / "sample_fr.json")], capture_output=True, text=True, check=True).stdout)


def mymemory() -> dict[str, str]:
    out = {}
    for p in sample:  # anonymous use: no e-mail parameter; the free anonymous quota is 5000 characters per day
        url = "https://api.mymemory.translated.net/get?" + urllib.parse.urlencode({"q": p["fr"][:490], "langpair": "fr|en"})
        r = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "parlwatch-test"}), timeout=30).read())
        out[str(p["n"])] = r["responseData"]["translatedText"]
        if r.get("quotaFinished"):
            out[str(p["n"])] = "[QUOTA FINISHED]"
        time.sleep(0.5)
    return out


from parlwatch.settings import load_env  # noqa: E402

load_env()
t0 = time.time()
tr = {"nemotron": lambda: llm("translate_nemotron"), "gemma": lambda: llm("translate_gemma"), "argos": argos, "mymemory": mymemory}[system]()
dt = time.time() - t0
json.dump({"system": system, "seconds": round(dt, 1), "translations": tr}, open(D / f"out_{system}.json", "w"), ensure_ascii=False, indent=1)
print(system, f"{dt:.0f}s", len(tr), "sentences")
