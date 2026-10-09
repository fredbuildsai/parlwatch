"""Assemblée nationale open data: legislature "Agenda" (réunions) dumps -> MeetingCandidate.

Dumps (verified 2026-10-07): data.assemblee-nationale.fr/static/openData/repository/<N>/vp/reunions/
  XV  -> 15/.../Agenda_XV.json.zip (~38 MB, 55k meetings, from 2017-06)
  XVI -> 16/.../Agenda.json.zip    (~8 MB)
  XVII-> 17/.../Agenda.json.zip    (~8 MB, current)
Each zip holds json/reunion/<uid>.json = {"reunion": {...}} with the agenda text (ODJ), `captationVideo`,
`compteRenduRef` and participants. There is NO video id in it: see portal.py for the bridge.
"""

import json
import zipfile
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from parlwatch.countries.base import MeetingCandidate

REPO = "https://data.assemblee-nationale.fr/static/openData/repository"
DUMPS = {
    15: f"{REPO}/15/vp/reunions/Agenda_XV.json.zip",
    16: f"{REPO}/16/vp/reunions/Agenda.json.zip",
    17: f"{REPO}/17/vp/reunions/Agenda.json.zip",
}
KIND = {"reunionCommission_type": "commission", "seance_type": "plenary", "reunionInitParlementaire_type": "other"}


@retry(retry=retry_if_exception_type(httpx.TransportError), stop=stop_after_attempt(12), wait=wait_fixed(2), reraise=True)
def download_dump(legislature: int, dest_dir: Path, force: bool = False) -> Path:
    """Download a dump, resuming a partial `.part` file with a Range request (the server drops long transfers)."""
    dest = dest_dir / f"agenda_{legislature}.json.zip"
    if dest.exists() and not force:
        return dest
    dest_dir.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    have = tmp.stat().st_size if tmp.exists() and not force else 0
    headers = {"User-Agent": "parlwatch/0.1", **({"Range": f"bytes={have}-"} if have else {})}
    with httpx.stream("GET", DUMPS[legislature], follow_redirects=True, timeout=120, headers=headers) as r:
        if r.status_code == 416:  # already complete
            tmp.rename(dest)
            return dest
        r.raise_for_status()
        with open(tmp, "ab" if have and r.status_code == 206 else "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    tmp.rename(dest)
    return dest


def _as_list(x) -> list:
    return x if isinstance(x, list) else [] if x is None else [x]


def _clean(s: str) -> str:
    return s.replace("\r", "\n").strip()


def agenda_text(rec: dict) -> str:
    """Agenda text without duplicates (convocation and summary often repeat each other).

    Commissions carry free text in ODJ.convocationODJ/resumeODJ `item`; plenary sittings carry structured
    ODJ.pointsODJ.pointODJ[] whose `objet` is the subject (the other fields are type tokens and uids).
    """
    odj = rec.get("ODJ") or {}
    parts: list[str] = []
    for key in ("convocationODJ", "resumeODJ"):
        parts += [_clean(s) for s in _as_list((odj.get(key) or {}).get("item")) if isinstance(s, str)]
    for pt in _as_list((odj.get("pointsODJ") or {}).get("pointODJ")):
        if isinstance(pt, dict) and pt.get("objet"):
            parts.append(_clean(pt["objet"]))
    seen: list[str] = []
    for s in parts:
        if s and s not in seen:
            seen.append(s)
    return "\n".join(seen)


def to_candidate(rec: dict) -> MeetingCandidate:
    ts = rec.get("timeStampDebut") or ""
    agenda = agenda_text(rec)
    first = agenda.split("\n", 1)[0] if agenda else ""
    return MeetingCandidate(
        source="an-opendata",
        external_id=rec["uid"],
        title=first[:300] or rec["uid"],
        held_on=date.fromisoformat(ts[:10]) if ts else None,
        organ=rec.get("organeReuniRef"),
        kind=KIND.get(rec.get("@xsi:type"), "other"),
        agenda_text=agenda,
        raw={
            "start": ts,
            "end": rec.get("timeStampFin"),
            "captation_video": rec.get("captationVideo") == "true",
            "compte_rendu_ref": rec.get("compteRenduRef"),
            "lieu": (rec.get("lieu") or {}).get("libelleLong"),
            "press_open": rec.get("ouverturePresse") == "true",
        },
    )


def iter_meetings(zip_path: Path, since: date | None = None) -> Iterator[MeetingCandidate]:
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            if not name.endswith(".json"):
                continue
            rec = json.loads(z.read(name)).get("reunion")
            if not rec:
                continue
            m = to_candidate(rec)
            if since and m.held_on and m.held_on < since:
                continue
            yield m
