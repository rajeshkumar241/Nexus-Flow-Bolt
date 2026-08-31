"""
Nexus Flow — AI Code Generator (Multi-Step)
Generates complete production-ready React+Vite projects.
Multi-step pipeline: scaffolding → App → pages → components.
"""
import os
import json
import logging
from services.filename_sanitizer import sanitize_filepath

logger = logging.getLogger(__name__)


def _sanitize_file_keys(files):
    """Sanitize all keys in a files dict."""
    sanitized = {}
    for path, content in files.items():
        safe = sanitize_filepath(path)
        if safe != path:
            logger.info(f"[CodeGen] Sanitized: '{path}' -> '{safe}'")
        sanitized[safe] = content
    return sanitized


# ---------------------------------------------------------------------------
# JSX / React code validator (rejects docs like "CartDrawer\\nSlide-over...")
# ---------------------------------------------------------------------------

import re as _re

def is_valid_jsx(content: str, path: str = "") -> bool:
    """True only if content is executable React code, not documentation."""
    if not isinstance(content, str) or not content.strip():
        return False
    text = content.strip()
    if len(text) < 40:
        return False
    # Reject the exact failure: "CartDrawer\\nSlide-over..."
    if "Slide-over quick cart drawer" in text and "<" not in text:
        return False
    if text.startswith("CartDrawer") and "<" not in text and "export" not in text:
        return False
    # Only strict-validate React component/page files
    is_component = path.startswith("src/components/") or path.startswith("src/pages/") or path == "src/App.jsx"
    if is_component:
        has_export = "export default" in text or "export function" in text
        has_jsx_tag = bool(_re.search(r"<[a-zA-Z][a-zA-Z0-9]*(\s|>|/)", text))
        has_return = "return" in text and "(" in text
        if not (has_export and has_jsx_tag and has_return):
            return False
        # At least 30% code lines
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            code_lines = sum(1 for l in lines if any(k in l for k in ["import", "export", "return", "<", ">", "function", "const", "=>", "{", "}"]))
            if code_lines < len(lines) * 0.3:
                return False
        # Reject markdown headers without JSX (e.g., "# CartDrawer")
        if _re.search(r"^#{1,6}\s+\w+", text, _re.M) and "<" not in text[:500]:
            return False
        # Import React is expected but not strictly required for pages that use it implicitly
        # Warn but don't reject if missing import but has export+jsx
    # For other .js/.jsx (vite.config, main.jsx) just ensure not plain docs
    else:
        # Plain prose without code markers -> reject
        if "<" not in text and "import" not in text and "export" not in text and "defineConfig" not in text and "ReactDOM" not in text:
            # Check if it's pure description (no brackets)
            if "{" not in text and "}" not in text:
                return False
    return True


def _filter_valid_files(files: dict) -> dict:
    """Remove files that fail JSX validation (only strict for components/pages/App)."""
    valid = {}
    for path, content in files.items():
        # Only filter React component/page files; vite.config and main.jsx are lenient
        is_strict = path.startswith("src/components/") or path.startswith("src/pages/") or path == "src/App.jsx"
        if is_strict:
            if not is_valid_jsx(content, path):
                logger.warning(f"[CodeGen] REJECTED invalid JSX {path}: {content[:120]!r}")
                continue
        else:
            # Light check for other files: just not empty and not pure docs
            if isinstance(content, str) and "Slide-over quick cart drawer" in content and "<" not in content:
                logger.warning(f"[CodeGen] REJECTED doc {path}")
                continue
        if isinstance(content, str) and content.strip():
            valid[path] = content
    return valid


def _normalize_llm_files(parsed: dict) -> dict:
    """Accept both {"files":{...}} wrapper and flat {"src/...": "..."}."""
    if not isinstance(parsed, dict):
        return {}
    if "files" in parsed and isinstance(parsed["files"], dict):
        # spec shape: {"files": {"package.json": "...", "src/App.jsx": "..."}}
        inner = parsed["files"]
        if isinstance(inner, dict):
            return {str(k): str(v) for k, v in inner.items() if isinstance(v, str) and v.strip()}
    # flat shape
    return {str(k): str(v) for k, v in parsed.items() if isinstance(v, str) and v.strip()}


# ---------------------------------------------------------------------------
# Master system prompt for ALL generation — CODE ONLY, ZERO DOCS
# ---------------------------------------------------------------------------

