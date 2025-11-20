import os
import time
from typing import Callable, Iterable, List, Optional, Sequence

from g4f.client import Client
from g4f.Provider import OperaAria, Chatai, WeWordle, Startnest
from g4f.providers.retry_provider import RetryProvider
from g4f.errors import (
    ProviderNotWorkingError,
    RateLimitError,
    ModelNotFoundError,
    StreamNotSupportedError,
)


PROVIDER_REGISTRY = {
    "OperaAria": OperaAria,
    "Chatai": Chatai,
    "WeWordle": WeWordle,
    "Startnest": Startnest,
}


def _parse_provider_names(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [name.strip() for name in raw.split() if name.strip()]


class StableAIClient:
    """
    Wraps g4f.Client with a retry-aware provider configuration and backoff logic.
    The defaults follow the guidance from ИСПОЛЬЗОВАНИЕ_БЕСПЛАТНЫХ_ПРОВАЙДЕРОВ.md:
    - Use only free providers (needs_auth = False)
    - Randomize provider order to distribute load
    - Retry across providers before surfacing an error
    """

    def __init__(
        self,
        provider_names: Optional[Sequence[str]] = None,
        *,
        max_attempts: Optional[int] = None,
        backoff_seconds: Optional[float] = None,
        retry_provider_max_retries: Optional[int] = None,
    ):
        raw_env_providers = os.getenv("G4F_FREE_PROVIDERS")
        self.provider_names = (
            list(provider_names)
            if provider_names
            else _parse_provider_names(raw_env_providers)
            or ["OperaAria", "Chatai", "WeWordle", "Startnest"]
        )

        self.max_attempts = max_attempts or int(os.getenv("AI_CLIENT_MAX_ATTEMPTS", "3"))
        self.backoff_seconds = backoff_seconds or float(
            os.getenv("AI_CLIENT_BACKOFF_SECONDS", "5")
        )
        self.retry_provider_max_retries = retry_provider_max_retries or int(
            os.getenv("AI_PROVIDER_MAX_RETRIES", "3")
        )
        self.shuffle_providers = os.getenv("AI_PROVIDER_SHUFFLE", "true").lower() != "false"

        self.default_chat_model = os.getenv("G4F_CHAT_MODEL", "gpt-4o-mini")
        self.default_image_model = os.getenv("G4F_IMAGE_MODEL", "sdxl-1.0")

        self.client = self._build_client()

    def chat_completion(self, *, messages: List[dict], model: Optional[str] = None, **kwargs) -> str:
        payload = {
            "model": model or self.default_chat_model,
            "messages": messages,
            **kwargs,
        }

        response = self._run_with_retry(lambda: self.client.chat.completions.create(**payload))

        if not response or not getattr(response, "choices", None):
            raise RuntimeError("AI response did not contain any choices")

        return response.choices[0].message.content

    def generate_image(
        self,
        *,
        prompt: str,
        model: Optional[str] = None,
        response_format: str = "url",
        **kwargs,
    ):
        payload = {
            "model": model or self.default_image_model,
            "prompt": prompt,
            "response_format": response_format,
            **kwargs,
        }

        return self._run_with_retry(lambda: self.client.images.generate(**payload))

    def _run_with_retry(self, func: Callable):
        last_error = None

        for attempt in range(self.max_attempts):
            try:
                return func()
            except ModelNotFoundError as exc:
                # Fail immediately to let the caller switch models.
                raise exc
            except StreamNotSupportedError:
                # Fallback by reissuing the request without stream hint.
                return func()
            except (ProviderNotWorkingError, RateLimitError) as exc:
                last_error = exc
                if attempt < self.max_attempts - 1:
                    wait_time = self.backoff_seconds * (attempt + 1)
                    time.sleep(wait_time)
                    self._refresh_client()
                    continue
                break

        if last_error:
            raise RuntimeError(
                f"AI provider failed after {self.max_attempts} attempts: {last_error}"
            ) from last_error

        raise RuntimeError("AI provider failed without raising an explicit error")

    def _refresh_client(self):
        # Re-initialize the underlying g4f Client with a fresh provider rotation.
        self.client = self._build_client()

    def _build_client(self) -> Client:
        providers = self._resolve_providers(self.provider_names)

        retry_provider = RetryProvider(
            providers=providers,
            shuffle=self.shuffle_providers,
            single_provider_retry=False,
            max_retries=self.retry_provider_max_retries,
        )

        return Client(provider=retry_provider)

    @staticmethod
    def _resolve_providers(names: Iterable[str]):
        resolved = []
        for name in names:
            provider = PROVIDER_REGISTRY.get(name)
            if not provider:
                continue
            if getattr(provider, "working", True):
                resolved.append(provider)

        if not resolved:
            raise ValueError(
                "No working g4f providers found. "
                "Adjust G4F_FREE_PROVIDERS or update PROVIDER_REGISTRY."
            )

        return resolved

    def describe(self):
        return {
            "providers": self.provider_names,
            "max_attempts": self.max_attempts,
            "retry_provider_max_retries": self.retry_provider_max_retries,
            "chat_model": self.default_chat_model,
            "image_model": self.default_image_model,
        }

