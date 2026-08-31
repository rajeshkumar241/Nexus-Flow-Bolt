"""
Admin Control Center - Service Layer
Real-time dashboard statistics, provider monitoring, analytics.
"""
import os
import time
import logging
from datetime import datetime, timedelta, timezone
from pymongo import ASCENDING, DESCENDING

logger = logging.getLogger(__name__)

_user_col = None
_project_col = None
_download_col = None
_chat_col = None
_log_col = None
_llm_usage_col = None
_ai_settings_col = None
_version_col = None


def configure(collections):
    global _user_col, _project_col, _download_col, _chat_col
    global _log_col, _llm_usage_col, _ai_settings_col, _version_col
    _user_col = collections.get("users")
    _project_col = collections.get("projects")
    _download_col = collections.get("downloads")
    _chat_col = collections.get("chats")
    _log_col = collections.get("logs")
    _llm_usage_col = collections.get("llm_usage")
    _ai_settings_col = collections.get("ai_settings")
    _version_col = collections.get("project_versions")


def _safe_count(col):
    if col is None:
        return 0
    try:
        return col.count_documents({})
    except Exception:
        return 0


def get_dashboard_stats():
    total_users = _safe_count(_user_col)
    total_projects = _safe_count(_project_col)
    total_downloads = _safe_count(_download_col)
    total_chats = _safe_count(_chat_col)
    total_versions = _safe_count(_version_col)

    ai_requests = 0
    if _llm_usage_col is not None:
        try:
            ai_requests = _llm_usage_col.count_documents({})
        except Exception:
            ai_requests = 0

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    new_users_week = 0
    new_projects_week = 0
    new_downloads_week = 0
    ai_requests_week = 0

    if _user_col is not None:
        try:
            new_users_week = _user_col.count_documents({"created_at": {"$gte": week_ago}})
        except Exception:
            try:
                new_users_week = _user_col.count_documents({})
            except Exception:
                pass

    if _project_col is not None:
        try:
            new_projects_week = _project_col.count_documents({"created_at": {"$gte": week_ago}})
        except Exception:
            pass

    if _download_col is not None:
        try:
            new_downloads_week = _download_col.count_documents({"downloaded_at": {"$gte": week_ago}})
        except Exception:
            pass

    if _llm_usage_col is not None:
        try:
            ai_requests_week = _llm_usage_col.count_documents({"timestamp": {"$gte": week_ago}})
        except Exception:
            pass

    return {
        "total_users": total_users,
        "total_projects": total_projects,
        "total_downloads": total_downloads,
        "ai_requests": ai_requests,
        "total_chats": total_chats,
        "total_versions": total_versions,
        "new_users_week": new_users_week,
        "new_projects_week": new_projects_week,
        "new_downloads_week": new_downloads_week,
        "ai_requests_week": ai_requests_week,
    }


def get_users_list(search=None, role_filter=None, status_filter=None, limit=50, offset=0):
    if _user_col is None:
        return [], 0

    query = {}
    if search:
        regex = {"$regex": search, "$options": "i"}
        query["$or"] = [{"fullname": regex}, {"email": regex}]

    total = 0
    try:
        total = _user_col.count_documents(query)
    except Exception:
        pass

    users = []
    try:
        cursor = _user_col.find(query).sort("created_at", -1).skip(offset).limit(limit)
        for u in cursor:
            email = u.get("email", "")
            project_count = 0
            download_count = 0
            chat_count = 0

            if _project_col is not None:
                try:
                    project_count = _project_col.count_documents({"user_email": email})
                except Exception:
                    pass

            if _download_col is not None:
                try:
                    download_count = _download_col.count_documents({"user_email": email})
                except Exception:
                    pass

            if _chat_col is not None:
                try:
                    chat_count = _chat_col.count_documents({"user_email": email})
                except Exception:
                    pass

            created_at = u.get("created_at")
            created_fmt = ""
            if isinstance(created_at, datetime):
                created_fmt = created_at.strftime("%b %d, %Y")
            else:
                created_fmt = "Unknown"

            is_active = True
            if isinstance(created_at, datetime):
                thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
                if created_at < thirty_days_ago and project_count == 0 and download_count == 0:
                    is_active = False

            users.append({
                "id": str(u.get("_id", "")),
                "fullname": u.get("fullname", "Unknown"),
                "email": email,
                "profile_image": u.get("profile_image", ""),
                "project_count": project_count,
                "download_count": download_count,
                "chat_count": chat_count,
                "created_at": created_fmt,
                "is_active": is_active,
            })
    except Exception as e:
        logger.error("Error fetching users: %s", e)

    return users, total


