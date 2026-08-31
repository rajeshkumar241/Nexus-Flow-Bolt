"""
Dashboard Service - Real-time statistics for the Nexus Flow dashboard.
All data sourced from MongoDB collections.
"""
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_user_col = None
_project_col = None
_download_col = None
_chat_col = None
_version_col = None
_log_col = None


def configure(collections):
    global _user_col, _project_col, _download_col, _chat_col, _version_col, _log_col
    _user_col = collections.get("users")
    _project_col = collections.get("projects")
    _download_col = collections.get("downloads")
    _chat_col = collections.get("chats")
    _version_col = collections.get("project_versions")
    _log_col = collections.get("logs")


def _safe_count(col):
    if col is None:
        return 0
    try:
        return col.count_documents({})
    except Exception:
        return 0


def _safe_count_query(col, query):
    if col is None:
        return 0
    try:
        return col.count_documents(query)
    except Exception:
        return 0


def get_dashboard_data(user_email):
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_projects = _safe_count_query(_project_col, {"user_email": user_email})
    total_downloads = _safe_count_query(_download_col, {"user_email": user_email})
    total_chats = _safe_count_query(_chat_col, {"user_email": user_email})

    ai_generations = total_projects + total_chats

    total_bytes = 0
    if _download_col is not None:
        try:
            cursor = _download_col.find({"user_email": user_email}, {"file_size_bytes": 1})
            for doc in cursor:
                total_bytes += doc.get("file_size_bytes", 0)
        except Exception:
            pass
    storage_mb = round(total_bytes / (1024 * 1024), 2)
    storage_pct = min(100, round((storage_mb / 50.0) * 100, 1))

    new_projects_week = _safe_count_query(_project_col, {
        "user_email": user_email,
        "created_at": {"$gte": week_ago}
    })

    new_downloads_week = _safe_count_query(_download_col, {
        "user_email": user_email,
        "downloaded_at": {"$gte": week_ago}
    })

    recent_projects = []
    if _project_col is not None:
        try:
            cursor = _project_col.find({"user_email": user_email}).sort("updated_at", -1).limit(6)
            for p in cursor:
                created_at = p.get("created_at")
                updated_at = p.get("updated_at")
                created_fmt = ""
                if isinstance(created_at, datetime):
                    created_fmt = created_at.strftime("%b %d, %Y")
                updated_fmt = ""
                if isinstance(updated_at, datetime):
                    updated_fmt = _time_fmt(updated_at)
                elif isinstance(created_at, datetime):
                    updated_fmt = _time_fmt(created_at)

                recent_projects.append({
                    "id": str(p.get("_id", "")),
                    "title": p.get("title", "Untitled"),
                    "prompt": p.get("prompt", ""),
                    "status": p.get("status", "Active"),
                    "created_at": created_fmt,
                    "updated_at": updated_fmt,
                    "thumbnail_ref": f"/preview/{p.get('_id', '')}",
                })
        except Exception as e:
            logger.error("Error fetching recent projects: %s", e)

    activity = []
    if _project_col is not None:
        try:
            cursor = _project_col.find({"user_email": user_email}).sort("created_at", -1).limit(5)
            for p in cursor:
                ts = p.get("created_at")
                if isinstance(ts, datetime):
                    activity.append({
                        "icon": "fa-wand-magic-sparkles",
                        "color": "purple",
                        "title": "Website Generated",
                        "desc": p.get("title", "Untitled"),
                        "time": _time_fmt(ts),
                    })
        except Exception:
            pass

    if _download_col is not None:
        try:
            cursor = _download_col.find({"user_email": user_email}).sort("downloaded_at", -1).limit(3)
            for d in cursor:
                ts = d.get("downloaded_at")
                if isinstance(ts, datetime):
                    ft = d.get("file_type", "File")
                    activity.append({
                        "icon": "fa-file-arrow-down",
                        "color": "green",
                        "title": f"{ft} Exported",
                        "desc": d.get("file_name", ""),
                        "time": _time_fmt(ts),
                    })
        except Exception:
            pass

    if _log_col is not None:
        try:
            cursor = _log_col.find({"user_email": user_email}).sort("timestamp", -1).limit(3)
            for log in cursor:
                ts = log.get("timestamp")
                if isinstance(ts, datetime):
                    action = log.get("action", "")
                    if "login" in action:
                        continue
                    activity.append({
                        "icon": "fa-shield-halved",
                        "color": "blue",
                        "title": action.replace("_", " ").title(),
                        "desc": log.get("details", "")[:60],
                        "time": _time_fmt(ts),
                    })
        except Exception:
            pass

    activity.sort(key=lambda x: x.get("time", ""), reverse=False)
    activity = activity[:8]

    announcements = [
        {
            "tag": "feature",
            "tag_label": "New Feature",
            "title": "AI Code Quality Analyzer",
            "desc": "ML-powered code analysis with improvement suggestions.",
        },
        {
            "tag": "update",
            "tag_label": "Update",
            "title": "Gemini 2.5 Flash Active",
            "desc": "Upgraded to the latest Gemini model for faster generation.",
        },
        {
            "tag": "status",
            "tag_label": "Status",
            "title": "Deploy Bundles Now Available",
            "desc": "Export production-ready deployment packages.",
        },
    ]

    return {
        "total_projects": total_projects,
        "total_downloads": total_downloads,
        "ai_generations": ai_generations,
        "storage_mb": storage_mb,
        "storage_pct": storage_pct,
        "new_projects_week": new_projects_week,
        "new_downloads_week": new_downloads_week,
        "recent_projects": recent_projects,
        "activity": activity,
        "announcements": announcements,
    }


def _time_fmt(dt):
    if not isinstance(dt, datetime):
        return "Recently"
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        m = seconds // 60
        return f"{m}m ago"
    elif seconds < 86400:
        h = seconds // 3600
        return f"{h}h ago"
    elif seconds < 604800:
        d = seconds // 86400
        return f"{d}d ago"
    else:
        return dt.strftime("%b %d")
