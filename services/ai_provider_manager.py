"""
Nexus Flow — AI Provider Manager
Automatic model selection, fallback, and configuration management.
"""
import os
import json
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "ai_provider_config.json")

DEFAULT_MODELS = {
    "emergent": [
        "emergent-ai",
    ],
    "groq": [
        "llama-3.3-70b-versatile",
    ],
    "gemini": [
        "gemini-3.1-pro-preview",
        "gemini-2.5-flash",
        "gemini-1.5-flash",
    ],
    "deepseek": [
        "deepseek-chat",
        "deepseek-coder",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4.1",
        "gpt-4-turbo",
    ],
}

# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ModelConfig:
    provider: str
    model: str
    priority: int = 0
    enabled: bool = True
    last_tested: Optional[str] = None
    last_status: str = "unknown"
    last_error: Optional[str] = None

@dataclass
class ProviderConfig:
    name: str
    api_key_env: str
    models: List[str]
    enabled: bool = True
    priority: int = 0

@dataclass
class AIProviderConfig:
    active_provider: str = "emergent"
    active_model: str = "emergent-ai"
    providers: Dict[str, ProviderConfig] = None
    model_configs: Dict[str, ModelConfig] = None
    fallback_enabled: bool = True
    auto_select: bool = True
    last_updated: str = ""
    
    def __post_init__(self):
        if self.providers is None:
            self.providers = {}
        if self.model_configs is None:
            self.model_configs = {}
        if not self.last_updated:
            self.last_updated = datetime.utcnow().isoformat()

# ---------------------------------------------------------------------------
# Provider Manager
# ---------------------------------------------------------------------------

