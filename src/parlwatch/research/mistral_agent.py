"""Run one follow-up checkpoint through the Mistral Studio agent."""

import json
import os
import re
from datetime import date
from typing import Any

import yaml

from parlwatch.research.agent_io import AgentOutput, build_input, response_format
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
    return "".join(getattr(ch, "text", "") or "" for ch in c)


def parse_response(resp: Any) -> AgentOutput:
    """The last message output of the conversation, parsed and validated against the response format."""
    msgs = [o for o in resp.outputs if getattr(o, "type", "") == "message.output"]
    if not msgs:
        raise ValueError("the agent returned no message output")
    text = _text_of(msgs[-1]).strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"no JSON object in the agent's answer: {text[:200]}")
    return AgentOutput.model_validate(json.loads(m.group(0)))


def run_checkpoint(r: Research, checkpoint: str, today: date, client=None, config: dict[str, Any] | None = None):
    """Returns (parsed output, raw payload sent, agent version used, usage)."""
    cfg = config or load_config()
    client = client or make_client(cfg.get("api_key_env", "MISTRAL_API_KEY"))
    version = resolve_version(client, cfg["agent_id"], cfg.get("agent_version", "latest"))
    payload = build_input(r, checkpoint, today)
    kwargs: dict[str, Any] = {
        "agent_id": cfg["agent_id"],
        "inputs": [{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        "completion_args": {"temperature": cfg.get("temperature", 0.2), "response_format": response_format()},
    }
    if version is not None:
        kwargs["agent_version"] = version
    resp = client.beta.conversations.start(**kwargs)
    return parse_response(resp), payload, version, getattr(resp, "usage", None)
