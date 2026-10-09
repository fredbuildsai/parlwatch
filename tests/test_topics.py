import pytest

from parlwatch.topics.registry import TopicRegistry


def test_add_terms_and_generated_review(tmp_path):
    r = TopicRegistry(tmp_path / "t.yaml")
    r.add("nuclear", "Nuclear energy", "en", ["nuclear power", "reactor"])
    with pytest.raises(KeyError):
        r.matcher("nuclear", "fr")
    r.set_generated("nuclear", "fr", ["énergie nucléaire", "réacteur"], model="x")
    assert r.terms("nuclear", "fr") == []  # unreviewed terms are not used by default
    assert r.matcher("nuclear", "fr", include_unreviewed=True).find("le réacteur") == {"réacteur": 1}
    r.save()
    assert TopicRegistry(tmp_path / "t.yaml").names() == ["nuclear"]
