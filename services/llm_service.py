"""
Nexus Flow — LLM Service
Provider abstraction with automatic model selection and fallback.
Single choke-point for all AI calls.
"""
import os
import time
import logging
import json
from typing import Optional, Dict, Any

from services.ai_provider_manager import (
    get_provider_manager,
    get_fallback_provider,
    call_llm_with_fallback,
    call_llm_json_with_fallback,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider base (kept for compatibility)
# ---------------------------------------------------------------------------

class LLMProvider:
    """Base class for LLM providers."""
    name = "base"

    def generate(self, prompt, system_instruction=None, model=None, temperature=0.7, max_tokens=8192):
        raise NotImplementedError

    def generate_json(self, prompt, system_instruction=None, model=None, temperature=0.3, max_tokens=16384):
        """Call LLM and parse JSON from response."""
        raw = self.generate(
            prompt,
            system_instruction=system_instruction,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return _parse_json(raw)

    def is_available(self) -> bool:
        """Check if provider is available."""
        return True

    def check_health(self) -> Dict[str, Any]:
        """Check provider health. Override in subclasses."""
        return {"available": True, "message": "OK"}


# ---------------------------------------------------------------------------
# Custom exceptions for better error handling
# ---------------------------------------------------------------------------

class LLMError(Exception):
    """Base LLM error."""
    def __init__(self, message: str, error_type: str = "unknown", provider: str = "unknown"):
        super().__init__(message)
        self.error_type = error_type
        self.provider = provider


class LLMRateLimitError(LLMError):
    """Rate limit or quota exceeded."""
    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message, "rate_limit", provider)


class LLMQuotaExceededError(LLMError):
    """Quota exceeded."""
    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message, "quota_exceeded", provider)


class LLMAuthError(LLMError):
    """Authentication error."""
    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message, "auth_error", provider)


class LLMModelUnavailableError(LLMError):
    """Model unavailable."""
    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message, "model_unavailable", provider)


class LLMTimeoutError(LLMError):
    """Request timeout."""
    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message, "timeout", provider)


class LLMConnectionError(LLMError):
    """Connection error."""
    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message, "connection_error", provider)


# ---------------------------------------------------------------------------
# Helper: classify error from exception message
# ---------------------------------------------------------------------------

def _classify_error(error_msg: str, provider: str) -> LLMError:
    """Classify error message into specific error type."""
    err = error_msg.lower()
    
    if "429" in err or "rate limit" in err or "rate_limit" in err:
        return LLMRateLimitError(f"Rate limit exceeded: {error_msg}", provider)
    if "quota" in err or "exceeded" in err and "quota" in err:
        return LLMQuotaExceededError(f"Quota exceeded: {error_msg}", provider)
    if "401" in err or "403" in err or "api key" in err or "unauthorized" in err or "authentication" in err:
        return LLMAuthError(f"Authentication error: {error_msg}", provider)
    if "model" in err and ("not found" in err or "unavailable" in err or "does not exist" in err or "404" in err):
        return LLMModelUnavailableError(f"Model unavailable: {error_msg}", provider)
    if "timeout" in err or "timed out" in err:
        return LLMTimeoutError(f"Request timeout: {error_msg}", provider)
    if "connection" in err or "connect" in err or "network" in err or "dns" in err:
        return LLMConnectionError(f"Connection error: {error_msg}", provider)
    
    return LLMError(f"Unknown error: {error_msg}", "unknown", provider)


# ---------------------------------------------------------------------------
# JSON helper
# ---------------------------------------------------------------------------

def _parse_json(text):
    """Extract JSON from LLM response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Could not parse JSON from LLM response: {text[:200]}")


# ---------------------------------------------------------------------------
# Public API - uses provider manager with automatic fallback
# ---------------------------------------------------------------------------

def call_llm(prompt, system_instruction=None, model=None, temperature=0.7, max_tokens=8192):
    """Convenience: call the active provider with automatic fallback."""
    return call_llm_with_fallback(prompt, system_instruction, model, temperature, max_tokens)


def call_llm_json(prompt, system_instruction=None, model=None, temperature=0.3, max_tokens=16384):
    """Convenience: call LLM and parse JSON with automatic fallback."""
    return call_llm_json_with_fallback(prompt, system_instruction, model, temperature, max_tokens)


def get_provider():
    """Get the active provider (uses provider manager)."""
    manager = get_provider_manager()
    active_p, active_m = manager.get_active_provider()
    return manager.config.providers.get(active_p)


def get_provider_with_fallback():
    """Get provider with automatic fallback to next available model."""
    manager = get_provider_manager()
    return get_fallback_provider()


def check_provider_health() -> Dict[str, Any]:
    """Check health of all available providers."""
    manager = get_provider_manager()
    return manager.get_model_status()


def get_active_model() -> tuple:
    """Get currently active provider and model."""
    manager = get_provider_manager()
    return manager.get_active_provider()


def set_active_model(provider: str, model: str) -> bool:
    """Set the active model."""
    manager = get_provider_manager()
    return manager.set_active_model(provider, model)


def auto_select_best_model() -> bool:
    """Automatically select the best available model."""
    manager = get_provider_manager()
    return manager.auto_select_model()


def get_fallback_chain() -> list:
    """Get ordered list of fallback models."""
    manager = get_provider_manager()
    return manager.get_fallback_chain()