MASTER_SYSTEM_PROMPT = """You are an expert senior full-stack React developer. You generate ONLY valid executable source code.

ABSOLUTE CODE-ONLY RULES — VIOLATION = FAIL:
- Output must be VALID source code that runs. NEVER output documentation.
- FORBIDDEN: explanations, descriptions, markdown, comments describing UI.
- BAD (REJECTED): "CartDrawer\\nSlide-over quick cart drawer for viewing current items..."
- GOOD (REQUIRED): "export default function CartDrawer(){ return (<nav><h1>Brand</h1></nav>) }"
- Every React file MUST contain: 1) "export default function" OR "export default", 2) "return (" with JSX, 3) at least one JSX tag like <div> <nav> <button> <section>, 4) "import React"
- JSON values MUST be complete file content with code, not summaries.

GENERAL RULES:
1. NEVER generate placeholder code. Every file must be COMPLETE and FUNCTIONAL (50-300 lines).
2. Every component must have real UI — cards, buttons, inputs, layouts, styling.
3. Use ONLY functional components with React hooks.
4. Use ONLY inline styles (no external CSS imports except globals.css / index.css).
5. Use React Router v6 for navigation.
6. Export components as DEFAULT exports.
7. Each file must be self-contained and importable.
8. Use realistic content — real names, real numbers, real text.
9. All styling must use the CSS variables from globals.css.
10. Make everything responsive with media queries in inline styles.

FILENAME RULES (CRITICAL):
- NEVER use colon (:) in filenames. For dynamic routes use [param].jsx
- NEVER use these characters: < > : " | ? *
- Dynamic routes: [id].jsx, [slug].jsx — NOT :id.jsx

OUTPUT FORMAT (STRICT):
Return ONLY a JSON object. Two accepted shapes (prefer "files" wrapper):
{"files":{"package.json":"...","src/App.jsx":"...","src/components/Navbar.jsx":"..."}}
OR flat: {"src/components/Navbar.jsx":"...", "src/pages/Home.jsx":"..."}
Do NOT include markdown fences. Do NOT wrap in "explanation" or "notes". Output ONLY the JSON object."""


def generate_react_project(plan, generation_id=None):
    """
    Generate a complete React+Vite project using multi-step pipeline.
    Supports cancellation via generation_id.

    Steps:
    1. Scaffolding (package.json, vite.config, index.html, main.jsx, globals.css)
    2. App.jsx with routing
    3. Pages (one call per batch)
    4. Components (one call per batch)
    """
    from services.llm_service import call_llm_json, call_llm
    try:
        from services.generation_control import check_cancel
    except Exception:
        def check_cancel(gid, stage=""):  # no-op if not wired
            return

    files = {}
    project_name = plan.get("project_name", "nexus-app")
    color_scheme = plan.get("design", {}).get("color_scheme", {})
    pages = plan.get("pages", [])
    components = plan.get("components", [])
    features = plan.get("features", [])

    # ── Step 1: Scaffolding (built locally, no AI needed) ──────
    logger.info("[CodeGen] Step 1: Building scaffolding...")
    files["package.json"] = _build_package_json(plan)
    files["vite.config.js"] = _build_vite_config()
    files["index.html"] = _build_index_html(plan)
    files["src/main.jsx"] = _build_main_jsx()
    css_content = _build_globals_css(plan)
    files["src/styles/globals.css"] = css_content
    files["src/index.css"] = css_content  # required by spec (alias for builder)

    # ── Step 2: App.jsx with routing (validated + retry) ──────
    check_cancel(generation_id, "Generate code")
    logger.info("[CodeGen] Step 2: Generating App.jsx with routing...")
    app_jsx = _generate_app_jsx(plan)
    if not is_valid_jsx(app_jsx, "src/App.jsx"):
        logger.warning(f"[CodeGen] App.jsx failed JSX validation, retrying...")
        # one automatic retry with stricter prompt
        try:
            app_jsx = _generate_app_jsx(plan)  # second attempt uses same provider fallback
        except Exception:
            pass
        if not is_valid_jsx(app_jsx, "src/App.jsx"):
            logger.error(f"[CodeGen] App.jsx still invalid after retry, using fallback")
            app_jsx = _fallback_app_jsx(plan)
    files["src/App.jsx"] = app_jsx

    # ── Step 3: Generate components (validated) ─────────────
    if components:
        check_cancel(generation_id, "Generate components")
        logger.info(f"[CodeGen] Step 3: Generating {len(components)} components...")
        component_files = _generate_components_batch(plan, components)
        # Validate before merging
        valid_comps = _filter_valid_files(component_files)
        if len(valid_comps) < len(component_files):
            logger.warning(f"[CodeGen] {len(component_files)-len(valid_comps)} component(s) rejected (docs not code), retrying batch...")
            # retry once
            retry = _generate_components_batch(plan, components)
            valid_retry = _filter_valid_files(retry)
            # merge retry valid that were missing
            for k,v in valid_retry.items():
                if k not in valid_comps:
                    valid_comps[k] = v
        files.update(valid_comps)
        # Fill any missing expected components with fallback code
        for comp in components:
            path = f"src/components/{comp.get('name','Component')}.jsx"
            if path not in files or not is_valid_jsx(files.get(path,""), path):
                logger.warning(f"[CodeGen] Using fallback for {path}")
                files[path] = _fallback_component(comp, plan)

    # ── Step 4: Generate pages (validated) ──────────────────
    if pages:
        check_cancel(generation_id, "Generate code")
        logger.info(f"[CodeGen] Step 4: Generating {len(pages)} pages...")
        page_files = _generate_pages_batch(plan, pages)
        valid_pages = _filter_valid_files(page_files)
        if len(valid_pages) < len(page_files):
            logger.warning(f"[CodeGen] {len(page_files)-len(valid_pages)} page(s) rejected, retrying...")
            retry = _generate_pages_batch(plan, pages)
            valid_retry = _filter_valid_files(retry)
            for k,v in valid_retry.items():
                if k not in valid_pages:
                    valid_pages[k] = v
        files.update(valid_pages)
        for page in pages:
            path = f"src/pages/{page.get('name','Page')}.jsx"
            if path not in files or not is_valid_jsx(files.get(path,""), path):
                logger.warning(f"[CodeGen] Using fallback for {path}")
                files[path] = _fallback_page(page, plan)

    # ── Step 5: Ensure required components exist ──────────────
    _ensure_required_components(files, plan)

    # ── Final: Global validation + sanitize ──────────────────
    # Final sweep: reject any remaining invalid JSX before save
    files = _filter_valid_files(files)
    # Re-ensure critical files after filter
    if "src/App.jsx" not in files or not is_valid_jsx(files.get("src/App.jsx",""), "src/App.jsx"):
        files["src/App.jsx"] = _fallback_app_jsx(plan)
    _ensure_required_components(files, plan)

    logger.info(f"[CodeGen] Generated {len(files)} files total")
    return _sanitize_file_keys(files)