class AIProviderManager:
    """Manages AI provider configuration, model selection, and fallback."""
    
    def __init__(self):
        self.config = self._load_config()
        self._ensure_defaults()
    
    def _ensure_defaults(self):
        """Ensure default provider configurations exist and migrate deprecated models."""
        for provider_name, models in DEFAULT_MODELS.items():
            api_key_env = f"{provider_name.upper()}_API_KEY"
            # Emergent AI primary (0), Groq (1), Gemini (2), DeepSeek (3), OpenAI (4)
            priority_map = {"emergent": 0, "groq": 1, "gemini": 2, "deepseek": 3, "openai": 4}
            ak = os.getenv(api_key_env, "")
            has_real_key = bool(ak and not _is_placeholder_key(ak))
            
            if provider_name not in self.config.providers:
                self.config.providers[provider_name] = ProviderConfig(
                    name=provider_name,
                    api_key_env=api_key_env,
                    models=models,
                    enabled=has_real_key,
                    priority=priority_map.get(provider_name, 2),
                )
            else:
                # Update enabled status based on current env vars (ignore placeholders)
                self.config.providers[provider_name].enabled = has_real_key
                self.config.providers[provider_name].priority = priority_map.get(provider_name, 2)
                # Sync provider model list to DEFAULT_MODELS (ensures fallback list correct)
                self.config.providers[provider_name].models = list(models)
            
            for model in models:
                key = f"{provider_name}/{model}"
                if key not in self.config.model_configs:
                    self.config.model_configs[key] = ModelConfig(
                        provider=provider_name,
                        model=model,
                        priority=DEFAULT_MODELS[provider_name].index(model),
                    )
                else:
                    # Update priority to reflect new fallback order
                    self.config.model_configs[key].priority = DEFAULT_MODELS[provider_name].index(model)
        
        # Purge any remaining deprecated model_configs not in DEFAULT_MODELS
        for key in list(self.config.model_configs.keys()):
            prov, mod = key.split("/", 1) if "/" in key else (key, "")
            if prov in DEFAULT_MODELS and mod not in DEFAULT_MODELS[prov]:
                del self.config.model_configs[key]
                logger.info(f"[ProviderManager] Purged stale model {key}")

        # Ensure active model exists and is enabled - migrate deprecated active
        active_key = f"{self.config.active_provider}/{self.config.active_model}"
        if active_key not in self.config.model_configs:
            # If active was deprecated (e.g., old deprecated model), switch to primary of same provider or first available
            if self.config.active_provider == "gemini":
                self.config.active_provider = "gemini"
                self.config.active_model = "gemini-3.1-pro-preview"
                active_key = f"gemini/gemini-3.1-pro-preview"
                if active_key not in self.config.model_configs:
                    # fallback to first available
                    first_key = list(self.config.model_configs.keys())[0] if self.config.model_configs else None
                    if first_key:
                        mc = self.config.model_configs[first_key]
                        self.config.active_provider = mc.provider
                        self.config.active_model = mc.model
            elif self.config.model_configs:
                first_key = list(self.config.model_configs.keys())[0]
                mc = self.config.model_configs[first_key]
                self.config.active_provider = mc.provider
                self.config.active_model = mc.model
        
        # Auto-select best model if current active is not available
        if self.config.auto_select:
            self.auto_select_model()
        
        self._save_config()
    
    def _load_config(self) -> AIProviderConfig:
        """Load configuration from file."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                
                # Reconstruct dataclasses from dicts
                providers = {}
                for k, v in data.get("providers", {}).items():
                    providers[k] = ProviderConfig(**v)
                
                model_configs = {}
                for k, v in data.get("model_configs", {}).items():
                    model_configs[k] = ModelConfig(**v)
                
                data["providers"] = providers
                data["model_configs"] = model_configs
                
                return AIProviderConfig(**data)
            except Exception as e:
                logger.warning(f"[ProviderManager] Failed to load config: {e}")
        return AIProviderConfig()
    
    def _save_config(self):
        """Save configuration to file."""
        try:
            self.config.last_updated = datetime.utcnow().isoformat()
            data = asdict(self.config)
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"[ProviderManager] Failed to save config: {e}")
    
    def get_active_provider(self) -> Tuple[str, str]:
        """Get currently active provider and model."""
        return self.config.active_provider, self.config.active_model
    
    def set_active_model(self, provider: str, model: str) -> bool:
        """Set the active model."""
        key = f"{provider}/{model}"
        if key not in self.config.model_configs:
            # Try to find the model
            for k, mc in self.config.model_configs.items():
                if mc.provider == provider and mc.model == model:
                    key = k
                    break
            else:
                return False
        
        mc = self.config.model_configs[key]
        if not mc.enabled:
            logger.warning(f"[ProviderManager] Model {key} is disabled")
            return False
        
        self.config.active_provider = provider
        self.config.active_model = model
        self._save_config()
        logger.info(f"[ProviderManager] Active model set to {provider}/{model}")
        return True
    
    def get_available_models(self) -> List[ModelConfig]:
        """Get list of available models (enabled, with real API key)."""
        available = []
        for key, mc in self.config.model_configs.items():
            if not mc.enabled:
                continue
            provider = self.config.providers.get(mc.provider)
            if provider:
                ak = os.getenv(provider.api_key_env, "")
                if ak and not _is_placeholder_key(ak):
                    available.append(mc)
        return available
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get status of all models."""
        status = {}
        for key, mc in self.config.model_configs.items():
            provider = self.config.providers.get(mc.provider)
            has_key = provider and bool(os.getenv(provider.api_key_env))
            is_active = (mc.provider == self.config.active_provider and mc.model == self.config.active_model)
            
            status[key] = {
                "provider": mc.provider,
                "model": mc.model,
                "enabled": mc.enabled,
                "has_api_key": has_key,
                "priority": mc.priority,
                "last_tested": mc.last_tested,
                "last_status": mc.last_status,
                "last_error": mc.last_error,
                "is_active": is_active,
            }
        return status
    
    def update_model_status(self, provider: str, model: str, status: str, error: Optional[str] = None):
        """Update model test status."""
        key = f"{provider}/{model}"
        if key in self.config.model_configs:
            mc = self.config.model_configs[key]
            mc.last_tested = datetime.utcnow().isoformat()
            mc.last_status = status
            mc.last_error = error
            self._save_config()
    
    def select_best_model(self) -> Optional[Tuple[str, str]]:
        """Automatically select the best available model."""
        available = self.get_available_models()
        if not available:
            return None
        
        # Sort by priority, then by last_status (working first)
        status_order = {"working": 0, "partial": 1, "unknown": 2, "failed": 3}
        available.sort(key=lambda m: (m.priority, status_order.get(m.last_status, 2)))
        
        best = available[0]
        return best.provider, best.model
    
    def auto_select_model(self) -> bool:
        """Automatically select and set the best model."""
        if not self.config.auto_select:
            return False
        
        best = self.select_best_model()
        if best:
            return self.set_active_model(*best)
        return False
    
    def get_fallback_chain(self) -> List[Tuple[str, str]]:
        """Get ordered list of fallback models. Provider priority first, then model priority."""
        available = self.get_available_models()
        # Provider priority map ensures Emergent > Groq > Gemini > DeepSeek > OpenAI
        provider_order = {"emergent": 0, "groq": 1, "gemini": 2, "deepseek": 3, "openai": 4}
        available.sort(key=lambda m: (provider_order.get(m.provider, 99), m.priority))
        return [(m.provider, m.model) for m in available]


