# Translation test: who should translate the transcripts?

Question: for translating French hearing transcripts into English, is Claude (the model writing this) or a free service better suited?

## Method
30 sentences (733 words) drawn at random from the two cleaned transcripts, with 10 containing figures, 8 containing proper nouns and 12 plain
speech. They include speech-recognition slips ("circonception" for "circonscription"), disfluent speech and a garbled phrase. Five systems:

| system | what it is |
|---|---|
| **Claude** | the model doing this work, translating by hand in the session |
| **Nemotron** | Nemotron 3 Super (free tier on OpenRouter) through the project's LLM router |
| **Gemma** | local `gemma4:e4b` (quantized, via Ollama) |
| **Argos** | Argos Translate, open-source offline neural translation |
| **MyMemory** | free web translation API (anonymous use, 5,000 characters per day) |

Scoring: (1) automatic checks (figures and names preserved, chrF agreement), (2) a close reading of all 30 pairs, logging **meaning errors**
(wrong or lost meaning) separately from **literalness** (correct but stilted).

## Results

| system | sentences returned | time | meaning errors | notes |
|---|---|---|---|---|
| Claude | 30/30 | n/a (written by hand) | 0 | idiomatic; made interpretive choices (see below) |
| **Nemotron (free LLM)** | 30/30 | 15 s | **0** | literal in 5 places ("two small minutes", "fundamental exporter"); correctly read "circonception" as "constituency" |
| MyMemory | 30/30 | 67 s | 6 | left "circumception" in, dropped "Président" from "Président directeur général", turned "il" (the money) into "he", lost "horizon 50", changed the meaning of sentence 29, translated the name "Campus IA" |
| Argos | 30/30 | 16 s | 7 | "Congressman" for deputy, "public order" for public procurement, "more than 1 billion sales", "by 50", garbled sentence 30, "he goes back" for money |
| Gemma (local) | **20/30** | 126 s | n/a | ten sentences missing and one answer belonging to another sentence: unusable for batch work |

Automatic metrics barely separated the four working systems (chrF agreement 72 to 77 between any two), and the "figures kept" metric
*penalised* the best answers: Claude and Nemotron both wrote "2050" for the speaker's "horizon 50", which a literal check counts as a loss.
Read the sentence pairs, not the scores. Raw outputs and scores: `out_*.json`, `scores.json`.

## Decision
**Use Nemotron through the router for bulk translation.** It matched Claude on meaning, ran at about 2 sentences per second, costs nothing,
can be called by the tool (Claude cannot be a component of the pipeline), and works for the other languages later. Claude stays useful for
spot-checking quotes before publication and for judging hard passages.

## What happened at full scale (not visible in a 30-sentence test)
- First pass over 564 + 584 transcript sentences and 503 + 482 analysis fields: **about 2% of Klaba's sentences (11 of 564) and 12 analysis fields came back
  still in French**, because the model sometimes copies a sentence back. The tool now detects this and re-translates those items; all were repaired.
- A figure check that *rejected* batches on any change of digits failed twice for good reasons ("1 000" vs "1,000"; "horizon 50" vs "2050"). It now only
  *flags* sentences for review.
- Only random pairs were read at full scale (8 per hearing), not the whole text. Treat the English as a working translation.

## Caveats on this test
- Claude was both a candidate and the judge, and the labels were not blinded. The error tally is my reading; the files let anyone repeat it.
- 30 sentences from one domain and one language pair. MyMemory's anonymous quota (5,000 characters per day) would not cover even one hearing.
- Where Claude's version differs from the others it is by interpretation ("horizon 50" = 2050; "acteur de puissance" = "source of power"); a translator
  that interprets can also be wrong, so interpretive choices should be flagged in published text.