# ---------------------------------------------------------------------------
# Step 2: Generate App.jsx
# ---------------------------------------------------------------------------

def _generate_app_jsx(plan):
    """Generate App.jsx with routing."""
    from services.llm_service import call_llm

    pages = plan.get("pages", [])
    color_scheme = plan.get("design", {}).get("color_scheme", {})
    nav_type = plan.get("navigation", {}).get("type", "navbar")
    nav_links = plan.get("navigation", {}).get("links", [])

    page_list = "\n".join([
        f'  {{ name: "{p["name"]}", route: "{p.get("route", "/")}" }}'
        for p in pages
    ])

    prompt = f"""Generate a COMPLETE App.jsx file for a React Router v6 application. OUTPUT MUST BE ONLY VALID JSX CODE.

PROJECT: {plan.get("project_name", "app")}
PAGES:
{page_list}

NAVIGATION TYPE: {nav_type}

The App component must:
1. Import BrowserRouter, Routes, Route from react-router-dom
2. Import ALL page components from ./pages/[PageName]
3. Import a Navbar component from ./components/Navbar
4. Import a Footer component from ./components/Footer
5. Set up routes for EVERY page
6. Render Navbar at the top, page content in Routes, Footer at the bottom
7. Include a dark mode toggle using useState
8. Pass dark mode state to children via context or props
9. Add a wrapper div with className based on dark mode state

COLOR SCHEME: primary={color_scheme.get("primary")}, background={color_scheme.get("background")}

CODE-ONLY ENFORCEMENT:
- Return ONLY executable JSX. Example: export default function App(){{ return (<BrowserRouter><Navbar/></BrowserRouter>) }}
- FORBIDDEN: descriptions like "App component with routing" — REJECTED.
- Must contain: import React, export default function App, return (, <BrowserRouter>, <Routes>

Return ONLY the complete App.jsx file content. No markdown fences. No explanations, no docs."""

    result = call_llm(
        prompt,
        system_instruction=MASTER_SYSTEM_PROMPT,
        temperature=0.3,
        max_tokens=4096,
    )

    # Clean up the result
    result = _clean_code_output(result)
    return result


