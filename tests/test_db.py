from datetime import date

from parlwatch.db.models import Meeting, MeetingTopic
from parlwatch.db.session import init_db, session_scope


def test_meeting_roundtrip(tmp_path):
    url = f"sqlite:///{tmp_path / 't.db'}"
    init_db(url)
    with session_scope(url) as s:
        m = Meeting(country="fr", source="an", external_id="x1", title="Audition IA", held_on=date(2024, 3, 1))
        m.topics.append(MeetingTopic(topic="ai", label="core", keyword_score=3.0))
        s.add(m)
    with session_scope(url) as s:
        got = s.query(Meeting).one()
        assert got.topics[0].label == "core"
