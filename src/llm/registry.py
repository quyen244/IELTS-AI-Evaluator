"""Factory mapping provider name -> LLMClient implementation."""

from __future__ import annotations

from src.core.config import Settings, settings as default_settings
from src.llm.base import LLMClient
from src.llm.ollama_client import OllamaClient


def get_client(settings: Settings | None = None) -> LLMClient:
    s = settings or default_settings
    provider = s.llm_provider.lower()
    if provider == "ollama":
        return OllamaClient(s)
    raise ValueError(
        f"Unknown LLM_PROVIDER={provider!r}. Only 'ollama' is implemented at P0; "
        "add an adapter in src/llm/ and register it here."
    )
