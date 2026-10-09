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

Every call from ParlWatch also sends the response format itself, so the schema is enforced even if the Studio setting is missing. If the schema is changed in code, regenerate these files:
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
This was built and tested with a fake Mistral client. It has **not** been run against the real agent (no API key was available): the first dry run may show differences in how the answer is delivered. Whether the web-search tool returns page text or only snippets, and whether `agents.get` returns the newest version number, should be confirmed on that first run.
