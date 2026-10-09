from datetime import date

from parlwatch.research.checkpoints import add_months, due_checkpoints, make_checkpoints, upcoming
from parlwatch.research.render import to_markdown
from parlwatch.research.schema import Check, Claim, Research


def test_add_months_clamps_and_rolls_year():
    assert add_months(date(2026, 8, 31), 6) == date(2027, 2, 28)
    assert add_months(date(2028, 8, 31), 6) == date(2029, 2, 28)
    assert add_months(date(2026, 9, 30), 3) == date(2026, 12, 30)
    assert add_months(date(2026, 5, 12), 12) == date(2027, 5, 12)
    assert add_months(date(2026, 11, 30), 3) == date(2027, 2, 28)


def test_checkpoints_due_and_upcoming():
    r = Research(meeting_uid="x", title="t", meeting_date="2026-05-12", researched_on="2026-10-09",
                 checkpoints=make_checkpoints(date(2026, 5, 12)))
    assert [c.label for c in r.checkpoints] == ["at_meeting", "3m", "6m", "12m"]
    today = date(2026, 10, 9)
    assert [c.label for c in due_checkpoints(r, today)] == ["at_meeting", "3m"]
    assert [c.label for c in upcoming(r, today)] == ["6m", "12m"]
    r.checkpoints[1].done_on = "2026-10-09"
    assert [c.label for c in due_checkpoints(r, today)] == ["at_meeting"]


def test_render_roundtrip():
    r = Research(meeting_uid="x", title="Hearing", meeting_date="2026-09-30", researched_on="2026-10-09",
                 checkpoints=make_checkpoints(date(2026, 9, 30)),
                 claims=[Claim(id="K1", speaker="A", time="00:01:00", text="X is 5", kind="figure",
                               checks=[Check(checkpoint="at_meeting", verdict="partly_supported", checked_on="2026-10-09", evidence="It is 4.")])])
    r2 = Research.model_validate_json(r.model_dump_json())
    md = to_markdown(r2)
    assert "partly supported" in md and "K1" in md and "2026-12-30" in md
