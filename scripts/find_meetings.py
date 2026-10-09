"""Find video-recorded meetings whose agenda mentions a regex, bridge each to its portal video. usage: find_meetings.py <regex>"""
import re
import sys
import time
from pathlib import Path

import httpx

from parlwatch.countries.fr.opendata import download_dump, iter_meetings
from parlwatch.countries.fr.portal import match_meeting, search_day

pat = re.compile(sys.argv[1], re.I)
LEGS = [int(x) for x in (sys.argv[2].split(",") if len(sys.argv) > 2 else "15,16,17".split(","))]
hits = [m for leg in LEGS for m in iter_meetings(download_dump(leg, Path("data/raw")))
        if m.agenda_text and pat.search(m.agenda_text) and m.raw["captation_video"]]
with httpx.Client(timeout=30, headers={"User-Agent": "parlwatch/0.1"}) as c:
    for m in sorted(hits, key=lambda m: m.held_on):
        v, s = match_meeting(m, search_day(m.held_on, c)); time.sleep(1)
        line = next(l for l in m.agenda_text.split("\n") if pat.search(l))[:140]
        print(m.held_on, m.kind, m.external_id, f"{s:.2f}", v.page_url if v else None, "\n    ", line)
