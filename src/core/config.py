"""Central configuration. Everything tunable lives here, nothing is hardcoded downstream."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PIPELINE_VERSION = "pipeline-v1.0"


class Settings(BaseSettings):
    # The project .env carries many unrelated keys from earlier iterations, so we
    # ignore extras rather than fight it.
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---------------------------------------------------------------
    llm_provider: str = "ollama"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:4b"
    ollama_keep_alive: str = "30m"

    llm_temperature: float = 0.0
    llm_num_ctx: int = 8192
    llm_num_predict: int = 1024
    # The corrector emits a list of issues with Vietnamese explanations; 1024 tokens
    # truncates it mid-JSON on weak essays.
    llm_num_predict_corrector: int = 3072
    llm_enable_thinking: bool = False
    llm_max_retries: int = 2
    llm_timeout_s: int = 180
    llm_seed: int = 42

    # --- Pipeline ----------------------------------------------------------
    pipeline_max_sentence_issues: int = 8
    pipeline_min_words_task1: int = 150
    pipeline_min_words_task2: int = 250

    # --- Paths -------------------------------------------------------------
    data_dir: Path = PROJECT_ROOT / "data"
    reports_dir: Path = PROJECT_ROOT / "data" / "reports"

    @property
    def exams_dir(self) -> Path:
        return self.data_dir / "exams"

    def min_words(self, task_type: str) -> int:
        return (
            self.pipeline_min_words_task1
            if task_type == "task1"
            else self.pipeline_min_words_task2
        )


settings = Settings()
