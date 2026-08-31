"""
Nexus Flow — AI Planning Agent (Multi-Step)
Analyzes user prompt and creates a detailed project architecture plan.
"""
import json
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Step 1: Website Architecture Plan
# ---------------------------------------------------------------------------

PLANNING_SYSTEM_PROMPT = """You are an expert senior full-stack developer and website architect.

Given a user's description, create a COMPLETE and DETAILED project plan.

RULES:
- If it needs auth, dashboards, user accounts, carts, or state → "react"
- If it's a simple landing page or portfolio → "static"
- When in doubt, use "react"
- Always include a Home page
- Be VERY specific about what each page contains and how components work

Output ONLY valid JSON matching this schema:
{
  "project_name": "kebab-case-name",
  "project_type": "react" | "static",
  "description": "One sentence description",
  "pages": [
    {
      "name": "Home",
      "route": "/",
      "description": "Full description of what this page shows",
      "sections": ["hero", "features_grid", "testimonials", "cta"],
      "components_used": ["Navbar", "Hero", "Card", "Footer"]
    }
  ],
  "components": [
    {
      "name": "Navbar",
      "description": "Responsive navigation bar with logo, links, mobile hamburger menu",
      "props": ["links", "activeRoute"],
      "has_state": false
    }
  ],
  "features": ["dark_mode", "responsive", "authentication", "search"],
  "data_model": [
    {"name": "User", "fields": ["id", "name", "email", "avatar"]}
  ],
  "design": {
    "style": "modern" | "minimal" | "bold" | "elegant",
    "color_scheme": {
      "primary": "#hex",
      "secondary": "#hex",
      "background": "#hex",
      "surface": "#hex",
      "text": "#hex",
      "text_muted": "#hex",
      "accent": "#hex",
      "success": "#hex",
      "error": "#hex"
    },
    "fonts": {
      "heading": "Font Name",
      "body": "Font Name"
    }
  },
  "navigation": {
    "type": "navbar" | "sidebar" | "tabs",
    "links": [{"label": "Home", "route": "/", "icon": "fa-home"}]
  },
  "dependencies": ["react-router-dom", "recharts"]
}

Do NOT include markdown fences. Output ONLY the JSON object."""


def plan_website(prompt, project_name=None, generation_id=None):
    """
    Analyze a user prompt and return a detailed project architecture plan.
    Supports cancellation via generation_id.
    """
    # Early cancel check
    if generation_id:
        try:
            from services.generation_control import check_cancel
            check_cancel(generation_id, "Plan architecture")
        except Exception:
            raise
    from services.llm_service import call_llm_json

    user_msg = f"Create a website: {prompt}"
    if project_name:
        user_msg += f"\nProject name: {project_name}"

    logger.info(f"[Planner] Planning website: {prompt[:80]}...")

    plan = call_llm_json(
        user_msg,
        system_instruction=PLANNING_SYSTEM_PROMPT,
        temperature=0.3,
    )

    # Validate required fields
    required = ["project_name", "project_type", "pages", "components"]
    for field in required:
        if field not in plan:
            raise ValueError(f"Plan missing required field: {field}")

    # Ensure project_type is valid
    if plan["project_type"] not in ("react", "static"):
        plan["project_type"] = "react"

    # Ensure at least one page
    if not plan.get("pages"):
        plan["pages"] = [{"name": "Home", "route": "/", "description": "Landing page", "sections": ["hero"]}]
    # Ensure each page has required fields
    for page in plan["pages"]:
        if "name" not in page:
            page["name"] = "Page"
        if "route" not in page:
            page["route"] = "/" + page["name"].lower()
        if "description" not in page:
            page["description"] = page["name"]
        if "sections" not in page:
            page["sections"] = ["content"]

    # Ensure components list
    if not plan.get("components"):
        plan["components"] = []
    for comp in plan["components"]:
        if "name" not in comp:
            continue
        if "description" not in comp:
            comp["description"] = comp["name"]

    # Ensure design has color scheme
    if "design" not in plan:
        plan["design"] = {}
    if "color_scheme" not in plan["design"]:
        plan["design"]["color_scheme"] = {
            "primary": "#6366f1",
            "secondary": "#8b5cf6",
            "background": "#0f172a",
            "surface": "#1e293b",
            "text": "#f8fafc",
            "text_muted": "#94a3b8",
            "accent": "#06b6d4",
            "success": "#10b981",
            "error": "#ef4444",
        }

    if project_name:
        plan["project_name"] = project_name

    logger.info(f"[Planner] Plan created: {len(plan['pages'])} pages, {len(plan['components'])} components, type={plan['project_type']}")
    return plan
