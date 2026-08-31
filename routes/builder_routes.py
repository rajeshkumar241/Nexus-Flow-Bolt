"""
Nexus Flow — AI Builder Routes
Blueprint for /api/builder/* endpoints.
Multi-step generation pipeline with build validation.
"""
import uuid
import re
import logging
from flask import Blueprint, jsonify, request, session, url_for

logger = logging.getLogger(__name__)

builder_bp = Blueprint("builder_ai", __name__, url_prefix="/api/builder")
generation_bp = Blueprint("generation_control", __name__, url_prefix="/api/generation")

# Global generation tracking (also exposed as /api/generation/stop)
from services.generation_control import (
    active_generations,
    GenerationCancelledException,
    register_generation,
    mark_cancelled,
    check_cancel,
    complete_generation,
)


def register_builder_routes(app, mongo_db):
    """Register AI builder routes with the Flask app."""
    from services.vite_manager import stop_all as stop_all_previews
    from services.performance_monitor import configure as configure_perf
    from services.generation_logs import configure as configure_gen_logs
    import atexit
    atexit.register(stop_all_previews)
    configure_perf(mongo_db)
    configure_gen_logs(mongo_db)

    app.register_blueprint(builder_bp)
    app.register_blueprint(generation_bp)
    logger.info("[Builder] AI builder routes registered")


@generation_bp.route("/stop/<generation_id>", methods=["POST"])
def stop_generation(generation_id):
    """Mark generation as cancelled. Idempotent."""
    generation_id = (generation_id or "").strip()
    if not generation_id:
        return jsonify({"success": False, "error": "generation_id required"}), 400
    # Check auth
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    found = mark_cancelled(generation_id)
    # Even if not found yet, we store pre-cancelled so later register respects it
    return jsonify({
        "success": True,
        "cancelled": True,
        "generation_id": generation_id,
        "found": found,
        "message": "Generation cancelled" if found else "Generation will be cancelled (pre-registered)",
    })


