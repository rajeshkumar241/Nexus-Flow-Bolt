"""
Nexus Flow — AI Debugger
Analyzes code errors and generates fixes.
"""
import logging

logger = logging.getLogger(__name__)

DEBUG_SYSTEM_PROMPT = """You are an expert debugger. Analyze the code and find issues.

Given project files and optionally an error message, you should:
1. Identify the specific issue(s)
2. Explain what's wrong
3. Provide the fixed file(s)

RULES:
- Return ONLY files that need fixing
- Each file must be the COMPLETE corrected version
- Explain the fix in the "message" field

OUTPUT: Return ONLY a JSON object:
{
  "issues": [
    {"file": "path", "description": "What's wrong", "severity": "error" | "warning"}
  ],
  "fixes": {
    "path/to/file.jsx": "complete fixed file content"
  },
  "message": "Summary of what was fixed"
}

Do NOT include markdown fences. Output ONLY the JSON object."""


def debug_project(project_id, files, error_message=None):
    """
    Analyze project files for issues and fix them.
    
    Args:
        project_id: Project identifier
        files: dict of {filepath: content}
        error_message: Optional error message to help diagnose
    
    Returns:
        dict: {"issues": [...], "fixes": {...}, "message": str}
    """
    from services.llm_service import call_llm_json

    file_context = ""
    for path, content in files.items():
        if len(content) > 6000:
            content = content[:6000] + "\n... (truncated)"
        file_context += f"\n--- {path} ---\n{content}\n"

    prompt = f"""Here are the project files:
{file_context}
"""
    if error_message:
        prompt += f"\nERROR MESSAGE: {error_message}\n"
    prompt += "\nAnalyze these files for any issues (errors, warnings, best practices, accessibility, etc.). Then fix any problems found."

    logger.info(f"[Debugger] Analyzing {project_id}...")

    try:
        result = call_llm_json(
            prompt,
            system_instruction=DEBUG_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=16384,
        )

        issues = result.get("issues", [])
        fixes = result.get("fixes", {})
        message = result.get("message", "Analysis complete.")

        # Apply fixes to files
        fixed_files = []
        for path, content in fixes.items():
            if isinstance(content, str) and content.strip():
                files[path] = content
                fixed_files.append(path)

        if fixed_files:
            message += f" Fixed: {', '.join(fixed_files)}"

        logger.info(f"[Debugger] Found {len(issues)} issues, fixed {len(fixed_files)} files")
        return {
            "issues": issues,
            "fixes": fixes,
            "files": files,
            "message": message,
        }

    except Exception as e:
        logger.error(f"[Debugger] Analysis failed: {e}")
        return {
            "issues": [],
            "fixes": {},
            "files": files,
            "message": f"Debug analysis failed: {e}",
        }
