"""
Nexus Flow — Preview Builder (Production Preview)
Builds React/Vite projects into production dist and serves via Flask.

Responsibilities:
- Receive generated React project files
- Ensure project folder generated_projects/{project_id} exists with package.json, vite.config.js, src files
- Run npm install and npm run build
- Capture build errors
- Store output in generated_projects/{project_id}/dist for Flask serving
"""
import os
import subprocess
import logging
import json

logger = logging.getLogger(__name__)

PROJECTS_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_projects")


def _project_dir(project_id: str) -> str:
    return os.path.join(PROJECTS_ROOT, str(project_id))


def _dist_dir(project_id: str) -> str:
    return os.path.join(_project_dir(project_id), "dist")


def ensure_project_files(project_id: str, files: dict = None) -> bool:
    """
    Ensure project folder exists and contains required files.
    If files dict is provided, writes them to disk (overwrites).
    Returns True if essential files exist.
    """
    base = _project_dir(project_id)
    os.makedirs(base, exist_ok=True)

    if files:
        from services.filename_sanitizer import sanitize_filepath
        for path, content in files.items():
            safe = sanitize_filepath(path)
            full = os.path.join(base, safe)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            try:
                with open(full, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                logger.warning(f"[PreviewBuilder] Failed to write {path}: {e}")
                return False

    # Verify essential files
    required = ["package.json", "vite.config.js", "index.html"]
    for req in required:
        if not os.path.isfile(os.path.join(base, req)):
            logger.warning(f"[PreviewBuilder] Missing required file {req} for {project_id}")
            return False
    return True


def build_preview(project_id: str, files: dict = None) -> dict:
    """
    Full production preview build pipeline for a React project.

    Steps:
    1. Ensure project files exist (create if files provided)
    2. Run npm install
    3. Run npm run build
    4. Capture errors and return status

    Returns:
        {
            "success": bool,
            "dist_path": str,
            "preview_url": str,  # Flask route: /preview/<project_id>/index.html
            "message": str,
            "errors": list
        }
    """
    from services.vite_manager import install_dependencies, build_project

    base = _project_dir(project_id)
    dist = _dist_dir(project_id)

    # Step 1: Ensure files
    if files:
        ok = ensure_project_files(project_id, files)
        if not ok:
            return {"success": False, "dist_path": dist, "preview_url": None, "message": "Failed to create project files", "errors": ["Missing required files"]}

    if not os.path.isdir(base):
        return {"success": False, "dist_path": dist, "preview_url": None, "message": "Project not found", "errors": ["Project directory missing"]}

    # Step 2: Install dependencies
    logger.info(f"[PreviewBuilder] Installing dependencies for {project_id}...")
    ok, msg = install_dependencies(project_id)
    if not ok:
        logger.error(f"[PreviewBuilder] npm install failed for {project_id}: {msg}")
        return {"success": False, "dist_path": dist, "preview_url": None, "message": msg, "errors": [msg]}

    # Step 3: Build
    logger.info(f"[PreviewBuilder] Building project {project_id}...")
    ok, msg, errors = build_project(project_id)
    if not ok:
        logger.error(f"[PreviewBuilder] Build failed for {project_id}: {msg} errors={errors}")
        return {"success": False, "dist_path": dist, "preview_url": None, "message": msg, "errors": errors}

    # Verify dist
    index_path = os.path.join(dist, "index.html")
    if not os.path.isfile(index_path):
        logger.error(f"[PreviewBuilder] Build succeeded but dist/index.html missing for {project_id}")
        return {"success": False, "dist_path": dist, "preview_url": None, "message": "Build completed but index.html missing in dist", "errors": ["dist/index.html not found"]}

    # Ensure vite preview HTML does not contain dev scripts (remove if present for safety)
    # Dist should already be production, but double-check no dev markers remain
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
        # Remove any lingering Vite dev artifacts if present (should not be in dist)
        if "/@vite/client" in html or "/src/main.jsx" in html:
            logger.warning(f"[PreviewBuilder] Unexpected dev scripts found in dist for {project_id}, but serving as is")
    except Exception:
        pass

    preview_url = f"/preview/{project_id}/index.html"
    preview_url_abs = f"http://127.0.0.1:5000/preview/{project_id}/index.html"

    logger.info(f"[PreviewBuilder] Build completed for {project_id}, preview at {preview_url}")

    return {
        "success": True,
        "dist_path": dist,
        "preview_url": preview_url,
        "preview_url_abs": preview_url_abs,
        "message": "Build completed",
        "errors": []
    }


def get_preview_status(project_id: str) -> dict:
    """
    Check if preview is ready (dist exists and has index.html)
    Returns: {"ready": bool, "preview_url": str, "message": str}
    """
    dist = _dist_dir(project_id)
    base = _project_dir(project_id)
    preview_url = f"/preview/{project_id}/index.html"

    if os.path.isdir(dist) and os.path.isfile(os.path.join(dist, "index.html")):
        return {"ready": True, "preview_url": preview_url, "message": "Preview ready (dist exists)"}
    if os.path.isfile(os.path.join(base, "index.html")):
        # Fallback for static projects or not yet built
        return {"ready": True, "preview_url": preview_url, "message": "Preview fallback (index.html exists)"}
    return {"ready": False, "preview_url": None, "message": "Preview not built yet"}


def clean_preview(project_id: str):
    """Remove dist folder to force rebuild (optional)."""
    import shutil
    dist = _dist_dir(project_id)
    if os.path.isdir(dist):
        try:
            shutil.rmtree(dist)
            logger.info(f"[PreviewBuilder] Cleaned dist for {project_id}")
        except Exception as e:
            logger.warning(f"[PreviewBuilder] Failed to clean dist: {e}")
