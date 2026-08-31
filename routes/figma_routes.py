"""Nexus Flow - Figma Integration Routes.

Flask blueprint exposing Figma OAuth and design import APIs:

    GET  /api/figma/status          - Connection status
    GET  /api/figma/connect         - Redirect to Figma OAuth
    GET  /api/figma/callback        - OAuth callback (receives code)
    POST /api/figma/disconnect      - Remove connection
    POST /api/figma/import          - Import and analyze a Figma file
    POST /api/figma/generate        - Generate website from Figma design
"""
import json
import logging
import sys
import uuid

import requests
from flask import Blueprint, jsonify, request, session, redirect, current_app

_root_dir = __file__.rsplit("\\", 2)[0] if "\\" in __file__ else __file__.rsplit("/", 2)[0]
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from config.figma_config import is_configured, FIGMA_REDIRECT_URI
from services import figma_service

logger = logging.getLogger(__name__)

figma_bp = Blueprint("figma", __name__, url_prefix="/api/figma")


def _require_login():
    return "email" in session


# ── Connection Status ───────────────────────────────────────
@figma_bp.route("/status", methods=["GET"])
def figma_status():
    """GET /api/figma/status - Check Figma connection status."""
    if not _require_login():
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    email = session["email"]
    configured = is_configured()
    connected = figma_service.is_connected(email) if configured else False

    result = {
        "success": True,
        "configured": configured,
        "connected": connected,
    }

    if connected:
        conn = figma_service.get_connection(email)
        if conn:
            result["username"] = conn.get("figma_username", "")
            result["email"] = conn.get("figma_email", "")

    return jsonify(result), 200


# ── OAuth Connect ───────────────────────────────────────────
@figma_bp.route("/connect", methods=["GET"])
def figma_connect():
    """GET /api/figma/connect - Redirect to Figma OAuth authorization."""
    if not _require_login():
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    if not is_configured():
        return jsonify({
            "success": False,
            "error": "Figma OAuth not configured",
            "message": "Set FIGMA_CLIENT_ID and FIGMA_CLIENT_SECRET in your .env file.",
        }), 503

    state = uuid.uuid4().hex
    session["figma_oauth_state"] = state
    session["figma_oauth_email"] = session["email"]

    auth_url = figma_service.get_oauth_authorize_url(state)
    return redirect(auth_url)


# ── OAuth Callback ──────────────────────────────────────────
@figma_bp.route("/callback", methods=["GET"])
def figma_callback():
    """GET /api/figma/callback - Handle Figma OAuth callback.

    Exchanges the authorization code for an access token and stores it.
    """
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    if error:
        logger.warning("[Figma] OAuth callback error: %s", error)
        return redirect("/settings?tab=tab-integrations&figma_error=%s" % error)

    if not code:
        logger.warning("[Figma] OAuth callback missing code")
        return redirect("/settings?tab=tab-integrations&figma_error=no_code")

    # Validate state
    expected_state = session.pop("figma_oauth_state", None)
    user_email = session.pop("figma_oauth_email", None)

    if not expected_state or state != expected_state:
        logger.warning("[Figma] OAuth state mismatch")
        return redirect("/settings?tab=tab-integrations&figma_error=invalid_state")

    if not user_email:
        logger.warning("[Figma] OAuth callback missing session")
        return redirect("/settings?tab=tab-integrations&figma_error=no_session")

    try:
        logger.info("[Figma] Exchanging code for token...")
        token_data = figma_service.exchange_code_for_token(code)

        figma_service.save_connection(user_email, token_data, {})
        try:
            user_info = figma_service.get_figma_user(user_email)
            figma_service.save_connection(user_email, token_data, user_info)
            logger.info("[Figma] Connected: %s", user_info.get("handle", "unknown"))
        except Exception:
            logger.info("[Figma] Connected (no user info)")
            pass

        return redirect("/settings?tab=tab-integrations&figma_success=connected")
    except Exception as e:
        logger.error("[Figma] Callback error: %s", e)
        figma_service.remove_connection(user_email)
        return redirect("/settings?tab=tab-integrations&figma_error=token_exchange_failed")


# ── Disconnect ──────────────────────────────────────────────
@figma_bp.route("/disconnect", methods=["POST"])
def figma_disconnect():
    """POST /api/figma/disconnect - Remove Figma connection."""
    if not _require_login():
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    email = session["email"]
    figma_service.remove_connection(email)
    return jsonify({"success": True, "message": "Figma disconnected."}), 200


