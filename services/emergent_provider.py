"""
Nexus Flow — Emergent AI Provider
Integration for Emergent AI as planning/architecture/analysis agent.
Uses EMERGENT_API_KEY and EMERGENT_API_URL (OpenAI-compatible).
"""
import os
import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def _is_placeholder_key(api_key: str) -> bool:
    if not api_key:
        return True
    ak = api_key.strip().lower()
    return ak.startswith("your_") or ak in ("test", "placeholder", "none", "")


class EmergentProvider:
    """Emergent AI Provider — OpenAI-compatible, primary for planning/analysis/debugging."""
    name = "emergent"

    def __init__(self, api_key=None, default_model=None):
        self.api_key = api_key or os.getenv("EMERGENT_API_KEY", "")
        self.api_url = os.getenv("EMERGENT_API_URL", "") or os.getenv("EMERGENT_BASE_URL", "") or "https://api.emergent.sh/v1"
        self.default_model = default_model or os.getenv("EMERGENT_MODEL", "emergent-ai")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            # EMERGENT uses OpenAI-compatible endpoint
            base = self.api_url.rstrip("/")
            # Ensure base ends without /chat/completions
            self._client = OpenAI(api_key=self.api_key, base_url=base)
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key and not _is_placeholder_key(self.api_key) and self.api_url)

    def check_health(self) -> Dict[str, Any]:
        if not self.is_available():
            return {"available": False, "message": "No EMERGENT_API_KEY or EMERGENT_API_URL configured", "model": self.default_model}
        try:
            # Try models.list; if endpoint doesn't support, try a minimal generation
            try:
                self.client.models.list()
                return {"available": True, "message": "OK", "model": self.default_model}
            except Exception as e:
                # If models.list not supported, try to validate via API key presence
                msg = str(e)
                if "401" in msg or "403" in msg:
                    return {"available": False, "message": f"Auth failed: {msg[:200]}", "model": self.default_model}
                # Treat as available if endpoint reachable but list not supported
                return {"available": True, "message": f"Endpoint reachable ({msg[:100]})", "model": self.default_model}
        except Exception as e:
            return {"available": False, "message": f"Health check failed: {str(e)[:200]}", "model": self.default_model}

    def generate(self, prompt, system_instruction=None, model=None, temperature=0.7, max_tokens=8192):
        from services.ai_provider_manager import _classify_error, _should_retry, _get_retry_delay, LLMError
        model = model or self.default_model
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        last_error = None
        from services.ai_provider_manager import RETRY_CONFIG
        for attempt in range(RETRY_CONFIG["max_attempts"]):
            try:
                logger.info(f"[Emergent] Generating with {model} (attempt {attempt+1})")
                resp = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                text = resp.choices[0].message.content or ""
                # Clean markdown fences if present (ensure valid text)
                if text:
                    text = text.replace("```json", "").replace("```", "").strip()
                return text
            except Exception as e:
                error = _classify_error(str(e), self.name)
                last_error = error
                logger.warning(f"[Emergent] Attempt {attempt + 1}/{RETRY_CONFIG['max_attempts']} failed: {error.error_type} - {str(e)[:200]}")
                if not _should_retry(error, attempt):
                    logger.error(f"[Emergent] Non-retryable error ({error.error_type}): {error}")
                    raise
                if attempt < RETRY_CONFIG["max_attempts"] - 1:
                    delay = _get_retry_delay(attempt)
                    logger.info(f"[Emergent] Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
        if last_error:
            raise last_error
        raise LLMError("Emergent: max retries exceeded", "unknown", "emergent")

    def generate_json(self, prompt, system_instruction=None, model=None, temperature=0.3, max_tokens=16384):
        raw = self.generate(prompt, system_instruction, model, temperature, max_tokens)
        # Ensure JSON parsing with cleanup
        raw = raw.replace("```json", "").replace("```", "").strip()
        import json
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(raw[start:end])
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Could not parse JSON from Emergent response: {raw[:200]}")
