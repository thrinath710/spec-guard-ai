"""Structured-output LLM access with provider failover.

`call_structured` is the single interface the LangGraph nodes depend on. Behind it sits a
chain of providers tried in order, so exhausting one provider's free-tier quota degrades to
another *model* rather than to the deterministic heuristics - which would silently return
templated text that looks like real analysis.
"""

import json
import logging
import re
import time
from typing import Protocol

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, ValidationError

from backend.app.core.config import Settings, get_settings
from backend.app.models import LogLevel
from backend.app.services import progress

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Raised when no provider could produce a valid structured response."""


class LLMUnavailable(LLMError):
    """This provider cannot serve the request now (quota, outage). Try the next tier."""


REPAIR_INSTRUCTION = (
    "Your previous response could not be parsed as valid JSON matching the required schema.\n"
    "Previous response:\n{raw}\n\n"
    "Validation error:\n{error}\n\n"
    "Return ONLY corrected valid JSON matching the required schema. No commentary, no markdown fences."
)


def _retry_after_seconds(message: str) -> float | None:
    """Providers report the wait as prose: '17.22s', '12m53.28s', or '1h58m16.03s'."""
    match = re.search(r"try again in (?:(\d+)h)?(?:(\d+)m)?([\d.]+)s", message)
    if not match:
        return None
    return (
        float(match.group(1) or 0) * 3600
        + float(match.group(2) or 0) * 60
        + float(match.group(3))
    )


class Provider(Protocol):
    name: str
    batch_size: int

    def generate(self, system_prompt: str, user_content: str) -> str: ...


# ---------------------------------------------------------------- Gemini


class GeminiProvider:
    """Google Gemini via the REST API.

    Used first because it completes an entire document in a single request. Called over plain
    HTTP rather than through an SDK to avoid another dependency for what is one endpoint.
    """

    name = "gemini"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.batch_size = settings.gemini_batch_size
        self._endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent"
        )

    def generate(self, system_prompt: str, user_content: str) -> str:
        body = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_content}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
                "maxOutputTokens": self.settings.gemini_max_tokens,
            },
        }
        try:
            response = httpx.post(
                self._endpoint,
                params={"key": self.settings.gemini_api_key},
                json=body,
                timeout=self.settings.llm_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"Gemini request failed: {exc}") from exc

        if response.status_code in (429, 503, 500, 502, 504):
            raise LLMUnavailable(
                f"Gemini unavailable (HTTP {response.status_code}): "
                f"{response.text[:160]}"
            )
        if response.status_code != 200:
            raise LLMUnavailable(
                f"Gemini rejected the request (HTTP {response.status_code}): {response.text[:160]}"
            )

        payload = response.json()
        candidates = payload.get("candidates") or []
        if not candidates:
            # Safety filters and prompt rejections both land here.
            raise LLMUnavailable(f"Gemini returned no candidates: {str(payload)[:160]}")
        candidate = candidates[0]
        text = "".join(part.get("text", "") for part in candidate.get("content", {}).get("parts", []))
        if candidate.get("finishReason") == "MAX_TOKENS":
            logger.warning("Gemini response hit the output token cap; JSON may be truncated")
        if not text.strip():
            raise LLMUnavailable("Gemini returned an empty response")
        return text


# ---------------------------------------------------------------- Groq


class GroqProvider:
    """Groq, with its own two-model chain and rate-limit backoff.

    Kept as a tier because it is by far the fastest option on small documents.
    """

    name = "groq"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.batch_size = settings.improvement_batch_size
        self._primary_exhausted_until = 0.0
        self._chat = self._build(settings.groq_model, settings.groq_max_tokens)
        self._fallback_chat = (
            self._build(settings.groq_fallback_model, settings.groq_fallback_max_tokens)
            if settings.groq_fallback_model
            and settings.groq_fallback_model != settings.groq_model
            else None
        )

    def _build(self, model: str, max_tokens: int) -> ChatGroq:
        return ChatGroq(
            model=model,
            api_key=self.settings.groq_api_key,
            temperature=0.1,
            # Retries are handled here, with rate-limit awareness. Letting the SDK retry too
            # multiplies the wait on exactly the failures that are already slowest.
            max_retries=0,
            max_tokens=max_tokens,
            timeout=self.settings.llm_timeout_seconds,
            # Reasoning tokens are drawn from max_tokens, so an unbounded chain of thought
            # eats the budget the JSON answer needs. Groq keeps reasoning out of `content`,
            # so the response stays parseable either way.
            reasoning_effort=self.settings.groq_reasoning_effort,
            model_kwargs={"response_format": {"type": "json_object"}},
        )

    def generate(self, system_prompt: str, user_content: str) -> str:
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_content)]
        for attempt in range(self.settings.llm_rate_limit_retries + 1):
            try:
                if time.monotonic() < self._primary_exhausted_until:
                    if self._fallback_chat is None:
                        raise LLMUnavailable("Groq primary model quota exhausted")
                    return self._text(self._fallback_chat.invoke(messages))
                return self._text(self._chat.invoke(messages))
            except LLMUnavailable:
                raise
            except Exception as exc:  # noqa: BLE001
                text = str(exc)
                if "rate_limit" not in text and "429" not in text:
                    raise LLMUnavailable(f"Groq request failed: {exc}") from exc

                wait = _retry_after_seconds(text)
                if wait is not None and wait > self.settings.llm_rate_limit_max_wait_seconds:
                    # A multi-minute block is the daily quota, not the per-minute window.
                    self._primary_exhausted_until = time.monotonic() + wait
                elif wait is not None and attempt < self.settings.llm_rate_limit_retries:
                    logger.warning("Groq rate limited; waiting %.1fs before retry", wait)
                    progress.report(
                        f"Groq token limit reached — waiting {wait:.0f}s for the next window.",
                        LogLevel.warning,
                    )
                    time.sleep(wait + 0.5)
                    continue

                if self._fallback_chat is not None:
                    try:
                        return self._text(self._fallback_chat.invoke(messages))
                    except Exception as fallback_exc:  # noqa: BLE001
                        raise LLMUnavailable(f"Groq exhausted: {fallback_exc}") from fallback_exc
                raise LLMUnavailable(f"Groq exhausted: {exc}") from exc
        raise LLMUnavailable("Groq exhausted its rate-limit retries")

    @staticmethod
    def _text(response) -> str:
        content = response.content
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part) for part in content
            )
        return content


# ---------------------------------------------------------------- Ollama


class OllamaProvider:
    """Local inference. Unlimited and offline, but slow, so it sits last among the models.

    Spoken to over plain HTTP so the project carries no local-inference dependency: if the
    daemon is not running the tier simply reports itself unavailable.
    """

    name = "ollama"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.batch_size = settings.ollama_batch_size

    def generate(self, system_prompt: str, user_content: str) -> str:
        try:
            response = httpx.post(
                f"{self.settings.ollama_base_url}/api/chat",
                json={
                    "model": self.settings.ollama_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.1, "num_ctx": 8192},
                },
                timeout=self.settings.ollama_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"Ollama not reachable: {exc}") from exc
        if response.status_code != 200:
            raise LLMUnavailable(f"Ollama error (HTTP {response.status_code}): {response.text[:140]}")
        content = response.json().get("message", {}).get("content", "")
        if not content.strip():
            raise LLMUnavailable("Ollama returned an empty response")
        return content


# ---------------------------------------------------------------- tiered client


class TieredLLMClient:
    """Tries each configured provider in turn, then repairs invalid JSON once."""

    def __init__(self, providers: list[Provider]) -> None:
        if not providers:
            raise LLMError(
                "No AI provider is configured. Set GEMINI_API_KEY or GROQ_API_KEY in .env."
            )
        self.providers = providers
        self._active = providers[0]

    @property
    def batch_size(self) -> int:
        """Requirements per request, taken from whichever provider is currently serving."""
        return self._active.batch_size

    @property
    def active_name(self) -> str:
        return self._active.name

    def call_structured(self, system_prompt: str, user_content: str, schema: type[BaseModel]) -> BaseModel:
        failures: list[str] = []
        for provider in self.providers:
            try:
                raw = provider.generate(system_prompt, user_content)
            except LLMUnavailable as exc:
                failures.append(f"{provider.name}: {exc}")
                logger.warning("Provider %s unavailable, trying next tier: %s", provider.name, exc)
                progress.report(
                    f"{provider.name.title()} unavailable — switching provider.",
                    LogLevel.warning,
                )
                continue

            if provider is not self._active:
                self._active = provider
                progress.report(f"Now analyzing with {provider.name}.", LogLevel.info)

            try:
                return schema.model_validate_json(raw)
            except (ValidationError, json.JSONDecodeError) as exc:
                logger.warning(
                    "%s response failed validation for %s, attempting repair",
                    provider.name,
                    schema.__name__,
                )
                try:
                    repaired = provider.generate(
                        system_prompt,
                        f"{user_content}\n\n"
                        + REPAIR_INSTRUCTION.format(raw=raw[:4000], error=str(exc)[:600]),
                    )
                    return schema.model_validate_json(repaired)
                except (ValidationError, json.JSONDecodeError, LLMUnavailable) as repair_exc:
                    failures.append(f"{provider.name}: invalid JSON ({repair_exc})")
                    continue

        raise LLMError("All AI providers failed — " + "; ".join(failures[:3]))


def build_llm_client(settings: Settings | None = None) -> TieredLLMClient:
    settings = settings or get_settings()
    builders = {
        "gemini": lambda: GeminiProvider(settings) if settings.gemini_api_key else None,
        "groq": lambda: GroqProvider(settings) if settings.groq_api_key else None,
        # Included unconditionally: availability is decided at call time by whether the local
        # daemon answers, so a machine without Ollama simply falls through this tier.
        "ollama": lambda: OllamaProvider(settings),
    }
    providers: list[Provider] = []
    for name in settings.llm_provider_order:
        builder = builders.get(name)
        if builder is None:
            continue
        provider = builder()
        if provider is not None:
            providers.append(provider)

    logger.info("LLM provider chain: %s", " -> ".join(p.name for p in providers))
    return TieredLLMClient(providers)
