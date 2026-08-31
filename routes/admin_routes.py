"""
Admin Control Center Routes - Blueprint
Provides admin dashboard, user management, analytics, providers, logs.
"""
from flask import Blueprint, render_template, jsonify, session, redirect, url_for, request
from services import admin_service, audit_service

admin_bp = Blueprint("admin_center", __name__)


def _require_auth():
    if "email" not in session:
        return None
    return session["email"]


def register_admin_routes(app, mongo_db):
    collections = {
        "users": mongo_db.users,
        "projects": mongo_db.projects,
        "downloads": mongo_db.downloads,
        "chats": mongo_db.chats,
        "logs": mongo_db.logs,
        "llm_usage": mongo_db.llm_usage,
        "ai_settings": mongo_db.ai_settings,
        "project_versions": mongo_db.project_versions,
    }
    admin_service.configure(collections)
    audit_service.configure(mongo_db.logs)

    app.register_blueprint(admin_bp)

    print("[AdminControl] Admin Control Center routes registered.")


@admin_bp.route("/admin/dashboard")
def admin_dashboard():
    email = _require_auth()
    if not email:
        return redirect(url_for("login"))

    stats = admin_service.get_dashboard_stats()
    providers = admin_service.get_ai_providers_status()
    health = admin_service.get_system_health()
    recent_logs = audit_service.get_recent_logs_for_dashboard(15)

    return render_template("admin_center.html",
                           active_page="admin",
                           section="dashboard",
                           stats=stats,
                           providers=providers,
                           health=health,
                           recent_logs=recent_logs,
                           current_user_email=email)


@admin_bp.route("/admin/users")
def admin_users():
    email = _require_auth()
    if not email:
        return redirect(url_for("login"))

    search = request.args.get("search", "")
    users, total = admin_service.get_users_list(search=search if search else None, limit=50)

    return render_template("admin_center.html",
                           active_page="admin",
                           section="users",
                           users=users,
                           total_users=total,
                           search_query=search,
                           current_user_email=email)


@admin_bp.route("/admin/projects")
def admin_projects():
    email = _require_auth()
    if not email:
        return redirect(url_for("login"))

    analytics = admin_service.get_project_analytics()

    return render_template("admin_center.html",
                           active_page="admin",
                           section="projects",
                           analytics=analytics,
                           current_user_email=email)


@admin_bp.route("/admin/providers")
def admin_providers():
    email = _require_auth()
    if not email:
        return redirect(url_for("login"))

    providers = admin_service.get_ai_providers_status()
    health = admin_service.get_system_health()

    return render_template("admin_center.html",
                           active_page="admin",
                           section="providers",
                           providers=providers,
                           health=health,
                           current_user_email=email)


@admin_bp.route("/admin/logs")
def admin_logs():
    email = _require_auth()
    if not email:
        return redirect(url_for("login"))

    logs, total = audit_service.get_logs(limit=100)

    return render_template("admin_center.html",
                           active_page="admin",
                           section="logs",
                           logs=logs,
                           total_logs=total,
                           current_user_email=email)


@admin_bp.route("/admin/health")
def admin_health():
    email = _require_auth()
    if not email:
        return redirect(url_for("login"))

    health = admin_service.get_system_health()
    providers = admin_service.get_ai_providers_status()

    return render_template("admin_center.html",
                           active_page="admin",
                           section="health",
                           health=health,
                           providers=providers,
                           current_user_email=email)


@admin_bp.route("/admin/downloads")
def admin_downloads():
    email = _require_auth()
    if not email:
        return redirect(url_for("login"))

    download_analytics = admin_service.get_download_analytics()

    return render_template("admin_center.html",
                           active_page="admin",
                           section="downloads",
                           download_analytics=download_analytics,
                           current_user_email=email)


@admin_bp.route("/admin/api/stats")
def api_stats():
    email = _require_auth()
    if not email:
        return jsonify({"error": "Unauthorized"}), 401

    stats = admin_service.get_dashboard_stats()
    return jsonify({"success": True, "stats": stats})


@admin_bp.route("/admin/api/users", methods=["GET"])
def api_users():
    email = _require_auth()
    if not email:
        return jsonify({"error": "Unauthorized"}), 401

    search = request.args.get("search", "")
    users, total = admin_service.get_users_list(search=search if search else None, limit=50)
    return jsonify({"success": True, "users": users, "total": total})


@admin_bp.route("/admin/api/user/<user_id>", methods=["GET"])
def api_user_detail(user_id):
    email = _require_auth()
    if not email:
        return jsonify({"error": "Unauthorized"}), 401

    user = admin_service.get_user_detail(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"success": True, "user": user})


@admin_bp.route("/admin/api/user/<user_id>/delete", methods=["POST"])
def api_delete_user(user_id):
    email = _require_auth()
    if not email:
        return jsonify({"error": "Unauthorized"}), 401

    success, message = admin_service.delete_user(user_id, email)
    return jsonify({"success": success, "message": message})


@admin_bp.route("/admin/api/logs", methods=["GET"])
def api_logs():
    email = _require_auth()
    if not email:
        return jsonify({"error": "Unauthorized"}), 401

    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)
    action_filter = request.args.get("action", "")
    status_filter = request.args.get("status", "")
    user_filter = request.args.get("user", "")

    logs, total = audit_service.get_logs(
        limit=limit, offset=offset,
        action_filter=action_filter if action_filter else None,
        status_filter=status_filter if status_filter else None,
        user_filter=user_filter if user_filter else None,
    )
    return jsonify({"success": True, "logs": logs, "total": total})


@admin_bp.route("/admin/api/providers", methods=["GET"])
def api_providers():
    email = _require_auth()
    if not email:
        return jsonify({"error": "Unauthorized"}), 401

    providers = admin_service.get_ai_providers_status()
    return jsonify({"success": True, "providers": providers})


@admin_bp.route("/admin/api/provider/test", methods=["POST"])
def api_test_provider():
    email = _require_auth()
    if not email:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    provider_name = data.get("provider", "")
    if not provider_name:
        return jsonify({"success": False, "error": "Provider name required"}), 400

    success, message, latency = admin_service.test_provider_connection(provider_name)
    return jsonify({"success": success, "message": message, "latency_ms": latency})


@admin_bp.route("/admin/api/health", methods=["GET"])
def api_health():
    email = _require_auth()
    if not email:
        return jsonify({"error": "Unauthorized"}), 401

    health = admin_service.get_system_health()
    return jsonify({"success": True, "health": health})


@admin_bp.route("/admin/api/project-analytics", methods=["GET"])
def api_project_analytics():
    email = _require_auth()
    if not email:
        return jsonify({"error": "Unauthorized"}), 401

    analytics = admin_service.get_project_analytics()
    return jsonify({"success": True, "analytics": analytics})


@admin_bp.route("/admin/api/download-analytics", methods=["GET"])
def api_download_analytics():
    email = _require_auth()
    if not email:
        return jsonify({"error": "Unauthorized"}), 401

    analytics = admin_service.get_download_analytics()
    return jsonify({"success": True, "analytics": analytics})
