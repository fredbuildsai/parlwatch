# Context and follow-up research (core feature)

**Purpose.** A transcript says what was claimed. This feature says what it builds on, and whether it holds up. For each meeting the tool keeps a research record with:
(1) the context before the meeting (what the speakers rely on), (2) what happened after, and (3) the main assertions checked against evidence, then re-checked
**3, 6 and 12 months later**. Over time this is what turns a pile of hearings into a picture of how a country's politicians' understanding of AI compares with what then happened.

Status: pilot (October 2026). Data model, scheduling and rendering are built and tested; the research itself is still done by a researcher (a person or Claude Code) following the protocol below.
Code: `src/parlwatch/research/` (`schema.py`, `checkpoints.py`, `render.py`, `extract.py`). Pilot output: `docs/pilot-2026-10/briefs/*context-and-followup.md`.

## The record (`research.json`, one per meeting)
- **checkpoints**: `at_meeting`, `3m`, `6m`, `12m` with due dates (calendar months, day clamped), done date and a note.
- **topics**: the 3 to 6 subjects the meeting turns on, each with `before` and `after` findings, every finding with sources.
- **claims**: the assertions worth checking: speaker, time in the recording, the claim in English, the verbatim French quote, kind (`figure`, `forecast`, `policy_position`, `fact`, `opinion`), and a list of **checks**, one per checkpoint, each with a verdict, evidence, sources and the date it was done.
- **queue**: things noticed and not yet researched. Nothing is silently dropped.

## Context dimensions (a hearing is never researched from one side)
Added after the first pilot review: the Klaba record covered what the company supplies but not what industry at large demands, and only part of the regulation. Every record is now checked against seven dimensions, and
`pw research coverage` shows which are covered, partial or missing (a dimension can be marked "not relevant: reason" if it truly does not apply).

| dimension | question it answers |
|---|---|
| supply | who provides it: providers, capacity, products, competition |
| demand | who needs it and how much: compute, storage and AI demand from industry at large, enterprises, public sector; spending and capacity forecasts |
| regulation | the rules: in force, adopted but not yet applicable, proposed; certifications; procurement; enforcement |
| finance | investment, funding, capital expenditure, public funds, pricing |
| energy_resources | electricity, grid connection, siting, permits, water, materials |
| geopolitics_security | extraterritorial law, dependence on foreign suppliers, supply-chain and cyber risk |
| technology | hardware, models, efficiency, open source |

Each topic carries one dimension. Both agents receive the dimension list and the current coverage, must research the missing or partial ones (before the meeting and since), and return `new_topics` and `coverage_notes`; the code files each finding as before/after the meeting by its date.
Pilot result (2026-10-10): Klaba went from 4 to 9 topics and Mensch from 4 to 9, all seven dimensions covered. One new finding stands out: ADEME found connected data centres use only about 20% of their contracted connection capacity, which weighs on how to read the "15 GW" of capacity requests the inquiry cites.

## Verdict rules
`supported` · `partly_supported` (right in substance, a detail off) · `contradicted` · `outdated` (right when said, superseded since) · `unverifiable` (no public evidence found) · `pending` (outcome not yet knowable) · `not_checked`.
- A **policy position** is never true or false: record what happened to the position and keep `pending` until a decision point passes.
- A **forecast** stays `pending` until its date; tension with current plans is noted in the evidence.
- A figure is `partly_supported` when the order of magnitude and the argument hold but the number is off; say by how much.
- "No evidence found" is `unverifiable`, never `contradicted`.

## Source tiers (shown next to every source)
**primary** = official or original (laws, EU texts, parliament, company releases, statistics offices) · **secondary** = reputable press, law-firm notes, wire services · **weak** = aggregators, blogs, vendor blogs (a lead, not evidence).
Every source records the date it was accessed and a note on whether the page was opened or only a search summary was seen. A verdict should rest on a primary source when one exists.

