"""
Audit Service - Security audit logging for Admin Control Center.
Tracks user actions, project changes, downloads, AI usage.
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_log_col = None


def configure(log_collection):
    global _log_col
    _log_col = log_collection


def log_event(user_email, action, details="", status="SUCCESS"):
    if _log_col is None:
        return

    doc = {
        "user_email": user_email or "system",
        "action": action,
        "details": details,
        "status": status,
        "timestamp": datetime.now(timezone.utc),
    }

    try:
        _log_col.insert_one(doc)
    except Exception as e:
        logger.warning("Failed to write audit log: %s", e)


def clear_logs():
    """Delete all audit log documents from the collection."""
    if _log_col is None:
        return False

    try:
        result = _log_col.delete_many({})
        logger.info("Cleared %d audit log entries.", result.deleted_count)
        return True
    except Exception as e:
        logger.error("Failed to clear audit logs: %s", e)
        return False


def get_logs(limit=100, offset=0, action_filter=None, status_filter=None, user_filter=None):
    if _log_col is None:
        return [], 0

    query = {}
    if action_filter and action_filter != "all":
        query["action"] = {"$regex": action_filter, "$options": "i"}
    if status_filter and status_filter != "all":
        query["status"] = status_filter
    if user_filter:
        query["user_email"] = {"$regex": user_filter, "$options": "i"}

    total = 0
    try:
        total = _log_col.count_documents(query)
    except Exception:
        pass

    logs = []
    try:
        cursor = _log_col.find(query).sort("timestamp", -1).skip(offset).limit(limit)
        for log in cursor:
            ts = log.get("timestamp")
            ts_fmt = ""
            if isinstance(ts, datetime):
                ts_fmt = ts.strftime("%b %d, %Y %I:%M:%S %p")
            logs.append({
                "id": str(log.get("_id", "")),
                "user_email": log.get("user_email", "system"),
                "action": log.get("action", ""),
                "details": log.get("details", ""),
                "status": log.get("status", "INFO"),
                "timestamp": ts_fmt,
            })
    except Exception as e:
        logger.error("Error fetching audit logs: %s", e)

    return logs, total


def get_user_activity(user_email, limit=50):
    if _log_col is None:
        return []

    logs = []
    try:
        cursor = _log_col.find({"user_email": user_email}).sort("timestamp", -1).limit(limit)
        for log in logs:
            ts = log.get("timestamp")
            ts_fmt = ""
            if isinstance(ts, datetime):
                ts_fmt = ts.strftime("%b %d, %Y %I:%M:%S %p")
            logs.append({
                "id": str(log.get("_id", "")),
                "action": log.get("action", ""),
                "details": log.get("details", ""),
                "status": log.get("status", "INFO"),
                "timestamp": ts_fmt,
            })
    except Exception as e:
        logger.error("Error fetching user activity: %s", e)

    return logs


def get_recent_logs_for_dashboard(limit=20):
    if _log_col is None:
        return []

    logs = []
    try:
        cursor = _log_col.find().sort("timestamp", -1).limit(limit)
        for log in cursor:
            ts = log.get("timestamp")
            ts_fmt = ""
            if isinstance(ts, datetime):
                ts_fmt = ts.strftime("%b %d, %Y %I:%M:%S %p")
            logs.append({
                "id": str(log.get("_id", "")),
                "user_email": log.get("user_email", "system"),
                "action": log.get("action", ""),
                "details": log.get("details", ""),
                "status": log.get("status", "INFO"),
                "timestamp": ts_fmt,
            })
    except Exception:
        pass

    return logs


ACTION_LABELS = {
    "user_login": "User Login",
    "user_register": "User Registered",
    "user_logout": "User Logout",
    "profile_update": "Profile Updated",
    "project_created": "Project Created",
    "project_updated": "Project Updated",
    "project_deleted": "Project Deleted",
    "project_generated": "Website Generated",
    "download_zip": "ZIP Downloaded",
    "download_html": "HTML Exported",
    "download_deploy": "Deploy Bundle Downloaded",
    "ai_generation": "AI Generation Request",
    "ai_modify": "AI Modification Request",
    "ai_chat": "AI Chat",
    "provider_change": "Provider Changed",
    "user_deleted": "User Deleted",
    "download_cleared": "Download History Cleared",
}
