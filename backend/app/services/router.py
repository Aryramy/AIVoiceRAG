import time
from typing import Dict, Any, Optional, Tuple
from backend.app.schemas.settings import AISettingsResponse
from backend.app.integrations import get_provider_adapter
from backend.app.services.intent import UserIntent

class SmartAutoRouter:
    def __init__(self):
        # provider -> failure_count, last_failure_timestamp
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}

    def report_failure(self, provider: str):
        cb = self._circuit_breakers.setdefault(provider, {"failures": 0, "last_failure": 0})
        cb["failures"] += 1
        cb["last_failure"] = time.time()

    def report_success(self, provider: str):
        if provider in self._circuit_breakers:
            self._circuit_breakers[provider] = {"failures": 0, "last_failure": 0}

    def is_provider_healthy(self, provider: str) -> bool:
        cb = self._circuit_breakers.get(provider)
        if not cb:
            return True
        # If 3 or more consecutive failures and under 60 seconds cooldown, mark unhealthy
        if cb["failures"] >= 3 and (time.time() - cb["last_failure"] < 60):
            return False
        return True

    def select_model(
        self,
        settings: AISettingsResponse,
        intent: UserIntent,
        query_token_estimate: int = 100,
        has_docs: bool = False,
        is_voice: bool = False
    ) -> Tuple[str, str]:
        """
        Determines (provider, model) based on routing strategy, intent, and voice low-latency tier.
        """
        # If voice interaction is active, prioritize fast low-latency models for real-time responsiveness
        if is_voice:
            if settings.llm_provider == "openai" and self.is_provider_healthy("openai"):
                return "openai", "gpt-4o-mini"
            elif settings.llm_provider == "gemini" and self.is_provider_healthy("gemini"):
                return "gemini", "gemini-flash-latest"
            elif settings.llm_provider == "openrouter" and self.is_provider_healthy("openrouter"):
                return "openrouter", "openai/gpt-4o-mini"
            elif settings.llm_provider == "cheaper_inference" and self.is_provider_healthy("cheaper_inference"):
                return "cheaper_inference", "gpt-4o-mini"

        strategy = settings.routing_strategy or "smart_auto"

        if strategy == "manual":
            return settings.llm_provider, settings.llm_model

        if strategy == "low_cost":
            # Prefer cheapest configured provider
            if self.is_provider_healthy("gemini"):
                return "gemini", "gemini-flash-latest"
            if self.is_provider_healthy("openai"):
                return "openai", "gpt-4o-mini"
            if self.is_provider_healthy("openrouter"):
                return "openrouter", "openai/gpt-4o-mini"
            return settings.llm_provider, settings.llm_model

        if strategy == "high_quality":
            # Prefer top reasoning model
            if self.is_provider_healthy("openai"):
                return "openai", "gpt-4o"
            if self.is_provider_healthy("gemini"):
                return "gemini", "gemini-flash-latest"
            return settings.llm_provider, settings.llm_model

        # Default: smart_auto / balanced
        # If intent is conversational and no docs, low-cost model is fastest and best
        if intent == UserIntent.CONVERSATIONAL or (not has_docs and query_token_estimate < 200):
            if self.is_provider_healthy(settings.llm_provider):
                if settings.llm_provider == "openai":
                    return "openai", "gpt-4o-mini"
                elif settings.llm_provider == "gemini":
                    return "gemini", "gemini-flash-latest"
                return settings.llm_provider, settings.llm_model

        # For knowledge RAG queries with documents:
        if self.is_provider_healthy(settings.llm_provider):
            return settings.llm_provider, settings.llm_model

        # If primary provider is currently failing and fallback is enabled:
        if settings.fallback_enabled and settings.fallback_provider and settings.fallback_model:
            if self.is_provider_healthy(settings.fallback_provider):
                return settings.fallback_provider, settings.fallback_model

        return settings.llm_provider, settings.llm_model

_ROUTER = SmartAutoRouter()

def get_router() -> SmartAutoRouter:
    return _ROUTER

