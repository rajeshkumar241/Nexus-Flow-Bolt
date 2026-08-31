"""
Nexus Flow v2 — Project Generator
Single responsibility: create React/Vite project structure, validate, zip & persist.

Spec functions:
 - create_project_structure(project_id, plan, files)
 - validate_generated_files(files)
 - create_zip_export(project_id)

Store: generated_projects/{project_id}/
"""
import os
import json
import logging
import zipfile
from io import BytesIO
from datetime import datetime

from services.filename_sanitizer import sanitize_filepath

logger = logging.getLogger(__name__)

PROJECTS_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_projects")

# Required files for a valid React/Vite project (spec requires src/index.css)
REQUIRED_FILES = ["package.json", "vite.config.js", "index.html", "src/main.jsx", "src/App.jsx", "src/index.css"]
REQUIRED_DIRS = ["src/pages", "src/components"]

# JSX validation helper (mirror code_generator)
import re as _re
def _is_valid_jsx_file(path: str, content: str) -> bool:
    if not content or not content.strip() or len(content.strip()) < 40:
        return False
    text = content.strip()
    if "Slide-over quick cart drawer" in text and "<" not in text:
        return False
    if text.startswith("CartDrawer") and "<" not in text and "export" not in text:
        return False
    # Strict only for components/pages/App.jsx
    is_strict = path.startswith("src/components/") or path.startswith("src/pages/") or path == "src/App.jsx"
    if is_strict:
        has_export = "export default" in text or "export function" in text
        has_jsx = bool(_re.search(r"<[a-zA-Z][a-zA-Z0-9]*(\s|>|/)", text))
        has_return = "return" in text and "(" in text
        if not (has_export and has_jsx and has_return):
            return False
    else:
        # lenient for vite.config, main.jsx, css, json
        if path.endswith((".jsx", ".js")) and "<" not in text and "import" not in text and "export" not in text and "defineConfig" not in text and "ReactDOM" not in text:
            if "{" not in text:
                return False
    return True


def _project_dir(project_id):
    return os.path.join(PROJECTS_ROOT, str(project_id))