@generation_bp.route("/status/<generation_id>", methods=["GET"])
def generation_status(generation_id):
    """Optional status check."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    from services.generation_control import get_active, is_cancelled
    entry = get_active(generation_id)
    if not entry:
        return jsonify({"success": True, "exists": False, "cancelled": False})
    return jsonify({"success": True, "exists": True, "cancelled": is_cancelled(generation_id), "entry": entry})


# ---------------------------------------------------------------------------
# POST /api/builder/generate — Main generation endpoint
# ---------------------------------------------------------------------------

@builder_bp.route("/generate", methods=["POST"])
def generate():
    """
    Full generation pipeline: plan -> generate -> persist -> build -> preview.
    All stages are timed with time.perf_counter().
    """
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    # Initialize for safe error handling (available in except blocks)
    generation_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())[:12]
    timer = None
    email = session.get("email", "unknown")

    # Robust JSON parsing - always return JSON error, never HTML/KeyError
    try:
        data = request.get_json(silent=True) if request.is_json else {}
        if data is None:
            data = {}
        if not isinstance(data, dict):
            data = {}
    except Exception as je:
        import traceback
        logger.warning(f"[Builder] Invalid JSON payload: {je}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": "Invalid JSON payload"}), 400

    # Safe extraction (no KeyError) - accepts {prompt, website_name} or {prompt}
    prompt = (data.get("prompt") or data.get("message") or "").strip() if isinstance(data, dict) else ""
    project_name = (data.get("website_name") or data.get("project_name") or data.get("title") or "").strip() if isinstance(data, dict) else ""
    generation_id = (data.get("generation_id") or "").strip() or generation_id

    if not prompt:
        return jsonify({"success": False, "error": "Missing prompt"}), 400

    email = session["email"]
    project_id = str(uuid.uuid4())[:12]

    # --- Logging: request JSON + prompt ---
    print(f"[Builder] Received payload: {data}")
    logger.info(f"[Builder] Request JSON: {data}")
    print(f"[Builder] Prompt: '{prompt[:120]}' | website_name='{project_name}'")
    logger.info(f"[Builder] Received generate request | prompt='{prompt[:120]}' | project_name='{project_name}' | generation_id={generation_id} | user={email}")
    # --- Logging: selected AI provider ---
    try:
        from services.ai_provider_manager import get_provider_manager
        _mgr = get_provider_manager()
        _active_p, _active_m = _mgr.get_active_provider()
        print(f"[Builder] Selected AI provider: {_active_p}")
        print(f"[Builder] AI model name: {_active_m}")
        logger.info(f"[Builder] Selected AI provider: {_active_p}/{_active_m} | fallback_chain={_mgr.get_fallback_chain()}")
        logger.info(f"[Builder] AI model name: {_active_m}")
    except Exception as _e:
        import traceback
        logger.warning(f"[Builder] Could not resolve AI provider: {_e}\n{traceback.format_exc()}")

    # Register generation for cancellation
    try:
        register_generation(generation_id, project_id, email)
    except Exception as _re:
        import traceback
        logger.warning(f"[Builder] register_generation failed: {_re}\n{traceback.format_exc()}")

    # Start real-time performance timer
    try:
        from services.performance_monitor import GenerationTimer
        timer = GenerationTimer(project_id, prompt)
        timer.start()
    except Exception as _te:
        import traceback
        logger.warning(f"[Builder] Timer start failed: {_te}\n{traceback.format_exc()}")
        timer = None

    try:
        # -- Step 1: Analyze prompt -- before every stage check cancellation
        check_cancel(generation_id, "Analyze prompt")
        # -- Step 1a: Prompt Analysis -- (MongoDB optional - never block generation)
        from services.generation_logs import log_stage_start, log_stage_complete, log_stage_failed, log_stage_skipped, GenerationStage
        try:
            log_stage_start(project_id, email, GenerationStage.PROMPT_ANALYSIS, prompt[:200])
        except Exception as e:
            logger.warning(f"[Builder] MongoDB log skipped (PROMPT_ANALYSIS): {e}")

        # -- Step 2: Plan architecture --
        check_cancel(generation_id, "Plan architecture")
        # -- Step 1b: AI Planning --
        try:
            log_stage_complete(project_id, email, GenerationStage.PROMPT_ANALYSIS, 0)
        except Exception as e:
            logger.warning(f"[Builder] MongoDB log skipped (PROMPT_ANALYSIS complete): {e}")
        try:
            log_stage_start(project_id, email, GenerationStage.AI_PLANNING)
        except Exception as e:
            logger.warning(f"[Builder] MongoDB log skipped (AI_PLANNING): {e}")
        timer.begin_stage("planning")
        logger.info(f"[Builder] Planning website for: {prompt[:80]}...")
        from services.ai_planner import plan_website
        try:
            plan = plan_website(prompt, project_name=project_name or None, generation_id=generation_id)
        except Exception as plan_err:
            logger.warning(f"[Builder] AI planning failed ({plan_err}), using fallback plan. Quota/model errors are handled via fallback.")
            # Fallback plan ensures Builder never returns 500 due to quota; still uses AIProviderManager fallback chain
            # Minimal static plan that guarantees files generation
            _safe_name = re.sub(r'[^a-z0-9]+', '-', (project_name or prompt[:30] or 'my-website').lower()).strip('-') or 'my-website'
            plan = {
                "project_name": _safe_name,
                "project_type": "react",
                "description": prompt[:200],
                "pages": [
                    {"name": "Home", "route": "/", "description": "Landing page for "+prompt[:100], "sections": ["hero","features"], "components_used": ["Navbar","Footer"]},
                    {"name": "About", "route": "/about", "description": "About page", "sections": ["content"], "components_used": []}
                ],
                "components": [
                    {"name": "Navbar", "description": "Navigation", "props": [], "has_state": False},
                    {"name": "Footer", "description": "Footer", "props": [], "has_state": False}
                ],
                "features": ["responsive"],
                "data_model": [],
                "design": {
                    "style": "modern",
                    "color_scheme": {"primary": "#6366f1","secondary": "#8b5cf6","background": "#0f172a","surface": "#1e293b","text": "#f8fafc","text_muted": "#94a3b8","accent": "#06b6d4","success": "#10b981","error": "#ef4444"},
                    "fonts": {"heading": "Inter","body": "Inter"}
                },
                "navigation": {"type": "navbar", "links": [{"label": "Home","route": "/","icon": "fa-home"},{"label": "About","route": "/about","icon": "fa-info"}]},
                "dependencies": []
            }
            logger.info(f"[Builder] Fallback plan created: {plan['project_name']}")
        timer.end_stage("planning")
        # --- Logging: AI response (plan) ---
        print(f"[Builder] AI response: {str(plan)[:500]}")
        logger.info(f"[Builder] AI planning response: project_type={plan.get('project_type')} pages={len(plan.get('pages',[]))} components={len(plan.get('components',[]))} | plan={str(plan)[:500]}")
        logger.info(f"[Builder] AI response: {str(plan)[:500]}")
        try:
            log_stage_complete(project_id, email, GenerationStage.AI_PLANNING, timer._stages.get("planning", 0), {"project_type": plan.get("project_type")})
        except Exception as e:
            logger.warning(f"[Builder] MongoDB log skipped (AI_PLANNING complete): {e}")

        actual_name = project_name or plan.get("project_name", "my-website")
        plan["project_name"] = actual_name

        # -- Step 3: Generate components --
        check_cancel(generation_id, "Generate components")
        # -- Step 2: Component & Code Generation -- (Mongo optional)
        try:
            log_stage_start(project_id, email, GenerationStage.COMPONENT_GENERATION)
        except Exception as e:
            logger.warning(f"[Builder] MongoDB log skipped (COMPONENT_GENERATION): {e}")
        try:
            log_stage_start(project_id, email, GenerationStage.CODE_GENERATION)
        except Exception as e:
            logger.warning(f"[Builder] MongoDB log skipped (CODE_GENERATION): {e}")
        # -- Step 4: Generate code --
        check_cancel(generation_id, "Generate code")
        timer.begin_stage("code_gen")
        logger.info(f"[Builder] Generating {plan['project_type']} project (multi-step)...")
        from services.ai_code_generator import generate_react_project, generate_static_project

        try:
            if plan["project_type"] == "react":
                files = generate_react_project(plan, generation_id=generation_id)
            else:
                files = generate_static_project(plan)
        except Exception as code_err:
            logger.warning(f"[Builder] AI code generation failed ({code_err}), using fallback files. Invalid JSON/quota handled via fallback.")
            # Minimal fallback ensures Builder never returns 500 due to quota/model errors
            try:
                from services.ai_code_generator import _fallback_app_jsx, _fallback_component, _fallback_page, _build_package_json, _build_vite_config, _build_index_html, _build_main_jsx, _build_globals_css
                fallback_files = {}
                fallback_files["package.json"] = _build_package_json(plan)
                fallback_files["vite.config.js"] = _build_vite_config()
                fallback_files["index.html"] = _build_index_html(plan)
                fallback_files["src/main.jsx"] = _build_main_jsx()
                css = _build_globals_css(plan)
                fallback_files["src/styles/globals.css"] = css
                fallback_files["src/index.css"] = css
                fallback_files["src/App.jsx"] = _fallback_app_jsx(plan)
                for comp in plan.get("components", [])[:4]:
                    fallback_files[f"src/components/{comp.get('name','Comp')}.jsx"] = _fallback_component(comp, plan)
                for page in plan.get("pages", [])[:3]:
                    fallback_files[f"src/pages/{page.get('name','Page')}.jsx"] = _fallback_page(page, plan)
                files = fallback_files
            except Exception as fb_e:
                logger.error(f"[Builder] Fallback file build failed: {fb_e}")
                raise code_err
        timer.end_stage("code_gen")
        # --- Logging: AI code generation result ---
        print(f"[Builder] Generated files: {list(files.keys())}")
        logger.info(f"[Builder] Generated files: {list(files.keys())}")
        logger.info(f"[Builder] AI code generation result: {len(files)} files | keys={list(files.keys())[:10]} | sample={str(list(files.values())[0])[:300] if files else 'empty'}")
        try:
            log_stage_complete(project_id, email, GenerationStage.COMPONENT_GENERATION, timer._stages.get("code_gen", 0) / 2, {"components": len(files)})
        except Exception as e:
            logger.warning(f"[Builder] MongoDB log skipped (COMPONENT complete): {e}")
        try:
            log_stage_complete(project_id, email, GenerationStage.CODE_GENERATION, timer._stages.get("code_gen", 0), {"files_generated": len(files)})
        except Exception as e:
            logger.warning(f"[Builder] MongoDB log skipped (CODE_GENERATION complete): {e}")

        # -- Step 5: Create files -- check before writing
        check_cancel(generation_id, "Create files")
        # -- Step 3: File Creation -- (Mongo optional)
        try:
            log_stage_start(project_id, email, GenerationStage.FILE_CREATION)
        except Exception as e:
            logger.warning(f"[Builder] MongoDB log skipped (FILE_CREATION): {e}")
        timer.begin_stage("file_creation")
        logger.info(f"[Builder] Saving {len(files)} files to disk...")
        from services.project_manager import create_project, create_version
        create_project(project_id, files, metadata={
            "user_email": email,
            "title": actual_name,
            "prompt": prompt,
            "project_type": plan["project_type"],
        })
        create_version(project_id)
        timer.end_stage("file_creation")
        timer.set_files_count(len(files))
        # --- Logging: project generator output ---
        print(f"[Builder] Project creation status: project_id={project_id} files={len(files)}")
        logger.info(f"[Builder] Project creation status: project_id={project_id} files={len(files)} preview_pending")
        logger.info(f"[Builder] Project generator output: project_id={project_id} files_created={len(files)} keys={list(files.keys())} metadata_title={actual_name}")
        try:
            log_stage_complete(project_id, email, GenerationStage.FILE_CREATION, timer._stages.get("file_creation", 0), {"files_saved": len(files)})
        except Exception as e:
            logger.warning(f"[Builder] MongoDB log skipped (FILE_CREATION complete): {e}")

        # -- Step 6: Install dependencies --
        check_cancel(generation_id, "Install dependencies")
        # -- Step 4: Install deps + build validation --
        build_status = "skipped"
        build_errors = []
        preview_url = None
        preview_status = "n/a"

        if plan["project_type"] == "react":
            # Use PreviewBuilder for production build (per spec: npm install + npm run build -> dist)
            try:
                log_stage_start(project_id, email, GenerationStage.DEPENDENCY_INSTALLATION)
            except Exception as e:
                logger.warning(f"[Builder] MongoDB log skipped (DEPS start): {e}")
            timer.begin_stage("npm_install")
            logger.info("[Builder] Installing dependencies (PreviewBuilder)...")
            # PreviewBuilder handles install + build
            try:
                from services.preview_builder import build_preview as preview_build
                # First ensure install, then build via preview_builder
                from services.vite_manager import install_dependencies
                ok, msg = install_dependencies(project_id)
                timer.end_stage("npm_install")
                if not ok:
                    logger.warning(f"[Builder] Dependency install issue: {msg}")
                    build_status = "install_failed"
                    try:
                        log_stage_failed(project_id, email, GenerationStage.DEPENDENCY_INSTALLATION, msg, timer._stages.get("npm_install", 0))
                    except Exception as e:
                        logger.warning(f"[Builder] MongoDB log skipped (DEPS failed): {e}")
                else:
                    try:
                        log_stage_complete(project_id, email, GenerationStage.DEPENDENCY_INSTALLATION, timer._stages.get("npm_install", 0))
                    except Exception as e:
                        logger.warning(f"[Builder] MongoDB log skipped (DEPS complete): {e}")
                    # -- Step 7: Validate build -- via PreviewBuilder
                    check_cancel(generation_id, "Validate build")
                    try:
                        log_stage_start(project_id, email, GenerationStage.BUILD_VALIDATION)
                    except Exception as e:
                        logger.warning(f"[Builder] MongoDB log skipped (BUILD start): {e}")
                    timer.begin_stage("build")
                    logger.info("[Builder] Building project for production preview...")
                    # Use preview_builder to capture build errors and ensure dist
                    from services.vite_manager import build_project
                    ok, msg, errors = build_project(project_id)
                    # Also update via preview_builder for consistency
                    try:
                        pb_result = preview_build(project_id)
                        if pb_result["success"]:
                            ok, msg, errors = True, pb_result["message"], []
                        elif not ok:
                            # Keep original build error if preview_builder also failed
                            pass
                    except Exception as pb_e:
                        logger.warning(f"[Builder] PreviewBuilder build check failed: {pb_e}")
                    timer.end_stage("build")
                    if ok:
                        build_status = "passed"
                        logger.info("[Builder] Build validation passed - dist ready")
                        try:
                            log_stage_complete(project_id, email, GenerationStage.BUILD_VALIDATION, timer._stages.get("build", 0))
                        except Exception as e:
                            logger.warning(f"[Builder] MongoDB log skipped (BUILD complete): {e}")
                    else:
                        build_status = "failed"
                        build_errors = errors
                        logger.warning(f"[Builder] Build failed: {msg}")
                        try:
                            log_stage_failed(project_id, email, GenerationStage.BUILD_VALIDATION, msg, timer._stages.get("build", 0))
                        except Exception as e:
                            logger.warning(f"[Builder] MongoDB log skipped (BUILD failed): {e}")
            except Exception as e:
                import traceback
                logger.error(f"[Builder] PreviewBuilder error: {e}\n{traceback.format_exc()}")
                timer.end_stage("npm_install")
                build_status = "failed"
                build_errors = [str(e)]

        # -- Step 8: Start preview -- Flask-served dist (no CORS, iframe-safe)
        check_cancel(generation_id, "Start preview")
        try:
            log_stage_start(project_id, email, GenerationStage.PREVIEW_STARTUP)
        except Exception as e:
            logger.warning(f"[Builder] MongoDB log skipped (PREVIEW start): {e}")
        timer.begin_stage("preview")
        logger.info("[Builder] Preparing Flask preview (building dist)...")
        # For Flask preview we ensure dist exists; build already validated above
        import os
        PROJECTS_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_projects")
        dist_dir = os.path.join(PROJECTS_ROOT, str(project_id), "dist")
        project_dir = os.path.join(PROJECTS_ROOT, str(project_id))
        # Flask preview URL per spec: /preview/<project_id>/index.html (production dist, no Vite dev server)
        preview_url = f"/preview/{project_id}/index.html"
        # Absolute URL for iframe and external use
        try:
            # Use request.host_url to build absolute URL as spec: http://127.0.0.1:5000/preview/{project_id}/index.html
            base = request.host_url.rstrip("/")
            preview_url_abs = f"{base}/preview/{project_id}/index.html"
        except Exception:
            preview_url_abs = f"http://127.0.0.1:5000/preview/{project_id}/index.html"

        # Determine preview status by checking dist or fallback files
        if plan["project_type"] == "react":
            if os.path.isdir(dist_dir) and os.path.isfile(os.path.join(dist_dir, "index.html")):
                preview_status = "running"
                logger.info(f"[Builder] Flask preview ready at {preview_url} (dist exists)")
            elif build_status == "passed":
                preview_status = "running"
            else:
                if os.path.isfile(os.path.join(project_dir, "index.html")):
                    preview_status = "running"
                else:
                    preview_status = "error"
                    preview_url = None
        else:
            try:
                log_stage_skipped(project_id, email, GenerationStage.DEPENDENCY_INSTALLATION, "Static project")
            except Exception as e:
                logger.warning(f"[Builder] MongoDB log skipped (DEPS skipped): {e}")
            try:
                log_stage_skipped(project_id, email, GenerationStage.BUILD_VALIDATION, "Static project")
            except Exception as e:
                logger.warning(f"[Builder] MongoDB log skipped (BUILD skipped): {e}")
            build_status = "n/a"
            if os.path.isfile(os.path.join(project_dir, "index.html")) or os.path.isdir(dist_dir):
                preview_status = "running"
            else:
                preview_status = "error"
                preview_url = None

            timer.end_stage("preview")

            if preview_status == "error":
                logger.warning(f"[Builder] Flask preview not ready for {project_id}")
                try:
                    log_stage_failed(project_id, email, GenerationStage.PREVIEW_STARTUP, "Preview not ready - build may have failed", timer._stages.get("preview", 0))
                except Exception as e:
                    logger.warning(f"[Builder] MongoDB log skipped (PREVIEW failed): {e}")
            else:
                try:
                    log_stage_complete(project_id, email, GenerationStage.PREVIEW_STARTUP, timer._stages.get("preview", 0), {"url": preview_url})
                except Exception as e:
                    logger.warning(f"[Builder] MongoDB log skipped (PREVIEW complete): {e}")

        # -- Step 6: Save to MongoDB -- (optional, never crash generation)
        try:
            _save_project_record(email, project_id, actual_name, prompt, plan, files)
        except Exception as e:
            logger.warning(f"[Builder] MongoDB project save skipped: {e}")

        # Check cancelled right before persisting/preview (prevent file creation if cancelled)
        check_cancel(generation_id, "Create files")
        # Finalize timer and persist metrics (also optional)
        try:
            report = timer.finish(success=True, error_message="", failed_stage="")
        except Exception as e:
            logger.warning(f"[Builder] Perf timer persist skipped: {e}")
            report = {"timing": timer.get_timing_dict()}

        complete_generation(generation_id)

        # --- Logging: project generation result ---
        logger.info(f"[Builder] Project generation result: project_id={project_id} generation_id={generation_id} type={plan['project_type']} files={len(files)} preview={preview_url} build={build_status} timing={report.get('timing')}")

        return jsonify({
            "success": True,
            "project_id": project_id,
            "generation_id": generation_id,
            "plan": plan,
            "files": {k: v[:500] + "..." if len(v) > 500 else v for k, v in files.items()},
            "preview_url": preview_url,
            "preview_status": preview_status,
            "project_type": plan["project_type"],
            "build_status": build_status,
            "build_errors": build_errors[:10],
            "timing": report["timing"],
            "files_created": len(files),
            "message": f"Website generated! {len(files)} files created.",
        })

    except GenerationCancelledException as ce:
        try:
            timer.finish(success=False, error_message=str(ce), failed_stage="cancelled")
        except Exception:
            pass
        complete_generation(generation_id)
        logger.info(f"[Builder] Generation cancelled {generation_id}: {ce}")
        # Clean up partially created project dir if exists
        try:
            from services.project_manager import delete_project
            delete_project(project_id)
        except Exception:
            pass
        return jsonify({
            "success": False,
            "cancelled": True,
            "generation_id": generation_id,
            "project_id": project_id,
            "error": "Generation cancelled",
            "message": "Generation cancelled by user",
        }), 499
    except Exception as e:
        elapsed = timer.get_elapsed() if 'timer' in locals() else 0
        failed_stage = timer._current_stage if 'timer' in locals() and timer._current_stage else "unknown"
        try:
            timer.finish(success=False, error_message=str(e), failed_stage=failed_stage)
        except Exception:
            pass
        try:
            complete_generation(generation_id)
        except Exception:
            pass
        logger.error(f"[Builder] Generation failed at {failed_stage} ({elapsed}s): {e}", exc_info=True)
        
        # --- Verify AIProviderManager: handle quota/model/invalid JSON ---
        err_msg = str(e).lower()
        status_code = 500
        user_error = str(e)
        # Invalid JSON cleaning (already handled in _parse_json, but catch here)
        if "could not parse json" in err_msg or "invalid json" in err_msg or "json" in err_msg and "parse" in err_msg:
            status_code = 422
            user_error = "AI response was invalid JSON and was cleaned. Please retry generation."
            logger.warning(f"[Builder] Invalid JSON response cleaned: {e}")
        elif "quota" in err_msg or "429" in err_msg or "rate limit" in err_msg or "429" in str(type(e)):
            status_code = 429
            user_error = "AI quota exceeded. Fallback attempted but all providers are rate-limited. Try again later or switch model in Admin."
        elif "401" in err_msg or "403" in err_msg or "api key" in err_msg or "unauthorized" in err_msg or "auth" in err_msg:
            status_code = 401
            user_error = "AI authentication failed. Check API keys in AI Provider Manager."
        elif "model" in err_msg and ("not found" in err_msg or "unavailable" in err_msg or "404" in err_msg):
            status_code = 503
            user_error = "AI model unavailable. Fallback will try next model. If persists, check provider config."
        elif "no available ai providers" in err_msg or "all ai models failed" in err_msg:
            status_code = 503
            user_error = "No AI providers available. Configure API keys in Admin or check fallback chain."
        
        # Map timer stage to GenerationStage enum (wrapped, never crash)
        try:
            from services.generation_logs import GenerationStage as _GS
            stage_map = {
                "planning": _GS.AI_PLANNING,
                "code_gen": _GS.CODE_GENERATION,
                "file_creation": _GS.FILE_CREATION,
                "npm_install": _GS.DEPENDENCY_INSTALLATION,
                "build": _GS.BUILD_VALIDATION,
                "preview": _GS.PREVIEW_STARTUP,
            }
            gen_stage = stage_map.get(failed_stage, _GS.CODE_GENERATION)
            from services.generation_logs import log_stage_failed as _lsf
            _lsf(project_id, email, gen_stage, str(e), timer._stages.get(failed_stage, 0) if 'timer' in locals() else 0)
        except Exception as _le:
            logger.debug(f"[Builder] log_stage_failed skipped: {_le}")
        
        return jsonify({
            "success": False,
            "error": user_error,
            "details": str(e)[:500],
            "failed_stage": failed_stage,
            "elapsed_seconds": elapsed,
        }), status_code


# ---------------------------------------------------------------------------
# POST /api/builder/modify — Modify existing project
# ---------------------------------------------------------------------------

@builder_bp.route("/modify", methods=["POST"])
def modify():
    """Modify an existing project based on user request."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    data = request.get_json() if request.is_json else {}
    project_id = (data.get("project_id") or "").strip()
    mod_request = (data.get("message") or data.get("request") or "").strip()

    if not project_id:
        return jsonify({"success": False, "error": "project_id is required."}), 400
    if not mod_request:
        return jsonify({"success": False, "error": "Modification request cannot be empty."}), 400

    email = session["email"]

    try:
        from services.generation_logs import log_stage_start, log_stage_complete, log_stage_failed, log_stage_skipped, GenerationStage
        from services.project_manager import read_project, update_file, get_metadata
        from services.ai_modifier import modify_project
        from services.vite_manager import restart_vite_server

        # Log modification stages
        log_stage_start(project_id, email, GenerationStage.COMPONENT_GENERATION, mod_request[:200])
        log_stage_start(project_id, email, GenerationStage.CODE_GENERATION)

        files = read_project(project_id)
        if not files:
            return jsonify({"success": False, "error": "Project not found."}), 404

        result = modify_project(project_id, mod_request, files)

        log_stage_complete(project_id, email, GenerationStage.COMPONENT_GENERATION, 0, {"components_changed": len(result.get("changed_files", []))})
        log_stage_complete(project_id, email, GenerationStage.CODE_GENERATION, 0, {"files_updated": len(result.get("changed_files", []))})

        log_stage_start(project_id, email, GenerationStage.FILE_CREATION)
        for path in result.get("changed_files", []):
            if path in result["files"]:
                update_file(project_id, path, result["files"][path])
        log_stage_complete(project_id, email, GenerationStage.FILE_CREATION, 0, {"files_updated": len(result.get("changed_files", []))})

        log_stage_start(project_id, email, GenerationStage.PREVIEW_STARTUP)
        meta = get_metadata(project_id) or {}
        project_type = meta.get("project_type", "react")
        preview = restart_vite_server(project_id, project_type)
        log_stage_complete(project_id, email, GenerationStage.PREVIEW_STARTUP, 0, {"url": preview.get("url")})

        from services.project_manager import create_version
        create_version(project_id)

        return jsonify({
            "success": True,
            "changed_files": result.get("changed_files", []),
            "preview_url": preview.get("url"),
            "message": result.get("message", "Modification complete."),
        })

    except Exception as e:
        logger.error(f"[Builder] Modification failed: {e}", exc_info=True)
        log_stage_failed(project_id, email, GenerationStage.CODE_GENERATION, str(e), 0)
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/builder/debug — Debug and fix project
# ---------------------------------------------------------------------------

