"""Nexus Flow AI - Design Pattern Library Package

Contains curated UI/UX architecture patterns for:
- SaaS (Modern Dashboard, Startup Landing Page, Product Showcase)
- E-commerce (Product Listing, Product Detail, Checkout)
- Portfolio (Creative, Minimal, Agency)
- Dashboard (Analytics, Admin Panel)
- Automatic Pattern Selector
"""

from design_library.saas import SAAS_PATTERNS
from design_library.ecommerce import ECOMMERCE_PATTERNS
from design_library.portfolio import PORTFOLIO_PATTERNS
from design_library.dashboard import DASHBOARD_PATTERNS
from design_library.selector import PatternSelector, ALL_PATTERNS

__all__ = [
    "SAAS_PATTERNS",
    "ECOMMERCE_PATTERNS",
    "PORTFOLIO_PATTERNS",
    "DASHBOARD_PATTERNS",
    "PatternSelector",
    "ALL_PATTERNS",
]
