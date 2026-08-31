"""Nexus Flow AI - Preview Document Builder

Builds self-contained HTML preview documents from website state.
The preview is a complete, standalone HTML page with inlined CSS/JS.
"""

import re


def build_preview_document(state):
    """Build a complete, self-contained HTML preview document from website state.

    Returns a full HTML string ready for iframe srcdoc or direct display.
    """
    raw_html = state.get("html", "") or ""
    raw_css = state.get("css", "") or ""
    raw_js = state.get("javascript", "") or ""

    clean_h, extra_css, extra_js = clean_preview_html(raw_html)
    clean_c = clean_preview_css(raw_css + ("\n" + extra_css if extra_css else ""))
    clean_j = clean_preview_javascript(raw_js + ("\n" + extra_js if extra_js else ""))

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.6.0/css/all.min.css">\n'
        '  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">\n'
        "  <style>\n"
        + clean_c
        + "\n  </style>\n"
        "</head>\n"
        "<body>\n"
        + clean_h
        + '\n<script>\n  try {\n'
        + clean_j
        + "\n  } catch(e) {\n    console.error('Execution Error:', e);\n  }\n</script>\n"
        "</body>\n"
        "</html>"
    )


def clean_preview_html(html_str):
    """Extract body content from full HTML documents and return clean body markup."""
    if not isinstance(html_str, str):
        html_str = ""

    text = html_str.strip()

    embedded_css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", text, re.DOTALL | re.IGNORECASE))
    embedded_js = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", text, re.DOTALL | re.IGNORECASE))

    text = re.sub(r"<style[^>]*>.*?(?:</style>|$)", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?(?:</script>|$)", "", text, flags=re.DOTALL | re.IGNORECASE)

    body_match = re.search(r"<body[^>]*>(.*?)</body>", text, re.DOTALL | re.IGNORECASE)
    if body_match:
        text = body_match.group(1)
    else:
        text = re.sub(r"<!DOCTYPE[^>]*>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"</?html[^>]*>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<head[^>]*>.*?</head>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"</?body[^>]*>", "", text, flags=re.IGNORECASE)

    text = _balance_html_tags(text.strip())
    return text, embedded_css, embedded_js


def clean_preview_css(css_str):
    """Clean and normalize CSS for preview."""
    if not isinstance(css_str, str):
        css_str = ""
    text = css_str.strip()
    text = re.sub(r"</?style[^>]*>", "", text, flags=re.IGNORECASE).strip()

    if "/*" in text and "*/" not in text[text.rfind("/*"):]:
        text += " */"

    open_b = text.count("{")
    close_b = text.count("}")
    if open_b > close_b:
        text += "\n" + ("}" * (open_b - close_b))

    base_reset = (
        "*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }\n"
        "html { font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif; line-height: 1.6; -webkit-text-size-adjust: 100%; scroll-behavior: smooth; }\n"
        "body { margin: 0; padding: 0; width: 100%; min-height: 100vh; background-color: #090d16; color: #f8fafc; overflow-x: hidden; display: flex; flex-direction: column; }\n"
        "section, header, footer, nav, main, article, aside { display: block; position: relative; width: 100%; clear: both; box-sizing: border-box; }\n"
        ".container, .wrapper, .section-container { width: 100%; max-width: 1240px; margin-left: auto; margin-right: auto; padding-left: 1.5rem; padding-right: 1.5rem; box-sizing: border-box; }\n"
        "img, video, svg, iframe, canvas { max-width: 100%; height: auto; display: block; }\n"
        "a { text-decoration: none; color: inherit; transition: all 0.2s ease; }\n"
        "button, input, select, textarea { font-family: inherit; font-size: inherit; }"
    )

    if not text:
        return base_reset
    if "box-sizing" not in text:
        text = base_reset + "\n\n" + text
    return text


def clean_preview_javascript(js_str):
    """Clean and normalize JavaScript for preview."""
    if not isinstance(js_str, str):
        js_str = ""
    text = js_str.strip()
    text = re.sub(r"</?script[^>]*>", "", text, flags=re.IGNORECASE).strip()

    open_p = text.count("(")
    close_p = text.count(")")
    if open_p > close_p:
        text += ")" * (open_p - close_p)

    open_b = text.count("{")
    close_b = text.count("}")
    if open_b > close_b:
        text += "\n" + ("}" * (open_b - close_b))

    text = text.replace("</script>", "<\\/script>")
    return text


def _balance_html_tags(html_str):
    """Balance unclosed HTML tags."""
    if not html_str:
        return ""
    void_tags = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    tag_regex = re.compile(r"</?([a-zA-Z0-9-]+)(?:\s+[^>]*?)?>")
    stack = []
    for match in tag_regex.finditer(html_str):
        full_tag = match.group(0)
        tag_name = match.group(1).lower()
        if tag_name in void_tags or full_tag.endswith("/>"):
            continue
        if full_tag.startswith("</"):
            if stack and stack[-1] == tag_name:
                stack.pop()
        else:
            stack.append(tag_name)
    result = html_str
    while stack:
        missing_tag = stack.pop()
        result += "\n</" + missing_tag + ">"
    return result
