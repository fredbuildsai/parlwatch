"""Assemblée nationale video portal (Vodalys): page -> media, captions, chapters, speakers.

Verified 2026-10-07 on video.19502241_6ac548b948b27:
- the page embeds `captionUrl` (an SRT, ISO-8859-1) and `reportUrl` (the official compte rendu);
- `/Datas/an/<uid>/content/data.nvs` (XML) lists files (source mp4, audio mp3), a chapter tree with
  speaker ids, and a speaker directory (name + deputy id);
- audio is served directly at `anorigin.vodalys.com/vod/mp4/ida/domain1/<yyyy>/<mm>/<name>.mp3`
  (~160 MB for 2h48, vs 2.7 GB for the mp4), so video is never downloaded.
"""

import re
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

import httpx

BASE = "https://videos.assemblee-nationale.fr"
AUDIO_BASE = "http://anorigin.vodalys.com/vod/mp4/ida/domain1/"
HLS_BASE = "https://videos-an.vodalys.com/videos/definst/mp4/ida/domain1/"

_VIDEO_URL_RE = re.compile(r"video\.(\d+)_([0-9a-f]+)")
_FILE_PATH_RE = re.compile(r"domain1/(\d{4}/\d{2}/[^/]+\.(?:mp3|mp4))$")


@dataclass
class Chapter:
    id: str
    label: str
    type: str | None = None
    speaker_ids: list[str] = field(default_factory=list)
    depth: int = 0


@dataclass
class Speaker:
    id: str
    name: str
    deputy_id: str | None = None  # AN acteur uid is "PA" + this


@dataclass
class VideoPage:
    uid: str
    title: str
    caption_url: str | None
    report_url: str | None
    audio_url: str | None = None
    hls_url: str | None = None
    chapters: list[Chapter] = field(default_factory=list)
    speakers: dict[str, Speaker] = field(default_factory=dict)


def parse_uid(url: str) -> str:
    m = _VIDEO_URL_RE.search(url)
    if not m:
        raise ValueError(f"not an AN video url: {url}")
    return f"{m.group(1)}_{m.group(2)}"


def parse_page(html: str) -> dict[str, str | None]:
    cap = re.search(r"captionUrl\s*=\s*'([^']*)'", html)
    rep = re.search(r"reportUrl\s*=\s*'([^']*)'", html)
    title = re.search(r'<h2 class="mediaTitle">(.*?)</h2>', html, re.S)
    return {
        "caption_url": BASE + cap.group(1) if cap and cap.group(1) else None,
        "report_url": rep.group(1) if rep and rep.group(1) else None,
        "title": re.sub(r"<[^>]+>", "", title.group(1)).strip() if title else "",
    }


def parse_nvs(xml: str) -> tuple[str | None, str | None, list[Chapter], dict[str, Speaker]]:
    """Return (audio_url, hls_url, chapters, speakers) from data.nvs."""
    root = ET.fromstring(xml.encode() if xml.lstrip().startswith("<?xml") else xml)
    audio_url = hls_url = None
    for f in root.iterfind("./files/file"):
        m = _FILE_PATH_RE.search(f.get("url", ""))
        if not m:
            continue
        if f.get("title") == "audio":
            audio_url = AUDIO_BASE + m.group(1)
        elif f.get("title") == "source":
            hls_url = HLS_BASE + m.group(1) + "/master.m3u8"

    chapters: list[Chapter] = []

    def walk(el: ET.Element, depth: int) -> None:
        for ch in el.findall("chapter"):
            t = ch.find("type")
            chapters.append(
                Chapter(
                    id=ch.get("id", ""),
                    label=ch.get("label", ""),
                    type=t.get("value") if t is not None else None,
                    speaker_ids=[s.get("id", "") for s in ch.findall("speaker")],
                    depth=depth,
                )
            )
            walk(ch, depth + 1)

    chapters_el = root.find("chapters")
    if chapters_el is not None:
        walk(chapters_el, 0)

    speakers: dict[str, Speaker] = {}
    for s in root.iterfind("./speakers/speaker"):
        sid = s.get("id", "")
        speakers[sid] = Speaker(id=sid, name=(s.findtext("name") or "").strip(), deputy_id=s.findtext("url") or None)
    return audio_url, hls_url, chapters, speakers


def fetch_video_page(url: str, client: httpx.Client | None = None) -> VideoPage:
    own = client is None
    client = client or httpx.Client(follow_redirects=True, timeout=30, headers={"User-Agent": "parlwatch/0.1"})
    try:
        uid = parse_uid(url)
        page = parse_page(client.get(f"{BASE}/video.{uid}").text)
        nvs = client.get(f"{BASE}/Datas/an/{uid}/content/data.nvs").text
        audio, hls, chapters, speakers = parse_nvs(nvs)
        return VideoPage(uid=uid, audio_url=audio, hls_url=hls, chapters=chapters, speakers=speakers, **page)
    finally:
        if own:
            client.close()


def decode_srt(raw: bytes) -> str:
    """AN subtitles are ISO-8859-1, not UTF-8."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("iso-8859-1")
