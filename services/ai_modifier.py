"""
Nexus Flow — AI Modifier
Reads existing project files and applies targeted modifications.
"""
import json
import logging

logger = logging.getLogger(__name__)

MODIFY_SYSTEM_PROMPT = """You are an expert React/HTML developer. You modify existing project files based on a user request.

RULES:
1. PRESERVE everything that already exists. Only change what the user explicitly asked for.
2. Return COMPLETE updated files, not fragments.
3. If no change is needed for a file, do NOT include it in the response.
4. Maintain the existing design system, color scheme, fonts, and layout unless asked to change them.
5. Only return files that actually need modification.

OUTPUT: Return ONLY a JSON object where each key is a file path and each value is the COMPLETE updated file content.
Example:
{
  "src/components/Navbar.jsx": "import React from 'react';...",
  "src/styles/globals.css": ":root { ... }"
}

Do NOT include markdown fences. Output ONLY the JSON object."""


def modify_project(project_id, request, files):
    """
    Modify project files based on user request.
    
    Args:
        project_id: Project identifier
        request: User's modification request
        files: dict of {filepath: content} (current files)
    
    Returns:
        dict: {"changed_files": [...], "files": {filepath: content}, "message": str}
    """
    from services.llm_service import call_llm_json

    # Build context with all files
    file_context = ""
    for path, content in files.items():
        # Truncate very large files
        if len(content) > 8000:
            content = content[:8000] + "\n... (truncated)"
        file_context += f"\n--- {path} ---\n{content}\n"

    prompt = f"""Here are the current project files:
{file_context}

USER REQUEST: {request}

Modify the necessary files to fulfill this request. Return ONLY the files that changed."""

    logger.info(f"[Modifier] Modifying {project_id}: {request[:80]}...")

    try:
        changed = call_llm_json(
            prompt,
            system_instruction=MODIFY_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=16384,
        )

        # Determine which files actually changed
        changed_files = []
        for path, new_content in changed.items():
            if isinstance(new_content, str) and new_content.strip():
                old_content = files.get(path, "")
                if new_content != old_content:
                    changed_files.append(path)
                    files[path] = new_content

        message = f"Modified {len(changed_files)} file(s): {', '.join(changed_files)}" if changed_files else "No files needed modification."
        logger.info(f"[Modifier] {message}")

        return {
            "changed_files": changed_files,
            "files": files,
            "message": message,
        }

    except Exception as e:
        logger.error(f"[Modifier] Modification failed: {e}")
        return {
            "changed_files": [],
            "files": files,
            "message": f"Modification failed: {e}",
        }
