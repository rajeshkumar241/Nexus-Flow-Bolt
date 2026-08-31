"""
Nexus Flow — AI Model Testing System
Tests available AI providers/models and generates a report.
"""
import os
import time
import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Test Configuration
# ---------------------------------------------------------------------------

TEST_PROMPT = """Create a website architecture plan for a dashboard application with:
- User authentication (login, register, password reset)
- Dashboard with metrics overview and charts
- User management (list, create, edit, delete users)
- Settings page with profile and preferences
- Dark/light mode toggle
- Responsive navigation with sidebar

Return a JSON plan with project_name, project_type, pages, components, features, and design system."""

MODEL_CONFIGS = {
    "gemini": {
        "provider": "gemini",
        "models": [
            "gemini-3.1-pro-preview",
            "gemini-2.5-flash",
            "gemini-1.5-flash",
        ],
        "api_key_env": "GEMINI_API_KEY",
    },
    "openai": {
        "provider": "openai",
        "models": [
            "gpt-4o",
            "gpt-4.1",
        ],
        "api_key_env": "OPENAI_API_KEY",
    },
}

# ---------------------------------------------------------------------------
# Result Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ModelTestResult:
    provider: str
    model: str
    status: str  # "working", "failed", "skipped"
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    token_usage: Optional[Dict[str, Any]] = None
    response_preview: Optional[str] = None
    tested_at: str = ""
    
    def __post_init__(self):
        if not self.tested_at:
            self.tested_at = datetime.utcnow().isoformat()

@dataclass
class TestReport:
    timestamp: str
    results: List[ModelTestResult]
    summary: Dict[str, Any]
    recommended_model: Optional[Dict[str, str]] = None

# ---------------------------------------------------------------------------
# Model Tester Class
# ---------------------------------------------------------------------------

