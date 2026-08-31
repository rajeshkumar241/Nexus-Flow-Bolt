"""
Nexus Flow — Jarvis AI Development Assistant Service
Advanced development assistant integrated with AIProviderManager,
project context, memory, error analysis and auto-fix.
"""
import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# -------------------------------------------------------------
# Persona per mode
# -------------------------------------------------------------
JARVIS_PERSONA = """You are Jarvis, an advanced AI development assistant for Nexus Flow AI Website Builder.
Stack: Flask + Jinja2 + MongoDB + AIProviderManager (Emergent AI > Groq/Llama 3.3 > Gemini > DeepSeek > OpenAI)
Primary intelligence: Emergent AI for intent understanding, project analysis, and fix suggestions (fallback to Groq/Gemini/DeepSeek if Emergent unavailable).
You help with: website generation, code editing, live preview debugging, project management, error fixing.
Be concise, technical, helpful. Use plain language. Provide actionable steps and code when useful."""

MODE_PERSONAS = {
    "chat": JARVIS_PERSONA,
    "code": """You are Jarvis in CODE mode. Focus on explaining, generating and modifying code.
Explain files clearly, suggest clean HTML/CSS/JS changes, show snippets with file paths.""",
    "debug": """You are Jarvis in DEBUG mode. Analyze errors, build logs, preview failures.
For each error provide: Problem / Cause / Solution / Auto Fix. Be precise.""",
    "analyze": """You are Jarvis in ANALYZE mode. Review generated projects for structure, responsiveness, accessibility, performance.
Return sections: Overview, Files, Issues, Suggestions."""
}

# -------------------------------------------------------------
# Memory helpers (jarvis_memory collection)
# -------------------------------------------------------------
def _memory_collection():
    try:
        from services.mongo_connection import get_db
        return get_db().jarvis_memory
    except Exception as e:
        logger.debug(f"[Jarvis] memory collection unavailable: {e}")
        return None

def _now():
    return datetime.utcnow()


