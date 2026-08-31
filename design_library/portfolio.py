"""Nexus Flow AI - Design Pattern Library: Portfolio Patterns

Contains design architecture patterns for:
1. Creative Portfolio
2. Minimal Portfolio
3. Agency Portfolio
"""

from typing import Dict, Any

PORTFOLIO_PATTERNS: Dict[str, Dict[str, Any]] = {
    "creative": {
        "id": "portfolio_creative",
        "name": "Creative Designer & Developer Portfolio",
        "category": "portfolio",
        "description": "Expressive, bold personal brand showcase featuring dynamic project cards, interactive skills matrix, and fluid micro-animations.",
        "layout": {
            "type": "creative_grid",
            "max_width": "1200px",
        },
        "sections": [
            {"name": "Creative Navbar", "type": "navbar", "components": ["Name / Monogram Logo", "Availability Status Dot (🟢 Available for Q3 Projects)", "Nav links (Work, About, Skills, Contact)", "Resume PDF Button"]},
            {"name": "Hero Statement", "type": "hero", "components": ["Greeting / Role Pill (e.g. Senior Product Designer & AI Engineer)", "High-impact kinetic Headline ('Crafting digital experiences that push boundaries.')", "Short manifesto bio", "Quick Contact CTA + Social Links (GitHub, X, LinkedIn, Dribbble)"]},
            {"name": "Featured Projects Showcase", "type": "projects_grid", "components": ["Featured Case Study Cards with project tags, live preview link, GitHub repo link, interactive hover preview, and impact metrics (e.g. +240% Growth)"]},
            {"name": "Skills & Tech Stack Matrix", "type": "skills_matrix", "components": ["Categorized skill badges (Frontend, Backend, AI/ML, Design Systems, Cloud)", "Proficiency levels with animated gradient bars"]},
            {"name": "Experience & Career Timeline", "type": "timeline", "components": ["Interactive milestone timeline with role, company, duration, and key contributions"]},
            {"name": "Client Testimonials & Recommendations", "type": "recommendations", "components": ["Recommendations carousel with avatars and LinkedIn verification"]},
            {"name": "Get in Touch / Contact Drawer", "type": "contact_section", "components": ["Interactive contact form (Name, Email, Budget, Message)", "Direct email copy button with instant feedback toast", "Timezone and calendar booking link"]},
            {"name": "Minimal Creative Footer", "type": "footer", "components": ["Handcrafted with passion statement", "Social links", "Copyright 2026"]},
        ],
        "design_hints": {
            "aesthetic": "Dark canvas with vibrant neon gradients (Rose, Cyan, Indigo) on hover",
            "hover": "3D tilt or slight translateY(-6px) with glowing border highlight",
        }
    },
    "minimal": {
        "id": "portfolio_minimal",
        "name": "Minimalist Monochromatic Portfolio",
        "category": "portfolio",
        "description": "Ultra-clean, distraction-free portfolio focused on crisp typography, generous whitespace, and refined project storytelling.",
        "layout": {
            "type": "clean_editorial",
            "max_width": "980px",
        },
        "sections": [
            {"name": "Minimal Header", "type": "navbar", "components": ["Personal Name", "Index / Archive toggle", "Direct Email Link"]},
            {"name": "Personal Bio & Philosophy", "type": "hero", "components": ["Large editorial headline", "2-paragraph bio on craft, design principles, and background"]},
            {"name": "Curated Selected Works", "type": "projects_list", "components": ["Clean table or list-style project directory with year, client, role, and expandable case study preview"]},
            {"name": "Writing & Essays", "type": "articles", "components": ["Article links with publication dates and reading times"]},
            {"name": "Contact & Colophon", "type": "footer", "components": ["Simple contact paragraph", "Typography and tech credits", "Year"]},
        ],
        "design_hints": {
            "palette": "Black, white, and subtle slate gray borders",
            "typography": "Refined sans-serif (Inter) with generous line-height and calm pacing",
        }
    },
    "agency": {
        "id": "portfolio_agency",
        "name": "Creative Agency & Studio Showcase",
        "category": "portfolio",
        "description": "High-prestige agency website showcasing client case studies, capabilities, leadership team, and project inquiry system.",
        "layout": {
            "type": "agency_storytelling",
            "max_width": "1280px",
        },
        "sections": [
            {"name": "Agency Header", "type": "navbar", "components": ["Studio Mark", "Navigation (Work, Services, About, Insights)", "Let's Talk CTA button"]},
            {"name": "Manifesto Hero", "type": "hero", "components": ["Studio Tagline ('We build brands and digital platforms that define industries.')", "Full-width showreel video / mockup background", "Client logo marquee (Google, Spotify, Stripe, Nike)"]},
            {"name": "Selected Case Studies", "type": "case_studies", "components": ["Full-width case study cards with client sector, deliverables tag, problem-solution summary, and View Case Study CTA"]},
            {"name": "Core Capabilities & Services", "type": "services_grid", "components": ["4x Service Cards (Brand Strategy, Digital Product, AI Engineering, Growth & Marketing) with deliverables lists"]},
            {"name": "Studio Numbers & Impact", "type": "stats_banner", "components": ["4x Large Stat counters (e.g. $500M+ Raised by Clients, 48 Global Awards, 120+ Products Launched)"]},
            {"name": "Leadership & Team", "type": "team", "components": ["Partner / Team cards with photos, roles, and short bios"]},
            {"name": "Project Inquiry / Booking", "type": "inquiry_form", "components": ["Step-by-step project scope builder and contact form"]},
            {"name": "Agency Footer", "type": "footer", "components": ["Office locations (San Francisco, London, Tokyo)", "Social channels", "Legal & copyright"]},
        ],
        "design_hints": {
            "aesthetic": "Deep midnight background with sophisticated purple/magenta gradients and bold display typography",
            "animation": "Smooth section entry transitions and card hover scaling",
        }
    }
}