def get_user_detail(user_id):
    if _user_col is None:
        return None

    from bson import ObjectId
    try:
        u = _user_col.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None

    if not u:
        return None

    email = u.get("email", "")
    project_count = 0
    download_count = 0
    chat_count = 0

    if _project_col is not None:
        try:
            project_count = _project_col.count_documents({"user_email": email})
        except Exception:
            pass

    if _download_col is not None:
        try:
            download_count = _download_col.count_documents({"user_email": email})
        except Exception:
            pass

    if _chat_col is not None:
        try:
            chat_count = _chat_col.count_documents({"user_email": email})
        except Exception:
            pass

    created_at = u.get("created_at")
    created_fmt = ""
    if isinstance(created_at, datetime):
        created_fmt = created_at.strftime("%b %d, %Y %I:%M %p")

    return {
        "id": str(u.get("_id", "")),
        "fullname": u.get("fullname", "Unknown"),
        "email": email,
        "profile_image": u.get("profile_image", ""),
        "bio": u.get("bio", ""),
        "project_count": project_count,
        "download_count": download_count,
        "chat_count": chat_count,
        "created_at": created_fmt,
    }


def delete_user(user_id, admin_email):
    if _user_col is None:
        return False, "Database not available"

    from bson import ObjectId
    try:
        user = _user_col.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return False, "Invalid user ID"

    if not user:
        return False, "User not found"

    target_email = user.get("email", "")
    if target_email == admin_email:
        return False, "Cannot delete your own account"

    deleted_projects = 0
    deleted_downloads = 0
    deleted_chats = 0

    if _project_col is not None:
        try:
            result = _project_col.delete_many({"user_email": target_email})
            deleted_projects = result.deleted_count
        except Exception:
            pass

    if _download_col is not None:
        try:
            result = _download_col.delete_many({"user_email": target_email})
            deleted_downloads = result.deleted_count
        except Exception:
            pass

    if _chat_col is not None:
        try:
            result = _chat_col.delete_many({"user_email": target_email})
            deleted_chats = result.deleted_count
        except Exception:
            pass

    if _version_col is not None:
        try:
            _version_col.delete_many({"user_email": target_email})
        except Exception:
            pass

    try:
        _user_col.delete_one({"_id": ObjectId(user_id)})
    except Exception:
        return False, "Failed to delete user"

    from services.audit_service import log_event
    log_event(
        admin_email,
        "user_deleted",
        f"Deleted user {target_email} (Projects: {deleted_projects}, Downloads: {deleted_downloads}, Chats: {deleted_chats})",
        "WARNING"
    )

    return True, "User deleted successfully"


