"""Nexus Flow - Code Quality Analyzer routes.

Flask blueprint exposing the ML-based code quality analyzer as a JSON API:

    POST /api/code-quality/analyze
        body: {"html": "...", "css": "...", "javascript": "..."}
        ->   ML analysis result (score, level, confidence, features, issues)

    GET  /api/code-quality/project/<project_id>
        ->   the latest analysis stored for the user's project

Security notes
--------------
- The HTML/CSS/JS payload is treated as plain text for static analysis. It is
  NEVER executed, never saved to the filesystem, and never passed to a shell.
- Payloads are size-limited and type-checked before analysis.
- No filesystem paths or internal tracebacks are returned to the frontend.
"""

from datetime import datetime

from bson.objectid import ObjectId
from flask import Blueprint, jsonify, request, session

from ml.predict import ModelNotReadyError, analyze_code

MAX_CODE_LENGTH = 1_000_000  # per field
MAX_TOTAL_LENGTH = 3_000_000  # combined
MAX_ISSUES_RETURNED = 40

code_quality_bp = Blueprint("code_quality", __name__, url_prefix="/api/code-quality")

# Set by register_code_quality_routes() in app.py
code_quality_collection = None


def _collection():
    global code_quality_collection
    return code_quality_collection


def _require_login():
    return "email" in session


def _validate_payload(data):
    """Validate the submitted code payload.

    Returns (html, css, js) or raises ValueError with a user-safe message.
    """
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")

    html = data.get("html", "")
    css = data.get("css", "")
    js = data.get("javascript", data.get("js", ""))

    for name, value in (("html", html), ("css", css), ("javascript", js)):
        if not isinstance(value, str):
            raise ValueError("Field %r must be a string." % name)
        if len(value) > MAX_CODE_LENGTH:
            raise ValueError("Field %r exceeds the maximum allowed size." % name)

    if len(html) + len(css) + len(js) > MAX_TOTAL_LENGTH:
        raise ValueError("Combined code payload exceeds the maximum allowed size.")

    if not (html.strip() or css.strip() or js.strip()):
        raise ValueError("No code provided. Send html, css and/or javascript text.")
    return html, css, js


def _build_analysis_response(result, project_id=None, persist=True):
    """Attach success metadata and optionally store the analysis in MongoDB."""
    issues = result.get("issues", [])
    if isinstance(issues, list) and len(issues) > MAX_ISSUES_RETURNED:
        issues = issues[:MAX_ISSUES_RETURNED]
        result["issues"] = issues

    email = session.get("email")
    saved_id = None
    if persist and _collection() is not None:
        try:
            doc = {
                "project_id": project_id,
                "user_email": email,
                "quality_score": result.get("quality_score"),
                "quality_level": result.get("quality_level"),
                "model_quality_level": result.get("model_quality_level"),
                "confidence": result.get("confidence"),
                "features": result.get("features", {}),
                "issues": issues,
                "sections": result.get("sections", []),
                "analyzed_at": datetime.utcnow(),
            }
            res = _collection().insert_one(doc)
            saved_id = str(res.inserted_id)
        except Exception as exc:
            # Analysis must not fail because the audit log is unavailable.
            print("[CodeQuality] could not persist analysis: %s" % exc)

    payload = {"success": True, **result}
    if saved_id:
        payload["analysis_id"] = saved_id
    if project_id:
        payload["project_id"] = project_id
    return jsonify(payload), 200


@code_quality_bp.route("/analyze", methods=["POST"])
def analyze():
    """POST /api/code-quality/analyze"""
    if not _require_login():
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        data = request.get_json(silent=True) if request.is_json else {}
        if not isinstance(data, dict):
            return jsonify({"success": False, "error": "Invalid JSON payload."}), 400

        html, css, js = _validate_payload(data)
        project_id = data.get("project_id")

        result = analyze_code(html, css, js)
        return _build_analysis_response(result, project_id=project_id)

    except ValueError as e:
        print("[CodeQuality] Validation error: %s" % e)
        return jsonify({"success": False, "error": str(e)}), 400
    except ModelNotReadyError as e:
        print("[CodeQuality] Model not ready: %s" % e)
        return jsonify({
            "success": False,
            "error": "Code quality analyzer unavailable",
            "message": "The ML model has not been trained yet. Run `python ml/train_model.py`.",
        }), 503
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("[CodeQuality] Analysis failed: %s" % e)
        return jsonify({
            "success": False,
            "error": "Code quality analysis failed",
            "message": "An internal error occurred while analyzing the code.",
        }), 500


