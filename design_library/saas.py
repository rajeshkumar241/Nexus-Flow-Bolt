"""Nexus Flow AI - Design Pattern Library: SaaS Patterns

Contains design architecture patterns for:
1. Modern Dashboard
2. Startup Landing Page
3. Product Showcase
"""

from typing import Dict, Any

SAAS_PATTERNS: Dict[str, Dict[str, Any]] = {
    "modern_dashboard": {
        "id": "saas_modern_dashboard",
        "name": "Modern SaaS Dashboard",
        "category": "saas",
        "description": "Clean, high-information-density SaaS application layout with interactive telemetry widgets, charts, and metrics.",
        "layout": {
            "type": "sidebar_and_main",
            "sidebar_width": "260px",
            "topbar_height": "64px",
            "main_grid": "grid-template-columns: repeat(12, 1fr); gap: 1.5rem;",
        },
        "sections": [
            {"name": "Sidebar Navigation", "type": "sidebar", "components": ["App Logo", "Nav List with icons & badge counts", "Storage meter", "User profile avatar & menu"]},
            {"name": "Metric KPI Bar", "type": "metrics", "components": ["4x Stat Cards with sparklines, percentages, and trend indicators"]},
            {"name": "Main Chart Widget", "type": "chart", "components": ["Timeframe tabs (7D, 30D, 1Y)", "Revenue/Usage chart viewport", "Summary callout pill"]},
            {"name": "Activity & Transactions Feed", "type": "table_feed", "components": ["Search and filter bar", "Live status table with avatars, timestamps, badges, and action menus"]},
            {"name": "Quick Action Drawer / Modal", "type": "actions", "components": ["Create project button", "Invite member", "Export CSV"]},
        ],
        "design_hints": {
            "card_style": "glassmorphic surface with subtle 1px border",
            "accent_usage": "metrics delta indicators (green/red) and primary action glows",
            "spacing": "tight to compact component padding (1.25rem - 1.5rem)",
        }
    },
    "startup_landing_page": {
        "id": "saas_startup_landing",
        "name": "Startup Landing Page",
        "category": "saas",
        "description": "High-converting modern tech startup landing page featuring social proof, gradient headlines, interactive bento grid, and pricing cards.",
        "layout": {
            "type": "single_page_flow",
            "max_width": "1240px",
            "section_spacing": "6.5rem 0",
        },
        "sections": [
            {"name": "Sticky Navbar", "type": "navbar", "components": ["Logo with glow mark", "Links (Features, Pricing, Wall of Love, Docs)", "Sign In + Start Free Trial CTA"]},
            {"name": "Hero Section", "type": "hero", "components": ["Announcement Pill Badge", "Bold Headline with glowing gradient text", "Compelling subhead", "Dual CTAs (Primary + Watch Demo)", "Product UI Mockup with floating stat badges", "Trust Marquee with Fortune 500 / YC logos"]},
            {"name": "Bento Feature Grid", "type": "bento_features", "components": ["Hero Bento Card (large visual preview)", "2x Medium Capability Cards", "2x Small Integration Cards with animated icons"]},
            {"name": "Interactive Feature Tabs", "type": "tabs_deep_dive", "components": ["Tab switcher (Automate, Analyze, Scale)", "Split view with code/interactive playground and explanation checklist"]},
            {"name": "Tiered Pricing", "type": "pricing", "components": ["Monthly/Annual Toggle with -20% Pill", "3x Tier Cards (Free, Pro [Popular Badge], Enterprise)", "Feature checklist & CTA per tier"]},
            {"name": "Testimonials & Social Proof", "type": "testimonials", "components": ["Customer quote cards with author avatars, roles, and verified badges", "Key outcome metrics (e.g. 10x Faster Deployment)"]},
            {"name": "Pre-Footer Conversion CTA", "type": "cta_banner", "components": ["Full-width radiant banner", "Instant signup input or big CTA button", "No credit card required guarantee"]},
            {"name": "Footer", "type": "footer", "components": ["4-column directory", "Newsletter subscription", "Copyright and system status dot"]},
        ],
        "design_hints": {
            "hero_style": "radial-gradient glow background centered behind headline",
            "cards": "glass cards with subtle border glow on hover",
            "typography": "Plus Jakarta Sans for punchy tech authority",
        }
    },
    "product_showcase": {
        "id": "saas_product_showcase",
        "name": "Product Showcase & Demo",
        "category": "saas",
        "description": "Visual-first product walkthrough highlighting architecture, workflow demonstrations, interactive sandboxes, and tech specifications.",
        "layout": {
            "type": "split_storytelling",
            "max_width": "1240px",
        },
        "sections": [
            {"name": "Navbar", "type": "navbar", "components": ["Product logo", "Feature selector", "Live Sandbox Link", "Get Started CTA"]},
            {"name": "Product Hero", "type": "hero", "components": ["Product Category Badge", "Value-prop Headline", "Interactive 3D/CSS Device Frame with Live App Simulation"]},
            {"name": "Workflow Sequence", "type": "step_flow", "components": ["3-step visual pipeline (1. Connect, 2. Train AI, 3. Deploy Anywhere) with animated connector lines"]},
            {"name": "Interactive Sandbox Mockup", "type": "sandbox", "components": ["Live input playground", "Real-time output preview pane", "Copy code / Share result"]},
            {"name": "Integration Ecosystem", "type": "integrations_grid", "components": ["Interactive logo grid (GitHub, AWS, Slack, Stripe, Vercel)", "1-click connect cards"]},
            {"name": "Technical FAQ Accordion", "type": "faq", "components": ["Categorized collapsible FAQ items with rich formatting"]},
            {"name": "Footer", "type": "footer", "components": ["Product documentation links", "API reference link", "Community Discord / GitHub links"]},
        ],
        "design_hints": {
            "emphasis": "Interactive UI elements and real-time visual feedback",
            "theme": "Dark mode with luminous accents for developer-focused product clarity",
        }
    }
}
