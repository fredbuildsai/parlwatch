# Pilot run, October 2026

> **This is a pilot, not production data.** Two hearings of the French Assemblée nationale were pushed through an unfinished
> pipeline to find out what works, what breaks and what it costs, before building the full archive. Nothing here has been reviewed by
> a human editor. All machine output (transcripts, analyses, translations, research) must be verified before it is quoted or published.

Run on 2026-10-09 on a MacBook (Apple M1, 16 GB), using only free or local tools: Whisper large-v3-turbo (8-bit, local), a free cloud
LLM (Nemotron 3 Super via OpenRouter, through the `llmrouter-free` failover router), and web search for the research step.

## The two hearings

| | Arthur Mensch, Mistral AI | Octave Klaba, OVHcloud |
|---|---|---|
| Date | 12 May 2026 | 30 Sep 2026 |
| Body | Commission d'enquête on structural dependencies and systemic vulnerabilities in the digital sector | Commission des affaires économiques |
| Recording | 3h10 (two hearings back to back; only the Mistral part, 00:08 to 1:30:20, was analysed) | 1h25 (analysed 00:05 to 1:25) |
| Video page | `videos.assemblee-nationale.fr/video.18888392_6a0330a9d4404` | `videos.assemblee-nationale.fr/video.19471620_6abccf18f0e48` |

## What is in this folder

| Path | Content |
|---|---|
| [ASSESSMENT.md](ASSESSMENT.md) | **Start here.** What was done, stage by stage, what the numbers show, what went wrong and what to do next |
| `briefs/*.brief.fr.md`, `*.brief.en.md` | Summary, takeaways, Q&A and positions per hearing, in French and in English (machine-translated) |
| `briefs/*.context-and-followup.md` | **Research:** context before the meeting, what happened after, and checks of the main assertions, with follow-ups due at 3, 6 and 12 months |
| `transcripts/raw/` | Raw Whisper output with timestamps, including hallucinated lines (kept on purpose, to show the problem) |
| `transcripts/clean/` | Cleaned French transcript (sentences, hallucinations removed, names corrected) and its English translation |
| `analysis/` | The structured data behind the briefs (JSON), the cleaning log (every dropped line and name correction), the claim candidates proposed automatically, the research records, the portal metadata |
| [translation-test/](translation-test/README.md) | How five translation options were compared on 30 sentences, and why the free LLM was chosen |
| [../research-feature.md](../research-feature.md) | Design of the context and follow-up research feature, now part of the tool |

## Reproducing it

```bash
cd ~/code/parlwatch
pw transcribe https://videos.assemblee-nationale.fr/video.19471620_6abccf18f0e48 --quant q8   # audio -> Whisper -> segments
pw clean 19471620_6abccf18f0e48                                                               # hallucinations, names, sentences
pw analyze 19471620_6abccf18f0e48 --from 00:05:00 --to 01:25:00 --label full                  # Q&A, positions, summary
pw translate 19471620_6abccf18f0e48 --from 00:04:30 --to 01:25:00 --label full                # English transcript and brief
pw research init <uid> --date 2026-09-30 ; pw research due ; pw research render <uid>         # follow-up schedule
```

Date of this pilot snapshot: 2026-10-09. Follow-ups: see `pw research due`.
