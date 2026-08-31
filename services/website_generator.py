"""
Nexus Flow AI - Website Generator Service
Responsible for:
- Creating website folders
- Creating HTML files
- Creating CSS files
- Creating JavaScript files
- Updating existing files
- Reading generated files
"""

import os
import re
import uuid
import shutil
from datetime import datetime
from services.filename_sanitizer import sanitize_filepath

# Base directory for generated sites
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATED_SITES_DIR = os.path.join(BASE_DIR, "generated_sites")

# Allowed file extensions for generated files
ALLOWED_EXTENSIONS = {".html", ".css", ".js", ".md", ".txt", ".json"}

# Safe filenames for generated websites
SAFE_FILENAMES = {
    "index.html", "about.html", "contact.html", "menu.html", "services.html",
    "portfolio.html", "blog.html", "gallery.html", "projects.html",
    "style.css", "script.js", "styles.css", "main.css", "app.js", "main.js"
}


def ensure_generated_sites_dir():
    """Ensure the generated_sites directory exists."""
    os.makedirs(GENERATED_SITES_DIR, exist_ok=True)
    return GENERATED_SITES_DIR


def _get_project_dir(project_id):
    """Get the project directory path, validating the project ID."""
    if not project_id or not isinstance(project_id, str):
        raise ValueError("Invalid project ID")

    # Validate project ID format (UUID or similar safe format)
    if not re.match(r'^[a-zA-Z0-9_-]+$', project_id):
        raise ValueError("Invalid project ID format")

    ensure_generated_sites_dir()
    project_dir = os.path.join(GENERATED_SITES_DIR, f"project_{project_id}")

    # Prevent path traversal
    real_project_dir = os.path.realpath(project_dir)
    real_base_dir = os.path.realpath(GENERATED_SITES_DIR)
    if not real_project_dir.startswith(real_base_dir):
        raise ValueError("Invalid project directory path")

    return project_dir


def _is_safe_filename(filename):
    """Validate that a filename is safe for generated websites."""
    if not filename or not isinstance(filename, str):
        return False

    # No path traversal
    if ".." in filename:
        return False

    # Allow features/ subdirectory for reusable feature modules
    if filename.startswith("features/"):
        basename = filename[len("features/"):]
        if "/" in basename or "\\" in basename:
            return False
        if not re.match(r'^[a-zA-Z0-9_-]+\.js$', basename):
            return False
        return True

    # No path separators for top-level files
    if "/" in filename or "\\" in filename:
        return False

    # Must have allowed extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False

    # Only allow alphanumeric, dash, underscore, dot
    if not re.match(r'^[a-zA-Z0-9_-]+\.(html|css|js|md|txt|json)$', filename):
        return False

    return True


def create_project(project_id, files=None, metadata=None):
    """
    Create a new project directory and write its files.
    
    Args:
        project_id: Unique project ID
        files: Dict of {filename: content}
        metadata: Dict of metadata to store in metadata.json
    
    Returns:
        Dict with project info
    """
    project_dir = _get_project_dir(project_id)
    os.makedirs(project_dir, exist_ok=True)

    if files:
        write_files(project_id, files)

    # Write metadata
    if metadata is None:
        metadata = {}
    metadata.setdefault("project_id", project_id)
    metadata.setdefault("created_at", datetime.utcnow().isoformat())
    metadata.setdefault("updated_at", datetime.utcnow().isoformat())

    metadata_path = os.path.join(project_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        import json
        json.dump(metadata, f, indent=2)

    return {"project_id": project_id, "directory": project_dir, "metadata": metadata}


def write_files(project_id, files):
    """
    Write multiple files to a project directory.
    
    Args:
        project_id: Unique project ID
        files: Dict of {filename: content}
    
    Returns:
        List of written filenames
    """
    if not isinstance(files, dict):
        raise ValueError("Files must be a dict of {filename: content}")

    project_dir = _get_project_dir(project_id)
    os.makedirs(project_dir, exist_ok=True)

    written_files = []
    for filename, content in files.items():
        safe_name = sanitize_filepath(filename)
        filepath = os.path.join(project_dir, safe_name)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        written_files.append(safe_name)

    return written_files


def write_file(project_id, filename, content):
    """Write a single file to a project directory."""
    safe_name = sanitize_filepath(filename)

    project_dir = _get_project_dir(project_id)
    os.makedirs(project_dir, exist_ok=True)

    filepath = os.path.join(project_dir, safe_name)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


def read_file(project_id, filename):
    """Read a file from a project directory."""
    if not _is_safe_filename(filename):
        raise ValueError(f"Unsafe filename: {filename}")

    project_dir = _get_project_dir(project_id)
    filepath = os.path.join(project_dir, filename)

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filename}")

    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def list_files(project_id):
    """List all files in a project directory, including subdirectories like features/."""
    project_dir = _get_project_dir(project_id)

    if not os.path.exists(project_dir):
        return []

    files = []
    for root, dirs, filenames in os.walk(project_dir):
        for entry in filenames:
            if entry == "metadata.json":
                continue
            filepath = os.path.join(root, entry)
            rel_path = os.path.relpath(filepath, project_dir)
            # Normalize path separators for cross-platform consistency
            rel_path = rel_path.replace("\\", "/")
            files.append({
                "filename": rel_path,
                "size": os.path.getsize(filepath),
                "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
            })
    return files


def read_all_files(project_id):
    """Read all project files into a dict of {filename: content}."""
    files = list_files(project_id)
    result = {}
    for f in files:
        try:
            result[f["filename"]] = read_file(project_id, f["filename"])
        except Exception:
            continue
    return result


def update_file(project_id, filename, content):
    """Update an existing file in a project directory."""
    return write_file(project_id, filename, content)


def delete_file(project_id, filename):
    """Delete a file from a project directory."""
    if not _is_safe_filename(filename):
        raise ValueError(f"Unsafe filename: {filename}")

    project_dir = _get_project_dir(project_id)
    filepath = os.path.join(project_dir, filename)

    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def delete_project(project_id):
    """Delete an entire project directory."""
    project_dir = _get_project_dir(project_id)
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)
        return True
    return False


def project_exists(project_id):
    """Check if a project directory exists."""
    try:
        project_dir = _get_project_dir(project_id)
        return os.path.exists(project_dir)
    except Exception:
        return False


def generate_project_id():
    """Generate a unique project ID."""
    return uuid.uuid4().hex[:16]