"""Write docs/mistral-agent/ from the code (instructions, JSON Schema, example input) so the pasted text always matches the parser."""
import json
from datetime import date
from pathlib import Path

from parlwatch.research.agent_instructions import INSTRUCTIONS
from parlwatch.research.agent_io import AgentOutput, build_input, example_output, response_format, strict_schema
from parlwatch.research.schema import Research

D = Path("docs/mistral-agent")
D.mkdir(parents=True, exist_ok=True)
(D / "instructions.md").write_text(INSTRUCTIONS + "\n")
(D / "response_format.schema.json").write_text(json.dumps(strict_schema(AgentOutput), indent=2, ensure_ascii=False) + "\n")
(D / "response_format.mistral.json").write_text(json.dumps(response_format(), indent=2, ensure_ascii=False) + "\n")
r = Research.model_validate_json(Path("data/meetings/18888392_6a0330a9d4404/research.json").read_text())
today = date(2026, 11, 12)
(D / "example_input.json").write_text(json.dumps(build_input(r, "6m", today), indent=2, ensure_ascii=False) + "\n")
(D / "example_output.json").write_text(json.dumps(example_output(r, "6m", today), indent=2, ensure_ascii=False) + "\n")
print("written", sorted(p.name for p in D.iterdir()))
