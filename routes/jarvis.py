"""
Nexus Flow — Jarvis AI Development Assistant API Routes
Advanced assistant: chat, analyze, fix, modify, memory, context, models.
"""
import logging
from flask import Blueprint, jsonify, request, session

logger = logging.getLogger(__name__)

jarvis_bp = Blueprint("jarvis", __name__, url_prefix="/api/jarvis")


def register_jarvis_routes(app, mongo):
    """Register Jarvis AI routes with the Flask app."""
    # Ensure jarvis_memory collection exists (mock handles offline)
    try:
        if mongo is not None:
            # create index lazily
            try:
                mongo.jarvis_memory.create_index([("user_id", 1), ("project_id", 1)])
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"[Jarvis] index init: {e}")
    app.register_blueprint(jarvis_bp)
    logger.info("[Jarvis] AI assistant routes registered")


# -------------------------------------------------------------
# Helpers
# -------------------------------------------------------------
def _require_auth():
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return None

def _svc(project_id=None):
    from services.jarvis_service import JarvisService
    user_id = session.get("email")
    return JarvisService(user_id=user_id, project_id=project_id)


# -------------------------------------------------------------
# POST /api/jarvis/chat
# -------------------------------------------------------------
@jarvis_bp.route("/chat", methods=["POST"])
def jarvis_chat():
    """Advanced chat with project context, modes, memory."""
    auth = _require_auth()
    if auth: return auth
    if not request.is_json:
        return jsonify({"success": False, "error": "Content-Type must be application/json"}), 400
    try:
        data = request.get_json() or {}
    except Exception:
        return jsonify({"success": False, "error": "Invalid JSON"}), 400

    message = (data.get("message") or data.get("prompt") or "").strip()
    project_id = (data.get("project_id") or data.get("projectId") or "").strip() or None
    mode = (data.get("mode") or "chat").strip().lower()
    if mode not in ("chat","code","debug","analyze"):
        mode = "chat"
    if not message:
        return jsonify({"success": False, "error": "Message cannot be empty."}), 400

    try:
        svc = _svc(project_id)
        result = svc.chat(message, project_id=project_id, mode=mode, user_id=session.get("email"))
        return jsonify({
            "success": True,
            "response": result.get("response",""),
            "actions": result.get("actions",[]),
            "suggestions": result.get("suggestions",[]),
            "files_changed": result.get("files_changed",[]),
            "fixed_files": result.get("fixed_files",{}),
            "mode": result.get("mode",mode),
            "project_context": result.get("project_context",{}),
        })
    except Exception as e:
        logger.exception(f"[Jarvis] chat error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# -------------------------------------------------------------
# POST /api/jarvis/analyze
# -------------------------------------------------------------
@jarvis_bp.route("/analyze", methods=["POST"])
def jarvis_analyze():
    """Analyze generated files, build/preview/flask logs."""
    auth = _require_auth()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    project_id = (data.get("project_id") or data.get("projectId") or "").strip() or None
    # allow query param fallback
    if not project_id:
        project_id = (request.args.get("project_id") or "").strip() or None
    try:
        svc = _svc(project_id)
        analysis = svc.analyze_project(project_id)
        return jsonify({"success": True, **analysis})
    except Exception as e:
        logger.exception(f"[Jarvis] analyze error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@jarvis_bp.route("/analyze-project", methods=["POST"])
def jarvis_analyze_alias():
    return jarvis_analyze()


# -------------------------------------------------------------
# POST /api/jarvis/fix
# -------------------------------------------------------------
@jarvis_bp.route("/fix", methods=["POST"])
def jarvis_fix():
    """Fix errors: build, preview, generation, quota."""
    auth = _require_auth()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    error = (data.get("error") or data.get("error_log") or data.get("message") or "").strip()
    project_id = (data.get("project_id") or data.get("projectId") or "").strip() or None
    if not error:
        return jsonify({"success": False, "error": "error field required"}), 400
    try:
        svc = _svc(project_id)
        result = svc.fix_error(error, project_id=project_id)
        return jsonify({"success": True, **result})
    except Exception as e:
        logger.exception(f"[Jarvis] fix error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# -------------------------------------------------------------
# POST /api/jarvis/modify
# -------------------------------------------------------------
@jarvis_bp.route("/modify", methods=["POST"])
def jarvis_modify():
    """Modify website: prompt -> find files -> modify -> return updated files."""
    auth = _require_auth()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    req = (data.get("request") or data.get("message") or data.get("prompt") or "").strip()
    project_id = (data.get("project_id") or data.get("projectId") or "").strip() or None
    if not req:
        return jsonify({"success": False, "error": "request field required (e.g. Change navbar color to purple)"}), 400
    if not project_id:
        return jsonify({"success": False, "error": "project_id required"}), 400
    try:
        svc = _svc(project_id)
        result = svc.modify_project(req, project_id=project_id)
        if "error" in result and not result.get("fixed_files"):
            return jsonify({"success": False, **result}), 400
        return jsonify({"success": True, **result})
    except Exception as e:
        logger.exception(f"[Jarvis] modify error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# -------------------------------------------------------------
# GET /api/jarvis/context
# -------------------------------------------------------------
@jarvis_bp.route("/context", methods=["GET"])
def jarvis_context():
    auth = _require_auth()
    if auth: return auth
    project_id = (request.args.get("project_id") or "").strip() or None
    try:
        svc = _svc(project_id)
        ctx = svc._build_project_context(project_id)
        return jsonify({"success": True, "context": ctx})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# -------------------------------------------------------------
# GET /api/jarvis/memory
# -------------------------------------------------------------
@jarvis_bp.route("/memory", methods=["GET"])
def jarvis_memory():
    auth = _require_auth()
    if auth: return auth
    project_id = (request.args.get("project_id") or "").strip() or None
    try:
        svc = _svc(project_id)
        mem = svc.get_memory(user_id=session.get("email"), project_id=project_id)
        # hide _id for json
        if "_id" in mem:
            mem["_id"] = str(mem["_id"])
        return jsonify({"success": True, "memory": mem})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@jarvis_bp.route("/history", methods=["GET"])
def jarvis_history():
    return jarvis_memory()


# -------------------------------------------------------------
# Projects list
# -------------------------------------------------------------
@jarvis_bp.route("/projects", methods=["GET"])
def jarvis_projects():
    auth = _require_auth()
    if auth: return auth
    try:
        from services.mongo_connection import get_db
        db = get_db()
        email = session.get("email")
        projects = list(db.projects.find({"user_email": email}).sort("updated_at", -1).limit(30))
        out = []
        for p in projects:
            out.append({
                "id": str(p.get("_id")),
                "title": p.get("title","Untitled"),
                "prompt": (p.get("prompt","")[:80]),
                "status": p.get("status","Active"),
                "updated_at": p.get("updated_at").isoformat() if hasattr(p.get("updated_at"),"isoformat") else ""
            })
        return jsonify({"success": True, "projects": out})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# -------------------------------------------------------------
# Explain code
# -------------------------------------------------------------
@jarvis_bp.route("/explain", methods=["POST"])
def jarvis_explain():
    auth = _require_auth()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    file_path = (data.get("file_path") or data.get("file") or "").strip() or None
    code = data.get("code") or None
    project_id = (data.get("project_id") or "").strip() or None
    if not file_path and not code:
        return jsonify({"success": False, "error": "file_path or code required"}), 400
    try:
        svc = _svc(project_id)
        result = svc.explain_code(file_path=file_path, code=code, project_id=project_id)
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# -------------------------------------------------------------
# Models
# -------------------------------------------------------------
@jarvis_bp.route("/models", methods=["GET"])
def jarvis_models():
    auth = _require_auth()
    if auth: return auth
    try:
        from services.jarvis_service import get_available_models
        from services.llm_service import get_active_model
        models = get_available_models()
        active_provider, active_model = get_active_model()
        return jsonify({"success": True, "models": models, "active": {"provider": active_provider, "model": active_model}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@jarvis_bp.route("/model/select", methods=["POST"])
def jarvis_select_model():
    auth = _require_auth()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    provider = (data.get("provider") or "").strip()
    model = (data.get("model") or "").strip()
    if not provider or not model:
        return jsonify({"success": False, "error": "provider and model required"}), 400
    try:
        from services.llm_service import set_active_model
        ok = set_active_model(provider, model)
        if not ok:
            return jsonify({"success": False, "error": "Failed to set model (disabled or not found)"}), 400
        return jsonify({"success": True, "message": f"Switched to {provider}/{model}", "provider": provider, "model": model})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# -------------------------------------------------------------
# Apply pending changes (approval workflow)
# -------------------------------------------------------------
@jarvis_bp.route("/apply", methods=["POST"])
def jarvis_apply():
    """Apply pending file changes after user approved."""
    auth = _require_auth()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    project_id = (data.get("project_id") or "").strip() or None
    fixed_files = data.get("fixed_files") or data.get("files") or {}
    if not project_id:
        return jsonify({"success": False, "error": "project_id required"}), 400
    if not isinstance(fixed_files, dict) or not fixed_files:
        return jsonify({"success": False, "error": "fixed_files required"}), 400
    try:
        svc = _svc(project_id)
        ok = svc._apply_file_changes(project_id, fixed_files)
        if not ok:
            return jsonify({"success": False, "error": "Failed to apply"}), 500
        return jsonify({"success": True, "applied": list(fixed_files.keys()), "message": "Changes applied"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# -------------------------------------------------------------
# Health (legacy)
# -------------------------------------------------------------
@jarvis_bp.route("/health", methods=["GET"])
def jarvis_health():
    """Health check for Jarvis AI. Always returns JSON."""
    try:
        from services.llm_service import get_provider
        provider = get_provider()
        # provider may be None
        name = getattr(provider, 'name', None) or getattr(provider, 'provider', 'unknown')
        if isinstance(provider, dict):
            name = provider.get("name","unknown")
        return jsonify({
            "success": True,
            "status": "online",
            "provider": str(name),
        })
    except Exception as e:
        # fallback to active model
        try:
            from services.llm_service import get_active_model
            p,m = get_active_model()
            return jsonify({"success": True, "status": "online", "provider": p, "model": m})
        except Exception:
            return jsonify({
                "success": False,
                "status": "offline",
                "error": str(e),
            })
