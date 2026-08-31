"""
Nexus Flow — Generation Logs Service
Detailed stage-by-stage logging for website generation.
Stores logs in MongoDB collection: generation_logs
"""
import logging
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

_mongo_collection = None


class GenerationStage(Enum):
    """Stages of website generation pipeline."""
    PROMPT_ANALYSIS = "prompt_analysis"
    AI_PLANNING = "ai_planning"
    COMPONENT_GENERATION = "component_generation"
    CODE_GENERATION = "code_generation"
    FILE_CREATION = "file_creation"
    DEPENDENCY_INSTALLATION = "dependency_installation"
    BUILD_VALIDATION = "build_validation"
    PREVIEW_STARTUP = "preview_startup"


class GenerationStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


def configure(mongo_instance):
    """Wire MongoDB instance for persistence (supports real DB or mock)."""
    global _mongo_collection
    if mongo_instance is None:
        return
    try:
        if hasattr(mongo_instance, "db") and hasattr(mongo_instance.db, "generation_logs"):
            _mongo_collection = mongo_instance.db.generation_logs
        elif hasattr(mongo_instance, "generation_logs"):
            _mongo_collection = mongo_instance.generation_logs
        else:
            _mongo_collection = mongo_instance["generation_logs"]
        # Create index for efficient querying (no-op on mock)
        try:
            _mongo_collection.create_index([("project_id", 1), ("timestamp", 1)])
            _mongo_collection.create_index([("user_email", 1), ("timestamp", -1)])
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"[GenerationLogs] MongoDB wire error: {e}")


def log_stage_start(project_id, user_email, stage, prompt_snippet=None):
    """Log the start of a generation stage."""
    _log_stage(project_id, user_email, stage, GenerationStatus.IN_PROGRESS, None, prompt_snippet)


def log_stage_complete(project_id, user_email, stage, duration_seconds, details=None):
    """Log the successful completion of a generation stage."""
    _log_stage(project_id, user_email, stage, GenerationStatus.COMPLETED, duration_seconds, None, details)


def log_stage_failed(project_id, user_email, stage, error_message, duration_seconds=None):
    """Log a failed generation stage."""
    _log_stage(project_id, user_email, stage, GenerationStatus.FAILED, duration_seconds, error_message)


def log_stage_skipped(project_id, user_email, stage, reason):
    """Log a skipped generation stage."""
    _log_stage(project_id, user_email, stage, GenerationStatus.SKIPPED, 0, reason)


def _log_stage(project_id, user_email, stage, status, duration_seconds=None, error_message=None, details=None):
    """Internal function to log a stage."""
    if _mongo_collection is None:
        return

    try:
        doc = {
            "project_id": project_id,
            "user_email": user_email,
            "stage": stage.value if isinstance(stage, GenerationStage) else stage,
            "status": status.value if isinstance(status, GenerationStatus) else status,
            "timestamp": datetime.utcnow(),
            "duration_seconds": duration_seconds,
            "error_message": error_message,
            "details": details,
        }
        _mongo_collection.insert_one(doc)
    except Exception as e:
        logger.warning(f"[GenerationLogs] Failed to log stage {stage}: {e}")


def get_generation_logs(project_id):
    """Retrieve all generation logs for a project."""
    if _mongo_collection is None:
        return []

    try:
        docs = list(_mongo_collection.find(
            {"project_id": project_id},
            {"_id": 0}
        ).sort("timestamp", 1))

        for d in docs:
            if "timestamp" in d and hasattr(d["timestamp"], "isoformat"):
                d["timestamp"] = d["timestamp"].isoformat()
        return docs
    except Exception as e:
        logger.warning(f"[GenerationLogs] Failed to get logs for {project_id}: {e}")
        return []


def get_user_generation_history(user_email, limit=20):
    """Get recent generation attempts for a user."""
    if _mongo_collection is None:
        return []

    try:
        # Get unique project_ids for recent attempts
        pipeline = [
            {"$match": {"user_email": user_email}},
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$project_id",
                "latest_timestamp": {"$first": "$timestamp"},
                "stages": {"$push": "$$ROOT"}
            }},
            {"$limit": limit}
        ]
        docs = list(_mongo_collection.aggregate(pipeline))
        for d in docs:
            if "latest_timestamp" in d and hasattr(d["latest_timestamp"], "isoformat"):
                d["latest_timestamp"] = d["latest_timestamp"].isoformat()
            for s in d.get("stages", []):
                if "timestamp" in s and hasattr(s["timestamp"], "isoformat"):
                    s["timestamp"] = s["timestamp"].isoformat()
        return docs
    except Exception as e:
        logger.warning(f"[GenerationLogs] Failed to get history for {user_email}: {e}")
        return []


def clear_generation_logs(project_id):
    """Clear generation logs for a project (e.g., before retry)."""
    if _mongo_collection is None:
        return False

    try:
        result = _mongo_collection.delete_many({"project_id": project_id})
        return result.deleted_count > 0
    except Exception as e:
        logger.warning(f"[GenerationLogs] Failed to clear logs for {project_id}: {e}")
        return False