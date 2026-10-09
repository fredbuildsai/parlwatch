from parlwatch.asr.backends.base import AsrSegment
from parlwatch.transcripts.clean import correct_names, drop_hallucinations, merge_sentences, name_vocabulary


def seg(t, a=0.0, b=1.0):
    return AsrSegment(a, b, t, [])


def test_drop_hallucinations():
    kept, dropped = drop_hallucinations([seg("Sous-titrage ST' 501"), seg("..."), seg("Merci."), seg("Sous-titrage Société Radio-Canada"),
                                         seg("Le sous-titrage est un sujet.")])
    assert [s.text for s in kept] == ["Merci.", "Le sous-titrage est un sujet."]
    assert len(dropped) == 3


def test_name_correction_is_conservative():
    vocab = name_vocabulary(["M. Arthur Mensch", "Mme Audrey Herblin-Stoop", "Mme Cyrielle Chatelain"], ["Mistral"])
    out, log = correct_names([seg("Nous recevons M. Arthur Mench et Mme Herblain-Stoupe. Cyrielle Chatelin pose une question, "
                                  "chaque mensualité compte et les chatelains aussi.")], vocab)
    t = out[0].text
    assert "Arthur Mensch" in t and "Herblin-Stoop" in t and "Chatelain pose" in t
    assert "mensualité" in t and "chatelains" in t  # lower-case ordinary words untouched
    assert {c.after for c in log} == {"Mensch", "Herblin-Stoop", "Chatelain"}


def test_merge_sentences():
    segs = [seg("je vous propose de reprendre", 0, 2), seg("nos travaux.", 2, 3), seg("Merci.", 10, 11), seg("Bonjour", 11, 12),
            seg("à tous", 20, 21)]
    u = merge_sentences(segs)
    assert [x.text for x in u] == ["je vous propose de reprendre nos travaux.", "Merci.", "Bonjour", "à tous"]
    assert u[0].start_s == 0 and u[0].end_s == 3


def test_translate_validator_rejects_missing_but_flags_figures():
    import json

    import pytest

    from parlwatch.transcripts.translate import _validator, figure_flags

    src = ["Il fait 1,2 milliard.", "Bonjour."]
    v = _validator(src)
    assert v(json.dumps({"1": "It makes 1.2 billion.", "2": "Hello."}))["2"] == "Hello."
    with pytest.raises(ValueError):
        v(json.dumps({"1": "It makes 1.2 billion."}))  # sentence 2 missing
    assert figure_flags(src, ["It makes 2 billion.", "Hello."]) == [0]          # figure changed -> flagged, not rejected
    assert figure_flags(["à horizon 50"], ["by 2050"]) == []                     # '50' satisfied by '2050'
    assert figure_flags(["5, 10 ou 15 %"], ["five, ten or 15%"]) == [0]          # figures written as words -> review


def test_translate_figure_check_ignores_separators():
    from parlwatch.transcripts.translate import _nums

    assert _nums("1 000 clients et 0,65 point") == _nums("1,000 customers and 0.65 points") == {"1000", "065"}
    assert _nums("65 000 euros") == _nums("65,000 euros")
    assert _nums("5, 10 ou 15 %") == _nums("5, 10, or 15%") == {"5", "10", "15"}
    assert _nums("1,2 milliard") != _nums("2 billion")


def test_looks_untranslated():
    from parlwatch.transcripts.translate import looks_untranslated

    fr = "Donc comment empêcher que leur capital reste conservé sur le territoire ?"
    assert looks_untranslated(fr, fr)
    assert looks_untranslated(fr, "Donc how to prevent que le capital est conservé dans le territoire")
    assert not looks_untranslated(fr, "So how do we prevent their capital from staying on the territory?")
    assert not looks_untranslated("Merci.", "Merci.")  # short sentences are legitimately identical
