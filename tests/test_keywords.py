from parlwatch.screen.keywords import Matcher


def test_acronym_is_case_sensitive_and_bounded():
    m = Matcher(("IA", "intelligence artificielle"))
    assert m.find("Audition de Silvia Alvarez") == {}
    assert m.find("l'IA générative") == {"IA": 1}
    assert m.find("L'Intelligence Artificielle et l'intelligence artificielle") == {"intelligence artificielle": 2}


def test_accent_insensitive():
    assert Matcher(("régulation",)).find("la REGULATION") == {"régulation": 1}


def test_score_rewards_distinct_terms():
    m = Matcher(("IA", "algorithme"))
    assert m.score("IA algorithme") > m.score("IA IA IA")