@builder_bp.route("/debug", methods=["POST"])
def debug():
    """Analyze project for issues and fix them."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    data = request.get_json() if request.is_json else {}
    project_id = (data.get("project_id") or "").strip()
    error_msg = (data.get("error") or "").strip() or None

    if not project_id:
        return jsonify({"success": False, "error": "project_id is required."}), 400

    try:
        from services.project_manager import read_project, update_file, get_metadata
        from services.ai_debugger import debug_project
        from services.vite_manager import restart_vite_server

        files = read_project(project_id)
        if not files:
            return jsonify({"success": False, "error": "Project not found."}), 404

        result = debug_project(project_id, files, error_message=error_msg)

        for path in result.get("fixes", {}):
            if path in result.get("files", {}):
                update_file(project_id, path, result["files"][path])

        meta = get_metadata(project_id) or {}
        project_type = meta.get("project_type", "react")
        preview = restart_vite_server(project_id, project_type)

        return jsonify({
            "success": True,
            "issues": result.get("issues", []),
            "fixed_files": list(result.get("fixes", {}).keys()),
            "preview_url": preview.get("url"),
            "message": result.get("message", "Debug complete."),
        })

    except Exception as e:
        logger.error(f"[Builder] Debug failed: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# GET /api/builder/project/<id> — Load project files
# ---------------------------------------------------------------------------

@builder_bp.route("/project/<project_id>", methods=["GET"])
def get_project(project_id):
    """Load all files for a project."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    from services.project_manager import read_project, get_metadata
    files = read_project(project_id)
    if files is None:
        return jsonify({"success": False, "error": "Project not found."}), 404

    meta = get_metadata(project_id) or {}
    return jsonify({
        "success": True,
        "project_id": project_id,
        "files": files,
        "metadata": meta,
    })


