import sys
import os
PRIMARY_MODEL = "deepseek-chat"
_root = os.path.dirname(os.path.abspath(__file__))
# Root MUST be before backend so 'services' resolves to root/services/, not backend/services/
if _root not in sys.path:
    sys.path.insert(0, _root)
if os.path.join(_root, "backend") not in sys.path:
    sys.path.insert(1, os.path.join(_root, "backend"))

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file, make_response, flash, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

import uuid
from bson.objectid import ObjectId
from datetime import datetime
from io import BytesIO
import zipfile
import re
import json

# AI imports disabled - preparing for new AI builder integration
# from backend.ai.ai_manager import get_ai_manager, AIManager, PipelineStage
# from config.gemini_config import PRIMARY_MODEL, FALLBACK_MODELS
# from services.code_generator import CATEGORY_DESIGN_SYSTEMS, build_framer_system_instruction

# Initialize MongoDB with graceful fallback
from services.mongo_connection import init_mongo, get_db, is_mongo_connected, is_mongo_offline

load_dotenv()

class ConfigurationError(Exception):
    pass


def validate_startup_models():
    env_model = os.getenv("GEMINI_MODEL", "")
    try:
        with open(".env", "r", encoding="utf-8") as f:
            env_content = f.read()
    except:
        env_content = ""
        
    if "gemini-1.5-pro-latest" in env_model or "gemini-1.5-pro-latest" in env_content:
        raise ConfigurationError("Old Gemini model detected. Update configuration.")

validate_startup_models()

# Initialize MongoDB connection with timeout and fallback
MONGO_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "5000"))
mongo_connected = init_mongo(timeout_ms=MONGO_TIMEOUT_MS)

app = Flask(__name__)
CORS(app)
app.secret_key = "nexusflow123"

# Get database instance (real or mock)
mongo_db = get_db()

# Collection references (work with both real and mock MongoDB)
user_collection = mongo_db.users
project_collection = mongo_db.projects
version_collection = mongo_db.project_versions
download_collection = mongo_db.downloads
chat_collection = mongo_db.chats
log_collection = mongo_db.logs
code_quality_collection = mongo_db.code_quality
notification_collection = mongo_db.notifications
generation_cache_collection = mongo_db.ai_generation_cache

try:
    from services.performance_monitor import configure as configure_perf_monitor
    configure_perf_monitor(mongo_db)
except Exception as _e:
    pass

import logging as _startup_logging
_startup_logger = _startup_logging.getLogger(__name__)
logger = _startup_logger
# Ensure startup logs are visible even without prior basicConfig
try:
    _startup_logging.basicConfig(level=_startup_logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
except Exception:
    pass

# Clean startup logging - only Database: Connected / Offline mode (no stack traces)
if mongo_connected:
    print("Database: Connected")
else:
    print("Database: Offline mode")

# Expose DB availability helper for routes/templates
def is_db_available():
    """True when real MongoDB is connected; False in offline/mock mode."""
    try:
        return is_mongo_connected()
    except Exception:
        return False

app.config["MONGO_CONNECTED"] = mongo_connected

# ─── Global JSON Error Handlers for API Routes ───
# Ensure all /api/* routes return JSON errors instead of HTML pages
@app.errorhandler(404)
def handle_404(e):
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "error": "API endpoint not found"}), 404
    return render_template("404.html"), 404

@app.errorhandler(500)
def handle_500(e):
    logger.error(f"Internal server error: {e}")
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "error": "Internal server error"}), 500
    return render_template("500.html"), 500

@app.errorhandler(Exception)
def handle_exception(e):
    # Graceful fallback for MongoDB errors - never crash the app
    try:
        from pymongo.errors import PyMongoError
        if isinstance(e, PyMongoError):
            logger.warning(f"MongoDB operation failed (offline mode active): {e}")
            if request.path.startswith('/api/'):
                return jsonify({"success": False, "error": "Database unavailable - running in offline mode", "offline": True}), 503
            # For page routes, continue with fallback data instead of crashing
            raise
    except ImportError:
        pass
    logger.exception(f"Unhandled exception: {e}")
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "error": "Internal server error"}), 500
    # Re-raise for default Flask handling on non-API routes
    raise


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        app.static_folder,
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


@app.route("/api/mongo-status", methods=["GET"])
def mongo_status():
    """Return MongoDB connectivity status (no auth required for health checks)."""
    try:
        connected = is_mongo_connected()
    except Exception:
        connected = False
    return jsonify({
        "success": True,
        "connected": connected,
        "offline": not connected,
        "mode": "online" if connected else "offline",
        "message": "Database: Connected" if connected else "Database: Offline mode",
        "uri_configured": bool(os.getenv("MONGO_URI"))
    })


@app.route("/api/health", methods=["GET"])
def health_check():
    """General health check including MongoDB and AI Builder status."""
    try:
        db_connected = is_mongo_connected()
    except Exception:
        db_connected = False
    return jsonify({
        "success": True,
        "status": "ok",
        "database": "connected" if db_connected else "offline",
        "database_message": "Database: Connected" if db_connected else "Database: Offline mode",
        "ai_builder": "available",
        "offline_mode": not db_connected
    })

UPLOAD_FOLDER = "static/profile_pictures"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Profile image uploads (device files -> static/uploads/profile/<name>)
# Anchored to app.static_folder (absolute) so saved files are always inside the
# folder Flask serves, regardless of the process's current working directory.
PROFILE_UPLOAD_FOLDER = os.path.join(app.static_folder, "uploads", "profile")
app.config["PROFILE_UPLOAD_FOLDER"] = PROFILE_UPLOAD_FOLDER
ALLOWED_PROFILE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

def profile_image_url(u):
    """Resolve a user's stored profile_image value to a servable URL ('' when none)."""
    if not u:
        return ""
    img = u.get("profile_image") or ""
    if not img:
        return ""
    if img.startswith("/") or img.startswith("http://") or img.startswith("https://"):
        return img
    return url_for("static", filename=img)

def _delete_profile_image_file(image_value):
    """Best-effort removal of a previously saved profile image file from disk."""
    if not image_value:
        return
    rel = image_value[len("/static/"):] if image_value.startswith("/static/") else image_value
    path = os.path.join(app.static_folder, rel)
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass

def _save_profile_image(file_storage):
    """Validate + save an uploaded profile image. Returns the stored profile_image value.

    Raises ValueError with a friendly message when the file is missing or not a supported image type.
    """
    if not file_storage or not file_storage.filename:
        raise ValueError("No file selected.")
    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in ALLOWED_PROFILE_EXTENSIONS:
        raise ValueError("Unsupported image type. Please choose a JPG, JPEG, PNG or WEBP image.")
    os.makedirs(app.config["PROFILE_UPLOAD_FOLDER"], exist_ok=True)

    user = user_collection.find_one({"email": session.get("email")})
    uid = str(user.get("_id")) if user and user.get("_id") else re.sub(r"[^a-zA-Z0-9]", "", session.get("email", "user"))[:12]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    filename = "profile_{0}_{1}{2}".format(uid, timestamp, ext)
    file_storage.save(os.path.join(app.config["PROFILE_UPLOAD_FOLDER"], filename))

    old = (user or {}).get("profile_image")
    if old:
        _delete_profile_image_file(old)
    return "/static/uploads/profile/{0}".format(filename)

@app.context_processor
def inject_theme_color():
    """Expose the logged-in user, their theme color, theme mode and the profile-image helper to every template."""
    theme_color = ""
    theme_color_value = ""
    theme_mode = "dark"
    user = None
    notification_count = 0
    # MongoDB availability for templates (offline banner)
    try:
        _mongo_offline = is_mongo_offline()
    except Exception:
        _mongo_offline = False
    _mongo_connected = not _mongo_offline
    email = session.get("email")
    if email:
        try:
            u = user_collection.find_one({"email": email})
        except Exception:
            u = None
        if u:
            user = u
            theme_color = u.get("theme_color") or ""
            theme_color_value = u.get("theme_color_value") or ""
            theme_mode = u.get("theme_mode") or "dark"
        try:
            notification_count = notification_collection.count_documents({"user_email": email, "read": False})
        except Exception:
            notification_count = 0
    return {
        "user": user,
        "current_user": user,
        "theme_color": theme_color,
        "theme_color_value": theme_color_value,
        "theme_mode": theme_mode,
        "profile_image_url": profile_image_url,
        "notification_count": notification_count,
        "mongo_connected": _mongo_connected,
        "mongo_offline": _mongo_offline,
        "db_available": _mongo_connected,
    }


@app.context_processor
def inject_current_user():
    """Global user context processor - ensures profile_image is available on every page (builder, dashboard, Jarvis, settings, etc.)."""
    email = session.get("email")
    current_user = None
    avatar_url = ""
    if email:
        try:
            current_user = user_collection.find_one({"email": email})
            avatar_url = profile_image_url(current_user)
        except Exception:
            current_user = None
            avatar_url = ""
    # Fallback avatar (used when profile_image missing or load fails)
    fallback_avatar = url_for("static", filename="images/profile-icon.png")
    return {
        "current_user": current_user,
        "current_user_avatar": avatar_url,
        "fallback_avatar": fallback_avatar,
    }


def get_default_website_state():
    return {
        "website_name": "My AI Website",
        "prompt": "Modern SaaS Landing Page",
        "html": """<header class="navbar">
  <div class="container nav-container">
    <a href="#" class="logo"><i class="fa-solid fa-bolt"></i> Nexus Flow</a>
    <nav class="nav-links">
      <a href="#features">Features</a>
      <a href="#solutions">Solutions</a>
      <a href="#pricing">Pricing</a>
    </nav>
    <a href="#cta" class="nav-btn">Get Started</a>
  </div>
</header>

<section class="hero">
  <div class="container hero-container">
    <div class="badge"><i class="fa-solid fa-sparkles"></i> Next-Gen Web Architecture</div>
    <h1>Build Production Websites <span class="gradient-text">10x Faster</span></h1>
    <p>Nexus Flow AI combines elite UI design principles with clean, responsive Flexbox and Grid layouts.</p>
    <div class="hero-actions">
      <a href="#cta" class="btn btn-primary">Start Building Free <i class="fa-solid fa-arrow-right"></i></a>
      <a href="#features" class="btn btn-secondary">Explore Features</a>
    </div>
  </div>
</section>

<section id="features" class="features">
  <div class="container">
    <div class="section-header">
      <h2>Engineered for Excellence</h2>
      <p>Everything you need to launch sleek, modern web applications.</p>
    </div>
    <div class="grid-3">
      <div class="card">
        <div class="card-icon"><i class="fa-solid fa-layer-group"></i></div>
        <h3>Clean Layouts</h3>
        <p>Built with modern CSS Grid and Flexbox for seamless alignment across all devices.</p>
      </div>
      <div class="card">
        <div class="card-icon"><i class="fa-solid fa-mobile-screen"></i></div>
        <h3>100% Responsive</h3>
        <p>Optimized for mobile, tablet, and widescreen desktop displays natively.</p>
      </div>
      <div class="card">
        <div class="card-icon"><i class="fa-solid fa-wand-magic-sparkles"></i></div>
        <h3>Framer Aesthetic</h3>
        <p>Polished dark mode styling with glassmorphism textures and subtle micro-animations.</p>
      </div>
    </div>
  </div>
</section>

<footer class="footer">
  <div class="container footer-container">
    <p>&copy; 2026 Nexus Flow AI. All rights reserved.</p>
    <div class="footer-links">
      <a href="#">Privacy Policy</a>
      <a href="#">Terms of Service</a>
    </div>
  </div>
</footer>""",
        "css": """.navbar { padding: 1.25rem 0; border-bottom: 1px solid rgba(255,255,255,0.08); background: rgba(9, 13, 22, 0.8); backdrop-filter: blur(12px); sticky: top: 0; z-index: 100; }
.nav-container { display: flex; justify-content: space-between; align-items: center; }
.logo { font-size: 1.25rem; font-weight: 800; color: #fff; display: flex; align-items: center; gap: 0.5rem; }
.logo i { color: #ff6b00; }
.nav-links { display: flex; gap: 2rem; }
.nav-links a { color: #94a3b8; font-weight: 500; font-size: 0.95rem; }
.nav-links a:hover { color: #fff; }
.nav-btn { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); padding: 0.5rem 1.25rem; border-radius: 999px; font-weight: 600; font-size: 0.9rem; color: #fff; }

.hero { padding: 6rem 0 4rem; text-align: center; }
.hero-container { display: flex; flex-direction: column; align-items: center; }
.badge { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.4rem 1rem; border-radius: 999px; background: rgba(255, 107, 0, 0.12); border: 1px solid rgba(255, 107, 0, 0.3); color: #ff6b00; font-size: 0.85rem; font-weight: 600; margin-bottom: 1.5rem; }
.hero h1 { font-size: 3.5rem; font-weight: 800; line-height: 1.15; max-width: 800px; margin-bottom: 1.25rem; letter-spacing: -0.02em; }
.gradient-text { background: linear-gradient(135deg, #ff6b00, #ff2d2d); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.hero p { font-size: 1.2rem; color: #94a3b8; max-width: 620px; margin-bottom: 2.5rem; }
.hero-actions { display: flex; gap: 1rem; flex-wrap: wrap; justify-content: center; }
.btn { padding: 0.85rem 1.75rem; border-radius: 10px; font-weight: 600; font-size: 1rem; display: inline-flex; align-items: center; gap: 0.5rem; }
.btn-primary { background: linear-gradient(135deg, #ff6b00, #ff2d2d); color: #fff; box-shadow: 0 4px 20px rgba(255, 107, 0, 0.3); }
.btn-secondary { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: #fff; }

.features { padding: 5rem 0; background: rgba(255,255,255,0.01); border-top: 1px solid rgba(255,255,255,0.05); }
.section-header { text-align: center; margin-bottom: 3.5rem; }
.section-header h2 { font-size: 2.25rem; font-weight: 700; margin-bottom: 0.75rem; }
.section-header p { color: #94a3b8; font-size: 1.1rem; }
.grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 2rem; }
.card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); padding: 2rem; border-radius: 16px; transition: all 0.3s ease; }
.card:hover { transform: translateY(-4px); border-color: rgba(255, 107, 0, 0.4); box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
.card-icon { width: 48px; height: 48px; border-radius: 12px; background: rgba(255, 107, 0, 0.15); color: #ff6b00; display: grid; place-items: center; font-size: 1.25rem; margin-bottom: 1.25rem; }
.card h3 { font-size: 1.25rem; font-weight: 600; margin-bottom: 0.75rem; }
.card p { color: #94a3b8; font-size: 0.95rem; line-height: 1.6; }

.footer { padding: 3rem 0; border-top: 1px solid rgba(255,255,255,0.08); margin-top: auto; }
.footer-container { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; color: #64748b; font-size: 0.9rem; }
.footer-links { display: flex; gap: 1.5rem; }

@media (max-width: 768px) {
  .nav-links { display: none; }
  .hero h1 { font-size: 2.25rem; }
  .hero { padding: 4rem 0 3rem; }
}""",
        "javascript": """document.addEventListener('DOMContentLoaded', () => {
  console.log('Nexus Flow Framer-grade template initialized successfully.');
});""",
        "preview": "",
        "generation_time": None,
        "last_modified": None,
        "chat_history": []
    }


def get_current_website_state():
    state = session.get("website_state")
    if not isinstance(state, dict):
        state = {}

    default_state = get_default_website_state()
    default_state.update(state)

    if not isinstance(default_state.get("chat_history"), list):
        default_state["chat_history"] = []

    return default_state


def save_current_website_state(state):
    normalized_state = get_default_website_state()
    normalized_state.update(state)

    if not isinstance(normalized_state.get("chat_history"), list):
        normalized_state["chat_history"] = []

    normalized_state["preview"] = build_preview_document(normalized_state)
    normalized_state["last_modified"] = datetime.utcnow().isoformat()
    session["website_state"] = normalized_state
    session.modified = True
    return normalized_state


# =========================================================
# NEXUS FLOW AI - AUTOMATIC CODE REPAIR & SANITIZATION ENGINE
# =========================================================

