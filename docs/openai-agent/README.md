# Research agent on the OpenAI Agents SDK (Nemotron + DuckDuckGo)

An alternative to the Mistral Studio agent. Same instructions, input message, response format and merge guards; different engine and tools. Nothing here needs a Mistral account.

| piece | what |
|---|---|
| Model | `nvidia/nemotron-3-super-120b-a12b:free` through OpenRouter (OpenAI-compatible), set in `configs/research_agent_openai.yaml`; key `OPENROUTER_API_KEY` in `.env` |
| Framework | `openai-agents` (OpenAI Agents SDK); tracing to OpenAI is switched off |
| Search | DuckDuckGo through `ddgs`, implemented in `src/parlwatch/websearch/` as a pluggable `Searcher`. DuckDuckGo has no official API, so it can be rate-limited or change; swap in another provider if reliability matters |
| Page reading | `fetch_page`: http(s) only, public addresses only (re-checked on every redirect), 3 MB cap, HTML via trafilatura, PDFs (first 12 pages) via pypdf, page text handed to the model as untrusted data |
| Budgets | `max_web_searches` and `max_page_fetches`, enforced in code (a call beyond the budget is refused and not performed) |
| Evidence ledger | every search, result and fetch is recorded in `data/meetings/<uid>/agent_runs/<date>_<cp>_oa_trace.json`; citations are checked against it |

```bash
uv run pw research agent <uid> --backend openai --checkpoint 3m --since 2026-09-30 --blind    # second opinion, never applied
uv run pw research agent <uid> --backend openai --checkpoint 6m --apply                       # append the checks
```

## Why this backend adds value
- **Checkable citations.** A source may claim `page_content` only if the page was really fetched; otherwise it is downgraded. URLs that appear in no search result and are not already in the record are dropped.
- **No daily web-search quota** of the kind that stopped the Mistral runs (20 searches a day on that key). Free OpenRouter models have their own daily limits.
- **Every step is inspectable**: the trace holds all queries and pages read.

## Results so far (blind runs on the Klaba hearing, 2026-10-10)
| run | what changed | outcome |
|---|---|---|
| 1 | first live run (day before) | research worked; answer had wrong field names, repair failed |
| 2 | valid example + better repair message | valid JSON; but 7 of 10 claims "unverifiable: no new evidence in the period": the agent looked only for new events in the 9-day window |
| 3 | instructions: judge each claim on all evidence of any date | judged properly (4 claims) but spent its 12 searches on them and answered "not researched" for 6 |
| 4 | claims in batches of 4, each run with its own budget, plus context-only run | 36 searches, 14 pages read, 830k tokens, about 8 minutes; verdicts compared below |

Run 4 against the manual research (10 claims): **4 agree** (K1, K2, K3, K9); **3 not researched** (K4, K7, K8: the 12-search budget per run was still too small); **1 clear agent error** (K5: it called a forecast "contradicted" because a gigawatt campus is *planned*, which cannot refute "will never exist"); **2 where the agent was at least as careful as the manual research** (K6: it found no public source for the "only 1.4 GW for European operators" split, which the manual record had accepted from press summaries; K10: it found a revenue-per-megawatt benchmark, about $15M, that the manual record had not checked). A recurring slip: it cited 9 to 11% growth guidance for OVHcloud, which is FY2025's, not FY2026's 5 to 7%.

Fixes made after run 4 (not yet re-run live): budgets now scale with the claims in a run (4 searches and 3 page reads per claim, 12 and 8 for the context-only run); the merge now **refuses** a true/false verdict on a forecast, policy position or opinion (the K5 mistake), leaving it for a human.

**Conclusion so far:** usable as a first pass or a second opinion, with a person reading the disagreements. Not usable unattended: it can still reason badly while citing real sources, and the guards check citations and rules, not logic.

## Known weaknesses
- The free Nemotron model does not reliably follow the JSON shape. First live run (2026-10-09): research worked (12 searches, 4 pages read, 19 model calls) but the answer used wrong field names and plain-string sources, and the repair turn failed the same way. Fixes added on 2026-10-10: a valid example in the instructions, a compact list of the errors in the repair message, and schema-constrained decoding for the repair turn. See the run log for whether that is enough.
- DuckDuckGo results carry no reliable date except in news mode; the agent must check dates itself.
- Quality is only measured on one hearing (10 claims). Use `--blind` and read the disagreements before trusting any verdict.
- The free model sometimes needs the repair step (it did once in run 4); running several batches per checkpoint takes about 8 minutes and 800k tokens.
