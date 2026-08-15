from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SpecGuard AI"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    max_upload_mb: int = 10
    data_dir: Path = Path("data")
    uploads_dir: Path = Path("data/uploads")

    # Providers are tried in this order; the first one able to answer wins. Gemini leads
    # because it completes a whole document in one call, where Groq's per-minute token
    # budget forces a large document into many rate-limited batches.
    llm_provider_order: list[str] = Field(
        default_factory=lambda: ["gemini", "groq", "ollama"]
    )

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-flash-lite-latest"
    # Gemini handles every requirement in a single request, so batching is unnecessary.
    gemini_batch_size: int = 200
    gemini_max_tokens: int = 32000

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b-instruct"
    ollama_batch_size: int = 6
    # Local inference is far slower than hosted, so it gets a longer ceiling.
    ollama_timeout_seconds: float = 300.0

    groq_api_key: str | None = None
    # Groq decommissioned both Llama tiers on 2026-08-16; these are the replacements it
    # names for them (llama-3.3-70b-versatile -> gpt-oss-120b, llama-3.1-8b-instant -> 20b).
    groq_model: str = "openai/gpt-oss-120b"
    # Separate quota from the primary model, used when the primary is exhausted.
    groq_fallback_model: str = "openai/gpt-oss-20b"
    # The gpt-oss models reason before answering and bill those tokens against the same
    # completion budget as the JSON. Low effort keeps roughly a third of the reasoning
    # spend of the default, leaving the cap below for the answer itself.
    groq_reasoning_effort: str = "low"
    llm_timeout_seconds: float = 90.0
    # Groq defaults to a 4096-token completion cap. A whole-document analysis response
    # exceeds that on real specs and gets truncated mid-JSON, which silently drops whichever
    # sections the model emits last (conflicts and edge cases).
    # Groq admits a request against the per-minute budget using prompt + max_tokens, so a cap
    # at or above the TPM limit gets every large request rejected outright, with no retry hint.
    # Keep it comfortably under the model's tokens-per-minute allowance.
    groq_max_tokens: int = 7000
    # The fallback model has a smaller per-request budget than the primary; reusing the
    # primary's cap makes every fallback request fail with HTTP 413.
    groq_fallback_max_tokens: int = 2500
    # Requirements per call in the second pass. Keeps each response well inside the token
    # cap so coverage does not degrade as documents grow.
    improvement_batch_size: int = 8
    # Groq's free tier enforces a tokens-per-minute budget, so batches are issued serially:
    # firing them concurrently bursts straight through the limit and triggers 429s.
    llm_max_parallel: int = 1
    # Groq's per-minute token window refills every 60s, so several short waits can be needed
    # to push a large document through on the free tier.
    llm_rate_limit_retries: int = 4
    # Hard ceiling on the whole analysis. Once passed, remaining stages use the deterministic
    # analyzers so a request always terminates instead of queueing behind rate-limit waits.
    # Must stay under the frontend's 5-minute poll timeout. Large documents on a rate-limited
    # free tier legitimately need minutes; cutting them off early is what produced templated
    # fallback output instead of real analysis.
    analysis_deadline_seconds: float = 270.0
    # Wait out short per-minute windows, but fail fast on a multi-minute daily-quota block.
    llm_rate_limit_max_wait_seconds: float = 75.0

    # Groq exposes no embeddings endpoint, so RAG vectors are produced in-process by
    # fastembed. 768 dimensions to match the pgvector column in the Supabase schema.
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    # The ONNX embedding model needs ~740MB resident (bge-base) or ~390MB (bge-small).
    # Turn off on memory-constrained hosts: analysis still runs in full, only the pgvector
    # storage and retrieval step is skipped.
    embeddings_enabled: bool = True
    use_llm: bool = False

    supabase_url: str | None = None
    supabase_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    return settings
