"""
Nexus Flow — Generation Control
Tracks active generations and supports cancellation.
Must be MongoDB-independent (pure memory) so it works offline.
"""
import threading
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class GenerationCancelledException(Exception):
    """Raised when generation is cancelled by user before next stage."""
    pass

active_generations: Dict[str, Dict] = {}
_lock = threading.Lock()

def register_generation(generation_id: str, project_id: str, email: str = ""):
    with _lock:
        active_generations[generation_id] = {
            "generation_id": generation_id,
            "project_id": project_id,
            "email": email,
            "cancelled": False,
            "stage": 0,
        }
        logger.info(f"[GenControl] Registered {generation_id} -> {project_id}")

def mark_cancelled(generation_id: str) -> bool:
    with _lock:
        if generation_id in active_generations:
            active_generations[generation_id]["cancelled"] = True
            logger.info(f"[GenControl] Cancelled {generation_id}")
            return True
        # If not yet registered (race), create a cancelled placeholder so later register respects it
        active_generations[generation_id] = {
            "generation_id": generation_id,
            "project_id": "",
            "email": "",
            "cancelled": True,
            "stage": 0,
        }
        logger.info(f"[GenControl] Pre-cancelled {generation_id} (not yet registered)")
        return False

def is_cancelled(generation_id: Optional[str]) -> bool:
    if not generation_id:
        return False
    with _lock:
        entry = active_generations.get(generation_id)
        return bool(entry and entry.get("cancelled"))

def check_cancel(generation_id: Optional[str], stage_name: str = ""):
    """Raise if cancelled. Call before every stage."""
    if is_cancelled(generation_id):
        logger.info(f"[GenControl] Abort at stage '{stage_name}' for {generation_id}")
        raise GenerationCancelledException(f"Generation cancelled at {stage_name}")

def complete_generation(generation_id: Optional[str]):
    if not generation_id:
        return
    with _lock:
        if generation_id in active_generations:
            del active_generations[generation_id]
            logger.info(f"[GenControl] Completed/removed {generation_id}")

def get_active(generation_id: str):
    with _lock:
        return active_generations.get(generation_id)

def list_active():
    with _lock:
        return dict(active_generations)