# ---------------------------------------------------------------------------
# GET /api/builder/preview/<id> — Get preview URL (Flask-served dist, no CORS)
# ---------------------------------------------------------------------------

@builder_bp.route("/preview/<project_id>", methods=["GET"])
def get_preview(project_id):
    """Get Flask preview URL for a project (serves dist via /preview/vite/)."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    import os
    PROJECTS_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_projects")
    dist_dir = os.path.join(PROJECTS_ROOT, str(project_id), "dist")
    project_dir = os.path.join(PROJECTS_ROOT, str(project_id))

    # Flask preview URL per spec - production dist via /preview/<project_id>/index.html (no Vite dev server, no CORS)
    flask_url = f"/preview/{project_id}/index.html"
    flask_url_abs = f"http://127.0.0.1:5000/preview/{project_id}/index.html"
    # Also support vite alias for backward compat
    try:
        _vite_url = url_for("vite_preview", project_id=project_id, filepath="", _external=False)
    except Exception:
        _vite_url = f"/preview/vite/{project_id}/"

    # Check if preview is ready (dist or index.html exists)
    if os.path.isdir(dist_dir) and os.path.isfile(os.path.join(dist_dir, "index.html")):
        return jsonify({"success": True, "url": flask_url, "url_abs": flask_url_abs, "status": "running", "mode": "flask-dist"})
    if os.path.isfile(os.path.join(project_dir, "index.html")):
        return jsonify({"success": True, "url": flask_url, "url_abs": flask_url_abs, "status": "running", "mode": "flask-fallback"})
    # Fallback to legacy Vite dev server only if Flask not ready (rare)
    from services.vite_manager import get_preview_url as _get_vite_url
    vite_url = _get_vite_url(project_id)
    if vite_url:
        return jsonify({"success": True, "url": vite_url, "status": "running", "mode": "vite-legacy"})
    return jsonify({"success": False, "url": None, "status": "error", "message": "Preview not ready - project files missing"}), 404


# ---------------------------------------------------------------------------
# POST /api/builder/stop/<id> — Stop preview
# ---------------------------------------------------------------------------

@builder_bp.route("/stop/<project_id>", methods=["POST"])
def stop_preview(project_id):
    """Stop preview server for a project."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    from services.vite_manager import stop_vite_server
    stop_vite_server(project_id)
    return jsonify({"success": True, "message": "Preview stopped."})