def get_project_analytics():
    if _project_col is None:
        return {
            "total": 0, "recent": [], "by_user": [], "categories": {},
        }

    total = 0
    try:
        total = _project_col.count_documents({})
    except Exception:
        pass

    recent = []
    try:
        cursor = _project_col.find().sort("created_at", -1).limit(10)
        for p in cursor:
            created_at = p.get("created_at")
            created_fmt = ""
            if isinstance(created_at, datetime):
                created_fmt = created_at.strftime("%b %d, %Y %H:%M")
            recent.append({
                "id": str(p.get("_id", "")),
                "title": p.get("title", "Untitled"),
                "user_email": p.get("user_email", ""),
                "created_at": created_fmt,
            })
    except Exception:
        pass

    by_user = []
    try:
        pipeline = [
            {"$group": {"_id": "$user_email", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]
        for doc in _project_col.aggregate(pipeline):
            by_user.append({
                "email": doc.get("_id", "Unknown"),
                "count": doc.get("count", 0),
            })
    except Exception:
        pass

    categories = {"portfolio": 0, "saas": 0, "ecommerce": 0, "restaurant": 0, "blog": 0, "other": 0}
    try:
        cursor = _project_col.find({}, {"prompt": 1, "title": 1})
        for p in cursor:
            text = (p.get("prompt", "") + " " + p.get("title", "")).lower()
            if any(w in text for w in ["portfolio", "personal", "resume", "cv"]):
                categories["portfolio"] += 1
            elif any(w in text for w in ["saas", "software", "app", "dashboard", "platform"]):
                categories["saas"] += 1
            elif any(w in text for w in ["shop", "store", "ecommerce", "e-commerce", "product", "cart"]):
                categories["ecommerce"] += 1
            elif any(w in text for w in ["restaurant", "cafe", "food", "menu", "dining"]):
                categories["restaurant"] += 1
            elif any(w in text for w in ["blog", "article", "post", "news"]):
                categories["blog"] += 1
            else:
                categories["other"] += 1
    except Exception:
        pass

    return {
        "total": total,
        "recent": recent,
        "by_user": by_user,
        "categories": categories,
    }


def get_download_analytics():
    if _download_col is None:
        return {"total": 0, "by_type": {}, "recent": []}

    total = 0
    try:
        total = _download_col.count_documents({})
    except Exception:
        pass

    by_type = {"zip": 0, "html": 0, "deploy": 0}
    try:
        pipeline = [
            {"$group": {"_id": "$file_type", "count": {"$sum": 1}}},
        ]
        for doc in _download_col.aggregate(pipeline):
            ft = (doc.get("_id") or "").lower()
            if "zip" in ft:
                by_type["zip"] += doc.get("count", 0)
            elif "html" in ft or "standalone" in ft:
                by_type["html"] += doc.get("count", 0)
            elif "deploy" in ft:
                by_type["deploy"] += doc.get("count", 0)
    except Exception:
        pass

    recent = []
    try:
        cursor = _download_col.find().sort("downloaded_at", -1).limit(10)
        for d in cursor:
            dt = d.get("downloaded_at")
            dt_fmt = ""
            if isinstance(dt, datetime):
                dt_fmt = dt.strftime("%b %d, %Y %H:%M")
            size_bytes = d.get("file_size_bytes", 0)
            if size_bytes >= 1048576:
                size_str = f"{size_bytes / 1048576:.1f} MB"
            else:
                size_str = f"{size_bytes / 1024:.0f} KB"
            recent.append({
                "id": str(d.get("_id", "")),
                "title": d.get("title", ""),
                "file_name": d.get("file_name", ""),
                "file_type": d.get("file_type", ""),
                "size": size_str,
                "downloaded_at": dt_fmt,
                "user_email": d.get("user_email", ""),
            })
    except Exception:
        pass

    return {"total": total, "by_type": by_type, "recent": recent}


def get_ai_providers_status():
    """Get detailed status of all AI providers and models."""
    from services.ai_provider_manager import get_provider_manager
    
    manager = get_provider_manager()
    model_status = manager.get_model_status()
    active_provider, active_model = manager.get_active_provider()
    
    providers = []
    
    # Group models by provider
    provider_models = {}
    for key, status in model_status.items():
        provider = status["provider"]
        if provider not in provider_models:
            provider_models[provider] = []
        provider_models[provider].append(status)
    
    for provider_name, models in provider_models.items():
        has_key = any(m["has_api_key"] for m in models)
        configured_models = [m for m in models if m["enabled"] and m["has_api_key"]]
        
        # Find active model for this provider
        active_model_for_provider = None
        if provider_name == active_provider:
            active_model_for_provider = active_model
        
        # Get provider display name
        display_name = {
            "gemini": "Google Gemini",
            "openai": "OpenAI",
            "openrouter": "OpenRouter",
        }.get(provider_name, provider_name.title())
        
        providers.append({
            "name": display_name,
            "provider_key": provider_name,
            "configured": has_key,
            "has_api_key": has_key,
            "active_model": active_model_for_provider,
            "models": models,
            "model_count": len(configured_models),
            "total_models": len(models),
        })
    
    return providers


def test_provider_connection(provider_name):
    """Test connection to a specific provider."""
    provider_name_lower = (provider_name or "").lower()
    
    from services.ai_provider_manager import get_provider_manager
    manager = get_provider_manager()
    model_status = manager.get_model_status()
    
    # Find a model for this provider that has an API key
    test_model = None
    for key, status in model_status.items():
        if status["provider"] == provider_name_lower and status["has_api_key"] and status["enabled"]:
            test_model = status["model"]
            break
    
    if not test_model:
        return False, f"No available models for provider: {provider_name}", 0
    
    if provider_name_lower == "gemini":
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        if not gemini_key:
            return False, "GEMINI_API_KEY not configured", 0
        try:
            import urllib.request
            start = time.time()
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                latency = int((time.time() - start) * 1000)
                return True, f"Gemini API online ({latency}ms)", latency
        except Exception as e:
            return False, f"Gemini API error: {e}", 0
    
    if provider_name_lower == "openai":
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if not openai_key:
            return False, "OPENAI_API_KEY not configured", 0
        try:
            import urllib.request
            start = time.time()
            req = urllib.request.Request("https://api.openai.com/v1/models", method="GET")
            req.add_header("Authorization", f"Bearer {openai_key}")
            with urllib.request.urlopen(req, timeout=10) as resp:
                latency = int((time.time() - start) * 1000)
                return True, f"OpenAI API online ({latency}ms)", latency
        except Exception as e:
            return False, f"OpenAI API error: {e}", 0
    
    return False, f"Unknown provider: {provider_name}", 0


def get_system_health():
    health = {}

    try:
        # Use connection manager to detect offline mode gracefully
        try:
            from services.mongo_connection import is_mongo_offline
            if is_mongo_offline():
                health["database"] = {"status": "warning", "message": "MongoDB unavailable - running in offline mode"}
            elif _user_col is not None:
                _user_col.database.command("ping")
                health["database"] = {"status": "healthy", "message": "MongoDB connected"}
            else:
                health["database"] = {"status": "error", "message": "Database not initialized"}
        except ImportError:
            if _user_col is not None:
                _user_col.database.command("ping")
                health["database"] = {"status": "healthy", "message": "MongoDB connected"}
            else:
                health["database"] = {"status": "error", "message": "Database not initialized"}
    except Exception as e:
        # Offline mock throws; treat as warning not hard error
        try:
            from services.mongo_connection import is_mongo_offline
            if is_mongo_offline():
                health["database"] = {"status": "warning", "message": "MongoDB unavailable - running in offline mode"}
            else:
                health["database"] = {"status": "error", "message": f"MongoDB error: {e}"}
        except Exception:
            health["database"] = {"status": "warning", "message": f"MongoDB unavailable - running in offline mode"}

    # Use provider manager for AI health
    from services.ai_provider_manager import get_provider_manager
    manager = get_provider_manager()
    active_provider, active_model = manager.get_active_provider()
    model_status = manager.get_model_status()
    
    # Check if active model is healthy
    active_key = f"{active_provider}/{active_model}"
    active_status = model_status.get(active_key, {})
    
    if active_status.get("last_status") == "failed":
        ai_status = "error"
        ai_message = f"{active_provider}/{active_model} - {active_status.get('last_error', 'Failed')}"
    elif active_status.get("last_status") == "working":
        ai_status = "healthy"
        ai_message = f"{active_provider}/{active_model} - Online"
    elif active_status.get("last_status") == "partial":
        ai_status = "warning"
        ai_message = f"{active_provider}/{active_model} - Partial (check output)"
    else:
        ai_status = "warning"
        ai_message = f"{active_provider}/{active_model} - Not tested"
    
    health["ai_services"] = {
        "status": ai_status, 
        "message": ai_message, 
        "provider": active_provider,
        "model": active_model
    }

    try:
        projects_count = _safe_count(_project_col)
        storage_est = projects_count * 0.05
        if storage_est < 1:
            storage_status = "healthy"
            storage_msg = f"~{storage_est:.1f} MB estimated"
        elif storage_est < 10:
            storage_status = "warning"
            storage_msg = f"~{storage_est:.1f} MB estimated"
        else:
            storage_status = "warning"
            storage_msg = f"~{storage_est:.1f} MB estimated - consider cleanup"
        health["storage"] = {"status": storage_status, "message": storage_msg}
    except Exception:
        health["storage"] = {"status": "healthy", "message": "Storage nominal"}

    health["api"] = {"status": "healthy", "message": "Backend API running"}

    return health
