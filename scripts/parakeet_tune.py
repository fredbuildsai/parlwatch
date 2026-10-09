"""Try to make Parakeet v3 behave on French: chunk length, beam decoding, silence-based splitting. q8 only."""
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
from parakeet_mlx import from_pretrained

AUDIO = "data/spike/seg.wav"
model = from_pretrained("mlx-community/parakeet-tdt-0.6b-v3")
nn.quantize(model, group_size=64, bits=8); mx.eval(model.parameters())

def run(name, fn):
    t = time.time(); text = fn(); dt = time.time() - t
    Path(f"data/spike/hyp_pk_{name}.txt").write_text(text)
    en = len(re.findall(r"\b(the|and|is|of|that|this|with|thank|mister)\b", text.lower()))
    print(json.dumps({"cfg": name, "s": round(dt), "words": len(text.split()), "english_markers": en}), flush=True)

def vad_split(lo=12, hi=28, noise='-35dB', d=0.4):
    # cut at silences so each piece is one breath group (<= 30 s), transcribe each independently
    out = subprocess.run(["ffmpeg", "-i", AUDIO, "-af", f"silencedetect=noise={noise}:d={d}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    cuts, last = [0.0], 0.0
    for e in ends:
        if e - last >= lo: cuts.append(e); last = e
    cuts.append(600.0)
    texts = []
    with tempfile.TemporaryDirectory() as d:
        for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
            f = f"{d}/{i}.wav"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(a), "-to", str(b), "-i", AUDIO, f])
            texts.append(model.transcribe(f).text)
    print("pieces:", len(texts))
    return " ".join(texts)

for c in (8, 12):
    run(f"chunk{c}", lambda c=c: model.transcribe(AUDIO, chunk_duration=c, overlap_duration=2).text)
run("silence_6s", lambda: vad_split(6))
run("silence_9s", lambda: vad_split(9))
run("silence_9s_d02", lambda: vad_split(9, noise="-32dB", d=0.25))
