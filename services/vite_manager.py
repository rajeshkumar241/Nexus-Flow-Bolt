"""
Nexus Flow — Vite Manager
Manages npm install, vite dev server lifecycle, and build validation.
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
_lock = threading.RLock()  # Reentrant lock — functions can call each other


def _find_free_port():
    """Find an available port in the range (checks both our registry and system)."""
    import socket
    used = {s["port"] for s in _servers.values()}
    for port in range(PORT_RANGE_START, PORT_RANGE_END):
        if port in used:
            continue
        # Check if port is actually free on the system
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            if result != 0:  # Connection refused = port is free
                return port
        except Exception:
            return port  # Assume free if we can't check
    raise RuntimeError("No available ports for preview server")


def install_dependencies(project_id):
    """
    Run npm install in the project directory.
    Returns: (success: bool, message: str)
    """
    project_dir = os.path.join(PROJECTS_ROOT, str(project_id))
    if not os.path.exists(project_dir):
        return False, "Project directory not found"

    node_modules = os.path.join(project_dir, "node_modules")
    if os.path.exists(node_modules):
        logger.info(f"[Vite] node_modules already exists for {project_id}")
        return True, "Dependencies already installed"

    logger.info(f"[Vite] Installing dependencies for {project_id}...")
    try:
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        result = subprocess.run(
            [npm_cmd, "install"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            logger.info(f"[Vite] Dependencies installed for {project_id}")
            return True, "Dependencies installed"
        else:
            err = result.stderr[:500] if result.stderr else result.stdout[:500]
            logger.error(f"[Vite] npm install failed: {err}")
            return False, f"npm install failed: {err}"
    except subprocess.TimeoutExpired:
        return False, "npm install timed out after 120s"
    except FileNotFoundError:
        return False, "npm not found. Please install Node.js."


def build_project(project_id):
    """
    Run npm run build to validate the project compiles.
    Returns: (success: bool, message: str, errors: list)
    """
    project_dir = os.path.join(PROJECTS_ROOT, str(project_id))
    if not os.path.exists(project_dir):
        return False, "Project directory not found", []

    # Ensure dependencies are installed
    ok, msg = install_dependencies(project_id)
    if not ok:
        return False, msg, []

    logger.info(f"[Vite] Building project {project_id}...")
    try:
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        result = subprocess.run(
            [npm_cmd, "run", "build"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            logger.info(f"[Vite] Build succeeded for {project_id}")
            return True, "Build succeeded", []
        else:
            # Parse errors from output
            errors = _parse_build_errors(result.stdout + "\n" + result.stderr)
            err_msg = result.stderr[:500] if result.stderr else result.stdout[:500]
            logger.error(f"[Vite] Build failed: {err_msg}")
            return False, f"Build failed: {err_msg}", errors
    except subprocess.TimeoutExpired:
        return False, "Build timed out after 120s", []


def start_vite_server(project_id):
    """
    Start a Vite dev server for a project.
    Installs dependencies first if needed.
    Verifies the server is actually responding before returning.

    Returns:
        dict: {"url": str, "port": int, "status": str, "message": str}
    """
    with _lock:
        # Stop existing server for this project
        if project_id in _servers:
            stop_vite_server(project_id)

        project_dir = os.path.join(PROJECTS_ROOT, str(project_id))
        if not os.path.exists(project_dir):
            return {"url": None, "port": None, "status": "error", "message": "Project directory not found"}

        # Verify key files exist
        missing = _check_project_files(project_dir)
        if missing:
            return {"url": None, "port": None, "status": "error",
                    "message": f"Missing project files: {', '.join(missing)}"}

        # Install dependencies if needed
        ok, msg = install_dependencies(project_id)
        if not ok:
            return {"url": None, "port": None, "status": "error", "message": f"Dependency install failed: {msg}"}

        port = _find_free_port()

        try:
            npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
            # Use DEVNULL for stdout/stderr — we check readiness via HTTP, not output
            proc = subprocess.Popen(
                [npx_cmd, "vite", "--port", str(port), "--host", "0.0.0.0"],
                cwd=project_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )

            url = f"http://localhost:{port}"

            # Wait for Vite to be actually responding
            ready = _wait_for_vite(proc, port, timeout=45)

            if not ready:
                # Server didn't start
                try:
                    proc.terminate()
                except Exception:
                    pass
                return {"url": None, "port": None, "status": "error",
                        "message": "Vite server failed to start. Check for build errors in the project."}

            _servers[project_id] = {
                "process": proc,
                "port": port,
                "url": url,
                "type": "react",
                "started_at": time.time(),
            }

            logger.info(f"[Vite] Server ready for {project_id} on port {port}")
            return {"url": url, "port": port, "status": "running", "message": "Vite server started"}

        except Exception as e:
            logger.error(f"[Vite] Failed to start server: {e}")
            return {"url": None, "port": None, "status": "error", "message": str(e)}


def start_static_server(project_id):
    """Start a simple HTTP server for static projects."""
    with _lock:
        if project_id in _servers:
            stop_vite_server(project_id)

        project_dir = os.path.join(PROJECTS_ROOT, str(project_id))
        if not os.path.exists(project_dir):
            return {"url": None, "port": None, "status": "error", "message": "Project not found"}

        port = _find_free_port()

        try:
            proc = subprocess.Popen(
                ["python", "-m", "http.server", str(port), "--bind", "0.0.0.0"],
                cwd=project_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )

            url = f"http://localhost:{port}"
            time.sleep(1)

            _servers[project_id] = {
                "process": proc,
                "port": port,
                "url": url,
                "type": "static",
                "started_at": time.time(),
            }

            return {"url": url, "port": port, "status": "running", "message": "Server started"}

        except Exception as e:
            return {"url": None, "port": None, "status": "error", "message": str(e)}


def stop_vite_server(project_id):
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
        logger.info(f"[Vite] Stopped server for {project_id}")


def get_preview_url(project_id):
    """Get the preview URL for a project, if running. Verifies server is alive."""
    import socket
    with _lock:
        info = _servers.get(project_id)
        if info:
            proc = info.get("process")
            if proc and proc.poll() is None:
                # Server process is alive — verify port is open
                port = info["port"]
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex(("127.0.0.1", port))
                    sock.close()
                    if result == 0:
                        return info["url"]
                except Exception:
                    pass
                # Port not responding, clean up
                try:
                    proc.terminate()
                except Exception:
                    pass
                del _servers[project_id]
                return None
            else:
                del _servers[project_id]
        return None


def restart_vite_server(project_id, project_type="react"):
    """Restart a preview server."""
    stop_vite_server(project_id)
    time.sleep(0.5)
    if project_type == "static":
        return start_static_server(project_id)
    return start_vite_server(project_id)


def stop_all():
    """Stop all running preview servers."""
    with _lock:
        for project_id in list(_servers.keys()):
            stop_vite_server(project_id)


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
# Internal helpers
# ---------------------------------------------------------------------------

def _wait_for_vite(proc, port, timeout=30):
    """Wait for Vite server to be ready. Returns True if ready, False if failed."""
    import socket

    start = time.time()
    while time.time() - start < timeout:
        # Check if process died
        if proc.poll() is not None:
            logger.error(f"[Vite] Process exited with code {proc.returncode} on port {port}")
            return False

        # Try a raw TCP connection to the port
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            if result == 0:
                logger.info(f"[Vite] Server ready on port {port}")
                return True
        except Exception:
            pass
        time.sleep(1)

    # Timeout — check if process is still alive
    if proc.poll() is not None:
        logger.error(f"[Vite] Process died during startup on port {port}")
        return False

    logger.warning(f"[Vite] Server start timeout on port {port}, proceeding anyway")
    return True


def _check_project_files(project_dir):
    """Check that essential React+Vite files exist. Returns list of missing files."""
    missing = []
    if not os.path.exists(os.path.join(project_dir, "package.json")):
        missing.append("package.json")
    if not (os.path.exists(os.path.join(project_dir, "vite.config.js")) or
            os.path.exists(os.path.join(project_dir, "vite.config.ts"))):
        missing.append("vite.config.js/ts")
    if not (os.path.exists(os.path.join(project_dir, "src", "main.jsx")) or
            os.path.exists(os.path.join(project_dir, "src", "main.tsx"))):
        missing.append("src/main.jsx")
    return missing


def _parse_build_errors(output):
    """Parse build errors from npm/vite output."""
    errors = []
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue
        if "error" in line.lower() or "failed" in line.lower():
            errors.append(line)
    return errors[:20]  # Cap at 20 errors