def validate_generated_files(files):
    """
    Validate generated files dict.

    Returns: (is_valid: bool, errors: list, warnings: list)
    - Checks REQUIRED_FILES exist and non-empty
    - Checks filenames are sanitized (no traversal / illegal chars)
    - Checks package.json is valid JSON with react deps
    - Checks at least one page/component exists
    """
    errors = []
    warnings = []

    if not isinstance(files, dict) or not files:
        return False, ["No files generated"], warnings

    # Check required files (allow globals.css as alias for index.css)
    for req in REQUIRED_FILES:
        if req == "src/index.css":
            # accept either src/index.css or src/styles/globals.css
            if req not in files and "src/styles/globals.css" not in files:
                errors.append(f"Missing required file: {req} (or src/styles/globals.css)")
            elif (req in files and not files[req].strip()) and ("src/styles/globals.css" not in files or not files.get("src/styles/globals.css","").strip()):
                errors.append(f"Required file empty: {req}")
            continue
        if req not in files:
            found = any(k == req or k.replace("\\", "/") == req for k in files.keys())
            if not found:
                errors.append(f"Missing required file: {req}")
        else:
            if not files[req] or not files[req].strip():
                errors.append(f"Required file empty: {req}")

    # Validate .jsx files contain executable JSX (reject docs like CartDrawer description)
    for path, content in list(files.items()):
        if path.endswith((".jsx",)):
            if not _is_valid_jsx_file(path, content):
                errors.append(f"Invalid JSX (docs not code) rejected: {path} -> {content[:80]!r}")

    # Validate package.json
    if "package.json" in files:
        try:
            pkg = json.loads(files["package.json"])
            if "dependencies" not in pkg or "react" not in pkg.get("dependencies", {}):
                warnings.append("package.json missing react dependency")
            if "scripts" not in pkg:
                warnings.append("package.json missing scripts")
        except json.JSONDecodeError as e:
            errors.append(f"package.json invalid JSON: {e}")

    # Validate vite.config.js exists and mentions vite
    if "vite.config.js" in files:
        if "vite" not in files["vite.config.js"].lower():
            warnings.append("vite.config.js does not mention vite")

    # Check sanitized filenames
    for path in files.keys():
        safe = sanitize_filepath(path)
        if safe != path:
            warnings.append(f"Filename sanitized: '{path}' -> '{safe}'")
        if ".." in path or path.startswith("/"):
            errors.append(f"Invalid path (traversal): {path}")

    # Check at least one page/component
    has_page = any(k.startswith("src/pages/") for k in files.keys())
    has_component = any(k.startswith("src/components/") for k in files.keys())
    if not has_page:
        warnings.append("No pages generated (src/pages/*)")
    if not has_component:
        warnings.append("No components generated (src/components/*)")

    # Size check
    total_chars = sum(len(v) for v in files.values() if isinstance(v, str))
    if total_chars < 1000:
        warnings.append(f"Generated files very small ({total_chars} chars)")

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def create_project_structure(project_id, plan=None, files=None):
    """
    Create project structure on disk at generated_projects/{project_id}/

    Args:
        project_id: str unique id
        plan: optional architecture plan dict (saved as plan.json)
        files: dict of {filepath: content}

    Returns: dict metadata
    """
    if files is None:
        files = {}

    # Validate first
    is_valid, errors, warnings = validate_generated_files(files)
    if not is_valid:
        logger.warning(f"[ProjectGenerator] Validation failed for {project_id}: {errors}")
        # Do not block creation - log and continue, caller can handle

    if warnings:
        logger.info(f"[ProjectGenerator] Warnings for {project_id}: {warnings}")

    base = _project_dir(project_id)
    os.makedirs(base, exist_ok=True)

    # Write files
    for filepath, content in files.items():
        safe_path = sanitize_filepath(filepath)
        full_path = os.path.join(base, safe_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    # Save plan if provided
    if plan:
        with open(os.path.join(base, "plan.json"), "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)

    # Metadata
    meta = {
        "project_id": str(project_id),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "file_count": len(files),
        "files": list(files.keys()),
        "validation": {"valid": is_valid, "errors": errors, "warnings": warnings},
    }
    if plan:
        meta["project_name"] = plan.get("project_name")
        meta["project_type"] = plan.get("project_type", "react")
        meta["prompt"] = plan.get("description", "")

    with open(os.path.join(base, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    logger.info(f"[ProjectGenerator] Created {project_id}: {len(files)} files, valid={is_valid}")
    return meta


def create_zip_export(project_id):
    """
    Create ZIP export of project at generated_projects/{project_id}/
    Returns: BytesIO buffer or None if not found
    """
    base = _project_dir(project_id)
    if not os.path.exists(base):
        logger.warning(f"[ProjectGenerator] ZIP export failed: {project_id} not found")
        return None

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, filenames in os.walk(base):
            # Exclude versions dir and internal files
            dirs[:] = [d for d in dirs if d != "versions"]
            for fname in filenames:
                if fname in ("metadata.json", "plan.json"):
                    continue
                full = os.path.join(root, fname)
                arc = os.path.relpath(full, base)
                zf.write(full, arc)

    buf.seek(0)
    logger.info(f"[ProjectGenerator] ZIP created for {project_id}: {buf.getbuffer().nbytes} bytes")
    return buf


# Compatibility aliases for existing project_manager callers
def create_project(project_id, files, metadata=None):
    """Alias to create_project_structure for backward compat."""
    plan = None
    if metadata and "plan" in metadata:
        plan = metadata["plan"]
    return create_project_structure(project_id, plan=plan, files=files)


def build_zip(project_id):
    """Alias to create_zip_export for backward compat."""
    return create_zip_export(project_id)
