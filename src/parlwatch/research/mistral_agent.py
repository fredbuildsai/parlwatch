"""Run one follow-up checkpoint through the Mistral Studio agent."""

import json
import os
import re
import time
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from parlwatch.research.agent_io import AgentOutput, build_input, norm_url
from parlwatch.research.schema import Research
from parlwatch.settings import get_settings


def load_config() -> dict[str, Any]:
    return yaml.safe_load((get_settings().configs_dir / "research_agent.yaml").read_text())


def make_client(api_key_env: str = "MISTRAL_API_KEY"):
    from mistralai.client import Mistral

    key = os.environ.get(api_key_env)
    if not key:
        raise RuntimeError(f"{api_key_env} is not set (add it to .env)")
    return Mistral(api_key=key)


def resolve_version(client, agent_id: str, wanted: Any) -> int | None:
    """'latest' -> the agent's current version number, looked up now. An integer is used as given. None if the lookup fails."""
    if wanted not in (None, "latest"):
        return int(wanted)
    try:
        return int(client.beta.agents.get(agent_id=agent_id).version)
    except Exception:
        return None  # the call below then omits agent_version and the API default applies


def _text_of(output: Any) -> str:
    c = output.content
    if isinstance(c, str):
        return c
    return "".join(getattr(ch, "text", "") or "" for ch in c if getattr(ch, "type", "text") == "text")


def parse_text(text: str) -> AgentOutput:
    """The FIRST complete JSON object in the text (the agent sometimes repeats it inside a markdown fence), validated against the schema."""
    start = text.find("{")
    if start < 0:
        raise ValueError(f"no JSON object in the agent's answer: {text[:200]}")
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    return AgentOutput.model_validate(obj)


def parse_response(resp: Any) -> AgentOutput:
    """The last message output that contains text, parsed and validated. 'thinking' chunks are ignored."""
    texts = [t for t in (_text_of(o).strip() for o in resp.outputs if getattr(o, "type", "") == "message.output") if t]
    if not texts:
        raise ValueError("the agent returned no text answer")
    return parse_text(texts[-1])


def urls_in_search(raw: dict[str, Any]) -> set[str]:
    """URLs present in the agent's own tool (web search) results, normalised."""
    text = json.dumps([o for o in raw.get("outputs", []) if o.get("type") == "tool.execution"], ensure_ascii=False)
    return {norm_url(u.replace("\\", "")) for u in re.findall(r"https?://[^\s\"'<>)\]\\]+", text)}


def parse_raw_file(path: Path) -> AgentOutput:
    """Re-parse a saved raw response (data/meetings/<uid>/agent_runs/*_raw_response.json) without calling the agent again."""
    outs = json.loads(path.read_text())["outputs"]
    texts = []
    for o in outs:
        if o.get("type") == "message.output":
            c = o.get("content")
            t = c if isinstance(c, str) else "".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
            if t.strip():
                texts.append(t.strip())
    if not texts:
        raise ValueError("no text answer in the saved response")
    return parse_text(texts[-1])


class DailyQuotaExhausted(RuntimeError):
    """Mistral's per-day allowance (e.g. web_search 20 per day on the free tier) is used up: waiting a minute will not help."""


def _is_rate_limit(e: Exception) -> bool:
    return getattr(e, "status_code", None) == 429 or "429" in str(e)[:120] or "rate limit" in str(e).lower()[:300]


def _limit_headers(e: Exception) -> dict[str, str]:
    h = getattr(e, "headers", None) or getattr(getattr(e, "raw_response", None), "headers", None)
    return {k.lower(): v for k, v in dict(h).items()} if h else {}


def _daily_exhausted(e: Exception) -> bool:
    return any(k.startswith("x-ratelimit-remaining") and k.endswith("-day") and v == "0" for k, v in _limit_headers(e).items())


def run_checkpoint(r: Research, checkpoint: str, today: date, client=None, config: dict[str, Any] | None = None,
                   raw_sink: Path | None = None, wait_s: float = 65.0, max_attempts: int = 4, since: date | None = None,
                   blind: bool = False):
    """Returns (parsed output, raw payload sent, agent version used, usage).

    Waits and retries when Mistral answers 429 (token rate limit). If `raw_sink` is given, the agent's raw response is written there
    BEFORE parsing, so a parsing problem never costs a (slow, rate-limited) answer.
    """
    cfg = config or load_config()
    client = client or make_client(cfg.get("api_key_env", "MISTRAL_API_KEY"))
    version = resolve_version(client, cfg["agent_id"], cfg.get("agent_version", "latest"))
    payload = build_input(r, checkpoint, today, since, blind, cfg.get("max_web_searches"))
    kwargs: dict[str, Any] = {
        "agent_id": cfg["agent_id"],
        "inputs": [{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        # No completion_args here: the API rejects them for agent conversations (verified 2026-10-09, error 3001). The response format and
        # temperature are part of the agent's own configuration in Mistral Studio; the answer is validated against the schema on our side.
    }
    if version is not None:
        kwargs["agent_version"] = version
    for attempt in range(1, max_attempts + 1):
        try:
            resp = client.beta.conversations.start(**kwargs)
            break
        except Exception as e:
            if not _is_rate_limit(e):
                raise
            if _daily_exhausted(e):
                lim = {k: v for k, v in _limit_headers(e).items() if "ratelimit" in k}
                raise DailyQuotaExhausted(f"daily quota used up ({lim}); try again after it resets, or use a key with a higher allowance") from e
            if attempt == max_attempts:
                raise
            time.sleep(wait_s)
    if raw_sink is not None:
        raw_sink.write_text(resp.model_dump_json(indent=1) if hasattr(resp, "model_dump_json") else json.dumps(str(resp)))
        raw_sink.with_name(raw_sink.name.replace("_raw_response", "_run_meta")).write_text(json.dumps(
            {"agent_id": cfg["agent_id"], "agent_version": version, "checkpoint": checkpoint, "today": today.isoformat(),
             "period": payload["period"], "model": next((getattr(o, "model", None) for o in resp.outputs if getattr(o, "model", None)), None)}, indent=1))
    return parse_response(resp), payload, version, getattr(resp, "usage", None)