## Protocol v0 (what the pilot followed)
1. Read the analysis and pick 8 to 10 assertions that matter and can be checked: figures, dated facts, comparisons, forecasts. (`pw research extract` proposes candidates; a person chooses.)
2. For each topic, search what existed **before** the meeting date and what happened **since**; prefer primary sources; open the page.
3. Record the verdict, the evidence in one or two sentences, and the next step.
4. Verify mechanically: every French quote must appear in the transcript and every time must point at it (done in the pilot: it caught two errors).
5. Run `pw research init` to schedule 3, 6 and 12 months; `pw research due` lists what is open; repeat steps 2 and 3 for the open checkpoints, add a `Check` rather than overwriting the old one.

## Commands
`pw research init <uid> --date YYYY-MM-DD` · `pw research due [--today ...]` · `pw research render <uid>` · `pw research extract <uid> --from --to` (candidate claims).

## Follow-up runner (scheduled task, manual by default)
A Claude scheduled task named **`parlwatch-research-followups`** ("ParlWatch: research follow-ups (3/6/12 months)") does steps 2 and 3 of the protocol for every checkpoint that
`pw research due` reports as due. It appends checks (never overwrites), sets `done_on`, re-renders, validates the records, runs the tests and reports which verdicts changed.
Its instructions are stored in `~/.claude/scheduled-tasks/parlwatch-research-followups/SKILL.md`. It only reads the web and writes the research files of the meetings it checks.

- **Default: manual only.** It has no schedule and never runs by itself. Start it from the "Scheduled" section of the Claude app ("Run now"), or ask Claude Code to run it. Do a first "Run now" yourself so the tool permissions it needs are approved once and stored on the task.
- **Next dates** (see `pw research due`): Mensch 6m 2026-11-12, 12m 2027-05-12; Klaba 3m 2026-12-30, 6m 2027-03-30, 12m 2027-09-30. Mensch's 3m check was done late on 2026-10-09.
- **To make it automatic later:** ask Claude Code to set a schedule on the task, for example weekly on Monday at 09:00 (`0 9 * * 1`, local time). It does nothing when no checkpoint is due. It runs only while the Claude app is open; a missed run happens at the next launch. To go back to manual, remove the schedule or set `enabled: false`.
- **Before turning it on, read the first manual report.** The runner can be wrong in the ways described under "Lessons from the pilot"; its output is research for a person to review, not publishable fact.

## Mistral agent (automated follow-ups)
A Mistral Studio agent with web search can run the checks: see [mistral-agent/README.md](mistral-agent/README.md) and the first-run record in `pilot-2026-10/agent-run/`.
The code builds the question (`build_input`), validates the answer against a strict schema and merges it append-only with guards (`merge`): a new or changed verdict needs a source the agent actually retrieved in that run, invented URLs are dropped, unchanged verdicts are carried forward, a checkpoint closes only when every claim has an accepted check. Quality is unproven until blind runs are compared with the manual research.

## Lessons from the pilot
- The context the transcript lacks is often the most important finding (the AI Act delay agreed five days before the hearing; a report adopted two and a half months before another).
- Speakers' numbers are often **approximately** right and arithmetically off in detail (Klaba's "€40M a year" vs "up to €180M over 6 years"). `partly_supported` with the size of the gap is more useful than a yes or no.
- A claim can be right today and **outdated** in four months (Mistral's valuation €12bn → €21bn). The follow-up schedule is what makes that visible.
- Search summaries are not sources: 20 of 26 pilot source citations were not opened (seen only as search summaries). The protocol requires opening the page.
- Two of the researcher's own entries were wrong (a guessed timestamp; a dropped nuance). Research needs a check like any other output.

## Roadmap
1. **Search API and page archiving** (e.g. a search API plus a snapshot of each cited page) so checks can run unattended and stay reproducible when pages change.
2. **Automatic claim ranking** (importance to the argument × checkability) so extraction proposes 8, not 60.
3. **Domain connectors** for primary data: Légifrance and the Journal officiel, EUR-Lex, company filings, INSEE/RTE statistics, parliament open data.
4. **A scheduled runner** that executes due checkpoints and flags verdict changes. (Not created: scheduling is an ongoing configuration the owner should approve.)
5. **Verdict review queue**: nothing published until a person has seen it; keep an audit trail of changes.
6. **Cross-meeting view**: the same claim checked across many hearings, by party and over time, feeding the trend tables.
7. Other languages and parliaments: the record is language-neutral; only the source connectors change.
