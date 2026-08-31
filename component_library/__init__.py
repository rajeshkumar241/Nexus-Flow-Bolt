"""ComponentLibrary — reusable UI component templates.

Provides pre-built component templates that the DesignerAgent and CoderAgent
can select, customize, and assemble into complete websites.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Component Registry ───────────────────────────────────────────────

COMPONENT_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_component(category: str, name: str, component: Dict[str, Any]) -> None:
    """Register a component in the library."""
    if category not in COMPONENT_REGISTRY:
        COMPONENT_REGISTRY[category] = {}
    COMPONENT_REGISTRY[category][name] = component


def get_component(category: str, name: str) -> Optional[Dict[str, Any]]:
    """Get a component by category and name."""
    return COMPONENT_REGISTRY.get(category, {}).get(name)


def list_components(category: Optional[str] = None) -> Dict[str, List[str]]:
    """List available components, optionally filtered by category."""
    if category:
        comps = COMPONENT_REGISTRY.get(category, {})
        return {category: list(comps.keys())}
    return {cat: list(comps.keys()) for cat, comps in COMPONENT_REGISTRY.items()}


def select_components_for_prompt(prompt: str, page_type: str = "landing") -> List[Dict]:
    """Select suitable components based on a user prompt and page type."""
    prompt_lower = prompt.lower()
    selected = []

    # Always include navbar and footer
    for cat in ("navbar", "footer"):
        comps = COMPONENT_REGISTRY.get(cat, {})
        if comps:
            first_name = next(iter(comps))
            selected.append({"category": cat, "name": first_name, **comps[first_name]})

    # Hero section
    if any(w in prompt_lower for w in ("landing", "home", "saas", "startup", "modern")):
        comps = COMPONENT_REGISTRY.get("hero", {})
        for name, comp in comps.items():
            if "gradient" in name or "modern" in name:
                selected.append({"category": "hero", "name": name, **comp})
                break
        else:
            if comps:
                first_name = next(iter(comps))
                selected.append({"category": "hero", "name": first_name, **comps[first_name]})

    # Features/cards
    if any(w in prompt_lower for w in ("feature", "service", "benefit", "saas", "product")):
        comps = COMPONENT_REGISTRY.get("cards", {})
        for name, comp in comps.items():
            if "feature" in name:
                selected.append({"category": "cards", "name": name, **comp})
                break
        else:
            if comps:
                first_name = next(iter(comps))
                selected.append({"category": "cards", "name": first_name, **comps[first_name]})

    # Pricing
    if any(w in prompt_lower for w in ("pricing", "plan", "subscription", "saas")):
        comps = COMPONENT_REGISTRY.get("pricing", {})
        if comps:
            first_name = next(iter(comps))
            selected.append({"category": "pricing", "name": first_name, **comps[first_name]})

    # Forms
    if any(w in prompt_lower for w in ("contact", "form", "signup", "login", "register")):
        comps = COMPONENT_REGISTRY.get("forms", {})
        if comps:
            first_name = next(iter(comps))
            selected.append({"category": "forms", "name": first_name, **comps[first_name]})

    # Dashboard
    if any(w in prompt_lower for w in ("dashboard", "admin", "analytics", "panel")):
        comps = COMPONENT_REGISTRY.get("dashboard", {})
        for name, comp in comps.items():
            selected.append({"category": "dashboard", "name": name, **comp})

    return selected


# ── Initialize with default components ───────────────────────────────

def _init_defaults():
    """Register default component templates."""
    # Navbar
    register_component("navbar", "sticky_glass", {
        "description": "Sticky navbar with glassmorphism blur effect",
        "html": '<nav class="navbar"><div class="container"><a href="/" class="logo">{logo}</a><div class="nav-links">{links}</div><a href="#cta" class="btn btn-primary">{cta_text}</a></div></nav>',
        "css": ".navbar{position:sticky;top:0;z-index:100;background:rgba(15,23,42,0.8);backdrop-filter:blur(12px);border-bottom:1px solid rgba(255,255,255,0.1);padding:16px 0}.navbar .container{max-width:1240px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;padding:0 24px}",
        "variants": ["dark", "light", "transparent"],
    })

    register_component("navbar", "centered_links", {
        "description": "Navbar with centered navigation links",
        "html": '<nav class="navbar"><div class="container"><a href="/" class="logo">{logo}</a><div class="nav-center">{links}</div><div class="nav-actions">{cta}</div></div></nav>',
        "css": ".nav-center{display:flex;gap:32px}.nav-center a{color:#94A3B8;text-decoration:none;font-size:14px;transition:color 0.2s}.nav-center a:hover{color:#F1F5F9}",
    })

    # Hero
    register_component("hero", "gradient_modern", {
        "description": "Modern hero with gradient background and centered text",
        "html": '<section class="hero"><div class="container"><h1>{heading}</h1><p class="hero-subtitle">{subtitle}</p><div class="hero-cta">{buttons}</div></div></section>',
        "css": ".hero{padding:120px 0 80px;text-align:center;background:linear-gradient(135deg,#0F172A 0%,#1E293B 50%,#0F172A 100%)}.hero h1{font-size:clamp(2rem,5vw,3.5rem);font-weight:800;background:linear-gradient(135deg,#6C63FF,#818CF8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:24px}.hero-subtitle{font-size:1.25rem;color:#94A3B8;max-width:600px;margin:0 auto 40px}",
        "variants": ["gradient", "split", "video_bg", "minimal"],
    })

    register_component("hero", "split_screen", {
        "description": "Hero with text on left, image/illustration on right",
        "html": '<section class="hero-split"><div class="container"><div class="hero-content"><h1>{heading}</h1><p>{subtitle}</p><div class="hero-cta">{buttons}</div></div><div class="hero-visual">{image}</div></div></section>',
        "css": ".hero-split .container{display:grid;grid-template-columns:1fr 1fr;gap:60px;align-items:center}.hero-content h1{font-size:3rem;font-weight:800;line-height:1.1}",
    })

    # Cards
    register_component("cards", "feature_grid", {
        "description": "3-column feature card grid with icons",
        "html": '<section class="features"><div class="container"><h2>{heading}</h2><div class="feature-grid">{cards}</div></div></section>',
        "css": ".feature-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:24px}.feature-card{padding:32px;border-radius:16px;background:rgba(30,41,59,0.5);border:1px solid rgba(255,255,255,0.05);transition:transform 0.2s,box-shadow 0.2s}.feature-card:hover{transform:translateY(-4px);box-shadow:0 20px 40px rgba(0,0,0,0.2)}",
        "variants": ["grid", "bento", "list", "masonry"],
    })

    register_component("cards", "bento_grid", {
        "description": "Bento-style asymmetric grid layout",
        "html": '<section class="bento"><div class="container"><div class="bento-grid">{cards}</div></div></section>',
        "css": ".bento-grid{display:grid;grid-template-columns:repeat(4,1fr);grid-auto-rows:200px;gap:16px}.bento-item{border-radius:16px;padding:24px;background:rgba(30,41,59,0.5);border:1px solid rgba(255,255,255,0.05)}.bento-item.span-2{grid-column:span 2}.bento-item.span-row{grid-row:span 2}",
    })

    # Pricing
    register_component("pricing", "three_tier", {
        "description": "Three-tier pricing with highlighted middle plan",
        "html": '<section class="pricing"><div class="container"><h2>{heading}</h2><div class="pricing-grid">{tiers}</div></div></section>',
        "css": ".pricing-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px;align-items:start}.pricing-card{padding:32px;border-radius:16px;background:#1E293B;border:1px solid #334155;text-align:center}.pricing-card.featured{border-color:#6C63FF;transform:scale(1.05);position:relative;z-index:1}",
        "variants": ["three_tier", "toggle", "comparison"],
    })

    # Forms
    register_component("forms", "contact", {
        "description": "Contact form with name, email, message",
        "html": '<section class="contact"><div class="container"><h2>{heading}</h2><form class="contact-form">{fields}<button type="submit" class="btn btn-primary">{submit_text}</button></form></div></section>',
        "css": ".contact-form{display:flex;flex-direction:column;gap:16px;max-width:500px;margin:0 auto}.contact-form input,.contact-form textarea{padding:12px 16px;border-radius:8px;border:1px solid #334155;background:#0F172A;color:#F1F5F9;font-size:16px}.contact-form input:focus,.contact-form textarea:focus{outline:none;border-color:#6C63FF;box-shadow:0 0 0 3px rgba(108,99,255,0.2)}",
    })

    register_component("forms", "login", {
        "description": "Login form with email and password",
        "html": '<div class="auth-form"><h2>{heading}</h2><form>{fields}<button type="submit" class="btn btn-primary">{submit_text}</button></form><p class="auth-link">{link_text}</p></div>',
        "css": ".auth-form{max-width:400px;margin:80px auto;padding:40px;border-radius:16px;background:#1E293B;border:1px solid #334155}",
    })

    # Dashboard
    register_component("dashboard", "stat_cards", {
        "description": "Dashboard stat cards with icons and trends",
        "html": '<div class="stat-grid">{cards}</div>',
        "css": ".stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}.stat-card{padding:24px;border-radius:12px;background:#1E293B;border:1px solid #334155}.stat-card .stat-value{font-size:2rem;font-weight:700;color:#F1F5F9}.stat-card .stat-label{color:#94A3B8;font-size:14px;margin-top:4px}.stat-card .stat-trend{font-size:12px;margin-top:8px}.stat-trend.up{color:#22C55E}.stat-trend.down{color:#EF4444}",
    })

    register_component("dashboard", "sidebar", {
        "description": "Collapsible sidebar navigation",
        "html": '<aside class="sidebar"><div class="sidebar-header">{logo}</div><nav class="sidebar-nav">{links}</nav><div class="sidebar-footer">{user}</div></aside>',
        "css": ".sidebar{width:256px;height:100vh;position:fixed;left:0;top:0;background:#111827;border-right:1px solid #1F2937;display:flex;flex-direction:column;padding:16px}.sidebar-nav{flex:1;display:flex;flex-direction:column;gap:4px}.sidebar-nav a{display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:8px;color:#94A3B8;text-decoration:none;transition:all 0.2s}.sidebar-nav a:hover,.sidebar-nav a.active{background:#1F2937;color:#F1F5F9}",
    })

    # Footer
    register_component("footer", "minimal", {
        "description": "Minimal footer with links and copyright",
        "html": '<footer class="footer"><div class="container"><div class="footer-content"><div class="footer-brand">{logo}<p>{tagline}</p></div><div class="footer-links">{links}</div></div><div class="footer-bottom"><p>{copyright}</p></div></div></footer>',
        "css": ".footer{padding:60px 0 24px;background:#0F172A;border-top:1px solid #1E293B}.footer-content{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:40px;margin-bottom:40px}.footer-brand p{color:#64748B;font-size:14px;margin-top:12px}.footer-links a{display:block;color:#94A3B8;text-decoration:none;font-size:14px;padding:4px 0;transition:color 0.2s}.footer-links a:hover{color:#F1F5F9}.footer-bottom{border-top:1px solid #1E293B;padding-top:24px;text-align:center;color:#64748B;font-size:13px}",
    })

    register_component("footer", "multi_column", {
        "description": "Multi-column footer with newsletter signup",
        "html": '<footer class="footer"><div class="container"><div class="footer-grid">{columns}</div><div class="footer-bottom">{bottom}</div></div></footer>',
        "css": ".footer-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:32px;padding-bottom:40px;border-bottom:1px solid #1E293B}",
    })


# Auto-initialize on import
_init_defaults()
