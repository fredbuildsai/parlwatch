import subprocess
from types import SimpleNamespace as NS

from parlwatch.asr.backends.mistral import MistralBackend


class FakeTranscriptions:
    def __init__(self):
        self.calls = []

    def complete(self, **kw):
        self.calls.append(kw)
        return NS(segments=[NS(start=0.0, end=2.0, text=" bonjour ", speaker_id="speaker_1")])


def test_chunks_offsets_and_params(tmp_path):
    wav = tmp_path / "a.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=d=25", str(wav)], check=True)
    fake = FakeTranscriptions()
    client = NS(audio=NS(transcriptions=fake))
    segs = MistralBackend(chunk_s=10, context_bias=["Legrain"], client=client).transcribe(str(wav), "fr")
    assert [round(s.start_s) for s in segs] == [0, 10, 20]  # 25 s -> 3 chunks, offsets applied
    assert segs[1].text == "bonjour" and segs[1].words[0]["speaker"] == "c1:speaker_1"
    assert fake.calls[0]["diarize"] is True and fake.calls[0]["language"] == "fr"
    assert fake.calls[0]["context_bias"] == ["Legrain"]
