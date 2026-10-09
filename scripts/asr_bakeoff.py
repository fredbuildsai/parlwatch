"""M0 spike (b): ASR bake-off on a 10-min AN segment. Reference = official SRT cues for the same window.
usage: asr_bakeoff.py <backend>   backend in: whisper-q4 | whisper-q8 | parakeet-bf16 | parakeet-q8 | parakeet-q4"""
import json
import re
import sys
import time
import unicodedata

import jiwer
import mlx.core as mx

AUDIO, REF = "data/spike/seg.wav", open("data/spike/ref.txt").read()
DUR = 600.0


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower().replace("’", "'")
    s = re.sub(r"n°\s*", "n ", s)
    s = re.sub(r"[^\w\s']", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def run_whisper(bits: str) -> str:
    from pathlib import Path

    import mlx_whisper
    from huggingface_hub import snapshot_download
    if bits == "fp16":  # REFERENCE ONLY (measures quantization loss); never a product backend
        repo = "mlx-community/whisper-large-v3-turbo"
    elif bits == "q4":
        repo = "mlx-community/whisper-large-v3-turbo-q4"  # ships weights.npz, the format mlx-whisper 0.4.3 reads
    else:  # 8bit repo ships model.safetensors: expose it under the name the loader expects
        src = Path(snapshot_download("mlx-community/whisper-large-v3-turbo-8bit"))
        repo = Path("data/spike/whisper-8bit")
        repo.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            (repo / ("weights.safetensors" if f.name == "model.safetensors" else f.name)).unlink(missing_ok=True)
            (repo / ("weights.safetensors" if f.name == "model.safetensors" else f.name)).symlink_to(f.resolve())
        repo = str(repo)
    return mlx_whisper.transcribe(AUDIO, path_or_hf_repo=repo, language="fr", condition_on_previous_text=False)["text"]


def run_parakeet(quant: str) -> str:
    import mlx.nn as nn
    from parakeet_mlx import from_pretrained
    model = from_pretrained("mlx-community/parakeet-tdt-0.6b-v3")
    if quant != "bf16":
        bits = int(quant[1:])
        nn.quantize(model, group_size=64, bits=bits)
        mx.eval(model.parameters())
    return model.transcribe(AUDIO, chunk_duration=float(sys.argv[2]) if len(sys.argv) > 2 else 120, overlap_duration=15).text


kind, _, q = sys.argv[1].partition("-")
t0 = time.time()
hyp = run_whisper(q) if kind == "whisper" else run_parakeet(q)
dt = time.time() - t0
r, h = norm(REF), norm(hyp)
out = {
    "backend": sys.argv[1], "seconds": round(dt, 1), "rtfx": round(DUR / dt, 1),
    "peak_mem_gb": round(mx.get_peak_memory() / 1e9, 2),
    "wer": round(jiwer.wer(r, h), 4), "cer": round(jiwer.cer(r, h), 4), "hyp_words": len(h.split()), "ref_words": len(r.split()),
}
print(json.dumps(out))
open(f"data/spike/hyp_{sys.argv[1]}.txt", "w").write(hyp)