# ---------------------------------------------------------------------------
# Fallback LLM Provider
# ---------------------------------------------------------------------------

class FallbackLLMProvider:
    """LLM Provider that automatically falls back through available models."""
    
    def __init__(self, manager: AIProviderManager):
        self.manager = manager
        self._providers_cache = {}
    
    def _get_provider_instance(self, provider_name: str, model: str):
        """Get or create provider instance."""
        key = f"{provider_name}/{model}"
        if key not in self._providers_cache:
            provider_config = self.manager.config.providers.get(provider_name)
            if not provider_config:
                return None
            
            api_key = os.getenv(provider_config.api_key_env, "")
            if not api_key or _is_placeholder_key(api_key):
                return None
            
            if provider_name == "emergent":
                from services.emergent_provider import EmergentProvider
                self._providers_cache[key] = EmergentProvider(api_key=api_key, default_model=model)
            elif provider_name == "groq":
                from services.ai_provider_manager import GroqProvider
                self._providers_cache[key] = GroqProvider(api_key=api_key, default_model=model)
            elif provider_name == "gemini":
                from services.ai_provider_manager import GeminiProvider
                self._providers_cache[key] = GeminiProvider(api_key=api_key, default_model=model)
            elif provider_name == "deepseek":
                from services.ai_provider_manager import DeepSeekProvider
                self._providers_cache[key] = DeepSeekProvider(api_key=api_key, default_model=model)
            elif provider_name == "openai":
                from services.ai_provider_manager import OpenAIProvider
                self._providers_cache[key] = OpenAIProvider(api_key=api_key, default_model=model)
            else:
                return None
        return self._providers_cache[key]
    
    def generate(self, prompt: str, system_instruction: str = None, 
                 model: str = None, temperature: float = 0.7, max_tokens: int = 8192) -> str:
        """Generate with automatic fallback."""
        fallback_chain = self.manager.get_fallback_chain()
        
        if not fallback_chain:
            raise RuntimeError("No available AI providers configured")
        
        last_error = None
        
        for provider_name, model in fallback_chain:
            provider = self._get_provider_instance(provider_name, model)
            if not provider:
                continue
            
            try:
                logger.info(f"[FallbackProvider] Trying {provider_name}/{model}")
                response = provider.generate(
                    prompt, 
                    system_instruction=system_instruction,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                # Success - update active model if different
                active_p, active_m = self.manager.get_active_provider()
                if active_p != provider_name or active_m != model:
                    self.manager.set_active_model(provider_name, model)
                return response
            except Exception as e:
                last_error = e
                logger.warning(f"[FallbackProvider] {provider_name}/{model} failed: {e}")
                if provider_name == "gemini":
                    logger.warning(f"Gemini model failed:\n{model}\n{str(e)[:500]}")
                    logger.info(f"Gemini model failed: {model} - will automatically continue to next provider")
                # Update model status
                self.manager.update_model_status(provider_name, model, "failed", str(e))
                continue
        
        # All models failed
        raise RuntimeError(f"All AI models failed. Last error: {last_error}")
    
    def generate_json(self, prompt: str, system_instruction: str = None,
                      model: str = None, temperature: float = 0.3, max_tokens: int = 16384) -> Dict:
        """Generate JSON with automatic fallback."""
        import json
        raw = self.generate(prompt, system_instruction, model, temperature, max_tokens)
        
        # Parse JSON
        text = raw.strip()
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
# Provider Implementations
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

def _is_placeholder_key(api_key: str) -> bool:
    """Detect placeholder / missing API keys like 'your_...here'."""
    if not api_key:
        return True
    ak = api_key.strip().lower()
    return ak.startswith("your_") or ak in ("test", "placeholder", "none", "")


def _classify_error(error_msg: str, provider: str) -> LLMError:
    """Classify error message into specific error type."""
    err = error_msg.lower()
    
    if "429" in err or "rate limit" in err or "rate_limit" in err:
        return LLMRateLimitError(f"Rate limit exceeded: {error_msg}", provider)
    if "402" in err or "insufficient balance" in err or "insufficient_balance" in err:
        return LLMQuotaExceededError(f"Quota / balance exceeded: {error_msg}", provider)
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
# Retry configuration
# ---------------------------------------------------------------------------

RETRY_CONFIG = {
    "max_attempts": 2,  # 2 per provider, then fallback to next provider
    "base_delays": [2, 5],
    "retryable_types": {"rate_limit", "timeout", "connection_error", "unknown"},
    "non_retryable_types": {"auth_error", "model_unavailable", "quota_exceeded"},
}


def _should_retry(error: LLMError, attempt: int) -> bool:
    """Determine if error should be retried."""
    if attempt >= RETRY_CONFIG["max_attempts"]:
        return False
    if error.error_type in RETRY_CONFIG["non_retryable_types"]:
        return False
    return error.error_type in RETRY_CONFIG["retryable_types"]


def _get_retry_delay(attempt: int) -> int:
    """Get delay for retry attempt (0-indexed)."""
    if attempt < len(RETRY_CONFIG["base_delays"]):
        return RETRY_CONFIG["base_delays"][attempt]
    return RETRY_CONFIG["base_delays"][-1]


# ---------------------------------------------------------------------------
# Gemini Provider
# ---------------------------------------------------------------------------

class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key=None, default_model=None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.default_model = default_model or os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key)

    def check_health(self) -> Dict[str, Any]:
        """Check if Gemini API is reachable and model is available."""
        if not self.api_key:
            return {"available": False, "message": "No API key configured", "model": self.default_model}
        
        try:
            models = self.client.models.list()
            model_names = [m.name for m in models]
            model_available = any(self.default_model in name for name in model_names)
            
            if not model_available:
                return {
                    "available": False, 
                    "message": f"Model '{self.default_model}' not found in available models",
                    "model": self.default_model,
                    "available_models": model_names[:10]
                }
            
            return {"available": True, "message": "OK", "model": self.default_model}
        except Exception as e:
            return {"available": False, "message": f"Health check failed: {str(e)}", "model": self.default_model}

    def generate(self, prompt, system_instruction=None, model=None, temperature=0.7, max_tokens=8192):
        model = model or self.default_model
        kwargs = dict(
            model=model,
            contents=prompt,
            config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )
        if system_instruction:
            kwargs["config"]["system_instruction"] = system_instruction

        last_error = None
        
        for attempt in range(RETRY_CONFIG["max_attempts"]):
            try:
                resp = self.client.models.generate_content(**kwargs)
                return resp.text or ""
            except Exception as e:
                error = _classify_error(str(e), self.name)
                last_error = error
                logger.warning(f"[Gemini] Attempt {attempt + 1}/{RETRY_CONFIG['max_attempts']} failed: {error.error_type} - {str(e)[:200]}")
                # Required logging: Gemini model failed: model name / error reason, then continue to fallback
                logger.warning(f"Gemini model failed:\n{model}\n{str(e)[:500]}")
                logger.info(f"Gemini model failed: {model} - {error.error_type} - will try fallback if available")
                
                if not _should_retry(error, attempt):
                    logger.error(f"[Gemini] Non-retryable error ({error.error_type}): {error}")
                    raise
                
                if attempt < RETRY_CONFIG["max_attempts"] - 1:
                    delay = _get_retry_delay(attempt)
                    logger.info(f"[Gemini] Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
        
        if last_error:
            raise last_error
        raise LLMError("Gemini: max retries exceeded", "unknown", "gemini")


# ---------------------------------------------------------------------------
# OpenAI Provider
# ---------------------------------------------------------------------------

class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key=None, default_model=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.default_model = default_model or os.getenv("OPENAI_MODEL", "gpt-4o")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key)

    def check_health(self) -> Dict[str, Any]:
        """Check if OpenAI API is reachable."""
        if not self.api_key:
            return {"available": False, "message": "No API key configured", "model": self.default_model}
        
        try:
            self.client.models.list()
            return {"available": True, "message": "OK", "model": self.default_model}
        except Exception as e:
            return {"available": False, "message": f"Health check failed: {str(e)}", "model": self.default_model}

    def generate(self, prompt, system_instruction=None, model=None, temperature=0.7, max_tokens=8192):
        model = model or self.default_model
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        
        for attempt in range(RETRY_CONFIG["max_attempts"]):
            try:
                resp = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                error = _classify_error(str(e), self.name)
                last_error = error
                logger.warning(f"[OpenAI] Attempt {attempt + 1}/{RETRY_CONFIG['max_attempts']} failed: {error.error_type} - {str(e)[:200]}")
                
                if not _should_retry(error, attempt):
                    logger.error(f"[OpenAI] Non-retryable error ({error.error_type}): {error}")
                    raise
                
                if attempt < RETRY_CONFIG["max_attempts"] - 1:
                    delay = _get_retry_delay(attempt)
                    logger.info(f"[OpenAI] Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
        
        if last_error:
            raise last_error
        raise LLMError("OpenAI: max retries exceeded", "unknown", "openai")


# ---------------------------------------------------------------------------
# DeepSeek Provider (OpenAI-compatible API)
# ---------------------------------------------------------------------------

class DeepSeekProvider(LLMProvider):
    name = "deepseek"

    def __init__(self, api_key=None, default_model=None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.default_model = default_model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            # DeepSeek uses OpenAI-compatible API with custom base URL
            self._client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com/v1"
            )
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key)

    def check_health(self) -> Dict[str, Any]:
        """Check if DeepSeek API is reachable."""
        if not self.api_key:
            return {"available": False, "message": "No API key configured", "model": self.default_model}
        
        try:
            self.client.models.list()
            return {"available": True, "message": "OK", "model": self.default_model}
        except Exception as e:
            return {"available": False, "message": f"Health check failed: {str(e)}", "model": self.default_model}

    def generate(self, prompt, system_instruction=None, model=None, temperature=0.7, max_tokens=8192):
        model = model or self.default_model
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        
        for attempt in range(RETRY_CONFIG["max_attempts"]):
            try:
                resp = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                error = _classify_error(str(e), self.name)
                last_error = error
                logger.warning(f"[DeepSeek] Attempt {attempt + 1}/{RETRY_CONFIG['max_attempts']} failed: {error.error_type} - {str(e)[:200]}")
                
                if not _should_retry(error, attempt):
                    logger.error(f"[DeepSeek] Non-retryable error ({error.error_type}): {error}")
                    raise
                
                if attempt < RETRY_CONFIG["max_attempts"] - 1:
                    delay = _get_retry_delay(attempt)
                    logger.info(f"[DeepSeek] Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
        
        if last_error:
            raise last_error
        raise LLMError("DeepSeek: max retries exceeded", "unknown", "deepseek")


# ---------------------------------------------------------------------------
# Groq Provider (OpenAI-compatible API) — Meta Llama 3.3
# ---------------------------------------------------------------------------

class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, api_key=None, default_model=None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.default_model = default_model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1"
            )
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key and not _is_placeholder_key(self.api_key))

    def check_health(self) -> Dict[str, Any]:
        """Check if Groq API is reachable via models list."""
        if not self.api_key or _is_placeholder_key(self.api_key):
            return {"available": False, "message": "No API key configured", "model": self.default_model}
        try:
            # Groq models.list validates key without heavy generation
            self.client.models.list()
            return {"available": True, "message": "OK", "model": self.default_model}
        except Exception as e:
            msg = str(e)
            # Map to friendly health status
            if "401" in msg or "403" in msg or "api_key" in msg.lower():
                return {"available": False, "message": f"Auth failed: {msg[:200]}", "model": self.default_model}
            return {"available": False, "message": f"Health check failed: {msg[:200]}", "model": self.default_model}

    def generate(self, prompt, system_instruction=None, model=None, temperature=0.7, max_tokens=8192):
        model = model or self.default_model
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        for attempt in range(RETRY_CONFIG["max_attempts"]):
            try:
                resp = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                error = _classify_error(str(e), self.name)
                last_error = error
                logger.warning(f"[Groq] Attempt {attempt + 1}/{RETRY_CONFIG['max_attempts']} failed: {error.error_type} - {str(e)[:200]}")
                if not _should_retry(error, attempt):
                    logger.error(f"[Groq] Non-retryable error ({error.error_type}): {error}")
                    raise
                if attempt < RETRY_CONFIG["max_attempts"] - 1:
                    delay = _get_retry_delay(attempt)
                    logger.info(f"[Groq] Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
        if last_error:
            raise last_error
        raise LLMError("Groq: max retries exceeded", "unknown", "groq")


# ---------------------------------------------------------------------------
# JSON helper
# ---------------------------------------------------------------------------

def _parse_json(text):
    """Extract JSON from LLM response, handling markdown fences."""
    # Explicit cleanup as per spec: remove markdown code blocks
    if isinstance(text, str):
        text = text.replace("```json", "")
        text = text.replace("```", "")
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
# Convenience Functions
# ---------------------------------------------------------------------------

_manager_instance = None

def get_provider_manager() -> AIProviderManager:
    """Get singleton provider manager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = AIProviderManager()
    return _manager_instance


def get_fallback_provider() -> FallbackLLMProvider:
    """Get fallback LLM provider instance."""
    return FallbackLLMProvider(get_provider_manager())


def call_llm_with_fallback(prompt: str, system_instruction: str = None,
                           model: str = None, temperature: float = 0.7, max_tokens: int = 8192) -> str:
    """Convenience function for generating with fallback."""
    return get_fallback_provider().generate(prompt, system_instruction, model, temperature, max_tokens)


def call_llm_json_with_fallback(prompt: str, system_instruction: str = None,
                                model: str = None, temperature: float = 0.3, max_tokens: int = 16384) -> Dict:
    """Convenience function for generating JSON with fallback."""
    return get_fallback_provider().generate_json(prompt, system_instruction, model, temperature, max_tokens)