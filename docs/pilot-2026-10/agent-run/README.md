# First run of the Mistral research agent (2026-10-09)

**Short version:** the plumbing works end to end on the live agent, one meeting was researched, and the second meeting could not be run because the key's daily
web-search allowance was used up. The agent's quality is **not yet established**: see "What this run does not show".

## What ran
| | |
|---|---|
| Agent | Mistral Studio agent `ag_01a120fd8db9758685e63f69e9814aa9`, version 2 (looked up as "latest" at call time), model `mistral-medium-latest`, web search enabled |
| Task | Klaba hearing (30 Sep 2026), checkpoint `3m`, default period = the day of the run, **dry run** (nothing written to the research record) |
| Cost | 98,679 tokens, of which 82,981 were web-search results; **19 web searches**; about 2.5 minutes |
| Output | 9 claim checks, 1 topic update, 3 new queue items, 5 unresolved items. Saved as `klaba-3m-2026-10-09.agent-output.json` (raw search results are not included) |

## Result
All nine verdicts equal the ones in the manual research record (partly supported ×3, supported ×3, pending ×2, unverifiable ×1); the agent reproduced the calculation that the
EU contract is at most €30M a year and the FY2026 revenue estimate of €1.14 to 1.16bn. Five checks were "carried forward" (verdict unchanged, no new evidence). It added one new
detail: the inquiry report's 15 GW figure is built from grid-connection requests, from a secondary source (to be confirmed in the report itself).

## What this run does not show
- **It does not show the agent is right.** It was given our earlier verdicts, evidence and hints, so agreement may be echo. A fair test is a **blind** run (`--blind`), which withholds them.
- **The window was one day**, so there was little to find.
- **None of the three URLs it cited came from its own search results.** They were URLs from our input. The tool now marks such sources "not retrieved in this run" and drops any URL that is in neither the search results nor the record.

## What went wrong, in order
1. The API refuses `completion_args` on an agent conversation (error 3001). Response format and temperature live in Studio only; the code no longer sends them and validates the answer itself.
2. A token rate limit (429) hit once; the code now waits and retries.
3. The agent printed its JSON twice (once plain, once in a markdown fence); the parser took both. Fixed: it takes the first complete object.
4. My instructions contradicted my guard: I told the agent to repeat unchanged verdicts for every claim and also that every verdict needs a source, so 4 of 9 checks were rejected. Fixed in both (the **instructions changed: paste the new `instructions.md` into Studio**, which creates version 3).
5. **Daily web-search quota.** The key allows 3 web searches per minute and **20 per day**; the first run used 19, so the Mensch run and the full-period Klaba run were refused (HTTP 429, "web_search rate limit reached", remaining per day: 0). Retrying cannot help, so the code now stops at once with a clear message.

## To finish the test
1. Paste the regenerated `docs/mistral-agent/instructions.md` into the Studio agent (it now includes the search budget and the blind mode).
2. When the daily allowance has reset, or with a key that has a higher one:
   ```bash
   pw research agent 18888392_6a0330a9d4404 --checkpoint 3m --since 2026-05-12 --blind     # independent second opinion on Mensch
   pw research agent 19471620_6abccf18f0e48 --checkpoint 3m --since 2026-09-30 --blind     # and on Klaba
   ```
   Each blind run prints how many verdicts agree with ours and lists the disagreements. `configs/research_agent.yaml` caps searches per run (`max_web_searches: 12`), so one run costs 12 of the 20 daily searches: **one meeting per day** on this key.
3. Review the disagreements by hand before trusting the agent for unattended follow-ups.
