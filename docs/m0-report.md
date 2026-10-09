# M0 report (2026-10-07/08)

## (a) France: meeting -> media (verified on real data)
- **Meetings**: legislature "Agenda" dumps on data.assemblee-nationale.fr (XV: 55k meetings from 2017-06, XVI: 8k, XVII: 8k). Agenda
  text in `ODJ` (commissions: free text; plenary: `pointsODJ.pointODJ[].objet`), flags `captationVideo`, `compteRenduRef`.
  No video id in the dump.
- **Bridge to video**: `videos.assemblee-nationale.fr/php/eventsearch.php?Date=DD/MM/YYYY&...` returns that day's videos (mediaId,
  uid, title, description = agenda text, type S/C, commission). Match on day + type + agenda-text similarity: **14/15** on a
  recent AI sample; the miss was one of three same-day plenary sittings.
- **Per video page**: SRT subtitles (`captionUrl`, ISO-8859-1), compte rendu link (`reportUrl`), `data.nvs` (chapters, speaker
  directory with deputy ids, file list incl. a direct **audio mp3**: 160 MB for 2h48 vs 2.7 GB video).
- **Caveat**: the SRT/compte rendu is the *edited* record, not verbatim. Fine for content analysis; useless as a WER reference.
- **Discovery recall caveat**: agenda-only keyword match finds 51 video-recorded meetings on AI in the XVII legislature. AI is
  often discussed in meetings whose agenda doesn't say so; M1 must also screen on compte-rendu full text.
- Keyword matching must use word boundaries and case-sensitive acronyms (substring "ia " matched "Silvia").

## (b) ASR bake-off (10 min of a plenary debate, M1 16 GB, content-word scoring vs the edited SRT)
| backend | content recall | precision | speed | peak mem |
|---|---|---|---|---|
| **whisper-large-v3-turbo q4** | **0.704** | 0.608 | 5.0x realtime | 1.2 GB |
| whisper-large-v3-turbo q8 | 0.706 | 0.619 | 5.2x | 1.6 GB |
| parakeet-tdt-0.6b-v3 bf16 | 0.193 | 0.384 | 5.3x | 3.1 GB |
| parakeet q8 (self-quantized) | 0.185 | 0.376 | 12x | 2.6 GB |
| parakeet q4 (self-quantized) | 0.106 | 0.289 | 13x | 2.3 GB |

Parakeet v3 (parakeet-mlx 0.5.3) drifted into English on French audio and dropped about half the words, so it is out. Voxtral Mini
3B was not run: mlx-community has only a bf16 build and Whisper q4 already gives usable content. **Default: Whisper turbo q4**
(~35 min for a 2h48 session). One 10-minute sample from one session: re-check on a commission audition before scaling.

## (c) Diarization
pyannote community-1 (ungated mirror `pyannote-community/speaker-diarization-community-1`) on MPS: 3.7x realtime, 6 speakers in
10 min of debate. Accuracy not scored (no per-speaker ground truth); speaker *names* come from the compte rendu / data.nvs.
Not quantizable (documented exception).

## (b, addendum) Parakeet tuning and Voxtral Mini (same 10-min sample)
Parakeet v3 q8 with short chunks: recall 0.19 (120 s) -> 0.50 (20 s) -> 0.61 (8 s), 11x realtime, but still ~60 English-looking
words (Whisper: 0). Beam search did not help. Script: scripts/parakeet_tune.py.

Voxtral Mini 3B (mzbac/voxtral-mini-3b-4bit-mixed, mlx-voxtral 0.0.6, language=fr): **recall 0.692, precision 0.608, 0 English
words**, i.e. level with Whisper q4 (0.704 / 0.608). But 1.6x realtime (6.4 min for 10 min of audio, ~1h45 per 2h48 session),
**10 GB peak memory**, 2 min model load. The 8-bit build thrashed swap (29 GB used) on the 16 GB M1 and was killed. No word
timestamps. Verdict: no accuracy gain over Whisper q4 at 3x the time and 8x the memory; not used. Script: scripts/voxtral_bakeoff.py.

## (b, addendum 2) Whisper unquantized (reference only)
whisper-large-v3-turbo fp16: recall 0.704, precision 0.617 (q8: 0.706 / 0.619, q4: 0.704 / 0.608). Identical within noise, so
quantization costs no measurable accuracy and fp16 is NOT adopted. Its 1890 s runtime is a swap-contention artifact (machine had
18 GB swap in use), not its true speed. Cloud option added: asr/backends/mistral.py (untested against the live API, no key yet).
