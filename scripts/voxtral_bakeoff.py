"""Voxtral Mini 3B (quantized MLX) on the 10-min AN segment. usage: voxtral_bakeoff.py <hf-repo> <tag>"""
import json
import sys
import time

import mlx.core as mx
from mlx_voxtral import VoxtralProcessor, load_voxtral_model

repo, tag = sys.argv[1], sys.argv[2]
t0 = time.time()
model, _ = load_voxtral_model(repo, dtype=mx.bfloat16)
proc = VoxtralProcessor.from_pretrained(repo)
load_s = time.time() - t0
inputs = proc.apply_transcrition_request(audio="data/spike/seg.wav", language="fr")
t1 = time.time()
out = model.generate(input_ids=inputs.input_ids, input_features=inputs.input_features,
                     max_new_tokens=4000, temperature=0.0, top_p=0.95)
dt = time.time() - t1
text = proc.decode(out[0, inputs.input_ids.shape[1]:], skip_special_tokens=True)
open(f"data/spike/hyp_voxtral-{tag}.txt", "w").write(text)
print(json.dumps({"backend": f"voxtral-{tag}", "load_s": round(load_s), "run_s": round(dt), "rtfx": round(600 / dt, 1),
                  "peak_mem_gb": round(mx.get_peak_memory() / 1e9, 2), "words": len(text.split())}))
