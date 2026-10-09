"""Single-video pipeline (France): portal page -> audio -> ASR -> files. First end-to-end slice of the full pipeline."""

import json
import time
from pathlib import Path

import httpx

from parlwatch.asr.backends.whisper import WhisperBackend
from parlwatch.countries.fr.media import BASE, decode_srt, fetch_video_page


def _download(url: str, dest: Path) -> None:
    """Resumable download (Range) of the audio file."""
    with httpx.Client(follow_redirects=True, timeout=120, headers={"User-Agent": "parlwatch/0.1"}) as c:
        total = int(c.head(url).headers["content-length"])
        for _ in range(12):
            have = dest.stat().st_size if dest.exists() else 0
            if have >= total:
                return
            try:
                with c.stream("GET", url, headers={"Range": f"bytes={have}-"} if have else {}) as r:
                    r.raise_for_status()
                    with open(dest, "ab" if have and r.status_code == 206 else "wb") as f:
                        for chunk in r.iter_bytes():
                            f.write(chunk)
            except httpx.TransportError:
                time.sleep(2)
        raise RuntimeError(f"incomplete download of {url}: {dest.stat().st_size}/{total}")


def hms(s: float) -> str:
    return f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d}"


def process_video(url: str, out_root: Path, quant: str = "q8", language: str = "fr", keep_audio: bool = False) -> Path:
    page = fetch_video_page(url)
    out = out_root / page.uid
    out.mkdir(parents=True, exist_ok=True)
    meta = {"uid": page.uid, "title": page.title, "url": f"{BASE}/video.{page.uid}", "report_url": page.report_url,
            "audio_url": page.audio_url, "speakers": {k: v.name for k, v in page.speakers.items()},
            "chapters": [{"label": c.label, "type": c.type, "depth": c.depth} for c in page.chapters]}
    if page.caption_url:
        raw = httpx.get(page.caption_url, headers={"User-Agent": "parlwatch/0.1"}, timeout=60).content
        (out / "official.srt").write_text(decode_srt(raw))
    if not page.audio_url:
        raise RuntimeError("no audio file listed for this video")
    audio = out / "audio.mp3"
    t0 = time.time()
    _download(page.audio_url, audio)
    meta["download_s"] = round(time.time() - t0)
    t1 = time.time()
    segs = WhisperBackend(quant).transcribe(str(audio), language, checkpoint_dir=out / "chunks")
    meta.update(asr="whisper-large-v3-turbo", quant=quant, asr_s=round(time.time() - t1),
                audio_s=round(segs[-1].end_s) if segs else 0)
    meta["rtfx"] = round(meta["audio_s"] / max(meta["asr_s"], 1), 1)
    (out / "segments.json").write_text(json.dumps([s.__dict__ for s in segs], ensure_ascii=False))
    (out / "transcript.txt").write_text("\n".join(f"[{hms(s.start_s)}] {s.text}" for s in segs))
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    if not keep_audio:
        audio.unlink(missing_ok=True)
    return out
