"""CountryAdapter protocol: one implementation per parliament."""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol


@dataclass
class MeetingCandidate:
    source: str
    external_id: str
    title: str
    held_on: date | None = None
    organ: str | None = None
    kind: str | None = None
    agenda_text: str | None = None
    video_page_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class MediaRef:
    stream_url: str  # HLS/MP4 URL
    kind: str = "official"  # official | youtube


@dataclass
class OfficialText:
    text: str
    url: str | None = None
    has_speakers: bool = True
    has_timestamps: bool = False
    coverage: float = 1.0


class CountryAdapter(Protocol):
    country: str
    language: str

    def discover(self, terms: list[str], since: date) -> list[MeetingCandidate]: ...
    def resolve_media(self, meeting: MeetingCandidate) -> list[MediaRef]: ...
    def official_transcript(self, meeting: MeetingCandidate) -> OfficialText | None: ...