# ---------------------------------------------------------------------------
# Step 3: Generate components in batches
# ---------------------------------------------------------------------------

def _generate_components_batch(plan, components):
    """Generate all components in a single LLM call."""
    from services.llm_service import call_llm

    color_scheme = plan.get("design", {}).get("color_scheme", {})
    project_name = plan.get("project_name", "app")
    features = plan.get("features", [])

    comp_descriptions = "\n".join([
        f'- {c["name"]}: {c.get("description", "")} (props: {c.get("props", [])}, state: {c.get("has_state", False)})'
        for c in components
    ])

    prompt = f"""Generate ALL these React components as complete, production-ready FILES. CODE ONLY — DOCUMENTATION IS FORBIDDEN.

PROJECT: {project_name}
COLOR SCHEME: primary={color_scheme.get("primary")}, background={color_scheme.get("background")}, surface={color_scheme.get("surface")}, text={color_scheme.get("text")}
FEATURES: {", ".join(features)}

COMPONENTS TO GENERATE:
{comp_descriptions}

REQUIREMENTS FOR EVERY COMPONENT (NON-NEGOTIABLE):
1. Complete React functional component with hooks where needed
2. Must start with: import React from 'react'
3. Must contain: export default function <Name>() {{ return ( <JSX> ) }}
4. Must have at least ONE JSX tag: <div> <nav> <button> <section> <header>
5. ALL styling must be inline style objects using the CSS variable values
6. Must be responsive
7. Must use realistic content — not "Lorem ipsum"
8. Each file 50-200 lines of REAL executable JSX, not stubs
9. FORBIDDEN EXAMPLE (REJECT): "CartDrawer\\nSlide-over quick cart drawer for viewing current items..." -> THIS IS NOT CODE
10. REQUIRED EXAMPLE: export default function Navbar(){{ return (<nav><h1>Brand</h1></nav>) }}

OUTPUT: JSON object where each key is "src/components/[Name].jsx" and each value is COMPLETE EXECUTABLE CODE.
Preferred wrapper: {{"files": {{"src/components/Navbar.jsx":"import React..."}}}}
Do NOT include markdown fences. Output ONLY the JSON object. NO explanations."""

    result = call_llm(
        prompt,
        system_instruction=MASTER_SYSTEM_PROMPT,
        temperature=0.4,
        max_tokens=16384,
    )

    files = {}
    try:
        parsed = _parse_json(result)
        normalized = _normalize_llm_files(parsed)
        # Validate each file is executable JSX, reject docs
        files = _filter_valid_files(normalized)
        if len(files) < len(normalized):
            logger.warning(f"[CodeGen] Components: {len(normalized)-len(files)} file(s) rejected by JSX validator")
        if not files:
            raise ValueError("All component files rejected by validator")
    except Exception as e:
        logger.error(f"[CodeGen] Component generation parse/validation failed: {e}")
        # Generate fallback components
        for comp in components:
            name = comp.get("name", "Component")
            files[f"src/components/{name}.jsx"] = _fallback_component(comp, plan)

    return files


# ---------------------------------------------------------------------------
# Step 4: Generate pages in batches
# ---------------------------------------------------------------------------

