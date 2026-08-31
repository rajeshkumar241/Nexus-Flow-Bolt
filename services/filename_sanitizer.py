"""
Nexus Flow — Filename Sanitizer
Ensures all generated filenames are valid on Windows, macOS, and Linux.
"""
import re
import os
import logging

logger = logging.getLogger(__name__)

# Characters forbidden on Windows (and problematic on other OS)
INVALID_CHARS = r'[<>:"|?*\x00-\x1f]'

# Windows reserved device names
RESERVED_NAMES = {
    "con", "prn", "aux", "nul",
    "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
    "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9",
}


def sanitize_filename(name):
    """
    Sanitize a single filename component (not a full path).
    
    Rules:
    - Remove invalid characters: < > : " | ? * and control chars
    - Convert route params: :id -> [id], :slug -> [slug]
    - Collapse multiple underscores
    - Strip leading/trailing dots, spaces, and underscores on each segment
    - Replace reserved Windows names with prefixed versions
    - Ensure non-empty result
    
    Returns:
        str: Safe filename
    """
    if not name or not name.strip():
        return "index"

    # Convert route param syntax: :param -> [param]
    name = re.sub(r':([a-zA-Z_][a-zA-Z0-9_]*)', r'[\1]', name)

    # Remove invalid characters
    name = re.sub(INVALID_CHARS, '_', name)

    # Collapse multiple underscores/spaces into single underscore
    name = re.sub(r'[_\s]+', '_', name)

    # Strip leading/trailing dots, spaces, and underscores
    name = name.strip('. _')

    # Strip trailing underscores from base name (before extension)
    base, ext = os.path.splitext(name)
    base = base.rstrip('_. ')
    if not base:
        base = "index"
    name = base + ext

    # Handle reserved Windows names
    base_lower = os.path.splitext(name)[0].lower()
    if base_lower in RESERVED_NAMES:
        name = '_' + name

    # Fallback if everything was stripped
    if not name:
        name = "index"

    return name


def sanitize_filepath(filepath):
    """
    Sanitize a full relative file path (e.g. 'src/pages/:id.jsx').
    
    Splits into segments, sanitizes each, and rejoins.
    Preserves directory structure while fixing each component.
    Filters empty segments from double slashes.
    
    Returns:
        str: Safe relative file path
    """
    if not filepath or not filepath.strip():
        return "index.html"

    # Normalize forward slashes, then split
    filepath = filepath.replace("\\", "/")
    parts = filepath.split("/")

    sanitized = []
    changed = False
    for part in parts:
        # Skip empty segments from double slashes
        if not part.strip():
            changed = True
            continue
        safe = sanitize_filename(part)
        if safe != part:
            changed = True
        sanitized.append(safe)

    # Rebuild path — use '/' for cross-platform consistency in generated code
    result = "/".join(sanitized)

    if changed:
        logger.info(f"[Sanitize] '{filepath}' -> '{result}'")

    return result


def is_safe_filename(name):
    """Check if a filename is already safe (no sanitization needed)."""
    return sanitize_filename(name) == name


def is_safe_path(filepath):
    """Check if a full path is already safe."""
    return sanitize_filepath(filepath) == filepath