# -------------------------------------------------------------
# Core Service
# -------------------------------------------------------------
class JarvisService:
    """Advanced Jarvis development assistant."""

    def __init__(self, user_id: Optional[str] = None, project_id: Optional[str] = None):
        self.user_id = user_id
        self.project_id = project_id
        self.mode = "chat"

    # -- Memory -------------------------------------------------
    def _load_memory(self) -> Dict[str, Any]:
        col = _memory_collection()
        if not col or not self.user_id:
            return {}
        try:
            doc = col.find_one({"user_id": self.user_id, "project_id": self.project_id or "global"})
            return doc or {}
        except Exception:
            return {}

    def _save_memory(self, conversation_history=None, project_context=None, preferences=None, last_actions=None):
        col = _memory_collection()
        if not col or not self.user_id:
            return
        try:
            key = {"user_id": self.user_id, "project_id": self.project_id or "global"}
            update = {"$set": {"updated_at": _now()},
                      "$setOnInsert": {"created_at": _now(), "user_id": self.user_id, "project_id": self.project_id or "global"}}
            if conversation_history is not None:
                update["$set"]["conversation_history"] = conversation_history[-40:]
            if project_context is not None:
                update["$set"]["project_context"] = project_context
            if preferences is not None:
                update["$set"]["preferences"] = preferences
            if last_actions is not None:
                update["$set"]["last_actions"] = last_actions[-20:]
            col.update_one(key, update, upsert=True)
        except Exception as e:
            logger.debug(f"[Jarvis] save memory failed: {e}")

    def get_memory(self, user_id=None, project_id=None):
        uid = user_id or self.user_id
        pid = project_id or self.project_id
        col = _memory_collection()
        if not col or not uid:
            return {"user_id": uid, "project_id": pid, "conversation_history": [], "project_context": {}, "preferences": {}, "last_actions": []}
        try:
            doc = col.find_one({"user_id": uid, "project_id": pid or "global"})
            if not doc:
                return {"user_id": uid, "project_id": pid, "conversation_history": [], "project_context": {}, "preferences": {}, "last_actions": []}
            doc["id"] = str(doc.get("_id",""))
            return doc
        except Exception:
            return {"user_id": uid, "project_id": pid, "conversation_history": [], "project_context": {}, "preferences": {}, "last_actions": []}

    # -- Project Context ----------------------------------------
    def _build_project_context(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        pid = project_id or self.project_id
        if not pid:
            return {"framework": "Unknown", "files": [], "file_count": 0, "project": None}
        project = None
        files = {}
        framework = "Static HTML/CSS/JS"
        # Try mongo project
        try:
            from services.mongo_connection import get_db
            from bson.objectid import ObjectId
            db = get_db()
            # Try by ObjectId first, then by raw string project_id
            try:
                project = db.projects.find_one({"_id": ObjectId(pid)})
            except Exception:
                project = None
            if not project:
                project = db.projects.find_one({"_id": pid})
            if not project and self.user_id:
                project = db.projects.find_one({"_id": ObjectId(pid), "user_email": self.user_id}) if len(pid)==24 else db.projects.find_one({"user_email": self.user_id})
        except Exception as e:
            logger.debug(f"[Jarvis] project mongo lookup failed: {e}")

        # Try filesystem generated_sites
        try:
            from services.website_generator import read_all_files, list_files, project_exists
            if project_exists(pid):
                files = read_all_files(pid)
                fl = list_files(pid)
                framework = "Static HTML/CSS/JS"
                # Detect framework via files
                if any("package.json" in f for f in files):
                    import json as _j
                    try:
                        pkg = _j.loads(files.get("package.json","{}"))
                        deps = {**pkg.get("dependencies",{}), **pkg.get("devDependencies",{})}
                        if "react" in deps or "vite" in deps:
                            framework = "React/Vite"
                        elif "next" in deps:
                            framework = "Next.js"
                    except: pass
        except Exception:
            pass

        # Fallback: extract from project.website_state/files
        if not files and project and isinstance(project.get("website_state"), dict):
            ws = project["website_state"]
            files = ws.get("files") or {}
            if not files:
                # legacy html_code
                if project.get("html_code"):
                    files["index.html"] = project.get("html_code","")[:5000]
                if project.get("css_code"):
                    files["styles.css"] = project.get("css_code","")[:5000]

        file_list = list(files.keys()) if isinstance(files, dict) else []
        return {
            "framework": framework,
            "files": file_list,
            "file_count": len(file_list),
            "project": {"id": str(project.get("_id")) if project and project.get("_id") else pid, "title": project.get("title") if project else "Untitled", "prompt": project.get("prompt") if project else ""} if project else None,
            "files_content": {k: v[:4000] for k,v in list(files.items())[:6]} if files else {}
        }

    def analyze_project(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        pid = project_id or self.project_id
        ctx = self._build_project_context(pid)
        issues = []
        suggestions = []
        build_errors = []
        # Check files
        files = ctx.get("files", [])
        if not files:
            issues.append({"type":"error","message":"No generated files found for this project","file":""})
            suggestions.append("Generate a website first, then analyze.")
        else:
            # Check preview blank
            try:
                from services.website_generator import read_all_files
                all_files = read_all_files(pid) if pid else {}
                html = all_files.get("index.html","")
                if html and len(html.strip()) < 100:
                    issues.append({"type":"warning","message":"index.html is very small - preview may be blank","file":"index.html"})
            except Exception: pass
            # Check for missing css/js
            if "index.html" not in files and "index.htm" not in files:
                issues.append({"type":"warning","message":"Missing index.html","file":""})
            if not any(f.endswith(".css") for f in files):
                suggestions.append("Consider adding styles.css for better UI.")

        # Check generation logs
        try:
            from services.mongo_connection import get_db
            db = get_db()
            logs = list(db.generation_logs.find({"project_id": pid}).sort("timestamp", -1).limit(5)) if pid else []
            for lg in logs:
                if lg.get("status") == "failed":
                    build_errors.append({"stage": lg.get("stage"), "error": lg.get("error_message") or lg.get("details")})
                    issues.append({"type":"error","message": f"Build failed at {lg.get('stage')}: {lg.get('error_message','')[:120]}","file":""})
        except Exception: pass

        # Check Flask logs via LLM? simplified
        analysis = {
            "project_id": pid,
            "framework": ctx["framework"],
            "files": files,
            "file_count": ctx["file_count"],
            "issues": issues,
            "suggestions": suggestions,
            "build_errors": build_errors,
            "context": ctx
        }
        # Save to memory
        self._save_memory(project_context=ctx, last_actions=[{"action":"analyze","project_id":pid,"at":_now().isoformat()}])
        return analysis

    def explain_code(self, file_path: Optional[str] = None, code: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
        pid = project_id or self.project_id
        if not code and file_path and pid:
            try:
                from services.website_generator import read_file
                code = read_file(pid, file_path)
            except Exception as e:
                return {"explanation": f"Could not read {file_path}: {e}", "file_path": file_path}
        if not code:
            return {"explanation": "No code provided to explain.", "file_path": file_path}
        prompt = f"Explain this code from file {file_path or 'unknown'}:\n\n{code[:6000]}\n\nProvide: Purpose, Key parts, How it works, Suggestions."
        sys = MODE_PERSONAS["code"]
        try:
            from services.llm_service import call_llm
            resp = call_llm(prompt, system_instruction=sys, temperature=0.4, max_tokens=2048)
        except Exception as e:
            resp = f"Explain failed (LLM unavailable): {e}\n\nCode preview:\n{code[:800]}"
        return {"explanation": resp, "file_path": file_path}

    def fix_error(self, error: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        pid = project_id or self.project_id
        ctx = self._build_project_context(pid)
        # Classify error
        problem, cause, solution, auto_fix = self._classify_error(error)
        fixed_files = {}
        explanation = f"**Problem:** {problem}\n**Cause:** {cause}\n**Solution:** {solution}"
        # Attempt auto-fix for preview blank / build errors via LLM
        if auto_fix and ctx.get("files_content"):
            try:
                from services.llm_service import call_llm
                prompt = f"Project files: {json.dumps(ctx.get('files_content'), indent=2)[:5000]}\n\nError: {error}\n\nCause: {cause}\nProvide fixed files as JSON: {{\"fixed_files\": {{\"path\": \"content\"}}, \"explanation\": \"...\"}}"
                sys = MODE_PERSONAS["debug"]
                raw = call_llm(prompt, system_instruction=sys, temperature=0.3, max_tokens=4096)
                # Try parse json
                m = re.search(r"\{[\s\S]*\}", raw)
                if m:
                    parsed = json.loads(m.group(0))
                    fixed_files = parsed.get("fixed_files", {})
                    explanation = parsed.get("explanation", explanation)
            except Exception as e:
                logger.debug(f"[Jarvis] fix auto-fix LLM failed: {e}")
        return {"fixed_files": fixed_files, "explanation": explanation, "problem": problem, "cause": cause, "solution": solution, "auto_fix": auto_fix}

    def modify_project(self, request: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        pid = project_id or self.project_id
        if not pid:
            return {"error": "No project selected. Generate or select a project first.", "files_changed": []}
        ctx = self._build_project_context(pid)
        files_content = ctx.get("files_content", {})
        if not files_content:
            return {"error": "No files found for project", "files_changed": []}
        prompt = f"""You are Nexus Flow project modifier.
Current project files (truncated):
{json.dumps(files_content, indent=2)[:7000]}

User request: {request}

Task: Modify affected files to fulfill request. Return JSON only:
{{"files_changed": ["path"], "fixed_files": {{"path": "full new content"}}, "explanation": "what changed"}}
Keep other files unchanged. Preserve dark theme (#070b16)."""
        sys = MODE_PERSONAS["code"]
        try:
            from services.llm_service import call_llm
            raw = call_llm(prompt, system_instruction=sys, temperature=0.4, max_tokens=8192)
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                parsed = json.loads(m.group(0))
                fixed_files = parsed.get("fixed_files", {})
                files_changed = parsed.get("files_changed", list(fixed_files.keys()))
                explanation = parsed.get("explanation", "Modified as requested")
                # Apply to storage
                applied = self._apply_file_changes(pid, fixed_files)
                return {"fixed_files": fixed_files, "files_changed": files_changed, "explanation": explanation, "applied": applied}
            else:
                return {"error": "LLM did not return JSON", "raw": raw[:1000], "files_changed": []}
        except Exception as e:
            return {"error": str(e), "files_changed": []}

    def _apply_file_changes(self, project_id: str, files: Dict[str, str]) -> bool:
        if not files:
            return False
        try:
            from services.website_generator import write_files
            from services.mongo_connection import get_db
            from bson.objectid import ObjectId
            write_files(project_id, files)
            # Also update mongo project website_state.files
            try:
                db = get_db()
                proj = None
                try:
                    proj = db.projects.find_one({"_id": ObjectId(project_id)})
                except:
                    proj = db.projects.find_one({"_id": project_id})
                if proj:
                    ws = proj.get("website_state") or {}
                    ws_files = ws.get("files") or {}
                    ws_files.update(files)
                    ws["files"] = ws_files
                    # also update html/css if index.html/styles.css
                    if "index.html" in files:
                        ws["html"] = files["index.html"]
                    db.projects.update_one({"_id": proj["_id"]}, {"$set": {"website_state": ws, "updated_at": _now()}})
            except Exception as e:
                logger.debug(f"[Jarvis] mongo file sync failed: {e}")
            return True
        except Exception as e:
            logger.debug(f"[Jarvis] apply changes failed: {e}")
            return False

    def _classify_error(self, error: str):
        e = (error or "").lower()
        if "429" in e or "quota" in e or "rate limit" in e:
            return ("API quota exceeded", "Groq/Gemini/DeepSeek rate limit or quota", "Switch to fallback model (Groq Llama or DeepSeek) via Jarvis settings. Fallback is automatic.", True)
        if "401" in e or "403" in e or "api key" in e or "unauthorized" in e:
            return ("Authentication failed", "Invalid or missing API key", "Check AI Provider Manager & set valid key for active provider.", False)
        if "preview is blank" in e or "blank" in e or "white screen" in e:
            return ("Preview blank", "Missing HTML content, CSS not loaded, or JS error", "Ensure index.html has content, CSS is linked, check browser console for JS errors.", True)
        if "build failed" in e or "vite" in e or "npm" in e:
            return ("Build failure", "Dependency or syntax error during generation", "Check generation logs, fix syntax in indicated file.", True)
        if "template not found" in e:
            return ("Template missing", "Flask render_template file not found", "Verify templates/ folder has required file.", False)
        if "connection" in e or "timeout" in e:
            return ("Connection error", "Network or provider timeout", "Retry, check internet, fallback will try next model.", True)
        return ("Unknown error", "Unclassified error", "Share full log with Jarvis for detailed analysis.", False)

    # -- Main chat --------------------------------------------
    def chat(self, message: str, project_id: Optional[str] = None, mode: str = "chat", user_id: Optional[str] = None) -> Dict[str, Any]:
        pid = project_id or self.project_id
        uid = user_id or self.user_id
        mode = (mode or "chat").lower()
        if mode not in MODE_PERSONAS:
            mode = "chat"
        # Load memory
        mem = self._load_memory()
        history = mem.get("conversation_history", [])
        # Build context
        ctx = self._build_project_context(pid) if pid else {}
        ctx_str = ""
        if ctx and ctx.get("files"):
            ctx_str = f"\nProject Context: ID={pid}, Framework={ctx.get('framework')}, Files={ctx.get('files')[:10]}, Title={ctx.get('project',{}).get('title') if ctx.get('project') else ''}"
        sys = MODE_PERSONAS[mode] + ctx_str + "\nCurrent mode: "+mode
        # Detect intent for modify/analyze/debug shortcuts
        lower = message.lower()
        actions = []
        suggestions = []
        files_changed = []
        fixed_files = {}
        response = ""
        # Auto route: analyze / fix / modify keywords
        try:
            from services.llm_service import call_llm
            # Include recent history (last 4 turns) for context
            hist_prefix = ""
            if history:
                for h in history[-4:]:
                    hist_prefix += f"{h.get('role')}: {h.get('content')[:300]}\n"
            full_prompt = (hist_prefix + f"User: {message}" + ctx_str)[:6000]
            response = call_llm(full_prompt, system_instruction=sys, temperature=0.7, max_tokens=2048)
        except Exception as e:
            # Fallback via provider manager directly already handled, but if still fails
            response = f"Jarvis is temporarily offline ({e}). Your message was: {message}. Try switching AI model in settings."
        # Post-process for actions
        if any(k in lower for k in ["analyze", "review", "check project"]):
            analysis = self.analyze_project(pid)
            actions.append({"type":"analyze","data":analysis})
            suggestions.extend(analysis.get("suggestions",[]))
        if any(k in lower for k in ["fix", "error", "failed", "blank"]):
            suggestions.append("Try [Fix Errors] in workspace")
        if any(k in lower for k in ["change", "modify", "add ", "update ", "color", "navbar"]):
            suggestions.append("Use [Modify Website] to apply changes")

        # Update memory
        new_history = history + [{"role":"user","content":message, "at": _now().isoformat()}, {"role":"assistant","content":response, "at": _now().isoformat()}]
        self._save_memory(conversation_history=new_history, project_context=ctx if pid else None, last_actions=[{"action":"chat","mode":mode,"project_id":pid,"at":_now().isoformat()}])

        return {
            "response": response,
            "actions": actions,
            "suggestions": suggestions,
            "files_changed": files_changed,
            "fixed_files": fixed_files,
            "mode": mode,
            "project_context": ctx
        }

# -------------------------------------------------------------
# Backwards compatibility: simple generate_response
# -------------------------------------------------------------
def generate_response(user_message: str):
    """Legacy simple wrapper - uses JarvisService chat without project."""
    try:
        svc = JarvisService()
        result = svc.chat(user_message)
        return {"response": result.get("response","")}
    except Exception as e:
        logger.error(f"[Jarvis] generate_response error: {e}")
        return {"response": "I'm having trouble connecting to the AI service right now. Please try again.", "error": str(e)}

# -------------------------------------------------------------
# Helper for model selector
# -------------------------------------------------------------
def get_available_models():
    try:
        from services.ai_provider_manager import get_provider_manager
        mgr = get_provider_manager()
        return mgr.get_model_status()
    except Exception:
        return {}