def _generate_pages_batch(plan, pages):
    """Generate all pages in a single LLM call."""
    from services.llm_service import call_llm

    color_scheme = plan.get("design", {}).get("color_scheme", {})
    project_name = plan.get("project_name", "app")
    components = plan.get("components", [])
    features = plan.get("features", [])

    page_descriptions = "\n".join([
        f'- {p["name"]} (route: {p.get("route", "/")}) — {p.get("description", "")}\n  Sections: {p.get("sections", [])}\n  Components used: {p.get("components_used", [])}'
        for p in pages
    ])

    comp_names = [c.get("name", "") for c in components]

    prompt = f"""Generate ALL these React page components as complete, production-ready FILES. CODE ONLY — NO DOCUMENTATION.

PROJECT: {project_name}
COLOR SCHEME: primary={color_scheme.get("primary")}, background={color_scheme.get("background")}, surface={color_scheme.get("surface")}, text={color_scheme.get("text")}, text_muted={color_scheme.get("text_muted")}, accent={color_scheme.get("accent")}
AVAILABLE COMPONENTS: {comp_names}
FEATURES: {", ".join(features)}

PAGES TO GENERATE:
{page_descriptions}

REQUIREMENTS FOR EVERY PAGE (STRICT):
1. Complete React functional component: import React from 'react' + export default function <Name>() {{ return (<JSX>) }}
2. Must contain at least one JSX tag: <section> <div> <h1> <button>
3. Must have return ( with JSX, not plain text
4. Import and USE available components where appropriate
5. ALL styling must be inline style objects
6. Must have realistic content, functional UI (buttons, forms with useState)
7. Each page 80-300 lines of REAL executable code
8. FORBIDDEN: page description without code (e.g., "Home page with hero") -> REJECTED
9. REQUIRED: export default function Home(){{ return (<div><h1>...</h1></div>) }}

OUTPUT: JSON where each key is "src/pages/[Name].jsx" and value is COMPLETE EXECUTABLE JSX.
Preferred: {{"files": {{"src/pages/Home.jsx":"import React..."}}}}
Do NOT include markdown fences. Output ONLY JSON. NO docs."""

    result = call_llm(
        prompt,
        system_instruction=MASTER_SYSTEM_PROMPT,
        temperature=0.4,
        max_tokens=16384,
    )

    files = {}
    try:
        parsed = _parse_json(result)
        normalized = _normalize_llm_files(parsed)
        files = _filter_valid_files(normalized)
        if len(files) < len(normalized):
            logger.warning(f"[CodeGen] Pages: {len(normalized)-len(files)} file(s) rejected by JSX validator")
        if not files:
            raise ValueError("All page files rejected by validator")
    except Exception as e:
        logger.error(f"[CodeGen] Page generation parse/validation failed: {e}")
        for page in pages:
            name = page.get("name", "Page")
            files[f"src/pages/{name}.jsx"] = _fallback_page(page, plan)

    return files


# ---------------------------------------------------------------------------
# Ensure required components exist
# ---------------------------------------------------------------------------

def _ensure_required_components(files, plan):
    """Ensure Navbar, Footer, and other critical components exist."""
    components = plan.get("components", [])
    comp_names = [c.get("name", "") for c in components]
    nav_links = plan.get("navigation", {}).get("links", [])
    color_scheme = plan.get("design", {}).get("color_scheme", {})
    dark_mode = "dark_mode" in plan.get("features", [])

    if "Navbar" not in files and "src/components/Navbar.jsx" not in files:
        links_js = json.dumps([{"label": l.get("label", ""), "route": l.get("route", "/")} for l in nav_links])
        project_title = plan.get("project_name", "App").title()
        files["src/components/Navbar.jsx"] = (
            "import React from 'react'\n\n"
            "export default function Navbar({ darkMode, toggleDarkMode }) {\n"
            "  const links = " + links_js + "\n"
            "  const [mobileOpen, setMobileOpen] = React.useState(false)\n\n"
            "  return (\n"
            "    <nav style={{ background: darkMode ? '#1e293b' : '#ffffff', borderBottom: '1px solid ' + (darkMode ? '#334155' : '#e2e8f0'), padding: '0 24px', position: 'sticky', top: 0, zIndex: 100 }}>\n"
            "      <div style={{ maxWidth: 1200, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64 }}>\n"
            "        <a href='/' style={{ fontSize: '1.25rem', fontWeight: 700, color: '#6366f1', textDecoration: 'none' }}>\n"
            "          " + project_title + "\n"
            "        </a>\n"
            "        <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>\n"
            "          {links.map((link, i) => (\n"
            "            <a key={i} href={link.route} style={{ color: darkMode ? '#f8fafc' : '#1e293b', textDecoration: 'none', fontSize: 14, fontWeight: 500 }}>\n"
            "              {link.label}\n"
            "            </a>\n"
            "          ))}\n"
            "          {toggleDarkMode && (\n"
            "            <button onClick={toggleDarkMode} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 20, color: darkMode ? '#f8fafc' : '#1e293b' }}>\n"
            "              {darkMode ? '☀️' : '🌙'}\n"
            "            </button>\n"
            "          )}\n"
            "        </div>\n"
            "      </div>\n"
            "    </nav>\n"
            "  )\n"
            "}\n"
        )

    if "Footer" not in files and "src/components/Footer.jsx" not in files:
        project_title = plan.get("project_name", "App").title()
        description = plan.get("description", "A modern web application")
        footer_links = "".join([
            '<a key={i} href="' + l.get("route", "/") + '" style={{ color: "#94a3b8", textDecoration: "none", fontSize: 14 }}>{l.label}</a>'
            for l in nav_links
        ])
        files["src/components/Footer.jsx"] = (
            "import React from 'react'\n\n"
            "export default function Footer() {\n"
            "  return (\n"
            "    <footer style={{ background: '#1e293b', color: '#94a3b8', padding: '48px 24px 24px', marginTop: 'auto' }}>\n"
            "      <div style={{ maxWidth: 1200, margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 32 }}>\n"
            "        <div>\n"
            "          <h3 style={{ color: '#f8fafc', fontSize: '1.1rem', marginBottom: 12 }}>" + project_title + "</h3>\n"
            "          <p style={{ fontSize: 14, lineHeight: 1.6 }}>" + description + "</p>\n"
            "        </div>\n"
            "        <div>\n"
            "          <h4 style={{ color: '#f8fafc', marginBottom: 12 }}>Links</h4>\n"
            "          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>\n"
            "            " + footer_links + "\n"
            "          </div>\n"
            "        </div>\n"
            "      </div>\n"
            "      <div style={{ borderTop: '1px solid #334155', marginTop: 32, paddingTop: 16, textAlign: 'center', fontSize: 13 }}>\n"
            "        © {new Date().getFullYear()} " + project_title + ". All rights reserved.\n"
            "      </div>\n"
            "    </footer>\n"
            "  )\n"
            "}\n"
        )