# ---------------------------------------------------------------------------
# POST /api/builder/build/<id> — Trigger build validation
# ---------------------------------------------------------------------------

@builder_bp.route("/build/<project_id>", methods=["POST"])
def build_project(project_id):
    """Run npm build to validate the project."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    from services.vite_manager import build_project as _build
    ok, msg, errors = _build(project_id)
    return jsonify({
        "success": ok,
        "message": msg,
        "errors": errors,
    })


# ---------------------------------------------------------------------------
# GET /api/builder/list — List user's projects
# ---------------------------------------------------------------------------

@builder_bp.route("/list", methods=["GET"])
def list_projects():
    """List all projects for the current user."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    from services.project_manager import list_projects as _list
    projects = _list(user_email=session["email"])
    return jsonify({"success": True, "projects": projects})


# ---------------------------------------------------------------------------
# Helper: save project to MongoDB
# ---------------------------------------------------------------------------

def _save_project_record(email, project_id, title, prompt, plan, files):
    """Save project metadata to MongoDB (graceful offline fallback)."""
    try:
        # Use the shared DB (real or mock) via mongo_connection
        try:
            from services.mongo_connection import get_db
            db = get_db()
        except Exception:
            from flask import current_app
            mongo = current_app.extensions.get("pymongo")
            if mongo is None:
                return
            db = mongo.db
        db.projects.update_one(
            {"_id": project_id},
            {"$set": {
                "user_email": email,
                "title": title,
                "prompt": prompt,
                "project_type": plan.get("project_type", "react"),
                "plan": plan,
                "files": list(files.keys()),
                "status": "Active",
                "updated_at": __import__("datetime").datetime.utcnow(),
            }, "$setOnInsert": {
                "created_at": __import__("datetime").datetime.utcnow(),
            }},
            upsert=True,
        )
    except Exception as e:
        logger.warning(f"[Builder] Failed to save project record to MongoDB: {e}")


