"""
Nexus Flow — Generation Performance Tracker
Real-time performance measurement using time.perf_counter().
Tracks every stage of the website generation pipeline.
"""
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_mongo_collection = None


def configure(mongo_instance):
    """Wire MongoDB instance for persistence (supports real DB or mock)."""
    global _mongo_collection
    if mongo_instance is None:
        return
    try:
        # mongo_instance may be a Database (real or mock) or a Flask-PyMongo wrapper
        if hasattr(mongo_instance, "db") and hasattr(mongo_instance.db, "generation_performance"):
            _mongo_collection = mongo_instance.db.generation_performance
        elif hasattr(mongo_instance, "generation_performance"):
            _mongo_collection = mongo_instance.generation_performance
        else:
            _mongo_collection = mongo_instance["generation_performance"]
    except Exception as e:
        logger.warning(f"[PerfTracker] MongoDB wire error: {e}")


class GenerationTimer:
    """
    Real-time generation performance tracker.
    Uses time.perf_counter() for high-resolution timing.

    Usage:
        timer = GenerationTimer(project_id, prompt)
        timer.start()

        timer.begin_stage("planning")
        # ... do planning ...
        timer.end_stage("planning")

        timer.begin_stage("code_gen")
        # ... generate code ...
        timer.end_stage("code_gen")

        report = timer.finish(success=True, files_count=25)
    """

    def __init__(self, project_id, prompt=""):
        self.project_id = project_id
        self.prompt_snippet = (prompt or "")[:200]
        self._start = None
        self._stages = {}
        self._current_stage = None
        self._current_stage_start = None
        self._finished = False
        self._success = False
        self._error_message = ""
        self._failed_stage = ""
        self._files_count = 0

    def start(self):
        """Start the total timer. Call this immediately when request arrives."""
        self._start = time.perf_counter()
        return self

    def begin_stage(self, name):
        """Mark the start of a pipeline stage."""
        # If there's an ongoing stage, close it first
        if self._current_stage is not None:
            self.end_stage(self._current_stage)
        self._current_stage = name
        self._current_stage_start = time.perf_counter()

    def end_stage(self, name):
        """Mark the end of a pipeline stage and record its duration."""
        if self._current_stage_start is None:
            return 0.0
        elapsed = time.perf_counter() - self._current_stage_start
        self._stages[name] = round(elapsed, 2)
        self._current_stage = None
        self._current_stage_start = None
        return elapsed

    def set_files_count(self, count):
        """Record the number of files created."""
        self._files_count = count

    def finish(self, success=True, error_message="", failed_stage=""):
        """
        Finalize the timer. Calculate total duration and persist to MongoDB.
        Returns the timing report dict.
        """
        # Close any lingering stage
        if self._current_stage is not None:
            self.end_stage(self._current_stage)

        total = round(time.perf_counter() - self._start, 2) if self._start else 0.0
        self._success = success
        self._error_message = error_message
        self._failed_stage = failed_stage
        self._finished = True

        report = {
            "project_id": self.project_id,
            "prompt_snippet": self.prompt_snippet,
            "success": success,
            "files_count": self._files_count,
            "timing": {
                "planning_seconds": self._stages.get("planning", 0),
                "code_generation_seconds": self._stages.get("code_gen", 0),
                "file_creation_seconds": self._stages.get("file_creation", 0),
                "dependency_install_seconds": self._stages.get("npm_install", 0),
                "build_seconds": self._stages.get("build", 0),
                "preview_seconds": self._stages.get("preview", 0),
                "total_seconds": total,
            },
            "failed_stage": failed_stage if not success else "",
            "error_message": error_message if not success else "",
            "recorded_at": datetime.utcnow().isoformat(),
        }

        # Persist to MongoDB
        if _mongo_collection is not None:
            try:
                _mongo_collection.insert_one(report)
            except Exception as e:
                logger.warning(f"[PerfTracker] Failed to persist metrics: {e}")

        # Log summary
        logger.info(f"[PerfTracker] {self.project_id}: total={total:.1f}s "
                     f"planning={self._stages.get('planning', 0):.1f}s "
                     f"codegen={self._stages.get('code_gen', 0):.1f}s "
                     f"files={self._stages.get('file_creation', 0):.1f}s "
                     f"npm={self._stages.get('npm_install', 0):.1f}s "
                     f"build={self._stages.get('build', 0):.1f}s "
                     f"preview={self._stages.get('preview', 0):.1f}s "
                     f"files_count={self._files_count}")

        return report

    def get_elapsed(self):
        """Get total elapsed time so far (without finishing)."""
        if self._start is None:
            return 0.0
        return round(time.perf_counter() - self._start, 2)

    def get_timing_dict(self):
        """Get the current timing dict (can be called before finish)."""
        total = self.get_elapsed()
        return {
            "planning_seconds": self._stages.get("planning", 0),
            "code_generation_seconds": self._stages.get("code_gen", 0),
            "file_creation_seconds": self._stages.get("file_creation", 0),
            "dependency_install_seconds": self._stages.get("npm_install", 0),
            "build_seconds": self._stages.get("build", 0),
            "preview_seconds": self._stages.get("preview", 0),
            "total_seconds": total,
        }