class AIModelTester:
    """Tests AI models and generates evaluation report."""
    
    def __init__(self):
        self.results: List[ModelTestResult] = []
        
    def test_model(self, provider_name: str, model: str, api_key: str, timeout: int = 60) -> ModelTestResult:
        """Test a single model with the standard test prompt."""
        start_time = time.time()
        
        try:
            if provider_name == "gemini":
                return self._test_gemini_model(model, api_key, start_time, timeout)
            elif provider_name == "openai":
                return self._test_openai_model(model, api_key, start_time, timeout)
            else:
                return ModelTestResult(
                    provider=provider_name,
                    model=model,
                    status="skipped",
                    error_message=f"Unknown provider: {provider_name}",
                    error_type="unknown_provider",
                    response_time=time.time() - start_time,
                )
        except Exception as e:
            elapsed = time.time() - start_time
            return ModelTestResult(
                provider=provider_name,
                model=model,
                status="failed",
                response_time=elapsed,
                error_message=str(e),
                error_type=type(e).__name__,
            )
    
    def _test_gemini_model(self, model: str, api_key: str, start_time: float, timeout: int) -> ModelTestResult:
        """Test a Gemini model."""
        from google import genai
        
        client = genai.Client(api_key=api_key)
        
        # Check if model exists
        try:
            models = client.models.list()
            model_names = [m.name for m in models]
            if not any(model in name for name in model_names):
                return ModelTestResult(
                    provider="gemini",
                    model=model,
                    status="failed",
                    response_time=time.time() - start_time,
                    error_message=f"Model '{model}' not found in available models",
                    error_type="model_unavailable",
                    available_models=model_names[:10],
                )
        except Exception as e:
            # If we can't list models, continue anyway
            pass
        
        # Test generation
        try:
            resp = client.models.generate_content(
                model=model,
                contents=TEST_PROMPT,
                config={
                    "temperature": 0.3,
                    "max_output_tokens": 8192,
                },
            )
            elapsed = time.time() - start_time
            response_text = resp.text or ""
            
            # Try to parse JSON
            is_valid_json = False
            try:
                import json
                json.loads(response_text)
                is_valid_json = True
            except json.JSONDecodeError:
                pass
            
            return ModelTestResult(
                provider="gemini",
                model=model,
                status="working" if is_valid_json else "partial",
                response_time=elapsed,
                response_preview=response_text[:200] + "..." if len(response_text) > 200 else response_text,
                token_usage={"prompt_tokens": getattr(resp, 'usage_metadata', {}).get('prompt_token_count', 0),
                           "completion_tokens": getattr(resp, 'usage_metadata', {}).get('candidates_token_count', 0)} if hasattr(resp, 'usage_metadata') else None,
            )
        except Exception as e:
            elapsed = time.time() - start_time
            error_str = str(e).lower()
            
            error_type = "unknown"
            if "429" in error_str or "rate limit" in error_str:
                error_type = "rate_limit"
            elif "quota" in error_str:
                error_type = "quota_exceeded"
            elif "401" in error_str or "403" in error_str or "api key" in error_str:
                error_type = "auth_error"
            elif "model" in error_str and ("not found" in error_str or "404" in error_str):
                error_type = "model_unavailable"
            elif "timeout" in error_str:
                error_type = "timeout"
            
            return ModelTestResult(
                provider="gemini",
                model=model,
                status="failed",
                response_time=elapsed,
                error_message=str(e),
                error_type=error_type,
            )
    
    def _test_openai_model(self, model: str, api_key: str, start_time: float, timeout: int) -> ModelTestResult:
        """Test an OpenAI model."""
        from openai import OpenAI
        
        client = OpenAI(api_key=api_key)
        
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": TEST_PROMPT}],
                temperature=0.3,
                max_tokens=8192,
            )
            elapsed = time.time() - start_time
            response_text = resp.choices[0].message.content or ""
            
            # Try to parse JSON
            is_valid_json = False
            try:
                import json
                json.loads(response_text)
                is_valid_json = True
            except json.JSONDecodeError:
                pass
            
            return ModelTestResult(
                provider="openai",
                model=model,
                status="working" if is_valid_json else "partial",
                response_time=elapsed,
                response_preview=response_text[:200] + "..." if len(response_text) > 200 else response_text,
                token_usage={"prompt_tokens": resp.usage.prompt_tokens,
                           "completion_tokens": resp.usage.completion_tokens,
                           "total_tokens": resp.usage.total_tokens} if resp.usage else None,
            )
        except Exception as e:
            elapsed = time.time() - start_time
            error_str = str(e).lower()
            
            error_type = "unknown"
            if "429" in error_str or "rate limit" in error_str:
                error_type = "rate_limit"
            elif "quota" in error_str:
                error_type = "quota_exceeded"
            elif "401" in error_str or "403" in error_str or "api key" in error_str:
                error_type = "auth_error"
            elif "model" in error_str and ("not found" in error_str or "404" in error_str):
                error_type = "model_unavailable"
            elif "timeout" in error_str:
                error_type = "timeout"
            
            return ModelTestResult(
                provider="openai",
                model=model,
                status="failed",
                response_time=elapsed,
                error_message=str(e),
                error_type=error_type,
            )
    
    def run_all_tests(self) -> TestReport:
        """Run tests for all configured models."""
        logger.info("[ModelTester] Starting AI model tests...")
        
        for provider_name, config in MODEL_CONFIGS.items():
            api_key = os.getenv(config["api_key_env"], "")
            if not api_key:
                logger.info(f"[ModelTester] Skipping {provider_name} - no API key configured")
                for model in config["models"]:
                    self.results.append(ModelTestResult(
                        provider=provider_name,
                        model=model,
                        status="skipped",
                        error_message="No API key configured",
                        error_type="no_api_key",
                    ))
                continue
            
            for model in config["models"]:
                logger.info(f"[ModelTester] Testing {provider_name}/{model}...")
                result = self.test_model(provider_name, model, api_key)
                self.results.append(result)
                logger.info(f"[ModelTester] {provider_name}/{model}: {result.status} ({result.response_time:.1f}s)" if result.response_time else f"[ModelTester] {provider_name}/{model}: {result.status}")
        
        return self._generate_report()
    
    def _generate_report(self) -> TestReport:
        """Generate the test report with recommendations."""
        working = [r for r in self.results if r.status == "working"]
        partial = [r for r in self.results if r.status == "partial"]
        failed = [r for r in self.results if r.status == "failed"]
        skipped = [r for r in self.results if r.status == "skipped"]
        
        # Recommendation logic: prefer working models, then by response time
        candidates = working + partial
        recommended = None
        
        if candidates:
            # Sort by status (working first), then response time
            candidates.sort(key=lambda r: (0 if r.status == "working" else 1, r.response_time or 999))
            best = candidates[0]
            recommended = {
                "provider": best.provider,
                "model": best.model,
                "reason": f"Best available model (status: {best.status}, response: {best.response_time:.1f}s)"
            }
        
        summary = {
            "total_tested": len(self.results),
            "working": len(working),
            "partial": len(partial),
            "failed": len(failed),
            "skipped": len(skipped),
            "providers_tested": list(set(r.provider for r in self.results)),
        }
        
        return TestReport(
            timestamp=datetime.utcnow().isoformat(),
            results=self.results,
            summary=summary,
            recommended_model=recommended,
        )
    
    def print_report(self, report: TestReport) -> None:
        """Print a formatted test report."""
        print("\n" + "=" * 60)
        print("MODEL TEST REPORT")
        print("=" * 60)
        print(f"Timestamp: {report.timestamp}")
        print(f"Summary: {report.summary['working']} working, {report.summary['partial']} partial, "
              f"{report.summary['failed']} failed, {report.summary['skipped']} skipped")
        print("-" * 60)
        
        for result in report.results:
            status_icon = "[OK]" if result.status == "working" else "[~]" if result.status == "partial" else "[FAIL]" if result.status == "failed" else "[SKIP]"
            print(f"{status_icon} {result.provider} / {result.model}")
            print(f"   Status: {result.status}")
            if result.response_time:
                print(f"   Response time: {result.response_time:.1f}s")
            if result.error_message:
                print(f"   Error: {result.error_message}")
            if result.error_type:
                print(f"   Error type: {result.error_type}")
            if result.token_usage:
                print(f"   Tokens: {result.token_usage}")
            if result.response_preview:
                print(f"   Preview: {result.response_preview}")
            print()
        
        if report.recommended_model:
            print("-" * 60)
            print(f"RECOMMENDED: {report.recommended_model['provider']} / {report.recommended_model['model']}")
            print(f"Reason: {report.recommended_model['reason']}")
        print("=" * 60)


# ---------------------------------------------------------------------------
# Convenience Function
# ---------------------------------------------------------------------------

def run_model_tests() -> TestReport:
    """Run all model tests and return the report."""
    tester = AIModelTester()
    return tester.run_all_tests()


def save_report(report: TestReport, filepath: str = "model_test_report.json") -> None:
    """Save test report to JSON file."""
    # Convert dataclasses to dict
    data = {
        "timestamp": report.timestamp,
        "summary": report.summary,
        "recommended_model": report.recommended_model,
        "results": [asdict(r) for r in report.results],
    }
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"[ModelTester] Report saved to {filepath}")


if __name__ == "__main__":
    # Configure logging
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    
    # Load .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run tests
    report = run_model_tests()
    
    # Print and save
    AIModelTester().print_report(report)
    save_report(report)