def _fallback_component(comp, plan):
    """Generate a fallback component if AI fails."""
    name = comp.get("name", "Component")
    desc = comp.get("description", "")
    colors = plan.get("design", {}).get("color_scheme", {})
    surface = colors.get("surface", "#1e293b")
    text = colors.get("text", "#f8fafc")
    muted = colors.get("text_muted", "#94a3b8")
    return (
        "import React from 'react'\n\n"
        "export default function " + name + "() {\n"
        "  return (\n"
        "    <div style={{ padding: '24px', background: '" + surface + "', borderRadius: 12, marginBottom: 16 }}>\n"
        "      <h3 style={{ color: '" + text + "', marginBottom: 8 }}>" + name + "</h3>\n"
        "      <p style={{ color: '" + muted + "', fontSize: 14 }}>" + desc + "</p>\n"
        "    </div>\n"
        "  )\n"
        "}\n"
    )


def _fallback_page(page, plan):
    """Generate a fallback page if AI fails."""
    name = page.get("name", "Page")
    desc = page.get("description", "")
    colors = plan.get("design", {}).get("color_scheme", {})
    text = colors.get("text", "#f8fafc")
    muted = colors.get("text_muted", "#94a3b8")
    return (
        "import React from 'react'\n\n"
        "export default function " + name + "() {\n"
        "  return (\n"
        "    <div style={{ padding: '80px 24px', textAlign: 'center', minHeight: '60vh' }}>\n"
        "      <div style={{ maxWidth: 800, margin: '0 auto' }}>\n"
        "        <h1 style={{ fontSize: '3rem', marginBottom: 16, color: '" + text + "' }}>" + name + "</h1>\n"
        "        <p style={{ fontSize: '1.2rem', color: '" + muted + "' }}>" + desc + "</p>\n"
        "      </div>\n"
        "    </div>\n"
        "  )\n"
        "}\n"
     )


def _fallback_app_jsx(plan):
    """Fallback App.jsx that is always valid JSX."""
    pages = plan.get("pages", [{"name": "Home", "route": "/"}])
    imports = "\n".join([f"import {p['name']} from './pages/{p['name']}'" for p in pages])
    routes = "\n".join([f"        <Route path=\"{p.get('route','/')}\" element={{<{p['name']} />}} />" for p in pages])
    return f"""import React from 'react'
import {{ BrowserRouter, Routes, Route }} from 'react-router-dom'
{imports}
import Navbar from './components/Navbar'
import Footer from './components/Footer'

export default function App() {{
  const [darkMode, setDarkMode] = React.useState(false)
  return (
    <BrowserRouter>
      <div style={{{{ minHeight: '100vh', background: darkMode ? '#0f172a' : '#ffffff', color: darkMode ? '#f8fafc' : '#0f172a' }}}}>
        <Navbar darkMode={{darkMode}} toggleDarkMode={{() => setDarkMode(!darkMode)}} />
        <Routes>
{routes}
        </Routes>
        <Footer />
      </div>
    </BrowserRouter>
  )
}}
"""


# ---------------------------------------------------------------------------
# Scaffolding builders
# ---------------------------------------------------------------------------