def clean_markdown_fences(code_str):
    if not isinstance(code_str, str):
        return ""
    text = code_str.strip()
    json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text, re.IGNORECASE)
    if json_match:
        return json_match.group(1).strip()
    text = re.sub(r'^```[a-zA-Z0-9_-]*\s*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    text = re.sub(r'```', '', text)
    return text.strip()


def strip_typescript_annotations(js_str):
    if not isinstance(js_str, str):
        return ""
    text = js_str
    text = re.sub(r'interface\s+[A-Za-z0-9_]+\s*\{[^}]*\}', '', text, flags=re.DOTALL)
    text = re.sub(r'type\s+[A-Za-z0-9_]+\s*=[^;]+;', '', text)
    text = re.sub(r'enum\s+[A-Za-z0-9_]+\s*\{[^}]*\}', '', text, flags=re.DOTALL)
    text = re.sub(r'\s+as\s+[A-Za-z0-9_<>[\]]+', '', text)
    text = re.sub(r'(\b[a-zA-Z0-9_]+)\s*:\s*([A-Za-z0-9_<>[\]|&\s]+)(?=[=,\)\n;])', r'\1', text)
    text = re.sub(r'\)\s*:\s*([A-Za-z0-9_<>[\]|&\s]+)\s*=>', ') =>', text)
    text = re.sub(r'\)\s*:\s*([A-Za-z0-9_<>[\]|&\s]+)\s*\{', ') {', text)
    return text


def balance_html_tags(html_str):
    if not html_str:
        return ""

    lines = html_str.splitlines()
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        if stripped.startswith("# ") or stripped.startswith("## ") or stripped.startswith("### "):
            level = len(stripped.split()[0])
            content = stripped.lstrip('#').strip()
            cleaned_lines.append(f"<h{level}>{content}</h{level}>")
        else:
            cleaned_lines.append(line)
    html_str = "\n".join(cleaned_lines)

    void_tags = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
    tag_regex = re.compile(r'</?([a-zA-Z0-9-]+)(?:\s+[^>]*?)?>')
    stack = []

    for match in tag_regex.finditer(html_str):
        full_tag = match.group(0)
        tag_name = match.group(1).lower()

        if tag_name in void_tags or full_tag.endswith('/>'):
            continue

        if full_tag.startswith('</'):
            if stack and stack[-1] == tag_name:
                stack.pop()
            elif tag_name in stack:
                while stack and stack[-1] != tag_name:
                    stack.pop()
                if stack:
                    stack.pop()
        else:
            stack.append(tag_name)

    result = html_str
    while stack:
        missing_tag = stack.pop()
        result += f"\n</{missing_tag}>"

    return result


def clean_html(html_str):
    if not isinstance(html_str, str):
        html_str = ""
    text = clean_markdown_fences(html_str)

    embedded_css = '\n'.join(re.findall(r'<style[^>]*>(.*?)</style>', text, re.DOTALL | re.IGNORECASE))
    embedded_js = '\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL | re.IGNORECASE))

    text = re.sub(r'<style[^>]*>.*?(?:</style>|$)', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<script[^>]*>.*?(?:</script>|$)', '', text, flags=re.DOTALL | re.IGNORECASE)

    body_match = re.search(r'<body[^>]*>(.*?)</body>', text, re.DOTALL | re.IGNORECASE)
    if body_match:
        text = body_match.group(1)
    else:
        text = re.sub(r'<!DOCTYPE[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</?html[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<head[^>]*>.*?</head>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'</?body[^>]*>', '', text, flags=re.IGNORECASE)

    text = balance_html_tags(text.strip())
    return text, embedded_css, embedded_js


def clean_css(css_str):
    if not isinstance(css_str, str):
        css_str = ""
    text = clean_markdown_fences(css_str)
    text = re.sub(r'</?style[^>]*>', '', text, flags=re.IGNORECASE).strip()

    if '/*' in text and '*/' not in text[text.rfind('/*'):]:
        text += ' */'

    open_b = text.count('{')
    close_b = text.count('}')
    if open_b > close_b:
        text += '\n' + ('}' * (open_b - close_b))
    elif close_b > open_b:
        diff = close_b - open_b
        for _ in range(diff):
            last_idx = text.rfind('}')
            if last_idx != -1:
                text = text[:last_idx] + text[last_idx+1:]

    base_reset = """*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif; line-height: 1.6; -webkit-text-size-adjust: 100%; scroll-behavior: smooth; }
body { margin: 0; padding: 0; width: 100%; min-height: 100vh; background-color: #090d16; color: #f8fafc; overflow-x: hidden; display: flex; flex-direction: column; }
section, header, footer, nav, main, article, aside { display: block; position: relative; width: 100%; clear: both; box-sizing: border-box; }
.container, .wrapper, .section-container { width: 100%; max-width: 1240px; margin-left: auto; margin-right: auto; padding-left: 1.5rem; padding-right: 1.5rem; box-sizing: border-box; }
img, video, svg, iframe, canvas { max-width: 100%; height: auto; display: block; }
a { text-decoration: none; color: inherit; transition: all 0.2s ease; }
button, input, select, textarea { font-family: inherit; font-size: inherit; }"""

    if not text:
        return base_reset

    if "box-sizing" not in text:
        text = base_reset + "\n\n" + text

    return text


def clean_javascript(js_str):
    if not isinstance(js_str, str):
        js_str = ""
    text = clean_markdown_fences(js_str)
    text = re.sub(r'</?script[^>]*>', '', text, flags=re.IGNORECASE).strip()

    text = strip_typescript_annotations(text)

    open_p = text.count('(')
    close_p = text.count(')')
    if open_p > close_p:
        text += ')' * (open_p - close_p)

    open_b = text.count('{')
    close_b = text.count('}')
    if open_b > close_b:
        text += '\n' + ('}' * (open_b - close_b))

    text = text.replace('</script>', '<\\/script>')
    return text


def parse_modifier_response(raw_text, user_prompt=""):
    """
    Parse the AI Modifier response WITHOUT applying the fallback template.
    This preserves the user's existing website when the AI returns short snippets.
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {"html": "", "css": "", "javascript": "", "message": "", "changed_files": []}

    parsed_json = None
    html_code = ""
    css_code = ""
    js_code = ""
    message = ""
    changed_files = []

    cleaned_input = clean_markdown_fences(raw_text)
    try:
        parsed_json = json.loads(cleaned_input)
    except Exception:
        pass

    if not parsed_json:
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', raw_text, re.IGNORECASE)
        if json_match:
            try:
                parsed_json = json.loads(json_match.group(1))
            except Exception:
                pass

    if not parsed_json:
        brace_match = re.search(r'\{[\s\S]*\}', raw_text)
        if brace_match:
            candidate = brace_match.group(0)
            try:
                parsed_json = json.loads(candidate)
            except Exception:
                try:
                    repaired = re.sub(r',\s*([\}\]])', r'\1', candidate)
                    parsed_json = json.loads(repaired)
                except Exception:
                    pass

    if isinstance(parsed_json, dict):
        html_code = str(parsed_json.get("html", "") or "")
        css_code = str(parsed_json.get("css", "") or "")
        js_code = str(parsed_json.get("javascript") or parsed_json.get("js") or "")
        message = str(parsed_json.get("message") or parsed_json.get("reply") or parsed_json.get("explanation") or "")
        raw_changed = parsed_json.get("changed_files") or []
        if isinstance(raw_changed, list):
            changed_files = [str(f) for f in raw_changed if isinstance(f, str) and f.strip()]
        elif isinstance(raw_changed, str):
            changed_files = [f.strip() for f in raw_changed.replace("\n", ",").split(",") if f.strip()]

    if not html_code and not css_code and not js_code:
        html_match = re.search(r'```html\s*([\s\S]*?)\s*```', raw_text, re.IGNORECASE)
        css_match = re.search(r'```css\s*([\s\S]*?)\s*```', raw_text, re.IGNORECASE)
        js_match = re.search(r'```js(?:cript)?\s*([\s\S]*?)\s*```', raw_text, re.IGNORECASE)
        if html_match:
            html_code = html_match.group(1)
        if css_match:
            css_code = css_match.group(1)
        if js_match:
            js_code = js_match.group(1)

    if not html_code:
        tag_match = re.search(r'(<(?:section|div|header|main|article|nav|footer)[^>]*>[\s\S]*</(?:section|div|header|main|article|nav|footer)>)', raw_text, re.IGNORECASE)
        if tag_match:
            html_code = tag_match.group(1)

    # Clean but DO NOT fallback to template - modifier must preserve existing website
    clean_h, extra_css, extra_js = clean_html(html_code)
    clean_c = clean_css(css_code + ("\n" + extra_css if extra_css else ""))
    clean_j = clean_javascript(js_code + ("\n" + extra_js if extra_js else ""))

    if not message:
        message = f"Updated the website according to your request: '{user_prompt}'" if user_prompt else "Updated the website."

    return {
        "html": clean_h,
        "css": clean_c,
        "javascript": clean_j,
        "message": message,
        "changed_files": changed_files
    }


def _extract_files_from_fences(text):
    """Extract HTML/CSS/JS from markdown code blocks or FILE: directives.

    Returns a files dict with path-style keys (index.html / css/style.css /
    js/main.js) that _normalize_generated_files understands. Empty dict when
    no code fences are present.

    Supports:
    1. ```html / ```css / ```js markdown fences
    2. FILE: path/to/file followed by fenced or unfenced code
    3. ---FILE--- / ---CODE--- / ---END--- delimiters
    """
    if not text or not isinstance(text, str):
        return {}

    files = {}

    # Format 1: ---FILE--- / ---CODE--- / ---END--- blocks
    file_block_pattern = re.compile(
        r"---FILE---\s*\n\s*path:\s*(.+?)\s*\n\s*---CODE---\s*\n([\s\S]*?)\n\s*---END---",
        re.IGNORECASE,
    )
    for match in file_block_pattern.finditer(text):
        path = match.group(1).strip()
        code = match.group(2).strip()
        if path and code:
            lower = path.lower().strip()
            if lower in ("index.html", "index.htm", "home.html"):
                files["index.html"] = code
            elif lower.endswith(".css"):
                files["css/style.css"] = code
            elif lower.endswith(".js"):
                files["js/main.js"] = code
            else:
                files[path] = code

    if files:
        print(f"[Parser] Extracted {len(files)} files from ---FILE--- directives")
        return {k: v for k, v in files.items() if v}

    # Format 2: FILE: path followed by fenced code block
    file_fenced_pattern = re.compile(
        r"FILE:\s*(\S+)\s*\n```(?:\w+)?\s*\n([\s\S]*?)```",
        re.IGNORECASE,
    )
    for match in file_fenced_pattern.finditer(text):
        path = match.group(1).strip()
        code = match.group(2).strip()
        if path and code:
            lower = path.lower().strip()
            if lower in ("index.html", "index.htm", "home.html"):
                files["index.html"] = code
            elif lower.endswith(".css"):
                files["css/style.css"] = code
            elif lower.endswith(".js"):
                files["js/main.js"] = code
            else:
                files[path] = code

    if files:
        print(f"[Parser] Extracted {len(files)} files from FILE: directives with fences")
        return {k: v for k, v in files.items() if v}

    # Format 3: FILE: path followed by unfenced code (next FILE: or end of text)
    file_nofence_pattern = re.compile(
        r"^FILE:\s*(\S+)\s*\n([\s\S]+?)(?=^FILE:\s*\S|\Z)",
        re.MULTILINE | re.IGNORECASE,
    )
    for match in file_nofence_pattern.finditer(text):
        path = match.group(1).strip()
        code = match.group(2).strip()
        if path and code:
            lower = path.lower().strip()
            if lower in ("index.html", "index.htm", "home.html"):
                files["index.html"] = code
            elif lower.endswith(".css"):
                files["css/style.css"] = code
            elif lower.endswith(".js"):
                files["js/main.js"] = code
            else:
                files[path] = code

    if files:
        print(f"[Parser] Extracted {len(files)} files from FILE: directives (no fences)")
        return {k: v for k, v in files.items() if v}

    # Format 4: Standard markdown fences ```html / ```css / ```js
    blocks = {"index.html": "", "css/style.css": "", "js/main.js": ""}
    found = False
    for lang, body in re.findall(
        r"```\s*(html|css|js|javascript)\s*\n?([\s\S]*?)```", text, re.IGNORECASE
    ):
        lang = lang.lower()
        found = True
        if lang == "html":
            blocks["index.html"] = body.strip()
        elif lang == "css":
            blocks["css/style.css"] = body.strip()
        else:
            blocks["js/main.js"] = body.strip()

    if found:
        result = {k: v for k, v in blocks.items() if v}
        if result:
            print(f"[Parser] Extracted {len(result)} files from markdown fences")
            return result

    return {}


def _recover_nested_code_json(raw_text, files=None):
    """Find a real {html, css, javascript} JSON object embedded inside the raw
    model output or inside one of the already-extracted string values.

    Small local models occasionally double-encode the answer (the whole JSON
    object becomes a single string value). This scans every candidate `{...}`
    region and pulls the real code back out so the site is never lost.
    Returns a files dict or {} when nothing usable is found.
    """
    candidates = []
    if isinstance(raw_text, str) and len(raw_text) > 40:
        candidates.append(raw_text)
    if isinstance(files, dict):
        for v in files.values():
            if isinstance(v, str) and len(v) > 40:
                candidates.append(v)

    decoder = json.JSONDecoder()
    for cand in candidates:
        idx = 0
        n = len(cand)
        while idx < n:
            brace = cand.find("{", idx)
            if brace == -1:
                break
            try:
                obj, end = decoder.raw_decode(cand[brace:])
            except Exception:
                idx = brace + 1
                continue
            idx = brace + end
            if not isinstance(obj, dict):
                continue
            html = obj.get("html")
            css = obj.get("css") or obj.get("css_text") or obj.get("styles")
            js = obj.get("javascript") or obj.get("js")
            if isinstance(html, str) and html.strip() and isinstance(css, str):
                return {
                    "index.html": html,
                    "css/style.css": css,
                    "js/main.js": js if isinstance(js, str) else "",
                }
    return {}


# Public placeholder base used when the model emits a local/relative image path
# that would otherwise render broken (browser 404, ZIP export dangling file).
PUBLIC_IMAGE_BASE = "https://picsum.photos/seed"


def _is_public_url(url):
    """True when a URL can be loaded directly by a browser (no local file)."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not url:
        return False
    return bool(re.match(r"^(https?:)?//", url)) or url.startswith((
        "data:", "blob:", "about:", "#", "mailto:", "tel:", "sms:",
        "javascript:", "callto:",
    ))


def _placeholder_public_image(path):
    """Deterministic public placeholder URL derived from the broken path."""
    seed = re.sub(r"[^a-z0-9]+", "-", (path or "hero").lower()).strip("-")[:60] or "hero"
    return f"{PUBLIC_IMAGE_BASE}/{seed}/1600/900"


def _sanitize_image_sources(html_str):
    """Rewrite local/relative image references to working public URLs.

    Guarantees generated sites never ship broken local image paths: <img>,
    <video>, <source>, <iframe>, <picture> and <audio> src/srcset/poster/
    data-src attributes plus inline CSS background-image url() values that are
    not absolute public URLs are replaced with a deterministic public
    placeholder image. Absolute https://, protocol-relative, data:, blob:,
    anchor (#), mailto:, tel: and other safe values are left untouched.
    """
    if not html_str or not isinstance(html_str, str):
        return html_str or ""

    def _swap_url(url):
        url = url.strip().strip('"').strip("'")
        return url if _is_public_url(url) else _placeholder_public_image(url)

    def _fix_attr(m):
        return m.group(1) + _swap_url(m.group(2)) + m.group(3)

    def _fix_srcset(m):
        urls = []
        for part in m.group(2).split(","):
            part = part.strip()
            if not part:
                continue
            bits = part.split()
            if bits:
                bits[0] = _swap_url(bits[0])
                urls.append(" ".join(bits))
        return m.group(1) + ", ".join(urls) + m.group(3)

    def _fix_tag(match):
        tag = match.group(0)
        tag = re.sub(r"(\bsrc\s*=\s*[\"'])([^\"']*)([\"'])", _fix_attr, tag)
        tag = re.sub(r"(\bsrcset\s*=\s*[\"'])([^\"']*)([\"'])", _fix_srcset, tag)
        tag = re.sub(r"(\bposter\s*=\s*[\"'])([^\"']*)([\"'])", _fix_attr, tag)
        tag = re.sub(r"(\bdata-src\s*=\s*[\"'])([^\"']*)([\"'])", _fix_attr, tag)
        return tag

    html_str = re.sub(
        r"<(img|video|source|iframe|picture|audio)\b[^>]*>",
        _fix_tag, html_str, flags=re.IGNORECASE
    )

    html_str = re.sub(
        r"url\(\s*(['\"]?)[^'\")]+\1\s*\)",
        lambda m: "url('{0}')".format(
            _swap_url(m.group(0)[4:-1].strip().strip('"').strip("'"))
        ),
        html_str, flags=re.IGNORECASE
    )
    return html_str


def _sanitize_css_image_urls(css_str):
    """Rewrite relative background-image url() values in CSS to public URLs."""
    if not css_str or not isinstance(css_str, str):
        return css_str or ""

    def _fix_url(match):
        url = match.group(2).strip()
        return match.group(0) if _is_public_url(url) else "url('{0}')".format(
            _placeholder_public_image(url)
        )

    return re.sub(
        r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)",
        _fix_url, css_str, flags=re.IGNORECASE
    )


def _sanitize_generated_files(files):
    """Post-process generated file contents so sites never ship broken images."""
    if not isinstance(files, dict):
        return files or {}
    cleaned = {}
    for key, value in files.items():
        if isinstance(value, str):
            if key == "html" or key.endswith(".html"):
                value = _sanitize_image_sources(value)
            elif key == "css" or key.endswith(".css"):
                value = _sanitize_css_image_urls(value)
        cleaned[key] = value
    return cleaned


def parse_and_validate_ai_response(raw_text, user_prompt="", category_key="saas", website_name="My AI Website"):
    if not isinstance(raw_text, str) or not raw_text.strip():
        raw_text = ""

    print(f"[Parser] Parsing AI response: {len(raw_text)} chars")
    logger.info(f"[Parser] Parsing AI response: {len(raw_text)} chars")

    parsed_json = None
    html_code = ""
    css_code = ""
    js_code = ""
    message = ""

    cleaned_input = clean_markdown_fences(raw_text)
    try:
        parsed_json = json.loads(cleaned_input)
    except Exception:
        pass

    if not parsed_json:
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', raw_text, re.IGNORECASE)
        if json_match:
            try:
                parsed_json = json.loads(json_match.group(1))
            except Exception:
                pass

    if not parsed_json:
        brace_match = re.search(r'\{[\s\S]*\}', raw_text)
        if brace_match:
            candidate = brace_match.group(0)
            try:
                parsed_json = json.loads(candidate)
            except Exception:
                try:
                    repaired = re.sub(r',\s*([\}\]])', r'\1', candidate)
                    parsed_json = json.loads(repaired)
                except Exception:
                    try:
                        parsed_json, _ = json.JSONDecoder().raw_decode(candidate)
                    except Exception:
                        pass

    features = []
    files = {}

    # Fallback: if no JSON object was found, extract separately fenced
    # HTML / CSS / JS code blocks (```html / ```css / ```js). This makes
    # generation robust to small local models that answer in markdown code
    # blocks instead of strict JSON.
    if not parsed_json:
        files_from_fences = _extract_files_from_fences(raw_text)
        if files_from_fences:
            print(f"[Parser] Extracted {len(files_from_fences)} files from fences/directives")
            logger.info(f"[Parser] Extracted {len(files_from_fences)} files from fences/directives")
            return {
                "files": _sanitize_generated_files(files_from_fences),
                "message": "Generated from separated HTML/CSS/JavaScript blocks.",
                "features": [],
            }

    if isinstance(parsed_json, dict):
        if "files" in parsed_json:
            raw_files = parsed_json["files"]
            if isinstance(raw_files, list):
                files = {}
                for f in raw_files:
                    if isinstance(f, dict):
                        fname = f.get("filename") or f.get("path") or f.get("name") or ""
                        content = f.get("content", "")
                        if fname and content is not None:
                            lower = fname.lower().strip()
                            if lower in ("index.html", "index.htm", "home.html"):
                                files["index.html"] = str(content)
                            elif lower in ("styles.css", "style.css", "main.css", "css/style.css"):
                                files["css/style.css"] = str(content)
                            elif lower in ("script.js", "scripts.js", "main.js", "app.js", "js/main.js"):
                                files["js/main.js"] = str(content)
                            else:
                                files[fname] = str(content)
            elif isinstance(raw_files, dict):
                files = {k: str(v) for k, v in raw_files.items() if v is not None}
            else:
                files = {}
        else:
            files["index.html"] = str(parsed_json.get("html", "") or "")
            files["css/style.css"] = str(parsed_json.get("css", "") or "")
            files["js/main.js"] = str(parsed_json.get("javascript") or parsed_json.get("js") or "")

        message = str(parsed_json.get("message") or "")
        features = parsed_json.get("features", [])

    # Small models sometimes double-encode the answer (the whole JSON object
    # becomes one string value) or return only an empty SPA shell. Recover the
    # real code from an embedded JSON blob before giving up on the extraction.
    if not (files.get("index.html") or "").strip() or not (files.get("css/style.css") or files.get("styles.css") or "").strip():
        recovered = _recover_nested_code_json(raw_text, files)
        if recovered:
            files = recovered

    file_count = len([v for v in files.values() if isinstance(v, str) and v.strip()])
    print(f"[Parser] Files extracted: {file_count} ({', '.join(k for k, v in files.items() if isinstance(v, str) and v.strip())})")
    logger.info(f"[Parser] Files extracted: {file_count}")

    return {
        "files": _sanitize_generated_files(files),
        "message": message,
        "features": features
    }


