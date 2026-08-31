"""
Nexus Flow - Deployment Service
Builds deployment-ready bundles for static hosting (GitHub Pages / Netlify / Vercel).

Kept intentionally simple: given a project's unified state, it produces a
self-contained ZIP with the website files plus per-platform config files so
the user can push the folder to any static host. No live API calls made here.
"""

import io
import json
import re
import zipfile


def safe_rel_path(filename):
    """Return a sanitized relative path or None if unsafe (path traversal)."""
    if not filename or not isinstance(filename, str):
        return None
    norm = filename.replace("\\", "/")
    if norm.startswith("/") or ".." in norm.split("/"):
        return None
    return norm


def _sanitize_name(title):
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", title)
    return safe or "nexus-flow-site"


def build_deploy_manifest(files, title="Nexus Flow Website"):
    """Return the deployment config files as a dict {path: content}."""
    name = _sanitize_name(title).lower().replace("_", "-") or "nexus-flow-site"

    netlify_toml = f"""# Netlify configuration (Netlify.com)
[build]
  publish = "."

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[headers]
  "/*" = [
    "Cache-Control: public, max-age=0, must-revalidate",
    "X-Content-Type-Options: nosniff",
    "X-Frame-Options: SAMEORIGIN"
  ]
"""

    vercel_json = json.dumps({
        "name": name,
        "version": 2,
        "builds": [{"src": "index.html", "use": "@vercel/static"}],
        "routes": [
            {"src": "/(.*)", "dest": "/index.html"}
        ],
        "headers": [{
            "source": "/(.*)",
            "headers": [
                {"key": "Cache-Control", "value": "public, max-age=0, must-revalidate"},
                {"key": "X-Content-Type-Options", "value": "nosniff"},
                {"key": "X-Frame-Options", "value": "SAMEORIGIN"}
            ]
        }]
    }, indent=2)

    # GitHub Pages (Jekyll disabled via .nojekyll so static files are served as-is)
    gh_config = """# GitHub Pages - no Jekyll processing (static site served directly)
# Push this folder to a repo and enable Pages from the branch root.
"""

    deploy_readme = f"""# {title}

Generated with **Nexus Flow AI Website Builder**.

## Deploy options

### GitHub Pages
1. Push this folder to a GitHub repository.
2. Repo Settings → Pages → Source: "Deploy from a branch" → branch root.
3. The `.nojekyll` file disables Jekyll so your static files are served as-is.

### Netlify
1. Drag-and-drop this folder at https://app.netlify.com/drop
2. Or `netlify deploy --prod --dir .` with the CLI.
   `netlify.toml` is already configured.

### Vercel
1. `vercel` in this folder and follow the prompts.
2. Or import the repo on https://vercel.com — `vercel.json` is already configured.

## Run locally
Open `index.html` in a browser, or:
```bash
python -m http.server 8080
```
"""

    files_out = {
        "netlify.toml": netlify_toml,
        "vercel.json": vercel_json,
        "_config.yml": gh_config,
        ".nojekyll": "",
        "README-DEPLOY.md": deploy_readme,
    }
    # 404.html that redirects to index.html (SPA fallback on GitHub Pages)
    files_out["404.html"] = (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">'
        '<meta http-equiv="refresh" content="0; url=/index.html">'
        '<title>Redirecting...</title>\n</head>\n<body>\n'
        '<script>window.location.replace("/index.html");</script>\n'
        '<p><a href="/index.html">Continue to site</a></p>\n</body>\n</html>'
    )
    return files_out


def build_deploy_zip(files, title="Nexus Flow Website"):
    """
    Build a deployment-ready ZIP containing the website files + platform configs.

    Returns (bytes, filename).
    """
    deploy_configs = build_deploy_manifest(files, title)
    safe_name = _sanitize_name(title).lower().replace("_", "-") or "nexus-flow-site"

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        # Website files first (relative paths preserved)
        if isinstance(files, dict):
            for filename, content in files.items():
                safe = safe_rel_path(filename)
                if safe is None:
                    continue
                zf.writestr(safe, content or "")

        # Deployment config files
        for filename, content in deploy_configs.items():
            zf.writestr(filename, content or "")

    memory_file.seek(0)
    return memory_file.getvalue(), f"{safe_name}-deploy.zip"