def _build_package_json(plan):
    deps = {
        "react": "^18.2.0",
        "react-dom": "^18.2.0",
        "react-router-dom": "^6.20.0",
    }
    # Add extra dependencies from plan
    for dep in plan.get("dependencies", []):
        if dep not in deps:
            deps[dep] = "^1.0.0"

    return json.dumps({
        "name": plan.get("project_name", "nexus-app"),
        "private": True,
        "version": "0.0.1",
        "type": "module",
        "scripts": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview"
        },
        "dependencies": deps,
        "devDependencies": {
            "@vitejs/plugin-react": "^4.2.0",
            "vite": "^5.0.0"
        }
    }, indent=2)


def _build_vite_config():
    return """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    cors: true,
    headers: {
      'X-Frame-Options': 'ALLOWALL',
      'Access-Control-Allow-Origin': '*',
    },
  },
  preview: {
    host: '0.0.0.0',
    cors: true,
    headers: {
      'X-Frame-Options': 'ALLOWALL',
    },
  },
})
"""


def _build_index_html(plan):
    name = plan.get("project_name", "Nexus App")
    colors = plan.get("design", {}).get("color_scheme", {})
    bg = colors.get("background", "#0f172a")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{name}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>body{{margin:0;padding:0;background:{bg};font-family:'Inter',sans-serif}}</style>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.jsx"></script>
</body>
</html>"""


def _build_main_jsx():
    return """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles/globals.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
"""


def _build_globals_css(plan):
    colors = plan.get("design", {}).get("color_scheme", {})
    fonts = plan.get("design", {}).get("fonts", {})
    vars_css = "\n".join([f"  --color-{k}: {v};" for k, v in colors.items()])
    return f"""/* Global Styles */
:root {{
{vars_css}
  --font-heading: '{fonts.get("heading", "Inter")}', sans-serif;
  --font-body: '{fonts.get("body", "Inter")}', sans-serif;
  --radius: 12px;
  --radius-sm: 8px;
  --shadow: 0 4px 24px rgba(0,0,0,0.12);
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.08);
  --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}}

*, *::before, *::after {{
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}}