def build_preview_document(state):
    raw_html = state.get("html", "") or ""
    raw_css = state.get("css", "") or ""
    raw_js = state.get("javascript", "") or ""

    clean_h, extra_css, extra_js = clean_html(raw_html)
    clean_c = clean_css(raw_css + ("\n" + extra_css if extra_css else ""))
    clean_j = clean_javascript(raw_js + ("\n" + extra_js if extra_js else ""))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="/static/vendor/fontawesome/css/all.min.css">
  <link rel="stylesheet" href="/static/vendor/fonts/fonts.css">
<style>
{clean_c}
  </style>
</head>
<body>
{clean_h}
<script>
  try {{
{clean_j}
  }} catch(e) {{
    console.error('Execution Error:', e);
  }}
</script>
</body>
</html>"""


def build_full_project_html(title, html_code, css_code, js_code):
    clean_h, extra_css, extra_js = clean_html(html_code)
    clean_c = clean_css(css_code + ("\n" + extra_css if extra_css else ""))
    clean_j = clean_javascript(js_code + ("\n" + extra_js if extra_js else ""))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="/static/vendor/fontawesome/css/all.min.css">
    <link rel="stylesheet" href="/static/vendor/fonts/fonts.css">
<style>
{clean_c}
    </style>
</head>
<body>
{clean_h}
    <script>
  try {{
{clean_j}
  }} catch(e) {{
    console.error('Execution Error:', e);
  }}
    </script>
</body>
</html>"""


def save_project_from_state(email, state, project_id=None):
    title = (state.get("website_name") or "AI Generated Website").strip() or "AI Generated Website"
    prompt = (state.get("prompt") or "Modern responsive website").strip() or "Modern responsive website"
    html_code = state.get("html", "") or ""
    css_code = state.get("css", "") or ""
    js_code = state.get("javascript", "") or ""
    full_html = build_full_project_html(title, html_code, css_code, js_code)

    if project_id:
        try:
            project_collection.update_one(
                {"_id": ObjectId(project_id), "user_email": email},
                {"$set": {
                    "title": title,
                    "prompt": prompt,
                    "html_code": full_html,
                    "css_code": css_code,
                    "js_code": js_code,
                    "updated_at": datetime.utcnow()
                }}
            )
            session["active_project_id"] = project_id
            return project_id
        except Exception:
            pass

    new_doc = {
        "user_email": email,
        "title": title,
        "prompt": prompt,
        "html_code": full_html,
        "css_code": css_code,
        "js_code": js_code,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    res = project_collection.insert_one(new_doc)
    project_id = str(res.inserted_id)
    session["active_project_id"] = project_id
    return project_id


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = user_collection.find_one({"email": email})

        print(f"[AUTH] Login attempt for: {email}")

        if user is None:
            print("[AUTH] User not found")
            return render_template(
                "login.html",
                error="No account found. Please create an account."
            )

        print(f"[AUTH] User found: {email}")

        # Verify password against hashed value in MongoDB
        stored_password = user.get("password", "")
        if not stored_password.startswith("pbkdf2:sha256") and not stored_password.startswith("scrypt:"):
            # Backward compatibility: existing plain-text passwords from old registrations
            if stored_password == password:
                # Re-hash the plain text password and update MongoDB immediately
                new_hash = generate_password_hash(password)
                user_collection.update_one(
                    {"email": email},
                    {"$set": {"password": new_hash}}
                )
                print("[AUTH] Migrated plain-text password to hashed format")
            else:
                print("[AUTH] Password verification result: FAILED (legacy plain-text mismatch)")
                return render_template(
                    "login.html",
                    error="Incorrect password."
                )
        else:
            # New hashed password - verify with check_password_hash
            if not check_password_hash(stored_password, password):
                print("[AUTH] Password verification result: FAILED")
                return render_template(
                    "login.html",
                    error="Incorrect password."
                )

        print("[AUTH] Password verification result: SUCCESS")

        # Save the logged-in user's email
        session["email"] = email
        session.permanent = True

        try:
            from services.audit_service import log_event
            log_event(email, "user_login", f"User logged in successfully", "SUCCESS")
        except Exception:
            pass

        return redirect(url_for("dashboard"))

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Check password confirmation
        if password != confirm_password:
            return render_template(
                "register.html",
                error="Passwords do not match."
            )

        # Check if email already exists
        existing_user = user_collection.find_one({"email": email})

        if existing_user:
            return render_template(
                "register.html",
                error="Email already registered."
            )

        # Hash the password before storing (never store plain text)
        hashed_password = generate_password_hash(password)

        # Save user with hashed password
        user_collection.insert_one({
            "fullname": fullname,
            "email": email,
            "password": hashed_password
        })

        print(f"[AUTH] New user registered: {email} (password hashed)")

        try:
            from services.audit_service import log_event
            log_event(email, "user_register", f"New user registered: {fullname}", "SUCCESS")
        except Exception:
            pass

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/generate", methods=["POST"])
def generate():
    """Generate website - PLACEHOLDER for new AI integration."""
    try:
        data = request.get_json() if request.is_json else request.form
        prompt = (data.get("prompt", "") or "").strip()
        website_name = (data.get("website_name") or "My AI Website").strip() or "My AI Website"

        if not prompt:
            return jsonify({"error": "Prompt cannot be empty"}), 400

        # PLACEHOLDER: New AI builder will be connected here
        return jsonify({
            "success": True,
            "status": "ready",
            "message": "AI Builder connection pending.",
            "html": "",
            "css": "",
            "javascript": "",
            "js": "",
            "files": {"index.html": "", "styles.css": "", "script.js": ""},
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ecommerce/cart", methods=["POST"])
def api_cart():
    import time
    time.sleep(0.5)
    return jsonify({"success": True, "message": "Item added to cart successfully."})

@app.route("/api/ecommerce/checkout", methods=["POST"])
def api_checkout():
    import time
    time.sleep(1.5)
    return jsonify({"success": True, "message": "Checkout completed successfully! Order #12345 confirmed."})

@app.route("/api/search", methods=["POST"])
def api_search():
    import time
    time.sleep(0.8)
    data = request.get_json() or {}
    query = data.get("query", "")
    results = [
        {"id": 1, "title": f"Result 1 for {query}", "description": "Description of the first result."},
        {"id": 2, "title": f"Result 2 for {query}", "description": "Description of the second result."}
    ]
    return jsonify({"success": True, "results": results})


@app.route("/dashboard")
def dashboard():
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    user = user_collection.find_one({"email": email})
    user_projects = list(project_collection.find({"user_email": email}).sort("updated_at", -1))
    total_downloads = download_collection.count_documents({"user_email": email})
    total_chats = chat_collection.count_documents({"user_email": email})

    # Calculate storage metrics
    download_history = list(download_collection.find({"user_email": email}))
    total_bytes = sum(item.get("file_size_bytes", 0) for item in download_history)
    storage_mb = round(total_bytes / (1024 * 1024), 2)
    storage_pct = min(100, round((storage_mb / 50.0) * 100, 1))

    enriched_projects = [_project_display_fields(p) for p in user_projects]

    # Build a real recent-activity feed from projects, versions and downloads
    def _time_fmt(dt):
        if not isinstance(dt, datetime):
            return "Recently"
        delta = datetime.utcnow() - dt
        if delta.days > 0:
            return f"{delta.days}d ago"
        if delta.seconds >= 3600:
            return f"{int(delta.seconds // 3600)}h ago"
        if delta.seconds >= 60:
            return f"{int(delta.seconds // 60)}m ago"
        return "Just now"

    activity = []
    for p in enriched_projects[:6]:
        activity.append({
            "badge": "orange", "icon": "fa-wand-magic-sparkles",
            "title": "Website Created",
            "desc": f"\"{p.get('title') or p.get('prompt', 'Untitled')[:50]}\"",
            "time": _time_fmt(p.get("created_at")),
            "ts": p.get("created_at")
        })
    for v in list(version_collection.find({"user_email": email}).sort("created_at", -1).limit(3)):
        activity.append({
            "badge": "blue", "icon": "fa-pen-to-square",
            "title": "Version Saved",
            "desc": (v.get("description") or "Version snapshot")[:60],
            "time": _time_fmt(v.get("created_at")),
            "ts": v.get("created_at")
        })
    for d in download_history[-3:]:
        activity.append({
            "badge": "green", "icon": "fa-file-arrow-down",
            "title": "File Downloaded",
            "desc": d.get("file_name") or d.get("title") or "Export",
            "time": _time_fmt(d.get("downloaded_at")),
            "ts": d.get("downloaded_at")
        })
    activity.sort(key=lambda a: a.get("ts") or datetime.min, reverse=True)
    activity = activity[:8]

    return render_template(
        "dashboard.html",
        user=user,
        projects=enriched_projects[:5],
        total_projects=len(user_projects),
        total_downloads=total_downloads,
        total_chats=total_chats,
        storage_mb=storage_mb,
        storage_pct=storage_pct,
        recent_activity=activity
    )

@app.route("/dashboard/data")
def dashboard_data():
    if "email" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    from services.dashboard_service import get_dashboard_data
    data = get_dashboard_data(session["email"])
    return jsonify({"success": True, "data": data})

@app.route("/profile")
def profile():
    email = session.get("email")

    if email is None:
        return redirect(url_for("login"))

    # Default safe fallbacks (never pass None to template)
    fallback_user = {
        "fullname": "Nexus User",
        "email": email,
        "bio": "",
        "designation": None,
        "role": None,
        "phone": None,
        "dob": None,
        "date_of_birth": None,
        "location": None,
        "profile_image": None,
    }
    user = None
    user_projects = []
    download_count = 0
    chat_count = 0
    enriched_projects = []

    try:
        # --- User ---
        try:
            user = user_collection.find_one({"email": email})
        except Exception as e:
            logger.warning(f"[Profile] user lookup failed: {e}")
            user = None
        if not user or not isinstance(user, dict):
            # Keep fallback but preserve email if found
            user = dict(fallback_user)
            # Try to keep any partial data if user was partially fetched
            if isinstance(user, dict) and email:
                user["email"] = email
        else:
            # Ensure required keys exist for template (do not overwrite existing values)
            for k, v in fallback_user.items():
                if k not in user or user.get(k) is None:
                    # Keep existing email, otherwise fallback
                    if k == "email" and user.get("email"):
                        continue
                    # Only set if missing
                    if k not in user:
                        user[k] = v

        # --- Projects ---
        try:
            user_projects = list(project_collection.find({"user_email": email}).sort("updated_at", -1))
        except Exception as e:
            logger.warning(f"[Profile] projects lookup failed: {e}")
            user_projects = []

        # --- Counts ---
        try:
            download_count = download_collection.count_documents({"user_email": email})
        except Exception as e:
            logger.warning(f"[Profile] download count failed: {e}")
            download_count = 0

        try:
            chat_count = chat_collection.count_documents({"user_email": email})
        except Exception as e:
            logger.warning(f"[Builder] chat count failed: {e}")
            chat_count = 0

        # --- Enrich (safe even if project missing _id) ---
        enriched_projects = []
        for p in user_projects:
            try:
                if p:
                    enriched_projects.append(_project_display_fields(p))
            except Exception as e:
                logger.warning(f"[Profile] enrich project failed: {e}")

    except Exception as e:
        import traceback
        logger.error(f"[Profile] Unhandled error, returning empty state: {e}\n{traceback.format_exc()}")
        # Ensure we still have safe defaults
        if not user or not isinstance(user, dict):
            user = dict(fallback_user)
        user_projects = []
        enriched_projects = []
        download_count = 0
        chat_count = 0

    # Final safety: ensure template never receives None
    if user is None or not isinstance(user, dict):
        user = dict(fallback_user)
    if enriched_projects is None:
        enriched_projects = []
    if not isinstance(download_count, int):
        download_count = 0
    if not isinstance(chat_count, int):
        chat_count = 0

    return render_template(
        "profile.html",
        user=user,
        projects=enriched_projects[:4] if isinstance(enriched_projects, list) else [],
        total_projects=len(user_projects) if isinstance(user_projects, list) else 0,
        total_downloads=download_count,
        total_chats=chat_count
    )

@app.route("/profile/upload-image", methods=["POST"])
def profile_upload_image():
    if "email" not in session:
        return jsonify({"success": False, "message": "Not authenticated."}), 401

    file = request.files.get("profile") or request.files.get("image")
    try:
        stored = _save_profile_image(file)
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    user_collection.update_one(
        {"email": session["email"]},
        {"$set": {"profile_image": stored}}
    )
    return jsonify({"success": True, "image_url": stored, "message": "Profile photo updated."})

@app.route("/upload_profile", methods=["POST"])
def upload_profile():
    if "email" not in session:
        return redirect(url_for("login"))

    file = request.files.get("profile")
    try:
        stored = _save_profile_image(file)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("profile"))

    user_collection.update_one(
        {"email": session["email"]},
        {"$set": {"profile_image": stored}}
    )
    return redirect(url_for("profile"))

@app.route("/remove_profile", methods=["GET", "POST"])
def remove_profile():
    if "email" not in session:
        return redirect(url_for("login"))

    user = user_collection.find_one({"email": session["email"]})
    if user and user.get("profile_image"):
        _delete_profile_image_file(user["profile_image"])

    user_collection.update_one(
        {"email": session["email"]},
        {"$unset": {"profile_image": ""}}
    )

    if request.method == "POST" or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "message": "Profile picture removed."})
    return redirect(url_for("profile"))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    return _settings_page("settings.html")

@app.route("/app-settings", methods=["GET", "POST"])
def app_settings():
    return _settings_page("app_settings.html")

def _settings_page(template_name):
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    user = user_collection.find_one({"email": email})

    if not user:
        session.clear()
        return redirect(url_for("login"))

    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            action = data.get("action")

            if action == "profile":
                fullname = data.get("fullname", "").strip()
                new_email = data.get("email", "").strip()
                bio = data.get("bio", "").strip()
                phone = data.get("phone", "").strip()
                dob = data.get("dob", "").strip()
                designation = data.get("designation", "").strip()
                location = data.get("location", "").strip()

                if not fullname or not new_email:
                    return jsonify({"success": False, "error": "Full name and email are required."}), 400

                if new_email != email:
                    if user_collection.find_one({"email": new_email}):
                        return jsonify({"success": False, "error": "Email is already taken."}), 400

                update_fields = {
                    "fullname": fullname,
                    "email": new_email,
                    "bio": bio,
                    "phone": phone,
                    "dob": dob,
                    "designation": designation,
                    "location": location,
                }
                user_collection.update_one(
                    {"email": email},
                    {"$set": update_fields}
                )
                session["email"] = new_email
                return jsonify({"success": True, "message": "Profile updated successfully!"})

            elif action == "password":
                current_password = data.get("current_password", "")
                new_password = data.get("new_password", "")
                confirm_password = data.get("confirm_password", "")

                # Verify current password against stored hash
                stored_password = user.get("password", "")
                if stored_password.startswith("pbkdf2:sha256") or stored_password.startswith("scrypt:"):
                    if not check_password_hash(stored_password, current_password):
                        return jsonify({"success": False, "error": "Current password is incorrect."}), 400
                else:
                    if stored_password != current_password:
                        return jsonify({"success": False, "error": "Current password is incorrect."}), 400

                if len(new_password) < 6:
                    return jsonify({"success": False, "error": "New password must be at least 6 characters."}), 400

                if new_password != confirm_password:
                    return jsonify({"success": False, "error": "New passwords do not match."}), 400

                # Hash the new password before storing
                new_hashed = generate_password_hash(new_password)
                user_collection.update_one(
                    {"email": email},
                    {"$set": {"password": new_hashed}}
                )
                print("[AUTH] Password hash updated successfully")
                return jsonify({"success": True, "message": "Password updated successfully!"})

            elif action in ("appearance", "theme_color"):
                theme_color = data.get("theme_color", "blue")
                theme_color_value = data.get("theme_color_value", "").strip()
                theme_mode = data.get("theme_mode", "dark")
                preview_layout = data.get("preview_layout", "desktop")

                update = {
                    "theme_color": theme_color,
                    "theme_mode": theme_mode,
                    "appearance.preview_layout": preview_layout,
                }
                if theme_color_value:
                    update["theme_color_value"] = theme_color_value

                user_collection.update_one(
                    {"email": email},
                    {"$set": update}
                )
                return jsonify({
                    "success": True,
                    "message": "Appearance applied!",
                    "theme_color": theme_color,
                    "theme_color_value": theme_color_value,
                    "theme_mode": theme_mode
                })

            elif action == "notifications":
                notifications = {
                    "email_alerts": bool(data.get("email_alerts")),
                    "project_updates": bool(data.get("project_updates")),
                    "ai_updates": bool(data.get("ai_updates"))
                }
                user_collection.update_one(
                    {"email": email},
                    {"$set": {"notifications": notifications}}
                )
                return jsonify({"success": True, "message": "Notification preferences updated!"})

            elif action == "ai_preferences":
                ai_preferences = {
                    "default_model": data.get("default_model", PRIMARY_MODEL),
                    "code_style": data.get("code_style", "modern"),
                    "creativity": data.get("creativity", "balanced")
                }
                user_collection.update_one(
                    {"email": email},
                    {"$set": {"ai_preferences": ai_preferences}}
                )
                return jsonify({"success": True, "message": "AI preferences saved!"})

            return jsonify({"success": False, "error": "Invalid action specified."}), 400

        action = request.form.get("action")
        msg = None
        err = None

        if action == "profile":
            fullname = request.form.get("fullname", "").strip()
            new_email = request.form.get("email", "").strip()
            bio = request.form.get("bio", "").strip()
            phone = request.form.get("phone", "").strip()
            dob = request.form.get("dob", "").strip()
            designation = request.form.get("designation", "").strip()
            location = request.form.get("location", "").strip()

            if not fullname or not new_email:
                err = "Full name and email are required."
            elif new_email != email and user_collection.find_one({"email": new_email}):
                err = "Email is already in use."
            else:
                update_fields = {
                    "fullname": fullname,
                    "email": new_email,
                    "bio": bio,
                    "phone": phone,
                    "dob": dob,
                    "designation": designation,
                    "location": location,
                }
                user_collection.update_one(
                    {"email": email},
                    {"$set": update_fields}
                )
                session["email"] = new_email
                email = new_email
                msg = "Profile updated successfully!"

        elif action == "password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            stored_password = user.get("password", "")
            if stored_password.startswith("pbkdf2:sha256") or stored_password.startswith("scrypt:"):
                password_matches = check_password_hash(stored_password, current_password)
            else:
                password_matches = stored_password == current_password

            if not password_matches:
                err = "Current password is incorrect."
            elif len(new_password) < 6:
                err = "New password must be at least 6 characters."
            elif new_password != confirm_password:
                err = "New passwords do not match."
            else:
                new_hashed = generate_password_hash(new_password)
                user_collection.update_one({"email": email}, {"$set": {"password": new_hashed}})
                print("[AUTH] Password hash updated successfully")
                msg = "Password updated successfully!"

        elif action in ("appearance", "theme_color"):
            theme_color = request.form.get("theme_color", "blue")
            theme_color_value = request.form.get("theme_color_value", "").strip()
            theme_mode = request.form.get("theme_mode", "dark")
            preview_layout = request.form.get("preview_layout", "desktop")

            update = {
                "theme_color": theme_color,
                "theme_mode": theme_mode,
                "appearance.preview_layout": preview_layout,
            }
            if theme_color_value:
                update["theme_color_value"] = theme_color_value

            user_collection.update_one({"email": email}, {"$set": update})
            msg = "Appearance applied!"

        elif action == "notifications":
            notifications = {
                "email_alerts": "email_alerts" in request.form,
                "project_updates": "project_updates" in request.form,
                "ai_updates": "ai_updates" in request.form
            }
            user_collection.update_one({"email": email}, {"$set": {"notifications": notifications}})
            msg = "Notification preferences updated!"

        elif action == "ai_preferences":
            ai_preferences = {
                "default_model": request.form.get("default_model", PRIMARY_MODEL),
                "code_style": request.form.get("code_style", "modern"),
                "creativity": request.form.get("creativity", "balanced")
            }
            user_collection.update_one({"email": email}, {"$set": {"ai_preferences": ai_preferences}})
            msg = "AI preferences saved!"

        user = user_collection.find_one({"email": email})
        return render_template(template_name, user=user, message=msg, error=err)

    return render_template(template_name, user=user)

