"""Provider-agnostic LLM interface.

The pipeline talks only to this. Swapping Ollama for OpenAI or Gemini means adding
an adapter, not touching any evaluation logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


@dataclass
class LLMResponse:
    node: str
    model: str
    ok: bool
    content: str = ""
    parsed: BaseModel | None = None
    error: str | None = None
    attempts: int = 1
    latency_s: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    meta: dict = field(default_factory=dict)


@runtime_checkable
class LLMClient(Protocol):
    model_name: str

    def chat(
        self,
        messages: list[dict[str, str]],
        response_model: type[BaseModel] | None = None,
        *,
        node: str = "unknown",
        max_tokens: int | None = None,
    ) -> LLMResponse: ...

    def warmup(self) -> float: ...