@code_quality_bp.route("/fix", methods=["POST"])
def fix_bugs():
    """POST /api/code-quality/fix - detect and fix code bugs.

    Body: {"html": "...", "css": "...", "javascript": "...", "project_id": "...", "auto_fix": true}
    Returns: fix report with fixed code
    """
    if not _require_login():
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        data = request.get_json(silent=True) if request.is_json else {}
        if not isinstance(data, dict):
            return jsonify({"success": False, "error": "Invalid JSON payload."}), 400

        html, css, js = _validate_payload(data)
        project_id = data.get("project_id")
        auto_fix = data.get("auto_fix", True)

        from services.ai_bug_fixer import fix_code_bugs
        result = fix_code_bugs(
            html, css, js,
            user_id=session.get("email"),
            project_id=project_id,
            auto_fix=auto_fix,
        )

        # Persist the fix report
        email = session.get("email")
        if _collection() is not None and project_id:
            try:
                doc = {
                    "project_id": project_id,
                    "user_email": email,
                    "report": result.get("report", {}),
                    "fixed_at": datetime.utcnow(),
                }
                _collection().insert_one(doc)
            except Exception:
                pass

        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("[CodeQuality] Bug fix failed: %s" % e)
        return jsonify({
            "success": False,
            "error": "Bug fixing failed",
            "message": str(e),
        }), 500


@code_quality_bp.route("/analyze-bugs", methods=["POST"])
def analyze_bugs():
    """POST /api/code-quality/analyze-bugs - analyze code for bugs without fixing.

    Body: {"html": "...", "css": "...", "javascript": "..."}
    Returns: detailed bug analysis
    """
    if not _require_login():
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        data = request.get_json(silent=True) if request.is_json else {}
        if not isinstance(data, dict):
            return jsonify({"success": False, "error": "Invalid JSON payload."}), 400

        html, css, js = _validate_payload(data)

        from services.ai_bug_fixer import analyze_code_bugs
        result = analyze_code_bugs(html, css, js)

        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Bug analysis failed",
            "message": str(e),
        }), 500


@code_quality_bp.route("/project/<project_id>", methods=["GET"])
def get_latest_analysis(project_id):
    """GET /api/code-quality/project/<project_id> - latest analysis for a project."""
    if not _require_login():
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    email = session.get("email")
    collection = _collection()
    if collection is None:
        return jsonify({"success": False, "error": "Database unavailable"}), 503

    try:
        doc = collection.find_one(
            {"project_id": project_id, "user_email": email},
            sort=[("analyzed_at", -1)],
        )
        if not doc:
            return jsonify({"success": False, "error": "No analysis found for this project"}), 404

        result = {
            "quality_score": doc.get("quality_score"),
            "quality_level": doc.get("quality_level"),
            "model_quality_level": doc.get("model_quality_level"),
            "confidence": doc.get("confidence"),
            "features": doc.get("features", {}),
            "issues": doc.get("issues", []),
            "sections": doc.get("sections", []),
            "analyzed_at": doc.get("analyzed_at").isoformat()
            if isinstance(doc.get("analyzed_at"), datetime) else None,
        }
        return jsonify({"success": True, "result": result}), 200
    except Exception:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": "Unable to load analysis"}), 500


def register_code_quality_routes(app, mongo_instance):
    """Register the code-quality blueprint with the Flask app."""
    global code_quality_collection
    # mongo_instance is the database (real or mock)
    code_quality_collection = mongo_instance.code_quality
    app.register_blueprint(code_quality_bp)
    print("[CodeQuality] Code quality analyzer routes registered.")