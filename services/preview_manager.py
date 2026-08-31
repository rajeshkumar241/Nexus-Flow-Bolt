"""Nexus Flow AI - Preview Manager

Manages preview document building, HTML/CSS/JS cleaning, and
image source sanitization.
"""

import re
import hashlib


PUBLIC_IMAGE_BASE = "https://picsum.photos/seed"


def build_preview(state):
    """Build a preview document from website state.

    Returns a complete HTML string.
    """
    from services.preview_service import build_preview_document
    return build_preview_document(state)


def clean_html(html_str):
    """Extract body content from full HTML documents."""
    from services.preview_service import clean_preview_html
    return clean_preview_html(html_str)


def clean_css(css_str):
    """Clean and normalize CSS."""
    from services.preview_service import clean_preview_css
    return clean_preview_css(css_str)


def clean_javascript(js_str):
    """Clean and normalize JavaScript."""
    from services.preview_service import clean_preview_javascript
    return clean_preview_javascript(js_str)


def _is_public_url(url):
    """True when a URL can be loaded directly by a browser."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not url:
        return False
    return bool(re.match(r"^(https?:)?//", url)) or url.startswith((
        "data:", "blob:", "about:", "#", "mailto:", "tel:", "sms:",
        "javascript:", "callto:",
    ))


def _placeholder_public_image(path):
    """Deterministic public placeholder URL derived from the broken path."""
    seed = re.sub(r"[^a-z0-9]+", "-", (path or "hero").lower()).strip("-")[:60] or "hero"
    return f"{PUBLIC_IMAGE_BASE}/{seed}/1600/900"


def sanitize_image_sources(html_str):
    """Rewrite local/relative image references to working public URLs."""
    if not html_str or not isinstance(html_str, str):
        return html_str or ""

    def _swap_url(url):
        url = url.strip().strip('"').strip("'")
        return url if _is_public_url(url) else _placeholder_public_image(url)

    def _fix_attr(m):
        return m.group(1) + _swap_url(m.group(2)) + m.group(3)

    def _fix_srcset(m):
        urls = []
        for part in m.group(2).split(","):
            part = part.strip()
            if not part:
                continue
            bits = part.split()
            if bits:
                bits[0] = _swap_url(bits[0])
                urls.append(" ".join(bits))
        return m.group(1) + ", ".join(urls) + m.group(3)

    def _fix_tag(match):
        tag = match.group(0)
        tag = re.sub(r'(\bsrc\s*=\s*["\'])([^"\']*)(["\'])', _fix_attr, tag)
        tag = re.sub(r'(\bsrcset\s*=\s*["\'])([^"\']*)(["\'])', _fix_srcset, tag)
        tag = re.sub(r'(\bposter\s*=\s*["\'])([^"\']*)(["\'])', _fix_attr, tag)
        tag = re.sub(r'(\bdata-src\s*=\s*["\'])([^"\']*)(["\'])', _fix_attr, tag)
        return tag

    html_str = re.sub(
        r"<(img|video|source|iframe|picture|audio)\b[^>]*>",
        _fix_tag, html_str, flags=re.IGNORECASE
    )

    html_str = re.sub(
        r"url\(\s*(['"]?)[^'")]+\1\s*\)",
        lambda m: "url('" + _swap_url(m.group(0)[4:-1].strip().strip('"').strip("'")) + "')",
        html_str, flags=re.IGNORECASE
    )
    return html_str


def sanitize_css_image_urls(css_str):
    """Rewrite relative background-image url() values in CSS to public URLs."""
    if not css_str or not isinstance(css_str, str):
        return css_str or ""

    def _fix_url(match):
        url = match.group(2).strip()
        return match.group(0) if _is_public_url(url) else "url('" + _placeholder_public_image(url) + "')"

    return re.sub(
        r"url\(\s*(['"]?)([^'")]+)\1\s*\)",
        _fix_url, css_str, flags=re.IGNORECASE
    )
