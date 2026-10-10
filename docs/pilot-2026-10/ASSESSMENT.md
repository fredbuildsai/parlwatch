# Assessment of the October 2026 pilot

**Bottom line.** The chain works end to end on real material: from a portal video page to a cleaned French transcript, an English translation, a
structured analysis (Q&A, positions, summary) and a research record with follow-up dates, at zero cash cost on a 16 GB laptop. The raw
material is good enough to build on. The analysis layer is **not yet trustworthy without checking**: it produced a fabricated attribution in its first version, its labels are loose, and
most of what I could verify was verified by reading, not by tests. This pilot says "worth building", not "ready to publish".

## 1. What was run

Two hearings (details in the [README](README.md)). Stages: portal page → audio (mp3, never video) → local Whisper large-v3-turbo 8-bit in 10-minute pieces →
cleaning → free-LLM analysis in windows of about 15 minutes of speech → translation with the free LLM → manual research with web search.

## 2. Stage by stage

| stage | result | verdict |
|---|---|---|
| **Find the video** (M0) | Agenda dumps + the portal's day search matched 14 of 15 recent AI-related meetings; the miss was one of three plenary sittings on the same day | works, small gap |
| **Download** | Audio only: 160 to 183 MB per hearing instead of 2.7 GB of video; no bot protection met | works |
| **Transcribe** | Klaba 1h25 in 16 min (5.3× real time); Mensch 3h10 in 66 min (2.9×, machine under memory pressure). 2,508 and 916 segments | works after a serious fix (see §3) |
| **Clean** | 35 and 12 hallucinated or empty lines dropped; 10 name corrections, all correct (Mench→Mensch, Herblain-Stoupe→Herblin-Stoop, Lardit→Lhardit, Scalway→Scaleway…); phrases merged into 584 and 564 sentences | works; vocabulary is incomplete (below) |
| **Analyse** | Klaba: 5 windows, 36 Q&A (34 answered), 25 positions (24 quotes verbatim). Mensch: 6 windows, 28 Q&A (26 answered), 31 positions (29 verbatim). Question times found in the transcript for 36/36 and 25/28 | useful draft, not reliable |
| **Translate** | Free LLM chosen after a 5-way test ([details](translation-test/README.md)); full text translated, 23 untranslated items caught and repaired | works, working-quality |
| **Research** | 9 topics, 17 assertions, 19 checks, 26 source citations, follow-ups scheduled | useful, depends on live web, see §5 |
| **Existing-transcript check** | Neither video had an official subtitle file or a link to the compte rendu, so there was nothing to reuse. **The stage itself is not built yet**, only the page parser exists | not built |
| **Database** | Not used. Everything lives in files | not built |

## 3. What went wrong, and what it taught

1. **Whisper cannot take a 3-hour file in one go.** It builds the spectrogram of the whole recording at once; on 16 GB the machine swapped to a halt and produced nothing in 30 minutes.
   Fix: cut into 10-minute pieces at silences, clear the GPU cache after each piece (memory otherwise grew to 11 GB), save each piece so a killed run resumes. Found by watching the machine, not by a test.
2. **Whisper invents text over silence** ("Sous-titrage ST' 501", 34 times in one hearing). Filtered by pattern; the raw files keep them.
3. **The first analysis fabricated speakers.** The chair asked a block of questions; the model attributed them to three deputies who were in the participant list but were not speaking.
   It also pasted the same answer under every question. Fixes: the portal's own list of who speaks, in order, now goes into the prompt; a name is only allowed with a cue in the text; answers are paired per question;
   question and answer times are located by word overlap instead of trusting the model; names are snapped to the official spelling. This is the single most important lesson: **an LLM given a participant list will use it.**
4. **A figure check I wrote rejected correct translations** ("horizon 50" → 2050) and a plain length check missed sentences left in French. Both were found only at full scale.
5. **Two of my own research entries were wrong** until checked: a guessed timestamp and a summary that dropped a nuance in what Mensch said (he called market fragmentation partly an *asset*). An automated quote-and-time check caught them. Research needs the same verification as analysis.
6. **The data server stopped sending the legislature XV agenda file at 27.5 MB** (it worked once earlier). Not solved; matters for coverage back to 2017.

