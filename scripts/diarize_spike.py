"""M0 spike (c): pyannote community-1 diarization speed/quality on a 5-min AN segment (MPS)."""
import json
import time

import torch
from pyannote.audio import Pipeline

t0 = time.time()
pipe = Pipeline.from_pretrained("pyannote-community/speaker-diarization-community-1")
dev = "mps" if torch.backends.mps.is_available() else "cpu"
pipe.to(torch.device(dev))
load_s = time.time() - t0
t1 = time.time()
out = pipe("data/spike/seg.wav")
dia = getattr(out, "speaker_diarization", out)
dt = time.time() - t1
turns = [(round(t.start, 1), round(t.end, 1), spk) for t, _, spk in dia.itertracks(yield_label=True)]
speakers = sorted({s for *_, s in turns})
spoken = {s: round(sum(e - b for b, e, x in turns if x == s), 1) for s in speakers}
print(json.dumps({"device": dev, "load_s": round(load_s, 1), "run_s": round(dt, 1), "rtfx": round(600 / dt, 1),
                  "n_speakers": len(speakers), "n_turns": len(turns), "spoken_s": spoken}))
json.dump(turns, open("data/spike/diarization.json", "w"))
print(turns[:12])
