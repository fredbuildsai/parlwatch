import calendar
from datetime import date

from parlwatch.research.schema import Checkpoint, Research

FOLLOW_UP_MONTHS = {"3m": 3, "6m": 6, "12m": 12}


def add_months(d: date, n: int) -> date:
    """Calendar-month arithmetic that clamps the day (31 Aug + 6 months -> 28/29 Feb)."""
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def make_checkpoints(meeting_date: date) -> list[Checkpoint]:
    cps = [Checkpoint(label="at_meeting", due=meeting_date.isoformat())]
    cps += [Checkpoint(label=k, due=add_months(meeting_date, n).isoformat()) for k, n in FOLLOW_UP_MONTHS.items()]
    return cps


def due_checkpoints(r: Research, today: date) -> list[Checkpoint]:
    """Checkpoints whose date has passed and that have not been done yet."""
    return [c for c in r.checkpoints if date.fromisoformat(c.due) <= today and not c.done_on]


def upcoming(r: Research, today: date) -> list[Checkpoint]:
    return [c for c in r.checkpoints if date.fromisoformat(c.due) > today and not c.done_on]
