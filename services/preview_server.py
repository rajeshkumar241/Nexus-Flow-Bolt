"""
Nexus Flow — Preview Server
Manages per-project Vite dev servers or static file servers.
"""
import os
import subprocess
import signal
import time
import logging
import threading

logger = logging.getLogger(__name__)

PROJECTS_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_projects")

# Port range for preview servers
PORT_RANGE_START = 5173
PORT_RANGE_END = 5273

# Track running servers: {project_id: {"process": Popen, "port": int, "url": str}}
_servers = {}
_lock = threading.Lock()


def _find_free_port():
    """Find an available port in the range."""
    used = {s["port"] for s in _servers.values()}
    for port in range(PORT_RANGE_START, PORT_RANGE_END):
        if port not in used:
            return port
    raise RuntimeError("No available ports for preview server")


def start_preview(project_id, project_type="react"):
    """
    Start a preview server for a project.
    
    Args:
        project_id: Project identifier
        project_type: "react" or "static"
    
    Returns:
        dict: {"url": str, "port": int, "status": str}
    """
    with _lock:
        # Stop existing server for this project
        if project_id in _servers:
            stop_preview(project_id)

        project_dir = os.path.join(PROJECTS_ROOT, str(project_id))
        if not os.path.exists(project_dir):
            return {"url": None, "port": None, "status": "error", "message": "Project not found"}

        port = _find_free_port()

        try:
            if project_type == "react":
                proc = _start_vite(project_dir, port)
            else:
                proc = _start_static(project_dir, port)

            url = f"http://localhost:{port}"

            # Wait for server to start
            time.sleep(2)

            _servers[project_id] = {
                "process": proc,
                "port": port,
                "url": url,
                "type": project_type,
                "started_at": time.time(),
            }

            logger.info(f"[Preview] Started {project_type} server for {project_id} on port {port}")
            return {"url": url, "port": port, "status": "running"}

        except Exception as e:
            logger.error(f"[Preview] Failed to start server for {project_id}: {e}")
            return {"url": None, "port": None, "status": "error", "message": str(e)}


def stop_preview(project_id):
    """Stop a running preview server."""
    with _lock:
        if project_id not in _servers:
            return

        info = _servers[project_id]
        proc = info.get("process")
        if proc:
            try:
                if os.name == "nt":
                    proc.terminate()
                else:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except (ProcessLookupError, OSError):
                try:
                    proc.terminate()
                except Exception:
                    pass
            try:
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        del _servers[project_id]
        logger.info(f"[Preview] Stopped server for {project_id}")


def get_preview_url(project_id):
    """Get the preview URL for a project, if running."""
    with _lock:
        info = _servers.get(project_id)
        if info:
            # Check if process is still alive
            proc = info.get("process")
            if proc and proc.poll() is None:
                return info["url"]
            else:
                # Process died, clean up
                del _servers[project_id]
        return None


def restart_preview(project_id, project_type="react"):
    """Restart a preview server (e.g., after file changes)."""
    stop_preview(project_id)
    time.sleep(0.5)
    return start_preview(project_id, project_type)


def stop_all():
    """Stop all running preview servers."""
    with _lock:
        for project_id in list(_servers.keys()):
            stop_preview(project_id)


def list_previews():
    """List all running previews."""
    with _lock:
        result = []
        for pid, info in _servers.items():
            proc = info.get("process")
            running = proc and proc.poll() is None
            result.append({
                "project_id": pid,
                "url": info["url"] if running else None,
                "port": info["port"],
                "type": info["type"],
                "running": running,
            })
        return result


# ---------------------------------------------------------------------------
# Internal: start servers
# ---------------------------------------------------------------------------

def _start_vite(project_dir, port):
    """Start a Vite dev server for a React project."""
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
    # Check if node_modules exists, if not install first
    node_modules = os.path.join(project_dir, "node_modules")
    if not os.path.exists(node_modules):
        logger.info(f"[Preview] Installing dependencies for {os.path.basename(project_dir)}...")
        install = subprocess.run(
            [npm_cmd, "install"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if install.returncode != 0:
            raise RuntimeError(f"npm install failed: {install.stderr[:500]}")

    # Start Vite dev server
    proc = subprocess.Popen(
        [npx_cmd, "vite", "--port", str(port), "--host", "0.0.0.0"],
        cwd=project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    return proc


def _start_static(project_dir, port):
    """Start a simple HTTP server for static projects."""
    proc = subprocess.Popen(
        ["python", "-m", "http.server", str(port), "--bind", "0.0.0.0"],
        cwd=project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    return proc
