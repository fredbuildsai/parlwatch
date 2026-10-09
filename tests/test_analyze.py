import json
from types import SimpleNamespace as NS

from parlwatch.analyze.run import analyse, make_windows, verify_quote

S = [{"start_s": float(i * 10), "end_s": float(i * 10 + 9), "text": t} for i, t in enumerate([
    "La parole est à Mme Chatelain.",
    "Comment garantir notre souveraineté sur les puces et le calcul ?",
    "Je pense que l'Europe doit investir massivement dans les centres de données.",
    "Merci."])]


def test_verify_quote():
    plain = [s["text"] for s in S]
    assert verify_quote("l'Europe doit investir massivement dans les centres de données", plain)
    assert verify_quote("L'Europe doit investir massivement dans les centres de données !", plain)  # punctuation/case
    assert not verify_quote("l'Europe doit interdire tous les centres de données", plain)
    assert not verify_quote("court", plain)


def test_windows_cover_range_and_split():
    assert len(make_windows(S, 0, 100, max_chars=10_000)) == 1
    w = make_windows(S, 0, 100, max_chars=70)
    assert len(w) > 1 and sum(len(x) for x in w) == 4
    assert [s["start_s"] for s in make_windows(S, 10, 25)[0]] == [10.0, 20.0]


class FakeRouter:
    def complete(self, route, messages, **kw):
        prompt = messages[0]["content"]
        if "PART SUMMARIES" in prompt:
            out = {"summary": "S", "key_takeaways": ["a"], "open_questions": [], "ai_stance_overview": "o"}
        else:
            out = {"qa": [{"asker": "Mme Chatelain", "asker_role": "rapporteur", "question": "q", "answerer": "W", "answer": "a", "answered": True, "answer_time": "00:00:30",
                           "time": "00:00:10", "subtopics": ["sovereignty"], "ai_relevant": True}],
                   "positions": [{"speaker": "W", "target": "t", "subtopic": "compute_infrastructure", "stance": "calls_for_action", "claim": "c",
                                  "quote": "l'Europe doit investir massivement dans les centres de données", "time": "00:00:20"},
                                 {"speaker": "W", "target": "t", "subtopic": "x", "stance": "neutral", "claim": "c", "quote": "une phrase inventée de toutes pièces", "time": "00:00:20"}],
                   "window_summary": "résumé"}
        return NS(text=json.dumps(out), model="fake")


def test_analyse_end_to_end_with_fake_router():
    a = analyse(FakeRouter(), S, 0, 100, "ctx", "2026-01-01", ["Mme Chatelain"], workers=1)
    assert a["overall"]["summary"] == "S" and a["failed_windows"] == []
    assert [p["quote_verified"] for p in a["positions"]] == [True, False]
    assert a["qa"][0]["ai_relevant"] is True


def test_locate_and_roles():
    from parlwatch.analyze.run import locate, role_of

    win = [{"start_s": 10.0, "text": "Comment financer une accélération beaucoup plus forte"},
           {"start_s": 20.0, "text": "tout en la rendant soutenable ?"},
           {"start_s": 90.0, "text": "L'entreprise a évolué avec très peu de moyens extérieurs"}]
    assert locate("Comment financer une accélération plus forte et soutenable ?", win) == 10.0
    assert locate("moyens extérieurs très limités pour l'entreprise évolué", win, after_s=15.0, min_overlap=0.3) == 90.0
    assert locate("sujet totalement différent concernant l'énergie nucléaire", win) is None
    assert role_of("M. Stéphane Travert, président") == "chair" and role_of("Mme X, rapporteure") == "rapporteur"
    assert role_of("Mme Danielle Brulebois") == "deputy"


def test_canonical_name():
    from parlwatch.analyze.run import canonical_name

    people = ["Mme Valérie Rossi", "M. Octave Klaba", "Mme Cyrielle Chatelain", "M. Stéphane Travert"]
    assert canonical_name("Mme Valérie Rossier", people) == "Mme Valérie Rossi"
    assert canonical_name("Mme Cyrielle-Châtelain", people) == "Mme Cyrielle Chatelain"
    assert canonical_name("M. Octave Klaba, pdg OVHcloud", people) == "M. Octave Klaba"
    assert canonical_name("M. Stéphane Travert, président", people) == "M. Stéphane Travert"
    assert canonical_name("Unknown deputy", people) == "Unknown deputy"
    assert canonical_name("M. Jean Dupont", people) == "M. Jean Dupont"
