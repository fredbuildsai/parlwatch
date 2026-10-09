"""Clean a transcribed meeting directory: segments.json (+ meta.json) -> cleaned segments, sentences, review logs."""

import json
from dataclasses import asdict
from pathlib import Path

from parlwatch.asr.backends.base import AsrSegment
from parlwatch.pipeline import hms
from parlwatch.transcripts.clean import (
    correct_names,
    drop_hallucinations,
    fix_known_terms,
    merge_sentences,
    name_vocabulary,
)

DEFAULT_TERMS = ["Mistral", "OVHcloud", "Scaleway", "Nvidia"]


def postprocess(meeting_dir: Path, extra_terms: list[str] = DEFAULT_TERMS) -> dict:
    meta = json.loads((meeting_dir / "meta.json").read_text())
    segs = [AsrSegment(**d) for d in json.loads((meeting_dir / "segments.json").read_text())]
    kept, dropped = drop_hallucinations(segs)
    vocab = name_vocabulary(list(meta.get("speakers", {}).values()), extra_terms)
    fixed, corrections = correct_names(kept, vocab)
    fixed = fix_known_terms(fixed)
    sentences = merge_sentences(fixed)
    (meeting_dir / "sentences.json").write_text(json.dumps([asdict(u) for u in sentences], ensure_ascii=False))
    (meeting_dir / "transcript_clean.txt").write_text("\n".join(f"[{hms(u.start_s)}] {u.text}" for u in sentences))
    (meeting_dir / "corrections.json").write_text(json.dumps(
        {"dropped": [{"t": hms(s.start_s), "text": s.text} for s in dropped],
         "name_corrections": [{"t": hms(c.start_s), "before": c.before, "after": c.after, "score": c.score}
                              for c in corrections]}, ensure_ascii=False, indent=1))
    return {"segments": len(segs), "dropped": len(dropped), "name_corrections": len(corrections), "sentences": len(sentences)}