@app.route("/delete_account", methods=["POST"])
def delete_account():
    if "email" not in session:
        if request.is_json:
            return jsonify({"success": False, "error": "Unauthorized"}), 401
        return redirect(url_for("login"))

    email = session["email"]
    user = user_collection.find_one({"email": email})

    if request.is_json:
        data = request.get_json()
        password = data.get("password", "")
        stored_password = user.get("password", "") if user else ""
        if stored_password.startswith("pbkdf2:sha256") or stored_password.startswith("scrypt:"):
            password_matches = check_password_hash(stored_password, password)
        else:
            password_matches = stored_password == password
        if user and password_matches:
            user_collection.delete_one({"email": email})
            session.clear()
            return jsonify({"success": True, "redirect": url_for("home")})
        return jsonify({"success": False, "error": "Incorrect password. Failed to delete account."}), 400

@app.route("/projects")
def projects():
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    user = user_collection.find_one({"email": email})
    
    # Retrieve user projects sorted by latest
    user_projects = list(project_collection.find({"user_email": email}).sort("updated_at", -1))
    
    enriched_projects = [_project_display_fields(p) for p in user_projects]

    return render_template("projects.html", projects=enriched_projects, user=user)

@app.route("/projects/create", methods=["POST"])
def create_project():
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    email = session["email"]
    data = request.get_json() if request.is_json else request.form

    title = data.get("title", "").strip() or "Untitled AI Website"
    prompt = data.get("prompt", "").strip() or "Modern responsive website"
    html_code = data.get("html_code", "")

    if not html_code:
        html_code = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: 'Poppins', sans-serif; background: #0f172a; color: white; margin: 0; padding: 40px; text-align: center; }}
        h1 {{ color: #ff6b00; font-size: 2.8rem; margin-bottom: 10px; }}
        p {{ color: #94a3b8; font-size: 1.2rem; max-width: 600px; margin: 0 auto 30px auto; }}
        .badge {{ display: inline-block; padding: 8px 16px; background: rgba(255,107,0,0.15); color: #ff6b00; border: 1px solid #ff6b00; border-radius: 20px; font-weight: bold; margin-bottom: 20px; }}
        .btn {{ display: inline-block; padding: 14px 32px; background: linear-gradient(90deg, #ff4500, #ff2d2d); color: white; text-decoration: none; border-radius: 10px; font-weight: bold; font-size: 1rem; }}
    </style>
</head>
<body>
    <div class="badge">✨ Generated by Nexus Flow AI</div>
    <h1>{title}</h1>
    <p>{prompt}</p>
    <a href="#" class="btn">Get Started</a>
</body>
</html>"""

    new_project = {
        "user_email": email,
        "title": title,
        "prompt": prompt,
        "html_code": html_code,
        "status": "Active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = project_collection.insert_one(new_project)
    pid = str(result.inserted_id)
    _set_thumbnail_ref(pid, email)
    return jsonify({
        "success": True,
        "message": "Project created successfully!",
        "project_id": pid
    })

@app.route("/projects/get/<project_id>", methods=["GET"])
def get_project(project_id):
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        project = project_collection.find_one({"_id": ObjectId(project_id), "user_email": session["email"]})
        if not project:
            return jsonify({"success": False, "error": "Project not found"}), 404

        return jsonify({
            "success": True,
            "project": {
                "id": str(project["_id"]),
                "title": project.get("title", "Untitled Project"),
                "prompt": project.get("prompt", ""),
                "html_code": project.get("html_code", ""),
                "status": project.get("status", "Active"),
                "created_at": project.get("created_at").strftime("%b %d, %Y") if "created_at" in project and isinstance(project["created_at"], datetime) else "Recently",
                "updated_at": project.get("updated_at").strftime("%b %d, %Y, %I:%M %p") if "updated_at" in project and isinstance(project["updated_at"], datetime) else "Recently",
                "thumbnail_ref": project.get("thumbnail_ref") or url_for("isolated_preview", project_id=str(project["_id"]))
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/projects/edit/<project_id>", methods=["POST"])
def edit_project(project_id):
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    data = request.get_json() if request.is_json else request.form
    title = data.get("title", "").strip()
    prompt = data.get("prompt", "").strip()

    if not title:
        return jsonify({"success": False, "error": "Project title is required."}), 400

    try:
        update_fields = {"title": title, "updated_at": datetime.utcnow()}
        if prompt:
            update_fields["prompt"] = prompt

        result = project_collection.update_one(
            {"_id": ObjectId(project_id), "user_email": session["email"]},
            {"$set": update_fields}
        )

        if result.matched_count == 0:
            return jsonify({"success": False, "error": "Project not found."}), 404

        return jsonify({"success": True, "message": "Project updated successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/projects/duplicate/<project_id>", methods=["POST"])
def duplicate_project(project_id):
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        original = project_collection.find_one({"_id": ObjectId(project_id), "user_email": session["email"]})
        if not original:
            return jsonify({"success": False, "error": "Project not found."}), 404

        new_title = f"Copy of {original.get('title', 'Untitled')}"

        # Deep-copy the unified state so the duplicate is fully independent
        state = original.get("website_state")
        if isinstance(state, dict):
            state = json.loads(json.dumps(state, default=str))
            state["website_name"] = new_title
        else:
            state = {}

        duplicated_project = {
            "user_email": session["email"],
            "title": new_title,
            "prompt": original.get("prompt", ""),
            "html_code": original.get("html_code", ""),
            "css_code": original.get("css_code", "") or "",
            "js_code": original.get("js_code", "") or "",
            "website_state": state,
            "status": original.get("status") or "Active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = project_collection.insert_one(duplicated_project)
        # Point the thumbnail at the NEW project's live preview, not the original's
        _set_thumbnail_ref(str(result.inserted_id), session["email"])
        return jsonify({
            "success": True,
            "message": "Project duplicated successfully!",
            "new_project_id": str(result.inserted_id)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/projects/delete/<project_id>", methods=["POST", "DELETE"])
def delete_project(project_id):
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        project = project_collection.find_one({"_id": ObjectId(project_id), "user_email": session["email"]})
        if not project:
            return jsonify({"success": False, "error": "Project not found."}), 404

        project_collection.delete_one({"_id": ObjectId(project_id), "user_email": session["email"]})
        version_collection.delete_many({"project_id": str(project_id)})

        return jsonify({"success": True, "message": "Project deleted successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/projects/delete-all", methods=["POST", "DELETE"])
def delete_all_projects():
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        user_projects = list(project_collection.find({"user_email": session["email"]}, {"_id": 1}))
        project_ids = [str(p["_id"]) for p in user_projects]

        result = project_collection.delete_many({"user_email": session["email"]})
        if project_ids:
            version_collection.delete_many({"project_id": {"$in": project_ids}})

        if result.deleted_count == 0:
            return jsonify({"success": False, "error": "No projects to delete."}), 404

        return jsonify({"success": True, "message": "All projects deleted successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/downloads")
def downloads():
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    user = user_collection.find_one({"email": email})
    
    # Retrieve download history sorted by newest
    download_history = list(download_collection.find({"user_email": email}).sort("downloaded_at", -1))
    
    total_bytes = 0
    for item in download_history:
        item["_id_str"] = str(item["_id"])
        total_bytes += item.get("file_size_bytes", 0)
        if "downloaded_at" in item and isinstance(item["downloaded_at"], datetime):
            item["downloaded_at_fmt"] = item["downloaded_at"].strftime("%b %d, %Y %I:%M %p")
        else:
            item["downloaded_at_fmt"] = "Recently"

    # Calculate storage stats (50 MB limit for user profile allowance)
    storage_mb = round(total_bytes / (1024 * 1024), 2)
    storage_pct = min(100, round((storage_mb / 50.0) * 100, 1))

    # Retrieve user projects for Quick Download section
    user_projects = list(project_collection.find({"user_email": email}).sort("updated_at", -1))
    for p in user_projects:
        p["_id_str"] = str(p["_id"])

    return render_template(
        "downloads.html",
        downloads=download_history,
        projects=user_projects,
        user=user,
        storage_mb=storage_mb,
        storage_pct=storage_pct,
        total_downloads=len(download_history)
    )

@app.route("/download/zip/<project_id>", methods=["GET", "POST"])
def download_zip(project_id):
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    project = project_collection.find_one({"_id": ObjectId(project_id), "user_email": email})

    if not project:
        return "Project not found", 404
    else:
        title = project.get("title", "NexusFlow_Project")
        html_content = project.get("html_code", "<h1>Nexus Flow Website</h1>")
        css_content = project.get("css_code", "") or ""
        js_content = project.get("js_code", "") or ""
        # Prefer the unified website_state (contains the latest AI + manual edits)
        ws = project.get("website_state") or {}
        if isinstance(ws, dict):
            ws_files = ws.get("files") or {}
            if isinstance(ws_files, dict):
                # files is the single source of truth for the latest content
                if ws_files.get("index.html"):
                    html_content = ws_files["index.html"]
                elif ws.get("html"):
                    html_content = ws["html"]
                if ws_files.get("styles.css"):
                    css_content = ws_files["styles.css"]
                elif ws.get("css"):
                    css_content = ws["css"]
                if ws_files.get("script.js"):
                    js_content = ws_files["script.js"]
                elif ws.get("javascript"):
                    js_content = ws["javascript"]
                extra_files = ws_files
            else:
                if ws.get("html"):
                    html_content = ws["html"]
                if ws.get("css"):
                    css_content = ws["css"]
                if ws.get("javascript"):
                    js_content = ws["javascript"]
                extra_files = {}
        else:
            extra_files = {}

    safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title)
    safe_name = safe_title or "nexus-flow-website"

    package_json = json.dumps({
        "name": safe_name.lower().replace("_", "-"),
        "version": "1.0.0",
        "description": f"{title} - Generated by Nexus Flow AI Website Builder",
        "private": True,
        "scripts": {
            "start": "python -m http.server 8080",
            "serve": "npx serve ."
        }
    }, indent=2)

    readme = f"""# {title}

Generated with **Nexus Flow AI Website Builder**.

## Structure

```
project/
├── src/
│   ├── index.html
│   ├── styles.css
│   └── script.js
└── public/
    └── images/
```

## Run locally

Open `index.html` in your browser, or serve the folder:

```bash
npm run serve
# or
python -m http.server 8080
```

The download includes the latest AI-generated changes and any manual code edits.
"""

    def _safe_zip_path(filename):
        if not filename or not isinstance(filename, str):
            return None
        norm = filename.replace("\\", "/")
        if norm.startswith("/") or ".." in norm.split("/"):
            return None
        return norm

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('index.html', html_content)
        zf.writestr('styles.css', css_content or '/* Generated by Nexus Flow AI Website Builder */\nbody { font-family: sans-serif; }')
        zf.writestr('script.js', js_content or '// Generated by Nexus Flow AI Website Builder\nconsole.log("Nexus Flow Website Loaded");')
        zf.writestr('package.json', package_json)
        zf.writestr('README.md', readme)
        # Mirror into the project/ src structure
        zf.writestr('project/index.html', html_content)
        zf.writestr('project/src/index.html', html_content)
        zf.writestr('project/src/styles.css', css_content)
        zf.writestr('project/src/script.js', js_content)
        zf.writestr('project/src/components/README.md', 'Add your reusable components here.\n')
        zf.writestr('project/public/images/README.md', 'Add your website images here.\n')
        zf.writestr('project/package.json', package_json)
        # Include any additional generated files (relative paths preserved)
        if isinstance(extra_files, dict):
            for filename, content in extra_files.items():
                safe = _safe_zip_path(filename)
                if not safe or safe in ('index.html', 'styles.css', 'script.js', 'style.css', 'main.js'):
                    continue
                # Write at the ZIP root too, so opening index.html directly resolves
                # its referenced files (css/style.css, features/*.js, images/*, etc.)
                zf.writestr(safe, content or "")
                zf.writestr(f'project/src/{safe}', content or "")

    memory_file.seek(0)
    file_bytes = memory_file.getvalue()
    file_size = len(file_bytes)
    file_name = f"{safe_title}.zip"

    download_collection.insert_one({
        "user_email": email,
        "project_id": project_id,
        "title": title,
        "file_name": file_name,
        "file_type": "ZIP Archive",
        "file_size_bytes": file_size,
        "downloaded_at": datetime.utcnow()
    })

    _create_notification(
        email,
        "Website downloaded",
        f"{title} was downloaded as {file_name}.",
        "success",
        project_id=project_id,
    )

    return send_file(
        BytesIO(file_bytes),
        mimetype="application/zip",
        as_attachment=True,
        download_name=file_name
    )

@app.route("/download/html/<project_id>", methods=["GET", "POST"])
def download_html(project_id):
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    project = project_collection.find_one({"_id": ObjectId(project_id), "user_email": email})

    if not project:
        return "Project not found", 404
    else:
        title = project.get("title", "NexusFlow_Project")
        html_content = project.get("html_code", "<h1>Nexus Flow Website</h1>")

        # Prefer the unified website_state.files (single source of truth for latest
        # AI + manual edits), including path-style keys (css/style.css, js/main.js).
        ws = project.get("website_state") or {}
        if isinstance(ws, dict):
            ws_files = ws.get("files") or {}
            if isinstance(ws_files, dict) and ws_files:
                files_html, files_css, files_js = _normalize_generated_files(ws_files)
                if files_html:
                    # Inline CSS/JS so a multi-file generated site downloads as a
                    # single, working, self-contained HTML page.
                    if files_css or files_js:
                        html_content = build_full_project_html(title, files_html, files_css, files_js)
                    else:
                        html_content = files_html
                elif ws.get("html"):
                    html_content = ws["html"]
            elif ws.get("html"):
                html_content = ws["html"]

    safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title)
    file_bytes = html_content.encode('utf-8')
    file_size = len(file_bytes)
    file_name = f"{safe_title}.html"

    download_collection.insert_one({
        "user_email": email,
        "project_id": project_id,
        "title": title,
        "file_name": file_name,
        "file_type": "Standalone HTML",
        "file_size_bytes": file_size,
        "downloaded_at": datetime.utcnow()
    })

    _create_notification(
        email,
        "Website downloaded",
        f"{title} was downloaded as {file_name}.",
        "success",
        project_id=project_id,
    )

    return send_file(
        BytesIO(file_bytes),
        mimetype="text/html",
        as_attachment=True,
        download_name=file_name
    )

@app.route("/download/deploy/<project_id>", methods=["GET", "POST"])
def download_deploy(project_id):
    """Build a deployment-ready ZIP (website files + GitHub Pages/Netlify/Vercel configs)."""
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    try:
        project = project_collection.find_one({"_id": ObjectId(project_id), "user_email": email})
    except Exception:
        project = None

    if not project:
        return "Project not found", 404
    else:
        title = project.get("title", "NexusFlow_Project")
        files = {}
        ws = project.get("website_state") or {}
        if isinstance(ws, dict):
            ws_files = ws.get("files") or {}
            if isinstance(ws_files, dict) and ws_files:
                files = dict(ws_files)
            else:
                if ws.get("html"):
                    files["index.html"] = ws["html"]
                if ws.get("css"):
                    files["styles.css"] = ws["css"]
                if ws.get("javascript"):
                    files["script.js"] = ws["javascript"]
        # Fall back to flat fields for legacy projects
        if not files:
            html_code = project.get("html_code") or "<h1>Nexus Flow Website</h1>"
            css_code = project.get("css_code") or ""
            js_code = project.get("js_code") or ""
            files["index.html"] = html_code
            if css_code:
                files["styles.css"] = css_code
            if js_code:
                files["script.js"] = js_code

    from services.deployment_service import build_deploy_zip
    file_bytes, file_name = build_deploy_zip(files, title)

    download_collection.insert_one({
        "user_email": email,
        "project_id": project_id,
        "title": title,
        "file_name": file_name,
        "file_type": "Deploy Bundle",
        "file_size_bytes": len(file_bytes),
        "downloaded_at": datetime.utcnow()
    })

    _create_notification(
        email,
        "Website downloaded",
        f"{title} was downloaded as {file_name}.",
        "success",
        project_id=project_id,
    )

    return send_file(
        BytesIO(file_bytes),
        mimetype="application/zip",
        as_attachment=True,
        download_name=file_name
    )

@app.route("/downloads/delete/<download_id>", methods=["POST"])
def delete_download(download_id):
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        result = download_collection.delete_one({"_id": ObjectId(download_id), "user_email": session["email"]})
        if result.deleted_count == 0:
            return jsonify({"success": False, "error": "Record not found"}), 404

        return jsonify({"success": True, "message": "Download history record deleted."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/downloads/clear", methods=["POST"])
def clear_downloads():
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    email = session["email"]
    download_collection.delete_many({"user_email": email})
    return jsonify({"success": True, "message": "All download history cleared."})


# =========================================================
# NOTIFICATIONS (bell dropdown in the top nav bar)
# =========================================================

@app.route("/notifications", methods=["GET"])
def notifications_api():
    """Return the latest notifications + unread count for the logged-in user."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        docs = list(notification_collection.find(
            {"user_email": session["email"]}
        ).sort("created_at", -1).limit(30))
        unread = notification_collection.count_documents(
            {"user_email": session["email"], "read": False}
        )
        items = []
        for n in docs:
            ts = n.get("created_at")
            items.append({
                "id": str(n["_id"]),
                "title": n.get("title", ""),
                "message": n.get("message", ""),
                "type": n.get("type", "info"),
                "read": bool(n.get("read", False)),
                "project_id": n.get("project_id"),
                "created_at": ts.isoformat() + "Z" if isinstance(ts, datetime) else ""
            })
        return jsonify({"success": True, "notifications": items, "unread_count": unread})
    except Exception as e:
        print(f"[Notifications] list error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/notifications/read/<notif_id>", methods=["POST"])
def notifications_mark_read(notif_id):
    """Mark a single notification as read (ownership-checked)."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        res = notification_collection.update_one(
            {"_id": ObjectId(notif_id), "user_email": session["email"]},
            {"$set": {"read": True}}
        )
        unread = notification_collection.count_documents(
            {"user_email": session["email"], "read": False}
        )
        return jsonify({"success": True, "modified": res.modified_count > 0, "unread_count": unread})
    except Exception:
        return jsonify({"success": False, "error": "Invalid notification."}), 400


@app.route("/notifications/read-all", methods=["POST"])
def notifications_mark_all_read():
    """Mark every unread notification as read for the logged-in user."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    notification_collection.update_many(
        {"user_email": session["email"], "read": False},
        {"$set": {"read": True}}
    )
    return jsonify({"success": True, "unread_count": 0})


@app.route("/preview")
def preview_page():
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    user = user_collection.find_one({"email": email})
    state = get_current_website_state()
    return render_template("preview.html", user=user, state=state, active_page="preview")


@app.route("/code-editor")
def code_editor_page():
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    user = user_collection.find_one({"email": email})
    state = get_current_website_state()
    return render_template("code_editor.html", user=user, state=state, active_page="code-editor")


@app.route("/website-ai")
def website_ai_page():
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    user = user_collection.find_one({"email": email})
    state = get_current_website_state()
    return render_template("website_ai.html", user=user, state=state, active_page="website-ai")


@app.route("/jarvis")
def jarvis_page():
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    user = user_collection.find_one({"email": email})
    return render_template("jarvis.html", user=user, active_page="jarvis")


@app.route("/builder")
def builder_page():
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    user = user_collection.find_one({"email": email})
    state = get_current_website_state()
    project_id = request.args.get("project_id") or request.args.get("project") or None
    return render_template("builder.html", user=user, state=state, active_page="builder", initial_project_id=project_id)


@app.route("/code")
def code_page():
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    user = user_collection.find_one({"email": email})
    project_id = request.args.get("project_id") or request.args.get("project") or None
    return render_template("code.html", user=user, active_page="code", initial_project_id=project_id)


@app.route("/quality")
def quality_page():
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    user = user_collection.find_one({"email": email})
    project_id = request.args.get("project_id") or request.args.get("project") or None
    return render_template("quality.html", user=user, active_page="quality", initial_project_id=project_id)


@app.route("/preview/export")
def export_preview():
    if "email" not in session:
        return redirect(url_for("login"))

    state = get_current_website_state()
    preview_html = state.get("preview") or build_preview_document(state)
    return send_file(
        BytesIO(preview_html.encode("utf-8")),
        mimetype="text/html",
        as_attachment=True,
        download_name=f"{(state.get('website_name') or 'preview').replace(' ', '_')}.html"
    )


@app.route("/preview/<project_id>")
def isolated_preview(project_id):
    """
    Isolated preview route - returns ONLY the generated website HTML.
    No Nexus Flow templates, sidebar, or layout.
    """
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        project = project_collection.find_one({"_id": ObjectId(project_id), "user_email": session["email"]})
        if not project:
            return jsonify({"success": False, "error": "Project not found"}), 404

        html_code = project.get("html_code", "")
        if not html_code:
            return jsonify({"success": False, "error": "Project has no generated website"}), 404

        # Sanitize: remove any Nexus Flow Jinja template inheritance/sidebar includes
        sanitized_html = html_code
        sanitized_html = re.sub(r'{%\s*extends\s+["\']base\.html["\']\s*%}', '', sanitized_html)
        sanitized_html = re.sub(r'{%\s*include\s+["\'](?:components/)?sidebar\.html["\']\s*%}', '', sanitized_html)
        sanitized_html = re.sub(r'{%\s*[^%]*\s*%}', '', sanitized_html)
        sanitized_html = re.sub(r'\{\{\s*[^}]*\s*\}\}', '', sanitized_html)

        # Remove any Nexus Flow internal route references
        nexus_routes = r'/(?:builder|dashboard|login|register|profile|settings|projects|chat|admin|preview|code-editor|website-ai|home|logout|templates|downloads|camera)\b'
        sanitized_html = re.sub(r'href=["\']' + nexus_routes, 'href="#"', sanitized_html, flags=re.IGNORECASE)
        sanitized_html = re.sub(r'action=["\']' + nexus_routes, 'action="#"', sanitized_html, flags=re.IGNORECASE)

        # Return as text/html with no-cache headers
        response = make_response(sanitized_html)
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/preview/vite/<project_id>/")
@app.route("/preview/vite/<project_id>/<path:filepath>")
@app.route("/preview/<project_id>/")
@app.route("/preview/<project_id>/<path:filepath>")
def vite_preview(project_id, filepath=""):
    """
    Serve production build dist files through Flask to avoid CORS/iframe issues.
    Replaces direct Vite dev server iframe loading (localhost:5173) which was blocked.
    """
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    # Normalize filepath
    if filepath == "":
        filepath = "index.html"
    # Security: prevent path traversal
    if ".." in filepath or filepath.startswith("/") or "\\" in filepath:
        return jsonify({"success": False, "error": "Invalid path"}), 400
    try:
        # Check project exists in DB or filesystem
        try:
            from services.project_manager import project_exists
            if not project_exists(project_id):
                # Also check mongo for legacy projects
                proj = project_collection.find_one({"_id": ObjectId(project_id), "user_email": session["email"]}) if len(project_id)==24 else None
                if not proj:
                    return jsonify({"success": False, "error": "Project not found"}), 404
        except Exception:
            pass

        # Determine dist directory
        PROJECTS_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_projects")
        dist_dir = os.path.join(PROJECTS_ROOT, str(project_id), "dist")
        project_dir = os.path.join(PROJECTS_ROOT, str(project_id))

        # If dist not exists, try to build on demand (for preview)
        if not os.path.isdir(dist_dir):
            # Try to serve index.html from project root as fallback (for static projects)
            fallback_index = os.path.join(project_dir, "index.html")
            if os.path.isfile(fallback_index) and filepath == "index.html":
                response = send_from_directory(project_dir, "index.html")
                response.headers["X-Frame-Options"] = "ALLOWALL"
                response.headers["Access-Control-Allow-Origin"] = "*"
                response.headers["Cache-Control"] = "no-store"
                return response
            return jsonify({"success": False, "error": "Preview not built yet. Please generate and wait for build."}), 404

        # Serve requested file from dist, default to index.html for SPA routing
        full_path = os.path.join(dist_dir, filepath)
        if not os.path.isfile(full_path):
            # SPA fallback: serve index.html for unknown routes (React Router)
            if not os.path.splitext(filepath)[1]:  # no extension -> route
                response = send_from_directory(dist_dir, "index.html")
                response.headers["X-Frame-Options"] = "ALLOWALL"
                response.headers["Access-Control-Allow-Origin"] = "*"
                return response
            return jsonify({"success": False, "error": "File not found"}), 404

        response = send_from_directory(dist_dir, filepath)
        response.headers["X-Frame-Options"] = "ALLOWALL"
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Cache-Control"] = "no-store"
        # Ensure correct MIME for JS/CSS
        if filepath.endswith(".js"):
            response.headers["Content-Type"] = "application/javascript"
        elif filepath.endswith(".css"):
            response.headers["Content-Type"] = "text/css"
        return response
    except Exception as e:
        logger.error(f"[VitePreview] Failed to serve {project_id}/{filepath}: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/website_state/update", methods=["POST"])
def update_website_state():
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    email = session["email"]
    data = request.get_json() if request.is_json else request.form
    state = get_current_website_state()

    if isinstance(data, dict):
        if "website_name" in data:
            state["website_name"] = data.get("website_name", "") or state.get("website_name", "My AI Website")
        if "prompt" in data:
            state["prompt"] = data.get("prompt", "") or ""
        if "html" in data:
            state["html"] = data.get("html", "") or ""
        if "css" in data:
            state["css"] = data.get("css", "") or ""
        if "javascript" in data:
            state["javascript"] = data.get("javascript", "") or ""
        if "chat_history" in data:
            state["chat_history"] = data.get("chat_history", []) or []

    state = save_current_website_state(state)
    state["files"] = _extract_files_from_state(state)
    project_id = _save_builder_project(email, state, data.get("project_id") if isinstance(data, dict) else None)
    return jsonify({"success": True, "project_id": project_id, "state": state})


def build_fallback_site_bundle(category_key, user_prompt, website_name):
    ds = CATEGORY_DESIGN_SYSTEMS.get(category_key, CATEGORY_DESIGN_SYSTEMS["saas"])
    project_name = (website_name or "Nexus Flow").strip() or "Nexus Flow"
    prompt_text = (user_prompt or "Modern responsive website").strip() or "Modern responsive website"
    category_label = (category_key or "saas").replace("_", " ").title()

    if category_key == "restaurant":
        hero_title = f"A warm, memorable dining experience"
        hero_copy = f"{prompt_text} with a polished menu, elegant storytelling, and a booking-first experience that feels premium on every device."
        feature_items = [
            ("Curated menu", "Seasonal dishes and signature pairings displayed beautifully."),
            ("Reservations", "Fast booking flow for brunch, dinner, or private events."),
            ("Atmosphere", "Rich visuals and thoughtful micro-interactions that feel inviting.")
        ]
        service_items = [
            ("Chef's table", "Private experiences and tasting menus for special occasions."),
            ("Catering", "Elegant catering for corporate lunches and celebrations."),
            ("Events", "Private dining with dedicated hosting and room setup.")
        ]
    elif category_key == "portfolio":
        hero_title = f"A striking personal brand that sells your work"
        hero_copy = f"{prompt_text} designed to feel confident, modern, and conversion-oriented without sacrificing personality."
        feature_items = [
            ("Case studies", "Show your best work in a clean, story-driven layout."),
            ("About me", "Introduce your process, values, and background with clarity."),
            ("Contact", "Make it ridiculously easy for clients to reach out.")
        ]
        service_items = [
            ("Strategy", "Clear positioning, messaging, and creative direction."),
            ("Execution", "Thoughtful design systems and polished frontend work."),
            ("Launch", "Fast deployment support and follow-up iteration.")
        ]
    else:
        hero_title = f"A polished {category_label} experience"
        hero_copy = f"{prompt_text} featuring refined storytelling, premium visual hierarchy, and conversion-focused sections built to feel like a top-tier AI website builder output."
        feature_items = [
            ("Conversion-minded", "Every section is designed to guide visitors toward action."),
            ("Responsive by default", "Fluid layout systems that look sharp on mobile and desktop."),
            ("Refined visuals", "Glassmorphism, subtle gradients, and calm spacing for a premium feel.")
        ]
        service_items = [
            ("Strategy", "Clear messaging and a strong conversion narrative."),
            ("Experience", "Elegant interaction design with smooth transitions."),
            ("Launch", "A complete site ready for review, sharing, and iteration.")
        ]

    html = f"""<header class=\"site-header\">
  <div class=\"container nav-shell\">
    <a href=\"#top\" class=\"brand\"><span class=\"brand-mark\">✦</span>{project_name}</a>
    <nav class=\"nav-links\">
      <a href=\"#features\">Features</a>
      <a href=\"#about\">About</a>
      <a href=\"#services\">Services</a>
      <a href=\"#pricing\">Pricing</a>
      <a href=\"#faq\">FAQ</a>
    </nav>
    <a href=\"#contact\" class=\"nav-cta\">Book a demo</a>
  </div>
</header>

<main>
  <section id=\"top\" class=\"hero-section\">
    <div class=\"container hero-grid\">
      <div class=\"hero-copy\">
        <span class=\"pill\">{category_label} • Designed for impact</span>
        <h1>{hero_title}</h1>
        <p>{hero_copy}</p>
        <div class=\"hero-actions\">
          <a href=\"#pricing\" class=\"btn btn-primary\">Start free</a>
          <a href=\"#features\" class=\"btn btn-secondary\">See what’s included</a>
        </div>
      </div>
      <div class=\"hero-card\">
        <div class=\"hero-card-top\">
          <span>Live preview</span>
          <span class=\"status-dot\">●</span>
        </div>
        <div class=\"hero-card-body\">
          <h3>Polished, responsive, and ready</h3>
          <p>Built with modern layout systems, thoughtful typography, and clear calls to action.</p>
          <div class=\"mini-stats\">
            <div><strong>99.9%</strong><span>uptime</span></div>
            <div><strong>24/7</strong><span>support</span></div>
            <div><strong>10k+</strong><span>visitors</span></div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section id=\"features\" class=\"section\">
    <div class=\"container\">
      <div class=\"section-heading\">
        <p class=\"eyebrow\">Core strengths</p>
        <h2>Everything you need for a premium first impression</h2>
      </div>
      <div class=\"card-grid\">
        {''.join(f'<article class="feature-card"><h3>{title}</h3><p>{body}</p></article>' for title, body in feature_items)}
      </div>
    </div>
  </section>

  <section id=\"about\" class=\"section about-section\">
    <div class=\"container about-grid\">
      <div>
        <p class=\"eyebrow\">About</p>
        <h2>Designed to feel as refined as your brand</h2>
        <p>Every section is curated to make the experience feel intentional, modern, and conversion-ready.</p>
      </div>
      <div class=\"stats-grid\">
        <div class=\"stat-card\"><strong>99.9%</strong><span>Satisfaction</span></div>
        <div class=\"stat-card\"><strong>10K+</strong><span>Users</span></div>
        <div class=\"stat-card\"><strong>24/7</strong><span>Support</span></div>
      </div>
    </div>
  </section>

  <section id=\"services\" class=\"section\">
    <div class=\"container\">
      <div class=\"section-heading\">
        <p class=\"eyebrow\">Services</p>
        <h2>Flexible capabilities for modern products and brands</h2>
      </div>
      <div class=\"card-grid\">
        {''.join(f'<article class="feature-card"><h3>{title}</h3><p>{body}</p></article>' for title, body in service_items)}
      </div>
    </div>
  </section>

  <section id=\"pricing\" class=\"section\">
    <div class=\"container\">
      <div class=\"section-heading\">
        <p class=\"eyebrow\">Pricing</p>
        <h2>Simple plans for every stage of growth</h2>
      </div>
      <div class=\"pricing-grid\">
        <article class=\"pricing-card\"><h3>Starter</h3><p class=\"price\">$19<span>/mo</span></p><ul><li>One polished site</li><li>Fast publishing</li><li>Core analytics</li></ul><a href=\"#contact\" class=\"btn btn-secondary\">Get started</a></article>
        <article class=\"pricing-card featured\"><span class=\"featured-badge\">Most popular</span><h3>Pro</h3><p class=\"price\">$49<span>/mo</span></p><ul><li>Unlimited edits</li><li>Premium templates</li><li>Priority support</li></ul><a href=\"#contact\" class=\"btn btn-primary\">Choose Pro</a></article>
        <article class=\"pricing-card\"><h3>Enterprise</h3><p class=\"price\">Custom</p><ul><li>Advanced automation</li><li>Team collaboration</li><li>Custom onboarding</li></ul><a href=\"#contact\" class=\"btn btn-secondary\">Talk to sales</a></article>
      </div>
    </div>
  </section>

  <section class=\"section\">
    <div class=\"container\">
      <div class=\"section-heading\">
        <p class=\"eyebrow\">Testimonials</p>
        <h2>Trusted by teams that care about quality</h2>
      </div>
      <div class=\"card-grid\">
        <article class=\"feature-card\"><p>\"The quality felt premium from day one. It felt like a Framer-grade experience.\"</p><strong>— Maya, Product Lead</strong></article>
        <article class=\"feature-card\"><p>\"The layout felt polished, coherent, and incredibly easy to customize.\"</p><strong>— Jordan, Founder</strong></article>
        <article class=\"feature-card\"><p>\"It gave us a launch-ready site without the usual design bottlenecks.\"</p><strong>— Nina, Marketing Director</strong></article>
      </div>
    </div>
  </section>

  <section id=\"faq\" class=\"section\">
    <div class=\"container\">
      <div class=\"section-heading\">
        <p class=\"eyebrow\">FAQ</p>
        <h2>Questions teams ask before they launch</h2>
      </div>
      <div class=\"faq-list\">
        <div class=\"faq-item\"><button>Can I customize the design later?</button><p>Yes. The structure is easy to update with your own content, imagery, and brand details.</p></div>
        <div class=\"faq-item\"><button>Is the site responsive?</button><p>Absolutely. The layout adapts cleanly for phones, tablets, and desktops.</p></div>
        <div class=\"faq-item\"><button>Can I export it?</button><p>Yes. The builder can be saved, previewed, and downloaded as a complete static site.</p></div>
      </div>
    </div>
  </section>

  <section id=\"contact\" class=\"section\">
    <div class=\"container\">
      <div class=\"contact-card\">
        <div>
          <p class=\"eyebrow\">Contact</p>
          <h2>Ready to launch something beautiful?</h2>
          <p>Bring your idea to life with a premium site that feels thoughtful, polished, and ready to share.</p>
        </div>
        <form class=\"contact-form\">
          <input type=\"email\" placeholder=\"Email address\" />
          <button type=\"button\" class=\"btn btn-primary\">Request access</button>
        </form>
      </div>
    </div>
  </section>
</main>

<footer class=\"site-footer\">
  <div class=\"container footer-shell\">
    <p>© 2026 {project_name}. All rights reserved.</p>
    <div class=\"footer-links\">
      <a href=\"#features\">Features</a>
      <a href=\"#pricing\">Pricing</a>
      <a href=\"#faq\">FAQ</a>
    </div>
  </div>
</footer>"""

    css = f""":root {{
  --accent: {ds['accent']};
  --accent-gradient: {ds['gradient']};
  --bg: {ds['bg']};
  --card-bg: {ds['card_bg']};
  --border: {ds['border']};
  --text: {ds['text']};
  --muted: {ds['muted']};
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{ margin: 0; font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
a {{ color: inherit; text-decoration: none; }}
img {{ max-width: 100%; display: block; }}
.container {{ width: min(1180px, calc(100% - 2rem)); margin: 0 auto; }}
.site-header {{ position: sticky; top: 0; z-index: 50; background: rgba(9, 13, 22, 0.8); backdrop-filter: blur(18px); border-bottom: 1px solid rgba(255,255,255,0.08); }}
.nav-shell {{ display: flex; align-items: center; justify-content: space-between; padding: 1rem 0; gap: 1rem; }}
.brand {{ display: inline-flex; align-items: center; gap: 0.55rem; font-weight: 800; letter-spacing: -0.02em; }}
.brand-mark {{ display: inline-grid; place-items: center; width: 1.9rem; height: 1.9rem; border-radius: 999px; background: var(--accent-gradient); color: white; font-size: 0.95rem; }}
.nav-links {{ display: flex; gap: 1.25rem; color: var(--muted); }}
.nav-links a:hover, .footer-links a:hover {{ color: var(--text); }}
.nav-cta, .btn {{ display: inline-flex; align-items: center; justify-content: center; gap: 0.5rem; border-radius: 999px; padding: 0.8rem 1.2rem; font-weight: 700; transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease; }}
.nav-cta, .btn-primary {{ background: var(--accent-gradient); color: white; box-shadow: 0 10px 24px rgba(0,0,0,0.25); }}
.btn-secondary {{ border: 1px solid var(--border); background: rgba(255,255,255,0.04); color: var(--text); }}
.btn:hover, .nav-cta:hover {{ transform: translateY(-2px); }}
.hero-section {{ padding: 5rem 0 4rem; }}
.hero-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 2rem; align-items: center; }}
.pill, .eyebrow {{ display: inline-flex; align-items: center; gap: 0.45rem; width: fit-content; padding: 0.45rem 0.75rem; border-radius: 999px; background: rgba(255,255,255,0.06); border: 1px solid var(--border); color: var(--muted); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 1rem; }}
.hero-copy h1 {{ font-size: clamp(2.2rem, 4vw, 3.6rem); line-height: 1.05; margin: 0 0 1rem; letter-spacing: -0.03em; }}
.hero-copy p {{ color: var(--muted); font-size: 1.05rem; max-width: 640px; }}
.hero-actions {{ display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 1.75rem; }}
.hero-card {{ padding: 1.4rem; border-radius: 1.5rem; border: 1px solid var(--border); background: var(--card-bg); box-shadow: 0 24px 60px rgba(0,0,0,0.2); }}
.hero-card-top {{ display: flex; justify-content: space-between; align-items: center; color: var(--muted); font-size: 0.9rem; margin-bottom: 1rem; }}
.status-dot {{ color: var(--accent); }}
.hero-card-body {{ display: grid; gap: 0.75rem; }}
.hero-card-body h3 {{ margin: 0; }}
.hero-card-body p {{ margin: 0; color: var(--muted); }}
.mini-stats, .stats-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.75rem; }}
.mini-stats div, .stat-card {{ padding: 0.9rem; border-radius: 1rem; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); }}
.mini-stats strong, .stat-card strong {{ display: block; font-size: 1rem; }}
.mini-stats span, .stat-card span {{ color: var(--muted); font-size: 0.8rem; }}
.section {{ padding: 4rem 0; }}
.about-section {{ background: rgba(255,255,255,0.025); }}
.about-grid {{ display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 2rem; align-items: center; }}
.section-heading {{ max-width: 700px; margin-bottom: 1.75rem; }}
.section-heading h2 {{ font-size: clamp(1.6rem, 3vw, 2.2rem); margin: 0 0 0.6rem; letter-spacing: -0.02em; }}
.section-heading p, .about-grid p {{ color: var(--muted); }}
.card-grid, .pricing-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.2rem; }}
.feature-card, .pricing-card {{ padding: 1.4rem; border: 1px solid var(--border); border-radius: 1.2rem; background: var(--card-bg); }}
.feature-card:hover, .pricing-card:hover {{ transform: translateY(-3px); border-color: var(--accent); box-shadow: 0 12px 28px rgba(0,0,0,0.2); transition: all 180ms ease; }}
.feature-card h3, .pricing-card h3 {{ margin-top: 0; margin-bottom: 0.5rem; }}
.feature-card p, .pricing-card ul {{ color: var(--muted); }}
.pricing-card.featured {{ border-color: var(--accent); box-shadow: 0 16px 40px rgba(0,0,0,0.24); }}
.featured-badge {{ display: inline-block; margin-bottom: 0.7rem; color: var(--accent); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.16em; font-weight: 700; }}
.price {{ font-size: 2rem; font-weight: 800; margin: 0.4rem 0 1rem; }}
.price span {{ font-size: 1rem; color: var(--muted); }}
.pricing-card ul {{ padding-left: 1rem; display: grid; gap: 0.4rem; }}
.faq-list {{ display: grid; gap: 0.8rem; }}
.faq-item {{ padding: 1rem 1.2rem; border-radius: 1rem; border: 1px solid var(--border); background: rgba(255,255,255,0.03); }}
.faq-item button {{ background: none; border: 0; color: inherit; font-weight: 600; padding: 0; width: 100%; text-align: left; cursor: pointer; }}
.faq-item p {{ display: none; margin-bottom: 0; color: var(--muted); }}
.faq-item.open p {{ display: block; margin-top: 0.65rem; }}
.contact-card {{ display: flex; align-items: center; justify-content: space-between; gap: 1.3rem; padding: 1.8rem; border-radius: 1.5rem; border: 1px solid var(--border); background: linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03)); }}
.contact-form {{ display: flex; gap: 0.75rem; flex-wrap: wrap; }}
.contact-form input {{ border: 1px solid var(--border); background: rgba(255,255,255,0.05); color: var(--text); border-radius: 999px; padding: 0.8rem 1rem; min-width: 240px; }}
.site-footer {{ padding: 2rem 0 3rem; }}
.footer-shell {{ display: flex; justify-content: space-between; gap: 1rem; align-items: center; color: var(--muted); flex-wrap: wrap; }}
.footer-links {{ display: flex; gap: 1rem; }}
@media (max-width: 768px) {{
  .nav-links {{ display: none; }}
  .nav-shell {{ justify-content: space-between; }}
  .about-grid, .contact-card {{ grid-template-columns: 1fr; display: grid; }}
  .hero-section {{ padding-top: 3rem; }}
  .contact-form {{ flex-direction: column; }}
  .contact-form input {{ min-width: 0; }}
  .mini-stats, .stats-grid {{ grid-template-columns: 1fr; }}
}}"""

    javascript = """document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.faq-item button').forEach((button) => {
    button.addEventListener('click', () => {
      const item = button.parentElement;
      const isOpen = item.classList.contains('open');
      document.querySelectorAll('.faq-item').forEach((entry) => entry.classList.remove('open'));
      if (!isOpen) {
        item.classList.add('open');
      }
    });
  });
});"""

    return {"html": html, "css": css, "javascript": javascript, "message": f"Generated a polished {category_label} website for {project_name}."}


@app.route("/api/generate/fast", methods=["POST"])
def generate_fast():
    """Fast generate - PLACEHOLDER for new AI integration."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        data = request.get_json() if request.is_json else request.form
        prompt = (data.get("prompt") or "").strip()

        if not prompt:
            return jsonify({"success": False, "error": "Prompt cannot be empty."}), 400

        # PLACEHOLDER: New AI builder will be connected here
        return jsonify({
            "success": True,
            "status": "ready",
            "message": "AI Builder connection pending.",
            "html": "",
            "css": "",
            "js": "",
            "files": {"index.html": "", "styles.css": "", "script.js": ""},
            "project_id": None,
            "source": "placeholder",
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analyze-url", methods=["POST"])
def analyze_url():
    """Analyze URL - PLACEHOLDER for new AI integration."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify({
        "success": True,
        "status": "ready",
        "message": "AI Builder connection pending.",
        "analysis": {},
        "blueprint": {},
    })


@app.route("/api/component-library", methods=["GET"])
def component_library():
    """Component library - PLACEHOLDER for new AI integration."""
    return jsonify({
        "success": True,
        "status": "ready",
        "message": "AI Builder connection pending.",
        "components": [],
        "website_types": [],
    })


@app.route("/generate_website", methods=["POST"])
def generate_website():
    """Generate website - PLACEHOLDER for new AI integration."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        data = request.get_json() if request.is_json else request.form
        user_prompt = data.get("prompt", "").strip()
        website_name = (data.get("website_name") or "My AI Website").strip() or "My AI Website"

        if not user_prompt:
            return jsonify({"success": False, "error": "Prompt cannot be empty."}), 400

        # PLACEHOLDER: New AI builder will be connected here
        return jsonify({
            "success": True,
            "status": "ready",
            "message": "AI Builder connection pending.",
            "html": "",
            "css": "",
            "js": "",
            "javascript": "",
            "files": {"index.html": "", "styles.css": "", "script.js": ""},
            "category": "auto",
            "project_id": None,
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/ai-chat", methods=["POST"])
@app.route("/chat_website_edit", methods=["POST"])
def chat_website_edit():
    """AI chat edit - PLACEHOLDER for new AI integration."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify({
        "success": True,
        "status": "ready",
        "message": "AI Builder connection pending.",
        "reply": "AI Builder connection pending. New AI model will be integrated here.",
        "html": "", "css": "", "js": "", "javascript": "",
        "has_code_update": False, "project_id": None,
    })

@app.route("/save_builder_project", methods=["POST"])
def save_builder_project():
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    email = session["email"]
    data = request.get_json() if request.is_json else request.form

    state = get_current_website_state()
    state.update({
        "website_name": data.get("title", "").strip() or state.get("website_name", "AI Generated Website"),
        "prompt": data.get("prompt", "").strip() or state.get("prompt", "Modern responsive website"),
        "html": data.get("html", "") or state.get("html", ""),
        "css": data.get("css", "") or state.get("css", ""),
        "javascript": data.get("js", "") or state.get("javascript", "")
    })
    state["files"] = _extract_files_from_state(state)
    project_id = _save_builder_project(email, state, data.get("project_id"))
    _create_notification(
        email,
        "Project saved",
        f"\"{state.get('website_name') or 'My AI Website'}\" was saved successfully.",
        "success",
        project_id=project_id,
    )
    return jsonify({"success": True, "message": "Project saved to MongoDB!", "project_id": project_id})

# =========================================================
# UNIFIED AI BUILDER API
# Single source of truth: currentWebsiteState (html/css/js/files/chat_history)
# =========================================================

BUILDER_MODIFY_SYSTEM_PROMPT = """You are the Nexus Flow AI Website Builder. You modify an EXISTING website based on a new user request.

## CRITICAL MODIFICATION RULES
1. PRESERVE everything that already exists. Only change what the user explicitly asked for.
2. NEVER remove existing sections, components, content, or functionality unless the user asks to remove them.
3. Return COMPLETE updated files, not fragments. Each file you return must be the full, self-contained, working version.
4. If no change is needed for a file, still include it unchanged.
5. Maintain the existing design system, color scheme, fonts, and layout unless asked to change them.
6. Only generate the HTML body content (no <!DOCTYPE>, <html>, <head>, or <body> tags).

## OUTPUT FORMAT
Return ONLY a single valid JSON object matching this schema exactly:
{
  "html": "The complete, updated HTML body content, or an empty string if unchanged",
  "css": "The complete, updated CSS, or an empty string if unchanged",
  "javascript": "The complete, updated JavaScript (no <script> tags, no TypeScript), or an empty string if unchanged",
  "changed_files": ["List of filenames you actually changed, e.g. index.html, styles.css"],
  "message": "A short friendly reply to the user describing what was changed"
}
Do NOT include markdown fences (```json) or text outside the JSON object."""


def _is_usable_html(html_str):
    """A generated site is only usable when the HTML has real, renderable
    content. Empty shells (e.g. `<div id="app"></div>` with a JS router) render
    as a blank preview and must be rejected so generation retries / falls back."""
    if not html_str or not isinstance(html_str, str):
        return False
    stripped = html_str.strip()
    if not stripped:
        return False
    if len(stripped) < 40:
        return False
    if re.search(r'<div[^>]*id=["\']app["\'][^>]*>\s*</div>', stripped, re.I) and len(stripped) < 200:
        return False
    return True


def _build_fallback_site(website_name, prompt, spec=None, failure_reason=None):
    """Minimal, clean starter site used when the local model's output cannot be
    parsed into usable files, so the preview is never blank."""
    title = (website_name or "My AI Website").strip() or "My AI Website"
    desc = (prompt or "").strip() or "A modern website built with Nexus Flow."
    if failure_reason:
        desc += f" (Generated from template: {str(failure_reason)[:100]})"
    esc = lambda s: (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    # Turn the planning spec's pages into real fallback sections so the starter
    # site mirrors the user's request (hero, menu, gallery, about, contact...).
    sections_html = ""
    if isinstance(spec, dict):
        for idx, page in enumerate((spec.get("pages") or [])[:6]):
            if not isinstance(page, dict):
                continue
            pname = (page.get("name") or "").strip() or f"Section {idx + 1}"
            purpose = (page.get("purpose") or page.get("description") or "").strip()
            sid = re.sub(r"[^a-z0-9]+", "-", pname.lower()).strip("-") or f"section-{idx + 1}"
            sections_html += (
                f'\n  <section id="{sid}" class="section">\n'
                f'    <div class="container">\n'
                f'      <p class="eyebrow">{esc(pname)}</p>\n'
                f'      <h2>{esc(pname)}</h2>\n'
                f'      <p>{esc(purpose) or "This section is part of your website plan."}</p>\n'
                f'    </div>\n'
                f'  </section>'
            )

    html = """<header class="site-header">
  <div class="container nav-shell">
    <a href="#top" class="brand">{{TITLE}}</a>
    <nav class="nav-links">
      <a href="#about">About</a>
      <a href="#contact">Contact</a>
    </nav>
  </div>
</header>
<main>
  <section id="top" class="hero-section">
    <div class="container hero-grid">
      <h1>{{TITLE}}</h1>
      <p>{{DESC}}</p>
      <a href="#contact" class="btn">Get started</a>
    </div>
  </section>{{SECTIONS}}
  <section id="contact" class="section">
    <div class="container">
      <div class="contact-card">
        <p class="eyebrow">Contact</p>
        <h2>Get in touch</h2>
        <form class="contact-form">
          <input type="email" placeholder="Email address" />
          <button type="button" class="btn">Send</button>
        </form>
      </div>
    </div>
  </section>
</main>
<footer class="site-footer">
  <div class="container">&copy; 2026 {{TITLE}}</div>
</footer>"""
    html = html.replace("{{TITLE}}", esc(title)).replace("{{DESC}}", esc(desc)).replace("{{SECTIONS}}", sections_html)

    css = """:root {
  --accent: #6366f1;
  --bg: #0a0a12;
  --card-bg: rgba(255, 255, 255, 0.03);
  --border: rgba(255, 255, 255, 0.08);
  --text: #f8fafc;
  --muted: #94a3b8;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: Inter, system-ui, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }
a { color: inherit; text-decoration: none; }
.container { max-width: 1240px; margin: 0 auto; padding: 0 1.5rem; }
.site-header { padding: 1.25rem 0; border-bottom: 1px solid var(--border); }
.nav-shell { display: flex; justify-content: space-between; align-items: center; }
.brand { font-weight: 800; font-size: 1.25rem; color: var(--accent); }
.nav-links { display: flex; gap: 1.5rem; }
.hero-section { padding: 5rem 1.5rem; }
.hero-grid { display: grid; gap: 1.5rem; }
h1 { font-size: clamp(2rem, 5vw, 3.5rem); font-weight: 800; margin-bottom: 1rem; }
p { color: var(--muted); max-width: 560px; }
.btn { padding: 0.75rem 1.5rem; border-radius: 10px; font-weight: 600; background: var(--accent); color: #fff; display: inline-block; margin-top: 1.5rem; }
.section { padding: 4rem 1.5rem; border-top: 1px solid var(--border); }
.eyebrow { color: var(--accent); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.75rem; }
.contact-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 16px; padding: 2rem; }
.contact-form { display: flex; gap: 0.75rem; margin-top: 1rem; flex-wrap: wrap; }
.contact-form input { flex: 1; min-width: 220px; padding: 0.75rem 1rem; border-radius: 10px; border: 1px solid var(--border); background: transparent; color: var(--text); }
.site-footer { padding: 2rem 1.5rem; border-top: 1px solid var(--border); color: var(--muted); }"""
    return {"html": html, "css": css, "javascript": ""}


def _normalize_generated_files(files):
    """Map a raw files dict or FileList to (html, css, js).

    Handles flat names (index.html / styles.css / script.js),
    path-style keys produced by the framer prompt parser
    (css/style.css / js/main.js), and FileList/list of file dicts.
    """
    if isinstance(files, (list, tuple)) and not isinstance(files, dict):
        d = {}
        for item in files:
            if isinstance(item, dict):
                p = item.get("path") or item.get("filename") or item.get("name") or ""
                c = item.get("content", "")
                if p:
                    d[p] = c
        files = d
    elif not isinstance(files, dict):
        print(f"[Parser] _normalize_generated_files: unexpected type {type(files)}")
        logger.warning(f"[Parser] _normalize_generated_files: unexpected type {type(files)}")
        return "", "", ""

    html = files.get("index.html") or files.get("home.html") or ""
    css = (files.get("styles.css") or files.get("style.css") or files.get("main.css")
           or files.get("css/style.css") or files.get("css") or "")
    js = (files.get("script.js") or files.get("main.js") or files.get("app.js")
          or files.get("js/main.js") or files.get("javascript") or files.get("js") or "")
    return html, css, js


def _extract_files_from_state(state):
    """Return a stable files dict built from the current state."""
    files = dict(state.get("files") or {})
    files.setdefault("index.html", state.get("html") or "")
    files.setdefault("styles.css", state.get("css") or "")
    files.setdefault("script.js", state.get("javascript") or "")
    return files


def _save_builder_project(email, state, project_id=None):
    """Persist the unified website state to the projects collection."""
    title = (state.get("website_name") or "My AI Website").strip() or "My AI Website"
    prompt = (state.get("prompt") or "Modern responsive website").strip() or "Modern responsive website"
    status = (state.get("status") or "Active").strip() or "Active"

    # files is the single source of truth for the latest content (incl. manual edits)
    files = state.get("files") or {}
    if not isinstance(files, dict):
        files = {}
    html_code = files.get("index.html") or state.get("html", "") or ""
    css_code = files.get("styles.css") or state.get("css", "") or ""
    js_code = files.get("script.js") or state.get("javascript", "") or ""
    full_html = build_full_project_html(title, html_code, css_code, js_code)

    # ── Debug logging: trace what we're about to save ──────────────
    file_count = len([v for v in files.values() if isinstance(v, str) and v.strip()])
    file_names = [k for k, v in files.items() if isinstance(v, str) and v.strip()]
    print(f"[Writer] Preparing to save project: {title}")
    print(f"[Writer] Files in state: {file_count} ({', '.join(file_names[:10])})")
    print(f"[Writer] HTML content: {len(html_code)} chars, CSS: {len(css_code)} chars, JS: {len(js_code)} chars")
    logger.info(f"[Writer] Preparing to save project '{title}': {file_count} files ({', '.join(file_names[:10])})")

    state_copy = dict(state)
    state_copy.pop("project_id", None)
    state_copy["chat_history"] = state_copy.get("chat_history") or []
    if status:
        state_copy["status"] = status

    update_fields = {
        "title": title,
        "prompt": prompt,
        "html_code": full_html,
        "css_code": css_code,
        "js_code": js_code,
        "website_state": state_copy,
        "status": status,
        "updated_at": datetime.utcnow()
    }

    saved_id = project_id
    if project_id:
        try:
            res = project_collection.update_one(
                {"_id": ObjectId(project_id), "user_email": email},
                {"$set": update_fields}
            )
            if res.matched_count:
                _set_thumbnail_ref(project_id, email)
                saved_id = project_id
            else:
                saved_id = None
        except Exception:
            saved_id = None

    if not saved_id:
        new_doc = {
            "user_email": email,
            "title": title,
            "prompt": prompt,
            "html_code": full_html,
            "css_code": css_code,
            "js_code": js_code,
            "website_state": state_copy,
            "status": status,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        res = project_collection.insert_one(new_doc)
        saved_id = str(res.inserted_id)
        _set_thumbnail_ref(saved_id, email)

    print(f"[Writer] MongoDB saved: project_id={saved_id}")
    logger.info(f"[Writer] MongoDB saved: project_id={saved_id}")

    # Persist files to project storage on disk
    try:
        from services.website_generator import create_project, write_files
        if files:
            print(f"[Writer] Creating files on disk for project {saved_id}")
            logger.info(f"[Writer] Creating {len(files)} files on disk for project {saved_id}")
            create_project(str(saved_id), files, metadata={"title": title, "prompt": prompt, "user_email": email})
            print(f"[Writer] Files created successfully on disk")
            logger.info(f"[Writer] Files created successfully on disk")
        # Also mirror into project/generated/
        from services.filename_sanitizer import sanitize_filepath
        gen_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "project", "generated")
        os.makedirs(gen_dir, exist_ok=True)
        for fname, fcontent in files.items():
            if isinstance(fcontent, str) and fcontent:
                safe_name = sanitize_filepath(fname)
                fpath = os.path.join(gen_dir, safe_name)
                os.makedirs(os.path.dirname(fpath), exist_ok=True)
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(fcontent)
    except Exception as save_disk_err:
        logger.warning(f"[Save] Disk storage write warning: {save_disk_err}")
        print(f"[Writer] Disk storage warning: {save_disk_err}")

    # Verification: Validate that project files exist after saving
    saved_files = [f for f in ("index.html", "styles.css", "script.js") if f in files and files[f]]
    if not saved_files and not html_code:
        logger.error("Generation failed: No website files created")
        print("[Writer] ERROR: No website files created!")
        print(f"[Writer] files dict keys: {list(files.keys())}")
        print(f"[Writer] html_code length: {len(html_code)}")
        raise RuntimeError("Generation failed: No website files created")

    print(f"[6] Files saved successfully: {len(saved_files)} canonical files")
    logger.info(f"[6] Files saved: {saved_files}")

    return saved_id


def _set_thumbnail_ref(project_id, email):
    """Store the live-preview URL as the project's thumbnail reference."""
    try:
        project_collection.update_one(
            {"_id": ObjectId(project_id), "user_email": email},
            {"$set": {"thumbnail_ref": url_for("isolated_preview", project_id=project_id)}}
        )
    except Exception:
        pass


def _project_display_fields(project):
    """Enrich a raw project doc with display helpers for templates."""
    if not project or not isinstance(project, dict):
        # Return safe empty project to prevent Jinja UndefinedError
        return {
            "_id_str": "",
            "title": "Untitled Project",
            "prompt": "",
            "updated_at_fmt": "Recently",
            "updated_at_full": "Recently",
            "created_at_fmt": "Recently",
            "is_recent": False,
            "status": "Active",
            "thumbnail_ref": "",
            "has_website": False,
        }
    try:
        p = dict(project)
    except Exception:
        return {
            "_id_str": "",
            "title": "Untitled Project",
            "prompt": "",
            "updated_at_fmt": "Recently",
            "created_at_fmt": "Recently",
            "is_recent": False,
            "status": "Active",
            "thumbnail_ref": "",
            "has_website": False,
        }
    # Handle missing _id gracefully
    try:
        p["_id_str"] = str(p.get("_id", ""))
    except Exception:
        p["_id_str"] = ""
    now = datetime.utcnow()

    if p.get("updated_at") and isinstance(p["updated_at"], datetime):
        p["updated_at_fmt"] = p["updated_at"].strftime("%b %d, %Y")
        p["updated_at_full"] = p["updated_at"].strftime("%b %d, %Y, %I:%M %p")
        p["is_recent"] = (now - p["updated_at"]).days <= 7
    else:
        p["updated_at_fmt"] = "Recently"
        p["updated_at_full"] = "Recently"
        p["is_recent"] = False

    if p.get("created_at") and isinstance(p["created_at"], datetime):
        p["created_at_fmt"] = p["created_at"].strftime("%b %d, %Y")
    else:
        p["created_at_fmt"] = "Recently"

    p["status"] = (p.get("status") or "Active").strip() or "Active"
    p["thumbnail_ref"] = p.get("thumbnail_ref") or url_for("isolated_preview", project_id=p["_id_str"])
    p["has_website"] = bool(p.get("html_code") or (p.get("website_state") or {}).get("html"))
    return p


def _create_project_version(email, project_id, state, description="", force=False):
    """Snapshot the current project state into the project_versions collection.

    Returns the version number created, or None if nothing was saved.
    Auto-versioning is deduped (identical latest snapshot is skipped) unless
    force=True (explicit "Save Version" button).
    """
    if not project_id:
        return None

    # Ownership check first
    project = project_collection.find_one({"_id": ObjectId(project_id), "user_email": email})
    if not project:
        return None

    state = state if isinstance(state, dict) else (project.get("website_state") or {})
    files = state.get("files") or {}
    if not isinstance(files, dict):
        files = {}
    html_code = files.get("index.html") or state.get("html", "") or ""
    css_code = files.get("styles.css") or state.get("css", "") or ""
    js_code = files.get("script.js") or state.get("javascript", "") or ""

    latest = version_collection.find_one(
        {"project_id": project_id, "user_email": email},
        sort=[("version", -1)]
    )
    next_version = (latest.get("version", 0) if latest else 0) + 1

    if not force and latest:
        # Skip if content is identical to the latest snapshot
        same = (
            latest.get("html_code", "") == html_code
            and latest.get("css_code", "") == css_code
            and latest.get("js_code", "") == js_code
        )
        if same:
            return None

    version_doc = {
        "project_id": project_id,
        "user_email": email,
        "version": next_version,
        "html_code": html_code,
        "css_code": css_code,
        "js_code": js_code,
        "website_state": dict(state),
        "metadata": {
            "title": project.get("title", "My AI Website"),
            "prompt": project.get("prompt", ""),
            "status": project.get("status", "Active")
        },
        "description": (description or "Auto-saved snapshot").strip() or "Auto-saved snapshot",
        "created_at": datetime.utcnow()
    }
    version_collection.insert_one(version_doc)
    return next_version


def _restore_project_version(email, version_id):
    """Restore a project to a saved version. Returns the restored state.

    Only the version owner can restore (version is filtered by user_email,
    and the referenced project must also belong to the user).
    """
    version = version_collection.find_one({"_id": ObjectId(version_id), "user_email": email})
    if not version:
        return None

    project_id = version.get("project_id", "")
    project = project_collection.find_one({"_id": ObjectId(project_id), "user_email": email})
    if not project:
        return None

    state = version.get("website_state")
    if not isinstance(state, dict):
        state = get_default_website_state()
        state.update({
            "website_name": version.get("metadata", {}).get("title", "My AI Website"),
            "html": version.get("html_code", ""),
            "css": version.get("css_code", ""),
            "javascript": version.get("js_code", ""),
            "files": {}
        })
    else:
        state = dict(state)

    state["project_id"] = project_id
    state["files"] = _extract_files_from_state(state)
    state["chat_history"] = state.get("chat_history") or []

    title = version.get("metadata", {}).get("title") or project.get("title", "My AI Website")
    html_code = version.get("html_code") or state.get("html", "")
    css_code = version.get("css_code") or state.get("css", "")
    js_code = version.get("js_code") or state.get("javascript", "")

    project_collection.update_one(
        {"_id": ObjectId(project_id), "user_email": email},
        {"$set": {
            "title": title,
            "html_code": html_code,
            "css_code": css_code,
            "js_code": js_code,
            "website_state": state,
            "updated_at": datetime.utcnow()
        }}
    )
    _set_thumbnail_ref(project_id, email)
    return state


def _create_notification(email, title, message="", notif_type="info", project_id=None, unique=False):
    """Persist a notification for a user (best-effort, never breaks the caller).

    Types: info | success | warning | error. When unique=True, any existing
    unread notification with the same title is replaced so repeated failures
    (e.g. provider quota) don't spam the feed. Caps each user at 50 docs.
    """
    if not email:
        return None
    try:
        if unique:
            notification_collection.delete_many({"user_email": email, "title": title, "read": False})
        res = notification_collection.insert_one({
            "user_email": email,
            "title": title,
            "message": message or "",
            "type": notif_type,
            "read": False,
            "project_id": project_id or None,
            "created_at": datetime.utcnow()
        })
        try:
            extra = list(notification_collection.find(
                {"user_email": email}, {"_id": 1}
            ).sort("created_at", -1).skip(50))
            if extra:
                notification_collection.delete_many(
                    {"_id": {"$in": [d["_id"] for d in extra]}}
                )
        except Exception:
            pass
        return str(res.inserted_id)
    except Exception:
        return None


PROVIDER_UNAVAILABLE_MESSAGE = "Provider unavailable. Switch AI provider from settings."




@app.route("/builder/generate", methods=["POST"])
def builder_generate():
    """Generate a fresh website from a prompt - PLACEHOLDER for new AI integration."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        data = request.get_json() if request.is_json else request.form
        prompt = (data.get("prompt") or "").strip()
        website_name = (data.get("website_name") or "My AI Website").strip() or "My AI Website"

        if not prompt:
            return jsonify({"success": False, "error": "Prompt cannot be empty."}), 400

        # PLACEHOLDER: New AI builder will be connected here
        return jsonify({
            "success": True,
            "status": "ready",
            "message": "AI Builder connection pending. New AI model will be integrated here.",
            "html": "",
            "css": "",
            "js": "",
            "javascript": "",
            "files": {"index.html": "", "styles.css": "", "script.js": ""},
            "project_id": None,
            "chat_history": [],
            "preview": ""
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/builder/modify", methods=["POST"])
def builder_modify():
    """Modify the existing website - PLACEHOLDER for new AI integration."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        data = request.get_json() if request.is_json else request.form
        message = (data.get("message") or "").strip()

        if not message:
            return jsonify({"success": False, "error": "Message cannot be empty."}), 400

        # PLACEHOLDER: New AI builder will be connected here
        return jsonify({
            "success": True,
            "status": "ready",
            "message": "AI Builder connection pending. New AI model will be integrated here.",
            "reply": "Modification feature will be available once the new AI model is connected.",
            "html": data.get("html") or "",
            "css": data.get("css") or "",
            "js": data.get("js") or data.get("javascript") or "",
            "javascript": data.get("js") or data.get("javascript") or "",
            "files": data.get("files") or {},
            "changed_files": [],
            "chat_history": data.get("chat_history") or [],
            "project_id": data.get("project_id"),
            "preview": ""
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/builder/save", methods=["POST"])
def builder_save():
    """Save the current unified website state."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        data = request.get_json() if request.is_json else request.form
        state = data.get("state") or {}
        project_id = data.get("project_id") or None

        if not isinstance(state, dict) or not state:
            return jsonify({"success": False, "error": "No state provided."}), 400

        state["chat_history"] = state.get("chat_history") or []
        state["files"] = _extract_files_from_state(state)
        pid = _save_builder_project(session["email"], state, project_id)
        # Snapshot manual code edits into version history (deduped vs latest)
        version = _create_project_version(
            session["email"], pid, state,
            description="Manual save snapshot"
        )
        _create_notification(
            session["email"],
            "Project saved",
            f"\"{state.get('website_name') or 'My AI Website'}\" was saved successfully.",
            "success",
            project_id=pid,
        )
        return jsonify({
            "success": True,
            "project_id": pid,
            "version": version,
            "message": "Project saved successfully!"
        })

    except Exception as e:
        print(f"[Builder] save error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/builder/project/<project_id>", methods=["GET"])
def builder_get_project(project_id):
    """Load a saved project's full unified state for reopening in the builder."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        project = project_collection.find_one({"_id": ObjectId(project_id), "user_email": session["email"]})
        if not project:
            return jsonify({"success": False, "error": "Project not found"}), 404

        state = project.get("website_state")
        if not isinstance(state, dict):
            state = get_default_website_state()
            state.update({
                "website_name": project.get("title", "My AI Website"),
                "prompt": project.get("prompt", ""),
                "html": project.get("html_code", ""),
                "css": project.get("css_code", ""),
                "javascript": project.get("js_code", ""),
                "chat_history": []
            })
        else:
            state = dict(state)

        state["project_id"] = str(project["_id"])
        state["files"] = _extract_files_from_state(state)
        state["chat_history"] = state.get("chat_history") or []

        return jsonify({
            "success": True,
            "state": state,
            "project": {
                "id": str(project["_id"]),
                "title": project.get("title", "My AI Website"),
                "status": project.get("status", "Active"),
                "created_at": project.get("created_at").strftime("%b %d, %Y") if "created_at" in project and isinstance(project["created_at"], datetime) else "Recently",
                "updated_at": project.get("updated_at").strftime("%b %d, %Y, %I:%M %p") if "updated_at" in project and isinstance(project["updated_at"], datetime) else "Recently",
                "thumbnail_ref": project.get("thumbnail_ref") or url_for("isolated_preview", project_id=str(project["_id"]))
            }
        })

    except Exception as e:
        print(f"[Builder] load project error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/builder/version/create", methods=["POST"])
def builder_version_create():
    """Explicitly snapshot the current state as a new project version."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        data = request.get_json() if request.is_json else request.form
        project_id = data.get("project_id") or None
        state = data.get("state") or {}
        description = (data.get("description") or "").strip()

        if not project_id:
            return jsonify({"success": False, "error": "No project_id provided."}), 400
        if not isinstance(state, dict) or not state:
            return jsonify({"success": False, "error": "No state provided."}), 400

        state["files"] = _extract_files_from_state(state)
        state["chat_history"] = state.get("chat_history") or []
        version = _create_project_version(
            session["email"], project_id, state,
            description=description or "Manual snapshot",
            force=True
        )
        if version is None:
            return jsonify({"success": False, "error": "Project not found."}), 404
        return jsonify({"success": True, "version": version, "message": f"Version {version} saved successfully!"})

    except Exception as e:
        print(f"[Builder] version create error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/builder/versions/<project_id>", methods=["GET"])
def builder_versions(project_id):
    """List version history for a project (ownership enforced)."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        project = project_collection.find_one({"_id": ObjectId(project_id), "user_email": session["email"]})
        if not project:
            return jsonify({"success": False, "error": "Project not found"}), 404

        versions = list(version_collection.find(
            {"project_id": project_id, "user_email": session["email"]}
        ).sort("version", -1))

        result = []
        for v in versions:
            result.append({
                "id": str(v["_id"]),
                "version": v.get("version"),
                "description": v.get("description", ""),
                "created_at": v.get("created_at").strftime("%b %d, %Y, %I:%M %p")
                             if v.get("created_at") and isinstance(v["created_at"], datetime) else "Recently",
                "title": v.get("metadata", {}).get("title", project.get("title", "My AI Website"))
            })

        return jsonify({"success": True, "versions": result, "project_id": project_id})

    except Exception as e:
        print(f"[Builder] versions list error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/builder/version/<version_id>/restore", methods=["POST"])
def builder_version_restore(version_id):
    """Restore a project to a saved version and return the restored state."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        state = _restore_project_version(session["email"], version_id)
        if state is None:
            return jsonify({"success": False, "error": "Version not found"}), 404
        return jsonify({
            "success": True,
            "state": state,
            "project_id": state.get("project_id", ""),
            "preview": build_preview_document(state),
            "message": "Version restored successfully!"
        })

    except Exception as e:
        print(f"[Builder] version restore error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/admin")
def admin_dashboard():
    if "email" not in session:
        return redirect(url_for("login"))

    admin_user = user_collection.find_one({"email": session["email"]})
    
    # Gather aggregate counts from MongoDB
    total_users = user_collection.count_documents({})
    total_projects = project_collection.count_documents({})
    total_downloads = download_collection.count_documents({})
    total_chats = chat_collection.count_documents({})
    total_versions = version_collection.count_documents({})

    # Calculate total AI messages processed across chat documents
    chats_pipeline = [{"$project": {"message_count": {"$size": {"$ifNull": ["$messages", []]}}}}]
    try:
        ai_messages_count = sum(c.get("message_count", 0) for c in chat_collection.aggregate(chats_pipeline))
    except Exception:
        ai_messages_count = total_chats * 2

    search_query = request.args.get("search", "").strip()
    if search_query:
        query_filter = {
            "$or": [
                {"fullname": {"$regex": search_query, "$options": "i"}},
                {"email": {"$regex": search_query, "$options": "i"}}
            ]
        }
    else:
        query_filter = {}

    all_users = list(user_collection.find(query_filter))

    # Enrich users list with counts
    for u in all_users:
        u["_id_str"] = str(u["_id"])
        u_email = u.get("email", "")
        u["project_count"] = project_collection.count_documents({"user_email": u_email})
        u["download_count"] = download_collection.count_documents({"user_email": u_email})
        u["chat_count"] = chat_collection.count_documents({"user_email": u_email})
        u["version_count"] = version_collection.count_documents({"user_email": u_email})

    # Fetch recent system activity logs
    logs = list(log_collection.find().sort("timestamp", -1).limit(50))
    for log in logs:
        log["_id_str"] = str(log["_id"])
        if "timestamp" in log and isinstance(log["timestamp"], datetime):
            log["timestamp_fmt"] = log["timestamp"].strftime("%b %d, %Y %I:%M %p")
        else:
            log["timestamp_fmt"] = "Recently"

    # If log collection is empty, automatically construct initial audit log entries from project & download actions
    if not logs:
        recent_downloads = list(download_collection.find().sort("downloaded_at", -1).limit(10))
        recent_projects = list(project_collection.find().sort("created_at", -1).limit(10))
        
        sample_logs = []
        for d in recent_downloads:
            sample_logs.append({
                "timestamp_fmt": d.get("downloaded_at").strftime("%b %d, %Y %I:%M %p") if isinstance(d.get("downloaded_at"), datetime) else "Recently",
                "user_email": d.get("user_email", "System"),
                "action": "File Exported",
                "details": f"Downloaded {d.get('file_name', 'project file')} ({d.get('file_type', 'Archive')})",
                "status": "SUCCESS"
            })
        for p in recent_projects:
            sample_logs.append({
                "timestamp_fmt": p.get("created_at").strftime("%b %d, %Y %I:%M %p") if isinstance(p.get("created_at"), datetime) else "Recently",
                "user_email": p.get("user_email", "System"),
                "action": "Website Generated",
                "details": f"Created project '{p.get('title', 'Untitled')}'",
                "status": "SUCCESS"
            })
        logs = sample_logs

    return render_template(
        "admin.html",
        user=admin_user,
        total_users=total_users,
        total_projects=total_projects,
        total_downloads=total_downloads,
        total_chats=total_chats,
        total_versions=total_versions,
        ai_messages_count=ai_messages_count,
        users=all_users,
        logs=logs,
        search_query=search_query
    )

@app.route("/admin/search_users", methods=["GET"])
def admin_search_users():
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    query = request.args.get("query", "").strip()
    if query:
        filter_spec = {
            "$or": [
                {"fullname": {"$regex": query, "$options": "i"}},
                {"email": {"$regex": query, "$options": "i"}}
            ]
        }
    else:
        filter_spec = {}

    users = list(user_collection.find(filter_spec))
    users_data = []

    for u in users:
        u_email = u.get("email", "")
        users_data.append({
            "id": str(u["_id"]),
            "fullname": u.get("fullname", "User"),
            "email": u_email,
            "profile_image": u.get("profile_image", ""),
            "project_count": project_collection.count_documents({"user_email": u_email}),
            "download_count": download_collection.count_documents({"user_email": u_email}),
            "chat_count": chat_collection.count_documents({"user_email": u_email}),
            "version_count": version_collection.count_documents({"user_email": u_email})
        })

    return jsonify({"success": True, "users": users_data})

@app.route("/admin/delete_user/<user_id>", methods=["POST"])
def admin_delete_user(user_id):
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        user_to_delete = user_collection.find_one({"_id": ObjectId(user_id)})
        if not user_to_delete:
            return jsonify({"success": False, "error": "User not found."}), 404

        target_email = user_to_delete.get("email")

        # Prevent admin self-deletion if logged in
        if target_email == session.get("email"):
            return jsonify({"success": False, "error": "You cannot delete your active admin account."}), 400

        # Delete user and all associated MongoDB documents
        user_collection.delete_one({"_id": ObjectId(user_id)})
        if target_email:
            project_collection.delete_many({"user_email": target_email})
            download_collection.delete_many({"user_email": target_email})
            chat_collection.delete_many({"user_email": target_email})
            version_collection.delete_many({"user_email": target_email})

        # Log system audit entry
        log_collection.insert_one({
            "timestamp": datetime.utcnow(),
            "user_email": session.get("email", "Admin"),
            "action": "User Deleted",
            "details": f"Deleted user account: {target_email} ({user_to_delete.get('fullname')})",
            "status": "WARNING"
        })

        return jsonify({"success": True, "message": f"User {target_email} deleted successfully."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/admin/logs", methods=["GET"])
def admin_get_logs():
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    logs = list(log_collection.find().sort("timestamp", -1).limit(100))
    formatted_logs = []

    for l in logs:
        formatted_logs.append({
            "id": str(l["_id"]),
            "user": l.get("user_email", "System"),
            "action": l.get("action", "General Activity"),
            "details": l.get("details", ""),
            "status": l.get("status", "INFO"),
            "timestamp": l.get("timestamp").strftime("%b %d, %Y %I:%M %p") if isinstance(l.get("timestamp"), datetime) else "Recently"
        })

    return jsonify({"success": True, "logs": formatted_logs})

@app.route("/admin/logs/clear", methods=["POST"])
def admin_clear_logs():
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        from services.audit_service import clear_logs
        success = clear_logs()
        if success:
            return jsonify({"success": True, "message": "Audit logs cleared successfully."})
        return jsonify({"success": False, "error": "Failed to clear audit logs."}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ai/health", methods=["GET"])
def ai_health():
    """Report AI service readiness and the active provider (Groq > Gemini > DeepSeek)."""
    try:
        # Prefer new provider manager (Groq primary)
        try:
            from services.ai_provider_manager import get_provider_manager
            pm = get_provider_manager()
            active_p, active_m = pm.get_active_provider()
            chain = pm.get_fallback_chain()
            health = pm.get_model_status()
            if chain:
                return jsonify({
                    "status": "ok",
                    "model": active_m,
                    "provider": active_p,
                    "available": True,
                    "fallback_chain": chain,
                    "health": health,
                    "message": f"AI online via {active_p}/{active_m}",
                })
            # No chain => try legacy manager
        except Exception:
            pass
        manager = get_ai_manager()
        status = manager.get_provider_status()
        if status.get("success"):
            return jsonify({
                "status": "ok",
                "model": status.get("model"),
                "provider": manager.get_active_provider_name(),
                "available": True,
                "message": status.get("message", "AI is online."),
                "latency_ms": status.get("latency_ms", 0),
            })
        return jsonify({
            "status": "down",
            "model": None,
            "available": False,
            "message": status.get("message", "AI provider is unavailable."),
        }), 503
    except Exception as e:
        return jsonify({
            "status": "down",
            "model": None,
            "available": False,
            "message": f"AI health check failed: {e}",
        }), 503

@app.route("/api/ai/providers", methods=["GET"])
def ai_providers():
    """List providers and health (Groq > Gemini > DeepSeek)."""
    try:
        from services.ai_service import get_health
        return jsonify({"success": True, **get_health()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# =========================================================
# GENERATION PROGRESS ENDPOINTS
# =========================================================
@app.route("/api/generation/progress/<project_id>", methods=["GET"])
def generation_progress(project_id):
    """Generation progress - PLACEHOLDER."""
    return jsonify({"success": True, "progress": {"status": "ready", "message": "AI Builder connection pending."}})


@app.route("/api/generation/cancel/<project_id>", methods=["POST"])
def cancel_generation(project_id):
    """Cancel generation - PLACEHOLDER."""
    return jsonify({"success": True, "message": "AI Builder connection pending."})


@app.route("/api/generation/modes", methods=["GET"])
def generation_modes():
    """Generation modes - PLACEHOLDER."""
    return jsonify({"success": True, "modes": [], "current": "balanced"})


@app.route("/api/generation/cache/stats", methods=["GET"])
def generation_cache_stats():
    """Cache stats - PLACEHOLDER."""
    return jsonify({"success": True, "stats": {}})


@app.route("/api/generation/components", methods=["GET"])
def generation_components():
    """Components - PLACEHOLDER."""
    return jsonify({"success": True, "components": []})


@app.route("/api/generation/templates", methods=["GET"])
def generation_templates():
    """Templates - PLACEHOLDER."""
    return jsonify({"success": True, "templates": []})


# =========================================================
# REGISTER AI ROUTES BLUEPRINT (DISABLED - preparing for new AI builder)
# =========================================================
# from routes.ai_routes import register_ai_routes
# register_ai_routes(app, mongo_db)

# =========================================================
# REGISTER CODE QUALITY ANALYZER BLUEPRINT
# =========================================================
from routes.code_quality import register_code_quality_routes

register_code_quality_routes(app, mongo_db)

# =========================================================
# REGISTER AI BUILDER BLUEPRINT (NEW — real AI generation pipeline)
# =========================================================
from routes.builder_routes import register_builder_routes
register_builder_routes(app, mongo_db)

# REGISTER JARVIS AI ASSISTANT BLUEPRINT
# =========================================================
from routes.jarvis import register_jarvis_routes
register_jarvis_routes(app, mongo_db)

# =========================================================
# REGISTER ADMIN CONTROL CENTER BLUEPRINT
# =========================================================
from routes.admin_routes import register_admin_routes

register_admin_routes(app, mongo_db)

# =========================================================
# REGISTER FIGMA INTEGRATION BLUEPRINT (DISABLED - figma_service removed)
# =========================================================
try:
    from routes.figma_routes import register_figma_routes
    register_figma_routes(app, mongo_db)
except ImportError:
    pass

# =========================================================
# WIRE MULTI-AGENT AI SYSTEM (DISABLED - preparing for new AI builder)
# =========================================================
# from ai.agents.project_manager import configure as configure_multi_agent_system
# configure_multi_agent_system(mongo_db)

# =========================================================
# WIRE DASHBOARD SERVICE
# =========================================================
from services.dashboard_service import configure as configure_dashboard
configure_dashboard({
    "users": user_collection,
    "projects": project_collection,
    "downloads": download_collection,
    "chats": chat_collection,
    "project_versions": version_collection,
    "logs": log_collection,
})

# Wire generation cache (DISABLED - preparing for new AI builder)
# from services import generation_cache
# try:
#     generation_cache.set_cache_collection(generation_cache_collection)
# except Exception as e:
#     app.logger.warning(f"[Startup] Failed to wire generation cache: {e}")

# Wire LLM usage tracking (DISABLED - preparing for new AI builder)
# from services import llm_service
# try:
#     llm_service.set_usage_collection(mongo.db.llm_usage)
# except Exception as e:
#     app.logger.warning(f"[Startup] Failed to wire LLM usage collection: {e}")




@app.route("/api/generate-website", methods=["POST"])
def api_generate_website():
    """Generate website - PLACEHOLDER for new AI integration."""
    data = request.get_json() if request.is_json else request.form
    prompt = (data.get("prompt") or "").strip()
    website_name = (data.get("website_name") or "My AI Website").strip() or "My AI Website"

    if not prompt:
        return jsonify({"success": False, "error": "Prompt cannot be empty"}), 400

    # PLACEHOLDER: New AI builder will be connected here
    return jsonify({
        "success": True,
        "status": "ready",
        "message": "AI Builder connection pending.",
        "html": "",
        "css": "",
        "javascript": "",
        "js": "",
        "files": {"index.html": "", "styles.css": "", "script.js": ""},
        "file_list": ["index.html", "styles.css", "script.js"],
        "project_id": None,
        "preview": "",
        "reply": "AI Builder connection pending.",
        "model": "",
        "provider": "",
    })


@app.route("/api/project/<project_id>/files", methods=["GET"])
def api_get_project_files(project_id):
    """Return all files for a project for Code Preview."""
    try:
        if not re.match(r'^[a-zA-Z0-9_-]+$', project_id):
            return jsonify({"success": False, "error": "Invalid project ID", "files": []}), 400

        files_content = {}
        # 1. Check disk generated sites
        try:
            from services.website_generator import project_exists, read_all_files
            if project_exists(project_id):
                files_content = read_all_files(project_id)
        except Exception:
            pass

        # 2. Check MongoDB projects
        if not files_content or not any(files_content.values()):
            try:
                p = project_collection.find_one({"_id": ObjectId(project_id)})
                if p:
                    ws = p.get("website_state") or {}
                    files_content = ws.get("files") or {}
                    if not files_content:
                        files_content = {
                            "index.html": p.get("html_code", ""),
                            "styles.css": p.get("css_code", ""),
                            "script.js": p.get("js_code", "")
                        }
            except Exception:
                pass

        if not files_content or not any(files_content.values()):
            return jsonify({"success": False, "error": "No project files found", "files": []}), 404

        files_list = [
            {"name": name, "content": content}
            for name, content in sorted(files_content.items())
            if content is not None
        ]

        return jsonify({
            "success": True,
            "files": files_list,
            "file_list": list(files_content.keys()),
            "contents": files_content
        })
    except Exception as e:
        logger.error(f"Error in api_get_project_files: {e}")
        return jsonify({"success": False, "error": "Failed to load project files", "files": []}), 500


@app.route("/api/generate/stream", methods=["POST"])
def api_generate_stream():
    """SSE streaming endpoint - PLACEHOLDER for new AI integration."""
    from flask import Response, stream_with_context
    import json as _json

    data = request.get_json() if request.is_json else request.form
    prompt = (data.get("prompt") or "").strip()

    if not prompt:
        return jsonify({"success": False, "error": "Prompt cannot be empty"}), 400

    def generate_events():
        """Placeholder SSE events."""
        yield f"event: start\ndata: {_json.dumps({'prompt': prompt, 'status': 'ready'})}\n\n"
        yield f"event: done\ndata: {_json.dumps({'success': True, 'status': 'ready', 'message': 'AI Builder connection pending.'})}\n\n"

    return Response(
        stream_with_context(generate_events()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


# =========================================================
# NEXUS FLOW AI - DESIGN PLANNING LAYER
# Two-stage generation: Design Plan -> Code Generation
# =========================================================


@app.route("/api/design/plan", methods=["POST"])
def design_plan():
    """Design plan - PLACEHOLDER for new AI integration."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify({
        "success": True,
        "status": "ready",
        "message": "AI Builder connection pending.",
        "design_spec": {},
        "design_id": None,
    })


@app.route("/api/design/approve", methods=["POST"])
def design_approve():
    """Design approve - PLACEHOLDER for new AI integration."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify({
        "success": True,
        "status": "ready",
        "message": "AI Builder connection pending.",
        "files": {"index.html": "", "styles.css": "", "script.js": ""},
        "project_id": None,
    })


@app.route("/api/design/revise", methods=["POST"])
def design_revise():
    """Design revise - PLACEHOLDER for new AI integration."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify({
        "success": True,
        "status": "ready",
        "message": "AI Builder connection pending.",
        "design_spec": {},
    })


@app.route("/api/design/analyze-screenshot", methods=["POST"])
def analyze_screenshot_route():
    """Analyze screenshot - PLACEHOLDER for new AI integration."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify({
        "success": True,
        "status": "ready",
        "message": "AI Builder connection pending.",
        "design_reference": {},
        "planning_json": {},
    })


@app.route("/api/design/generate-from-screenshot", methods=["POST"])
def generate_from_screenshot():
    """Generate from screenshot - PLACEHOLDER for new AI integration."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify({
        "success": True,
        "status": "ready",
        "message": "AI Builder connection pending.",
        "files": {"index.html": "", "styles.css": "", "script.js": ""},
        "project_id": None,
    })


