"""
Nexus Flow — Project Manager
Disk-based project storage, versioning, and file I/O.
"""
import os
import json
import shutil
import zipfile
import time
import logging
from datetime import datetime
from io import BytesIO
from services.filename_sanitizer import sanitize_filepath

logger = logging.getLogger(__name__)

PROJECTS_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_projects")


def _project_dir(project_id):
    return os.path.join(PROJECTS_ROOT, str(project_id))


def _versions_dir(project_id):
    return os.path.join(_project_dir(project_id), "versions")


def create_project(project_id, files, metadata=None):
    """
    Create a project on disk.
    
    Args:
        project_id: Unique project identifier
        files: dict of {filepath: content}
        metadata: optional dict to save as metadata.json
    """
    base = _project_dir(project_id)
    os.makedirs(base, exist_ok=True)

    for filepath, content in files.items():
        safe_path = sanitize_filepath(filepath)
        full_path = os.path.join(base, safe_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    # Save metadata
    meta = {
        "project_id": project_id,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "file_count": len(files),
        "files": list(files.keys()),
    }
    if metadata:
        meta.update(metadata)

    with open(os.path.join(base, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    logger.info(f"[Project] Created {project_id}: {len(files)} files")
    return meta


def read_project(project_id):
    """Read all files from a project."""
    base = _project_dir(project_id)
    if not os.path.exists(base):
        return None

    files = {}
    for root, dirs, filenames in os.walk(base):
        # Skip versions directory and metadata
        dirs[:] = [d for d in dirs if d != "versions"]
        for fname in filenames:
            if fname == "metadata.json":
                continue
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, base)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    files[rel_path] = f.read()
            except UnicodeDecodeError:
                pass  # Skip binary files

    return files


def read_file(project_id, filepath):
    """Read a single file from a project."""
    full_path = os.path.join(_project_dir(project_id), filepath)
    if not os.path.exists(full_path):
        return None
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        return None


def update_file(project_id, filepath, content):
    """Update or create a single file in a project."""
    safe_path = sanitize_filepath(filepath)
    full_path = os.path.join(_project_dir(project_id), safe_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Update metadata
    _touch_metadata(project_id)


def delete_file(project_id, filepath):
    """Delete a single file from a project."""
    safe_path = sanitize_filepath(filepath)
    full_path = os.path.join(_project_dir(project_id), safe_path)
    if os.path.exists(full_path):
        os.remove(full_path)
        _touch_metadata(project_id)


def list_projects(user_email=None):
    """List all projects, optionally filtered by user."""
    projects = []
    if not os.path.exists(PROJECTS_ROOT):
        return projects

    for pid in os.listdir(PROJECTS_ROOT):
        meta_path = os.path.join(PROJECTS_ROOT, pid, "metadata.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if user_email and meta.get("user_email") != user_email:
                    continue
                projects.append(meta)
            except (json.JSONDecodeError, IOError):
                pass

    projects.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return projects


def get_metadata(project_id):
    """Get project metadata."""
    meta_path = os.path.join(_project_dir(project_id), "metadata.json")
    if not os.path.exists(meta_path):
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def save_metadata(project_id, metadata):
    """Update project metadata."""
    base = _project_dir(project_id)
    os.makedirs(base, exist_ok=True)
    meta_path = os.path.join(base, "metadata.json")
    existing = {}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    existing.update(metadata)
    existing["updated_at"] = datetime.utcnow().isoformat()
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


def _touch_metadata(project_id):
    """Update file list and timestamp in metadata."""
    files = read_project(project_id)
    save_metadata(project_id, {
        "file_count": len(files) if files else 0,
        "files": list(files.keys()) if files else [],
    })


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------

def create_version(project_id):
    """Snapshot current project state to versions/v<N>/."""
    base = _project_dir(project_id)
    ver_dir = _versions_dir(project_id)
    os.makedirs(ver_dir, exist_ok=True)

    # Find next version number
    existing = [d for d in os.listdir(ver_dir) if d.startswith("v")]
    nums = []
    for d in existing:
        try:
            nums.append(int(d[1:]))
        except ValueError:
            pass
    next_ver = max(nums, default=0) + 1
    ver_path = os.path.join(ver_dir, f"v{next_ver}")

    # Copy current files
    files = read_project(project_id)
    if files:
        for filepath, content in files.items():
            safe_path = sanitize_filepath(filepath)
            full = os.path.join(ver_path, safe_path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)

        # Save version metadata
        with open(os.path.join(ver_path, "version.json"), "w", encoding="utf-8") as f:
            json.dump({
                "version": next_ver,
                "created_at": datetime.utcnow().isoformat(),
                "file_count": len(files),
            }, f, indent=2)

    logger.info(f"[Project] Version v{next_ver} created for {project_id}")
    return next_ver


def list_versions(project_id):
    """List all versions of a project."""
    ver_dir = _versions_dir(project_id)
    if not os.path.exists(ver_dir):
        return []

    versions = []
    for d in sorted(os.listdir(ver_dir)):
        if d.startswith("v"):
            vpath = os.path.join(ver_dir, d, "version.json")
            if os.path.exists(vpath):
                try:
                    with open(vpath, "r", encoding="utf-8") as f:
                        versions.append(json.load(f))
                except (json.JSONDecodeError, IOError):
                    pass
    return versions


def restore_version(project_id, version_num):
    """Restore a project to a specific version."""
    ver_path = os.path.join(_versions_dir(project_id), f"v{version_num}")
    if not os.path.exists(ver_path):
        return False

    # Read version files
    files = {}
    for root, dirs, filenames in os.walk(ver_path):
        dirs[:] = [d for d in dirs if d != "versions"]
        for fname in filenames:
            if fname == "version.json":
                continue
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, ver_path)
            try:
                with open(full, "r", encoding="utf-8") as f:
                    files[rel] = f.read()
            except UnicodeDecodeError:
                pass

    if files:
        # Clear current project (except versions)
        base = _project_dir(project_id)
        for item in os.listdir(base):
            if item == "versions":
                continue
            item_path = os.path.join(base, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

        # Write restored files
        for filepath, content in files.items():
            safe_path = sanitize_filepath(filepath)
            full = os.path.join(base, safe_path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)

        _touch_metadata(project_id)
        logger.info(f"[Project] Restored {project_id} to v{version_num}")
        return True
    return False


# ---------------------------------------------------------------------------
# ZIP export
# ---------------------------------------------------------------------------

def build_zip(project_id):
    """Build a ZIP archive of the project."""
    base = _project_dir(project_id)
    if not os.path.exists(base):
        return None

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, filenames in os.walk(base):
            dirs[:] = [d for d in dirs if d != "versions"]
            for fname in filenames:
                full = os.path.join(root, fname)
                arc = os.path.relpath(full, base)
                zf.write(full, arc)

    buf.seek(0)
    return buf


def project_exists(project_id):
    """Check if a project exists on disk."""
    return os.path.exists(_project_dir(project_id))


def delete_project(project_id):
    """Delete a project from disk."""
    base = _project_dir(project_id)
    if os.path.exists(base):
        shutil.rmtree(base)
        logger.info(f"[Project] Deleted {project_id}")
