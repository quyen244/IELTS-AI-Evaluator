"""Ollama adapter with structured output, thinking disabled, and retry-with-repair."""

from __future__ import annotations

import json
import time

import ollama
from pydantic import BaseModel, ValidationError

from src.core.config import Settings, settings as default_settings
from src.llm.base import LLMResponse

REPAIR_TEMPLATE = (
    "Your previous response could not be validated.\n"
    "Error: {error}\n\n"
    "Return ONLY a JSON object that satisfies the schema. Do not add commentary, "
    "markdown fences, or extra fields."
)

# A truncated response is not a formatting mistake — the model ran out of output
# budget. Repeating the same request produces the same truncation, so the repair
# has to ask for a shorter answer instead.
TRUNCATION_TEMPLATE = (
    "Your previous response was cut off before the JSON was complete because it "
    "exceeded the output limit.\n\n"
    "Produce the same JSON structure but SHORTER: return at most half as many items "
    "in every list, and keep each text field under 200 characters. Completeness of "
    "the JSON matters more than completeness of the analysis."
)


class OllamaClientError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or default_settings
        self.model_name = self.settings.ollama_model
        self._client = ollama.Client(
            host=self.settings.ollama_host,
            timeout=self.settings.llm_timeout_s,
        )

    # ------------------------------------------------------------------ #
    def _options(self, max_tokens: int | None) -> dict:
        return {
            "temperature": self.settings.llm_temperature,
            "num_ctx": self.settings.llm_num_ctx,
            "num_predict": max_tokens or self.settings.llm_num_predict,
            "seed": self.settings.llm_seed,
            # Belt-and-braces: some Qwen chat templates read this flag directly,
            # in addition to the `think` API parameter below.
            "enable_thinking": self.settings.llm_enable_thinking,
        }

    def _raw_chat(self, messages: list[dict[str, str]], fmt, max_tokens: int | None):
        return self._client.chat(
            model=self.model_name,
            messages=messages,
            format=fmt,
            think=self.settings.llm_enable_thinking,  # False by design
            keep_alive=self.settings.ollama_keep_alive,
            options=self._options(max_tokens),
        )

    # ------------------------------------------------------------------ #
    def chat(
        self,
        messages: list[dict[str, str]],
        response_model: type[BaseModel] | None = None,
        *,
        node: str = "unknown",
        max_tokens: int | None = None,
    ) -> LLMResponse:
        fmt = response_model.model_json_schema() if response_model else None
        convo = list(messages)

        started = time.perf_counter()
        last_error: str | None = None
        content = ""
        prompt_tokens = completion_tokens = 0

        for attempt in range(1, self.settings.llm_max_retries + 2):
            try:
                raw = self._raw_chat(convo, fmt, max_tokens)
            except Exception as exc:  # connection refused, model missing, timeout
                return LLMResponse(
                    node=node,
                    model=self.model_name,
                    ok=False,
                    error=f"{type(exc).__name__}: {exc}",
                    attempts=attempt,
                    latency_s=time.perf_counter() - started,
                )

            content = raw.message.content or ""
            prompt_tokens += raw.prompt_eval_count or 0
            completion_tokens += raw.eval_count or 0
            truncated = getattr(raw, "done_reason", None) == "length"

            if response_model is None:
                return LLMResponse(
                    node=node,
                    model=self.model_name,
                    ok=True,
                    content=content,
                    attempts=attempt,
                    latency_s=time.perf_counter() - started,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )

            try:
                parsed = response_model.model_validate_json(content)
                return LLMResponse(
                    node=node,
                    model=self.model_name,
                    ok=True,
                    content=content,
                    parsed=parsed,
                    attempts=attempt,
                    latency_s=time.perf_counter() - started,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
            except (ValidationError, json.JSONDecodeError) as exc:
                last_error = ("output truncated at token limit: " if truncated else "") + str(exc)[:600]
                repair = (
                    TRUNCATION_TEMPLATE
                    if truncated
                    else REPAIR_TEMPLATE.format(error=last_error)
                )
                convo = convo + [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": repair},
                ]

        return LLMResponse(
            node=node,
            model=self.model_name,
            ok=False,
            content=content,
            error=last_error,
            attempts=self.settings.llm_max_retries + 1,
            latency_s=time.perf_counter() - started,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    # ------------------------------------------------------------------ #
    def warmup(self) -> float:
        """Load the model into VRAM.

        Cold load is ~110s on the reference machine. Without this, the first essay's
        latency is dominated by model loading and every timing number is meaningless.
        """
        started = time.perf_counter()
        try:
            self._raw_chat([{"role": "user", "content": "ok"}], None, 4)
        except Exception as exc:
            raise OllamaClientError(
                f"Cannot reach Ollama at {self.settings.ollama_host} with model "
                f"'{self.model_name}'. Is `ollama serve` running and has the model "
                f"been pulled (`ollama pull {self.model_name}`)?\nUnderlying error: {exc}"
            ) from exc
        return time.perf_counter() - started
