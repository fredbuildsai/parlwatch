"""Video portal day search: the bridge from an open-data meeting to its video page.

`GET videos.assemblee-nationale.fr/php/eventsearch.php?Date=DD/MM/YYYY&Intervenant=&Commission=&Heure=&TypeVideo=&Rubrique=`
returns a JSON list (UTF-8 BOM) of that day's videos: mediaId, date (epoch), title, description (the agenda
text again), video_type (S plenary / C commission), commission code, url (`/<mediaId>_<hash>`).
Verified 2026-10-07. Dates in ISO form return [].
"""

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from difflib import SequenceMatcher

import httpx

from parlwatch.countries.base import MeetingCandidate
from parlwatch.countries.fr.media import BASE

SEARCH = f"{BASE}/php/eventsearch.php"


@dataclass
class PortalVideo:
    media_id: str
    uid: str  # "<mediaId>_<hash>", usable with media.fetch_video_page
    title: str
    description: str
    video_type: str  # S | C
    commission: str | None
    start_epoch: int

    @property
    def page_url(self) -> str:
        return f"{BASE}/video.{self.uid}"


def search_day(day: date, client: httpx.Client) -> list[PortalVideo]:
    params = {"Date": day.strftime("%d/%m/%Y"), "Intervenant": "", "Commission": "", "Heure": "",
              "TypeVideo": "", "Rubrique": ""}
    r = client.get(SEARCH, params=params)
    r.raise_for_status()
    rows = json.loads(r.content.decode("utf-8-sig") or "[]")
    return [
        PortalVideo(
            media_id=str(x["mediaId"]),
            uid=x["url"].lstrip("/"),
            title=x.get("title") or "",
            description=x.get("description") or "",
            video_type=x.get("video_type") or "",
            commission=x.get("commission"),
            start_epoch=int(x["date"]),
        )
        for x in rows
    ]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def similarity(meeting: MeetingCandidate, video: PortalVideo) -> float:
    """Text similarity between the open-data agenda and the portal description, 0..1."""
    a = _norm(meeting.agenda_text or meeting.title)[:600]
    b = _norm(video.description or video.title)[:600]
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def match_meeting(meeting: MeetingCandidate, videos: list[PortalVideo], min_score: float = 0.5,
                  ) -> tuple[PortalVideo | None, float]:
    """Best portal video of the same day for a meeting. Plenary vs commission type must agree."""
    want = "S" if meeting.kind == "plenary" else "C"
    start = meeting.raw.get("start") or ""
    best, best_score = None, 0.0
    for v in (x for x in videos if x.video_type == want):
        score = similarity(meeting, v)
        if start:
            # recordings start up to ~15 min before the convened time; reward temporal proximity
            delta = abs(datetime.fromisoformat(start).timestamp() - v.start_epoch)
            if delta < 3600:
                score += 0.1
        if score > best_score:
            best, best_score = v, score
    return (best, best_score) if best_score >= min_score else (None, best_score)
