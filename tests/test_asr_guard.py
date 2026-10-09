import pytest

from parlwatch.asr.backends.base import UnquantizedModelError
from parlwatch.asr.backends.whisper import WhisperBackend


@pytest.mark.parametrize("q", [None, "", "bf16", "fp16"])
def test_unquantized_rejected(q):
    with pytest.raises(UnquantizedModelError):
        WhisperBackend(q)


def test_quantized_accepted():
    assert WhisperBackend("q4").quant == "q4"


def test_plan_cuts_prefers_silence_and_covers_everything():
    from parlwatch.asr.chunking import plan_cuts

    cuts = plan_cuts(2000.0, [590.0, 1230.0, 1500.0], target_s=600.0, search_s=90.0)
    assert cuts[0] == 0.0 and cuts[-1] == 2000.0
    assert 590.0 in cuts and 1230.0 in cuts          # snapped to silences near 600 / 1200
    assert all(b - a <= 600.0 + 90.0 for a, b in zip(cuts, cuts[1:], strict=False))
    assert plan_cuts(300.0, [], 600.0) == [0.0, 300.0]  # short audio: one piece
