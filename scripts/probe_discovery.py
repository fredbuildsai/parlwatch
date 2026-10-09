"""M0 spike: topic-filter a legislature dump, bridge to portal videos, report match quality.
usage: probe_discovery.py <legislature> <topic> [lang]"""
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

import httpx

from parlwatch.countries.fr.opendata import download_dump, iter_meetings
from parlwatch.countries.fr.portal import match_meeting, search_day
from parlwatch.settings import get_settings
from parlwatch.topics.registry import TopicRegistry

leg, topic = int(sys.argv[1]), sys.argv[2]
lang = sys.argv[3] if len(sys.argv) > 3 else "fr"
matcher = TopicRegistry(get_settings().configs_dir / "topics.yaml").matcher(topic, lang)
meetings = list(iter_meetings(download_dump(leg, Path("data/raw"))))
rec = [m for m in meetings if m.raw["captation_video"]]
hits = [m for m in rec if matcher.find(m.agenda_text or "")]
print(f"L{leg}: {len(meetings)} meetings, {len(rec)} video-recorded, {len(hits)} match '{topic}' ({lang})")
print(Counter(m.kind for m in hits), "| per year:", sorted(Counter(m.held_on.year for m in hits).items()))
sample = sorted(hits, key=lambda m: m.held_on)[-15:]
cache: dict[date, list] = {}
ok = 0
with httpx.Client(timeout=30, headers={"User-Agent": "parlwatch/0.1"}) as c:
    for m in sample:
        if m.held_on not in cache:
            cache[m.held_on] = search_day(m.held_on, c)
            time.sleep(1)
        v, s = match_meeting(m, cache[m.held_on])
        ok += v is not None
        day = cache[m.held_on]
        print(m.held_on, m.kind[:4], f"{s:.2f}", "OK " if v else "-- ", f"day_videos={len(day)}", sorted(matcher.find(m.agenda_text)), "|", m.title[:60].replace("\n", " "))
print(f"matched {ok}/{len(sample)}")