## 4. What I checked, and what I did not

Checked: 11 specific claims in the two briefs against the transcripts (all correct, including Mensch's 90%-of-value remark, 20% public-procurement share, 70% nuclear; Klaba's
15 to 20 million euros per megawatt, water cooling, the 5/10/15% procurement idea); all 17 French quotes in the research records appear verbatim; 30 translated sentences by hand and 8 more pairs per hearing at random.

Not checked: whether each Q&A pairing is right (I read the first Klaba window in detail, not the rest); whether the right person is named as the speaker (no speaker separation was run, the names come from text cues and the portal order, and
one deputy is credited with 10 of Klaba's 36 pairs, plausible for a multi-question block but unconfirmed against the audio); the stance labels (supportive, critical…), which are one free model's judgement; the
English text beyond samples; and 20 of the 26 research sources, which I saw only as search-result summaries, not as opened pages.

## 5. The research step

- **What it found** (full detail in the `context-and-followup` files). Examples that no transcript contains: the AI Act delay was agreed five days before Mensch spoke and became law in July; the inquiry whose hearing this was adopted a report with a
  moratorium on new data centres for US cloud giants; Mistral's valuation went from about €12bn (as Mensch said) to €21bn four months later; Klaba's "€40M a year" for the EU cloud contract does not match "up to €180M over 6 years" (at most €30M); his claim that a 1 GW site "will never exist" in France faces
  a 1.4 GW campus already announced. Verdicts: Mensch 4 supported, 1 outdated, 2 pending, 3 unverifiable; Klaba 3 supported, 3 partly supported, 2 pending, 1 unverifiable.
- **What it cannot yet do:** the follow-ups at 3, 6 and 12 months are scheduled, not done. Mensch's 3-month mark is past (done 58 days late, covering about five months); Klaba's first is due 2026-12-30.
- **Weak points:** most sources were not opened; two secondary sources disagree on one AI Act date (left flagged); the figure about Chinese open-weight models rests on aggregator sites and is marked weak; this is a web search at one point in time, so results will change.
- **The automatic claim finder** proposed 56 and 67 candidates and covered 10 of my 17 hand-picked claims (59%), and it found some I had missed (Mensch's "€1 trillion trade deficit" argument). It is a generator, not a prioritiser: most candidates are company history. It needs a ranking step.

### 5b. Context gap found and fixed (2026-10-10)
A review after the first run noted that the research looked at the witness's side only. For Klaba it covered OVHcloud, the EU contract and data-centre scale, but not **industry demand for compute and storage**, finance, geopolitics, and only part of the regulation.
The tool now has seven context dimensions with a coverage check (see `research-feature.md`), and both records were extended: 5 new topics for Klaba and 5 for Mensch, 22 and 26 findings in total, two new queued claims (K10, M9), and several conflicts between sources left visible
(who the main buyers of sovereign cloud are; whether the EU Cloud and AI Development Act sets a capacity target; the Article 50 date). Most of the added sources are search summaries, not opened pages; the `context-and-followup` files say which is which.

## 6. Limits of this pilot

Two hearings, both about AI and cloud, both with business leaders; one machine; one free model for analysis and translation; no second reviewer; no comparison against a human-made summary. Success rates here
should not be generalised to committee debates with many speakers, plenary sessions, or other languages.

## 7. Recommended next steps, in order

1. **Domain vocabulary for name correction** (organisation names and acronyms such as ANSSI, SecNumCloud, Post Telecom): the transcript has "ANSI" for ANSSI and "Deep" where the Commission's award names Post Telecom (my reading).
2. **Speaker check:** run speaker separation on one hearing and measure how often the LLM's attribution is right. Until then label attribution "inferred".
3. **Tighten the "AI-relevant" flag** (33 of 36 Klaba exchanges are tagged) and **rank** the claim candidates.
4. **Build the existing-transcript stage** and the database, then run discovery since 2017 and report counts and sample records before any bulk download (M1).
5. **Research:** archive each source page at check time, open the pages rather than relying on summaries, add a search API so checks can run unattended, and keep a human review gate before anything is published.
6. Fix the legislature XV download; test the Mistral cloud transcription backend with a real key; commit the repository.
