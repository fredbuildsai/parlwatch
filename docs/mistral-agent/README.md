# Mistral Studio agent: follow-up research

The agent performs one follow-up checkpoint (3, 6 or 12 months after a hearing) for ParlWatch: it re-checks each recorded assertion with web search and answers in a fixed JSON
format. ParlWatch builds the question, validates the answer, and merges it into `research.json` append-only. Design: [../research-feature.md](../research-feature.md).

## Configure the agent in Mistral Studio
| Studio setting | Value |
|---|---|
| Instructions | paste [instructions.md](instructions.md) |
| Tools | enable **web search** (the agent cannot do the job without it) |
| Response format (structured output / JSON schema) | paste [response_format.schema.json](response_format.schema.json); name it `followup_check`; strict on. [response_format.mistral.json](response_format.mistral.json) is the same thing wrapped the way the API expects it |
| Temperature | 0.2 |
| Model | the most capable model in your plan that supports tools and structured output |

**The response format and temperature can only be set in Studio:** the API refuses `completion_args` on a conversation with an agent (verified on the first live call, error 3001). ParlWatch therefore validates every answer against the schema itself and rejects anything that does not fit. If the schema is changed in code, regenerate these files:
`uv run python scripts/build_agent_files.py`, then paste the new files into Studio (this creates a new agent version).

## Versions
`configs/research_agent.yaml` has `agent_version: latest`. At each run ParlWatch asks Mistral for the agent's current version, uses that number and **records it on every check** (`agent_version`), so results stay traceable when you edit the agent. To pin a version, put an integer there.
The agent id lives in the same file; the API key does not: put `MISTRAL_API_KEY` in `.env`.

## Running it
```bash
uv run pw research agent <meeting_uid> --checkpoint 6m              # dry run: saves the raw answer, shows what would change, changes nothing
uv run pw research agent <meeting_uid> --checkpoint 6m --apply      # writes the checks; the previous research.json is kept in data/meetings/<uid>/agent_runs/
```
Raw answers, the exact input and the merge report are kept in `data/meetings/<uid>/agent_runs/`.

## What ParlWatch rejects instead of trusting
A check is not applied if: the claim id is unknown or repeated; the verdict is `supported`, `partly_supported`, `contradicted` or `outdated` but no source is given; a source URL is not http(s); the evidence is empty.
A checkpoint is marked done only when every claim got an accepted check. `verdict_changed` is recomputed from the record. Nothing the agent writes is published: it is research for a person to review.

## Not yet verified
First live call: 2026-10-09. `agents.get` returned the agent's version (2) and the request reached the agent; the first attempt failed because of `completion_args` (fixed). See `docs/pilot-2026-10/agent-run/` for the results of the first runs.

## Limits of the free tier (observed 2026-10-09)
The key used for the first run allows **3 web searches per minute and 20 per day** (response headers `x-ratelimit-limit-web-search-minute/day`), plus a token rate limit. One full run used 19 searches and about 99,000 tokens.
`max_web_searches` in `configs/research_agent.yaml` is sent to the agent as a budget (default 12), and the code stops immediately, without waiting, when the daily allowance is 0.

## Modes
- **normal**: the agent receives the claims, our earlier verdicts, evidence and hints, and appends a new check per claim. Unchanged verdicts are carried forward.
- **`--blind`**: earlier verdicts, evidence, sources and hints are withheld; the agent judges from scratch. Never applied; the command prints how many verdicts agree with ours. Use it to measure the agent, since a non-blind run tends to repeat what it is shown.
- **`--since YYYY-MM-DD`**: start of the period to examine (default: the latest done checkpoint). **`--from-raw FILE`** re-parses a saved response without calling the agent again.

## After editing the instructions in Studio
The agent gets a new version number. ParlWatch uses "latest" and records the version on every check, so results from different instruction versions can be told apart.