body {{
  font-family: var(--font-body);
  background: var(--color-background, #0f172a);
  color: var(--color-text, #f8fafc);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}}

h1, h2, h3, h4, h5, h6 {{
  font-family: var(--font-heading);
  line-height: 1.2;
}}

a {{
  color: var(--color-primary, #6366f1);
  text-decoration: none;
  transition: var(--transition);
}}

a:hover {{ opacity: 0.85; }}
img {{ max-width: 100%; height: auto; }}
button {{ cursor: pointer; font-family: inherit; }}
input, textarea, select {{ font-family: inherit; }}

.container {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}}

/* Scrollbar styling */
::-webkit-scrollbar {{ width: 8px; }}
::-webkit-scrollbar-track {{ background: var(--color-background); }}
::-webkit-scrollbar-thumb {{ background: var(--color-surface, #1e293b); border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--color-text_muted, #94a3b8); }}

@media (max-width: 768px) {{
  .container {{ padding: 0 16px; }}
}}
"""


# ---------------------------------------------------------------------------
# JSON parsing helper
# ---------------------------------------------------------------------------

def _parse_json(text):
    """Parse JSON from LLM response, handling markdown fences."""
    if not text:
        raise ValueError("Empty response")

    text = text.strip()

    # Remove markdown fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (fences)
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in the text
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from response: {text[:200]}...")


def _clean_code_output(text):
    """Clean LLM output to extract pure code."""
    if not text:
        return ""
    text = text.strip()
    # Remove markdown fences
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


# ---------------------------------------------------------------------------
# Static HTML generation
# ---------------------------------------------------------------------------

STATIC_SYSTEM_PROMPT = """You are an expert web developer. Generate complete, production-ready static HTML/CSS/JS files.

RULES:
- Each page is a complete HTML file with inline or linked CSS/JS
- Use modern CSS (flexbox, grid, custom properties)
- Make everything responsive
- Use semantic HTML5
- Share a common styles.css across pages
- Include navigation that links between pages
- Use realistic content, not placeholder text

FILENAME RULES (CRITICAL):
- NEVER use: < > : " | ? *
- Use only letters, numbers, hyphens, underscores, slashes

OUTPUT: Return ONLY a JSON object where each key is a file path and each value is the complete file content.
Do NOT include markdown fences. Output ONLY the JSON object."""


def generate_static_project(plan):
    """Generate a complete static HTML/CSS/JS project."""
    from services.llm_service import call_llm

    pages = plan.get("pages", [])
    color_scheme = plan.get("design", {}).get("color_scheme", {})

    page_descriptions = "\n".join([
        f'- {p["name"]} (file: {"index.html" if p.get("route") == "/" else p["name"].lower() + ".html"}) — {p.get("description", "")}'
        for p in pages
    ])

    prompt = f"""Generate a complete static website with ALL pages.

PROJECT: {plan.get("project_name", "my-site")}
DESCRIPTION: {plan.get("description", "")}

COLOR SCHEME:
- Primary: {color_scheme.get("primary", "#6366f1")}
- Background: {color_scheme.get("background", "#0f172a")}
- Surface: {color_scheme.get("surface", "#1e293b")}
- Text: {color_scheme.get("text", "#f8fafc")}

PAGES TO CREATE:
{page_descriptions}

REQUIREMENTS:
1. Each page must be a COMPLETE HTML file (not a stub)
2. Include a shared styles.css with all styles
3. Include a shared script.js with interactions
4. Every page must have a navigation bar linking all pages
5. Use realistic content — not "Lorem ipsum"
6. Make everything responsive
7. Use CSS variables from the color scheme

Return a JSON object with file paths as keys and full file contents as values."""

    files = {}
    try:
        result = call_llm(
            prompt,
            system_instruction=STATIC_SYSTEM_PROMPT,
            temperature=0.4,
            max_tokens=16384,
        )
        parsed = _parse_json(result)
        for path, content in parsed.items():
            if isinstance(content, str) and content.strip():
                files[path] = content
    except Exception as e:
        logger.error(f"[CodeGen] Static generation failed: {e}")
        files["index.html"] = _fallback_static_index(plan)
        files["styles.css"] = _fallback_static_css(plan)

    if "index.html" not in files:
        files["index.html"] = _fallback_static_index(plan)
    if "styles.css" not in files:
        files["styles.css"] = _fallback_static_css(plan)

    logger.info(f"[CodeGen] Static project generated: {len(files)} files")
    return _sanitize_file_keys(files)


def _fallback_static_index(plan):
    name = plan.get("project_name", "My Website")
    pages = plan.get("pages", [])
    nav_links = "".join([
        f'<a href="{p.get("route", "/") if p.get("route") == "/" else p["name"].lower() + ".html"}">{p["name"]}</a>'
        for p in pages
    ])
    colors = plan.get("design", {}).get("color_scheme", {})
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <nav class="navbar">
    <div class="container nav-content">
      <a href="index.html" class="logo">{name}</a>
      <div class="nav-links">{nav_links}</div>
    </div>
  </nav>
  <section class="hero">
    <div class="container">
      <h1>Welcome to {name}</h1>
      <p>{plan.get("description", "A modern website")}</p>
      <a href="#features" class="btn btn-primary">Learn More</a>
    </div>
  </section>
  <script src="script.js"></script>
</body>
</html>"""


def _fallback_static_css(plan):
    colors = plan.get("design", {}).get("color_scheme", {})
    return f"""/* {plan.get('project_name', 'Website')} Styles */
:root {{
  --primary: {colors.get('primary', '#6366f1')};
  --bg: {colors.get('background', '#0f172a')};
  --text: {colors.get('text', '#f8fafc')};
  --surface: {colors.get('surface', '#1e293b')};
}}
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 0 24px; }}
.navbar {{ padding: 16px 0; background: var(--surface); }}
.nav-content {{ display: flex; justify-content: space-between; align-items: center; }}
.logo {{ font-weight: 700; font-size: 1.3rem; color: var(--text); text-decoration: none; }}
.nav-links a {{ color: var(--text); text-decoration: none; margin-left: 24px; opacity: 0.8; }}
.nav-links a:hover {{ opacity: 1; }}
.hero {{ padding: 120px 0; text-align: center; }}
.hero h1 {{ font-size: 3rem; margin-bottom: 16px; }}
.hero p {{ font-size: 1.2rem; opacity: 0.8; margin-bottom: 32px; }}
.btn {{ display: inline-block; padding: 12px 24px; border-radius: 12px; font-weight: 600; text-decoration: none; transition: all 0.3s; }}
.btn-primary {{ background: var(--primary); color: white; }}
.btn-primary:hover {{ transform: translateY(-2px); box-shadow: 0 8px 24px rgba(99,102,241,0.4); }}
@media (max-width: 768px) {{
  .hero h1 {{ font-size: 2rem; }}
  .nav-links {{ display: none; }}
}}
"""