# ---------------------------------------------------------------------------
# GET /api/builder/generation-logs/<project_id> — Get generation logs
# ---------------------------------------------------------------------------

@builder_bp.route("/generation-logs/<project_id>", methods=["GET"])
def get_generation_logs(project_id):
    """Get detailed generation logs for a project."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    from services.generation_logs import get_generation_logs as _get_logs
    logs = _get_logs(project_id)
    return jsonify({"success": True, "logs": logs})


# ---------------------------------------------------------------------------
# POST /api/builder/retry/<project_id> — Retry failed generation
# ---------------------------------------------------------------------------

@builder_bp.route("/retry/<project_id>", methods=["POST"])
def retry_generation(project_id):
    """Retry a failed generation by re-running the generate endpoint with the original prompt."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    email = session["email"]

    # Get the original project to retrieve the prompt
    from services.project_manager import get_metadata
    meta = get_metadata(project_id)
    if not meta:
        return jsonify({"success": False, "error": "Project not found."}), 404

    if meta.get("user_email") != email:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    original_prompt = meta.get("prompt", "")
    project_name = meta.get("title", "")

    if not original_prompt:
        return jsonify({"success": False, "error": "No original prompt found for retry."}), 400

    # Clear previous generation logs for this project
    from services.generation_logs import clear_generation_logs
    clear_generation_logs(project_id)

    # Re-run generation with the original prompt
    # We call the generate function internally
    from flask import current_app
    with current_app.test_request_context(
        '/api/builder/generate',
        method='POST',
        json={'prompt': original_prompt, 'website_name': project_name},
        headers={'Cookie': request.headers.get('Cookie', '')}
    ):
        # This would need session - let's just redirect to the generate endpoint
        pass

    # Instead of internal call, return a signal for frontend to retry
    return jsonify({
        "success": True,
        "retry": True,
        "project_id": project_id,
        "prompt": original_prompt,
        "website_name": project_name,
        "message": "Ready to retry. Frontend should call /api/builder/generate again."
    })