# ── Import Figma File ───────────────────────────────────────
@figma_bp.route("/import", methods=["POST"])
def figma_import():
    """POST /api/figma/import - Import and analyze a Figma file.

    Body: { "url": "https://www.figma.com/design/..." }
    or:   { "file_key": "abc123..." }
    """
    if not _require_login():
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    email = session["email"]

    if not figma_service.is_connected(email):
        return jsonify({
            "success": False,
            "error": "Figma not connected",
            "message": "Connect your Figma account first.",
        }), 400

    data = request.get_json(silent=True) or {}
    url = data.get("url", "")
    file_key = data.get("file_key", "")

    if not file_key and url:
        file_key = figma_service.extract_file_key_from_url(url)

    if not file_key:
        return jsonify({
            "success": False,
            "error": "Invalid input",
            "message": "Provide a valid Figma URL or file key.",
        }), 400

    try:
        file_data = figma_service.get_figma_file(email, file_key)
        analysis = figma_service.analyze_figma_file(file_data)
        blueprint = figma_service.build_design_blueprint(analysis, data.get("name"))

        return jsonify({
            "success": True,
            "file_key": file_key,
            "file_name": file_data.get("name", "Untitled"),
            "analysis": analysis,
            "blueprint": blueprint,
        }), 200
    except RuntimeError as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": str(e),
        }), 400
    except Exception as e:
        logger.error("[Figma] Import error: %s", e)
        return jsonify({
            "success": False,
            "error": "Failed to import Figma file",
            "message": "An error occurred while fetching the Figma file.",
        }), 500


# ── Generate Website from Figma ─────────────────────────────
@figma_bp.route("/generate", methods=["POST"])
def figma_generate():
    """POST /api/figma/generate - Generate website from Figma design blueprint.

    Body: { "blueprint": {...}, "website_name": "...", "project_id": "..." }
    """
    if not _require_login():
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    email = session["email"]
    data = request.get_json(silent=True) or {}

    blueprint = data.get("blueprint")
    if not blueprint:
        return jsonify({
            "success": False,
            "error": "No blueprint provided",
            "message": "Analyze a Figma file first.",
        }), 400

    website_name = data.get("website_name", "My Figma Website")
    project_id = data.get("project_id")

    # Build a generation prompt from the blueprint
    prompt = _blueprint_to_prompt(blueprint, website_name)

    try:
        # Use the existing generation pipeline
        from app import _generate_website_state
        result = _generate_website_state(
            prompt=prompt,
            website_name=website_name,
            user_email=email,
            project_id=project_id,
        )
        return jsonify({
            "success": True,
            "project_id": result.get("project_id"),
            "reply": "Website generated from Figma design!",
        }), 200
    except Exception as e:
        logger.error("[Figma] Generation error: %s", e)
        return jsonify({
            "success": False,
            "error": "Generation failed",
            "message": str(e),
        }), 500


def _blueprint_to_prompt(blueprint, website_name):
    """Convert a design blueprint into a generation prompt."""
    style = blueprint.get("designStyle", "Modern")
    components = blueprint.get("components", [])
    colors = blueprint.get("colors", [])
    typography = blueprint.get("typography", {})
    pages = blueprint.get("pages", [])

    parts = [
        "Create a %s website named '%s'." % (style.lower(), website_name),
    ]

    if components:
        parts.append("Include these sections: %s." % ", ".join(components))

    if colors:
        parts.append("Use this color palette: %s." % ", ".join(colors[:5]))

    if typography:
        heading_font = typography.get("heading", "")
        body_font = typography.get("body", "")
        if heading_font:
            parts.append("Heading font: %s." % heading_font)
        if body_font:
            parts.append("Body font: %s." % body_font)

    if pages:
        page_names = [p.get("name", "") for p in pages if p.get("name")]
        if page_names:
            parts.append("Pages: %s." % ", ".join(page_names))

    parts.append("Make it responsive, professional, and production-ready.")

    return " ".join(parts)


# ── Registration ────────────────────────────────────────────
def register_figma_routes(app, mongo_instance):
    """Register the Figma integration blueprint with the Flask app."""
    figma_service.configure(mongo_instance)
    app.register_blueprint(figma_bp)
    print("[Figma] Figma integration routes registered.")
