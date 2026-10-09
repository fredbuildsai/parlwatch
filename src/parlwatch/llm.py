"""Shared LLM router (llmrouter-free): free-tier cloud first, local quantized Ollama as fallback."""

from llmrouter_free import build_router, load_routes

from parlwatch.db.session import make_engine
from parlwatch.settings import get_settings, load_env


def get_router():
    load_env()
    s = get_settings()
    return build_router(load_routes(s.configs_dir / "llm_routes.yaml"), engine=make_engine(f"sqlite:///{s.data_dir / 'llm.db'}"))