# =========================================================
# NEXUS FLOW AI WORKFLOW ROUTES
# =========================================================
# PROFESSIONAL WEBSITE DEVELOPMENT PIPELINE (PLACEHOLDER)
# Prompt -> Requirements -> Plan -> Design -> Approval -> Code -> Review -> Preview
# =========================================================


@app.route("/api/workflow/start", methods=["POST"])
def workflow_start():
    """Workflow start - PLACEHOLDER for new AI integration."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify({
        "success": True,
        "status": "ready",
        "message": "AI Builder connection pending.",
        "project_id": None,
        "stage": "ready",
    })


@app.route("/api/workflow/approve", methods=["POST"])
def workflow_approve():
    """Workflow approve - PLACEHOLDER for new AI integration."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify({
        "success": True,
        "status": "ready",
        "message": "AI Builder connection pending.",
        "files": {"index.html": "", "styles.css": "", "script.js": ""},
        "project_id": None,
    })


@app.route("/api/workflow/revise", methods=["POST"])
def workflow_revise():
    """Workflow revise - PLACEHOLDER for new AI integration."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify({
        "success": True,
        "status": "ready",
        "message": "AI Builder connection pending.",
        "project_id": None,
    })


@app.route("/api/workflow/status/<project_id>", methods=["GET"])
def workflow_status(project_id):
    """Workflow status - PLACEHOLDER for new AI integration."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify({
        "success": True,
        "status": "ready",
        "message": "AI Builder connection pending.",
        "pipeline": {},
    })


@app.route("/api/workflow/modify", methods=["POST"])
def workflow_modify():
    """Workflow modify - PLACEHOLDER for new AI integration."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify({
        "success": True,
        "status": "ready",
        "message": "AI Builder connection pending.",
        "files": {"index.html": "", "styles.css": "", "script.js": ""},
        "project_id": None,
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False
    )