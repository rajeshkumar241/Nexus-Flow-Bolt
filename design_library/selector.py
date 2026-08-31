"""Nexus Flow AI - Design Pattern Library: Automatic Selector

Analyzes prompts and website requirements to automatically select
and recommend the optimal design pattern from the library.
"""

from typing import Dict, Any, List, Optional
import re

from design_library.saas import SAAS_PATTERNS
from design_library.ecommerce import ECOMMERCE_PATTERNS
from design_library.portfolio import PORTFOLIO_PATTERNS
from design_library.dashboard import DASHBOARD_PATTERNS

ALL_PATTERNS: Dict[str, Dict[str, Any]] = {}
ALL_PATTERNS.update({f"saas:{k}": v for k, v in SAAS_PATTERNS.items()})
ALL_PATTERNS.update({f"ecommerce:{k}": v for k, v in ECOMMERCE_PATTERNS.items()})
ALL_PATTERNS.update({f"portfolio:{k}": v for k, v in PORTFOLIO_PATTERNS.items()})
ALL_PATTERNS.update({f"dashboard:{k}": v for k, v in DASHBOARD_PATTERNS.items()})


class PatternSelector:
    """Automatically selects the best design pattern for a prompt or requirement."""

    @classmethod
    def select_pattern(
        cls,
        prompt: str = "",
        category: str = "saas",
        industry: str = "saas"
    ) -> Dict[str, Any]:
        """Select the most suitable design pattern."""
        p_lower = (prompt or "").lower()
        cat_lower = (category or "").lower()
        ind_lower = (industry or "").lower()
        context = f"{p_lower} {cat_lower} {ind_lower}"

        # 1. Check for E-commerce triggers
        if any(w in context for w in ["checkout", "cart", "pay", "order", "buy", "purchase"]):
            if "checkout" in context or "payment" in context:
                return ECOMMERCE_PATTERNS["checkout"]
            elif "detail" in context or "single product" in context:
                return ECOMMERCE_PATTERNS["product_detail"]
            return ECOMMERCE_PATTERNS["product_listing"]
        if any(w in context for w in ["ecommerce", "e-commerce", "shop", "store", "product listing", "catalog"]):
            return ECOMMERCE_PATTERNS["product_listing"]

        # 2. Check for Dashboard triggers
        if any(w in context for w in ["admin", "admin panel", "user management", "permissions", "rbac"]):
            return DASHBOARD_PATTERNS["admin_panel"]
        if any(w in context for w in ["analytics", "metrics", "telemetry", "kpi", "chart", "graph", "dashboard"]):
            return DASHBOARD_PATTERNS["analytics"]

        # 3. Check for Portfolio triggers
        if any(w in context for w in ["portfolio", "resume", "cv", "personal site", "developer portfolio", "designer"]):
            if "minimal" in context or "clean" in context or "monochrome" in context:
                return PORTFOLIO_PATTERNS["minimal"]
            elif "agency" in context or "studio" in context:
                return PORTFOLIO_PATTERNS["agency"]
            return PORTFOLIO_PATTERNS["creative"]
        if "agency" in context or "studio" in context:
            return PORTFOLIO_PATTERNS["agency"]

        # 4. Check for SaaS triggers
        if "showcase" in context or "demo" in context or "product tour" in context:
            return SAAS_PATTERNS["product_showcase"]
        if "dashboard" in context:
            return SAAS_PATTERNS["modern_dashboard"]

        # Default SaaS landing page
        return SAAS_PATTERNS["startup_landing_page"]

    @classmethod
    def get_pattern(cls, category: str, pattern_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific pattern by category and name."""
        key = f"{category.lower()}:{pattern_name.lower()}"
        return ALL_PATTERNS.get(key)

    @classmethod
    def list_all_patterns(cls) -> List[Dict[str, Any]]:
        """Return list of all registered design patterns."""
        return list(ALL_PATTERNS.values())