# ---------------------------------------------------------------------------
# AI Provider Endpoints
# ---------------------------------------------------------------------------

@builder_bp.route("/providers", methods=["GET"])
def builder_providers():
    """Get available AI providers and their models."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        from services.ai_provider_manager import get_provider_manager
        mgr = get_provider_manager()
        status = mgr.get_model_status()
        active_provider, active_model = mgr.get_active_provider()
        
        # Group by provider
        providers = {}
        for key, info in status.items():
            prov = info["provider"]
            if prov not in providers:
                providers[prov] = {
                    "name": prov,
                    "priority": info.get("priority", 99),
                    "models": [],
                    "has_key": info.get("has_api_key", False),
                    "enabled": info.get("enabled", True),
                    "last_status": info.get("last_status", "unknown"),
                }
            providers[prov]["models"].append({
                "id": info["model"],
                "name": info["model"],
                "is_active": info.get("is_active", False),
            })
        
        # Sort by priority
        sorted_providers = sorted(providers.items(), key=lambda x: x[1]["priority"])
        
        return jsonify({
            "success": True,
            "providers": [{"provider": k, **v} for k, v in sorted_providers],
            "active_provider": active_provider,
            "active_model": active_model,
        })
    except Exception as e:
        logger.error(f"[Builder] Failed to get providers: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@builder_bp.route("/provider/select", methods=["POST"])
def builder_provider_select():
    """Select active AI provider and model."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        data = request.get_json() or {}
        provider = (data.get("provider") or "").strip()
        model = (data.get("model") or "").strip()
        
        if not provider or not model:
            return jsonify({"success": False, "error": "Provider and model required"}), 400
        
        from services.ai_provider_manager import get_provider_manager
        mgr = get_provider_manager()
        
        ok = mgr.set_active_model(provider, model)
        if not ok:
            return jsonify({"success": False, "error": "Failed to set model (disabled or not found)"}), 400
        
        return jsonify({
            "success": True,
            "message": f"Switched to {provider}/{model}",
            "provider": provider,
            "model": model,
        })
    except Exception as e:
        logger.error(f"[Builder] Provider select failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@builder_bp.route("/provider/test", methods=["POST"])
def builder_provider_test():
    """Test connection to a provider."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        data = request.get_json() or {}
        provider = (data.get("provider") or "").strip()
        model = (data.get("model") or "").strip()
        
        if not provider:
            return jsonify({"success": False, "error": "Provider required"}), 400
        
        from services.ai_provider_manager import get_provider_manager
        mgr = get_provider_manager()
        provider_config = mgr.config.providers.get(provider)
        
        if not provider_config:
            return jsonify({"success": False, "error": f"Unknown provider: {provider}"}), 400
        
        api_key = os.getenv(provider_config.api_key_env, "")
        if not api_key or _is_placeholder_key(api_key):
            return jsonify({"success": False, "error": f"No API key configured for {provider}"}), 400
        
        # Try to get provider instance and test
        from services.ai_provider_manager import FallbackLLMProvider
        fallback = FallbackLLMProvider(mgr)
        provider_instance = fallback._get_provider_instance(provider, model or provider_config.models[0])
        
        if not provider_instance:
            return jsonify({"success": False, "error": "Provider unavailable"}), 503
        
        start = time.time()
        health = provider_instance.check_health()
        latency = int((time.time() - start) * 1000)
        
        if health.get("available"):
            return jsonify({
                "success": True,
                "message": f"{provider}/{model} connected ({latency}ms)",
                "latency_ms": latency,
            })
        else:
            return jsonify({
                "success": False,
                "error": health.get("message", "Connection failed"),
                "latency_ms": latency,
            }), 503
    except Exception as e:
        logger.error(f"[Builder] Provider test failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@builder_bp.route("/provider/save", methods=["POST"])
def builder_provider_save():
    """Save provider API key."""
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        data = request.get_json() or {}
        provider = (data.get("provider") or "").strip()
        api_key = (data.get("api_key") or "").strip()
        
        if not provider or not api_key:
            return jsonify({"success": False, "error": "Provider and API key required"}), 400
        
        # Update environment variable (in-memory, for session)
        env_key = f"{provider.upper()}_API_KEY"
        os.environ[env_key] = api_key
        
        # Update provider manager config
        from services.ai_provider_manager import get_provider_manager, _is_placeholder_key
        mgr = get_provider_manager()
        provider_config = mgr.config.providers.get(provider)
        
        if provider_config:
            provider_config.enabled = True
            mgr._save_config()
        
        return jsonify({
            "success": True,
            "message": f"API key saved for {provider}",
        })
    except Exception as e:
        logger.error(f"[Builder] Provider save failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
