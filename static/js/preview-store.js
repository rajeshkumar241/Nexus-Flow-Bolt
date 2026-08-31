/* =========================================================
   NEXUS FLOW - SHARED PREVIEW STORE
   Single source of truth for website preview state across
   Builder, Code, and Quality pages.
   ========================================================= */
(function () {
    'use strict';

    /* ── State ──────────────────────────────────────────── */
    var _html = '';
    var _css = '';
    var _js = '';
    var _projectName = 'My AI Website';
    var _projectId = '';
    var _generating = false;
    var _error = null;
    var _listeners = [];

    /* ── Preview guard (same as builder-v2.js) ─────────── */
    var PREVIEW_GUARD_JS = [
        '(function(){',
        '  var EXTERNAL = /^(?:https?:|mailto:|tel:|data:|javascript:|#)/i;',
        '  document.addEventListener("click", function (e) {',
        '    var a = e.target && e.target.closest ? e.target.closest("a") : null;',
        '    if (a) {',
        '      var h = (a.getAttribute("href") || "").trim();',
        '      if (h && h.indexOf("//") !== 0 && !EXTERNAL.test(h)) e.preventDefault();',
        '    }',
        '  }, true);',
        '  document.addEventListener("submit", function (e) {',
        '    var f = e.target;',
        '    if (f && f.tagName === "FORM") {',
        '      var h = (f.getAttribute("action") || "").trim();',
        '      if (!h || (h.indexOf("//") !== 0 && !EXTERNAL.test(h))) e.preventDefault();',
        '    }',
        '  }, true);',
        '})();'
    ].join('\n');

    /* ── Helpers ────────────────────────────────────────── */
    function _notify() {
        for (var i = 0; i < _listeners.length; i++) {
            try { _listeners[i](_getState()); } catch (e) { console.error('[PreviewStore] Listener error:', e); }
        }
    }

    function _getState() {
        return {
            html: _html,
            css: _css,
            js: _js,
            projectName: _projectName,
            projectId: _projectId,
            generating: _generating,
            error: _error,
            hasContent: Boolean(_html || _css || _js)
        };
    }

    var _files = {};

    function prepareHtmlDocument(rawHtml, combinedCss, jsFiles, reactFiles, isReactProject) {
        var html = (rawHtml || '').trim();
        if (!html) {
            html = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head><body><div id="root"></div></body></html>';
        }

        // Strip relative stylesheet links while preserving external CDN links
        html = html.replace(/<link\b[^>]*\bhref=["']([^"']+)["'][^>]*>/gi, function (all, href) {
            var h = href.trim();
            if (/^(?:https?:|\/\/|data:)/i.test(h)) return all;
            return '';
        });

        // Strip relative script tags while preserving external CDN scripts
        html = html.replace(/<script\b[^>]*\bsrc=["']([^"']+)["'][^>]*>\s*<\/script>/gi, function (all, src) {
            var s = src.trim();
            if (/^(?:https?:|\/\/|data:)/i.test(s)) return all;
            return '';
        });

        // Replace relative media srcs to avoid 404s
        var ph = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><rect width="100" height="100" fill="#1e293b"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#64748b" font-family="sans-serif" font-size="12">Image</text></svg>');
        html = html.replace(/(<(?:img|source|video|audio|iframe)\b[^>]*\bsrc=["'])([^"']+)(["'][^>]*>)/gi, function (all, pre, src, post) {
            var s = src.trim();
            if (/^(?:https?:|\/\/|data:|blob:|#)/i.test(s)) return all;
            return pre + ph + post;
        });

        // Head elements
        var headInjections = [];
        headInjections.push('<script>\n' + PREVIEW_GUARD_JS + '\n</' + 'script>');

        if (isReactProject) {
            if (!html.includes('react.production.min.js') && !html.includes('react.development.js') && !html.includes('unpkg.com/react') && !html.includes('/static/vendor/react/')) {
                headInjections.push('<script crossorigin src="/static/vendor/react/react.production.min.js"></' + 'script>');
                headInjections.push('<script crossorigin src="/static/vendor/react/react-dom.production.min.js"></' + 'script>');
            }
            if (!html.includes('babel.min.js') && !html.includes('@babel/standalone') && !html.includes('/static/vendor/babel/')) {
                headInjections.push('<script src="/static/vendor/babel/babel.min.js"></' + 'script>');
            }
            if (!html.includes('tailwindcss') && !html.includes('cdn.tailwindcss.com') && !html.includes('/static/vendor/tailwind/')) {
                headInjections.push('<script src="/static/vendor/tailwind/tailwind.js"></' + 'script>');
            }
        }

        if (!html.includes('font-awesome') && !html.includes('/static/vendor/fontawesome')) {
            headInjections.push('<link rel="stylesheet" href="/static/vendor/fontawesome/css/all.min.css">');
        }
        if (!html.includes('/static/vendor/fonts/fonts.css') && !html.includes('fonts.googleapis.com')) {
            headInjections.push('<link rel="stylesheet" href="/static/vendor/fonts/fonts.css">');
        }

        if (combinedCss && combinedCss.trim()) {
            headInjections.push('<style id="nexus-injected-styles">\n' + combinedCss + '\n</style>');
        }

        var headContent = headInjections.join('\n');

        // Body scripts
        var bodyInjections = [];
        var standardJs = [];
        if (_js && !isReactProject) {
            standardJs.push(_js);
        }
        jsFiles.forEach(function (jf) {
            if (jf.content && standardJs.indexOf(jf.content) === -1) {
                standardJs.push(jf.content);
            }
        });

        if (standardJs.length > 0) {
            var fullJsCode = standardJs.join('\n\n');
            bodyInjections.push('<script id="nexus-injected-scripts">\nwindow.addEventListener("error", function(e) { console.error("[Preview JS Error]", e.message); });\ntry {\n' + fullJsCode + '\n} catch(e) { console.error("[Preview Runtime Error]", e); }\n</' + 'script>');
        }

        if (isReactProject && reactFiles.length > 0) {
            var reactCode = reactFiles.map(function (rf) {
                var code = rf.content || '';
                code = code.replace(/import\s+(?:React(?:\s*,\s*\{[^}]*\})?|\{[^}]*\})\s+from\s+['"][^'"]+['"];?/g, function(m) {
                    var namedMatch = m.match(/\{([^}]+)\}/);
                    if (namedMatch) {
                        var vars = namedMatch[1].split(',').map(function(v) { return v.trim(); }).filter(Boolean);
                        return 'const { ' + vars.join(', ') + ' } = React;';
                    }
                    return '';
                });
                code = code.replace(/import\s+[^;]+;?/g, '');
                code = code.replace(/export\s+default\s+/g, 'window.App = ');
                code = code.replace(/export\s+/g, '');
                return code;
            }).join('\n\n');

            var autoMountCode = [
                '\n// Auto mount React component if not explicitly mounted',
                'if (typeof window.App !== "undefined" || typeof App !== "undefined") {',
                '  const RootComp = typeof window.App !== "undefined" ? window.App : App;',
                '  const container = document.getElementById("root") || document.getElementById("app") || document.body;',
                '  if (container && window.ReactDOM && (window.ReactDOM.createRoot || window.ReactDOM.render)) {',
                '    try {',
                '      if (window.ReactDOM.createRoot) {',
                '        const root = window.ReactDOM.createRoot(container);',
                '        root.render(React.createElement(RootComp));',
                '      } else {',
                '        window.ReactDOM.render(React.createElement(RootComp), container);',
                '      }',
                '    } catch(mountErr) {',
                '      console.error("[React Auto-Mount Error]", mountErr);',
                '    }',
                '  }',
                '}'
            ].join('\n');

            bodyInjections.push('<script type="text/babel" id="nexus-injected-react">\n' + reactCode + '\n' + autoMountCode + '\n</' + 'script>');
        }

        var bodyScripts = bodyInjections.join('\n');

        var finalDoc = '';
        var hasDocType = /<!DOCTYPE/i.test(html);
        var hasHtmlTag = /<html[\s>]/i.test(html);
        var hasHeadTag = /<head[\s>]/i.test(html);
        var hasBodyTag = /<body[\s>]/i.test(html);

        if (hasHtmlTag && hasHeadTag && hasBodyTag) {
            finalDoc = html.replace(/<head([^>]*)>/i, '<head$1>\n' + headContent);
            finalDoc = finalDoc.replace(/<\/body>/i, bodyScripts + '\n</body>');
        } else if (hasHtmlTag && hasBodyTag) {
            finalDoc = html.replace(/<html([^>]*)>/i, '<html$1>\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n' + headContent + '\n</head>');
            finalDoc = finalDoc.replace(/<\/body>/i, bodyScripts + '\n</body>');
        } else if (hasBodyTag) {
            finalDoc = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n' + headContent + '\n</head>\n' + html.replace(/<\/body>/i, bodyScripts + '\n</body>') + '\n</html>';
        } else {
            var bodyWrapper = isReactProject && !html.includes('id="root"') && !html.includes('id="app"')
                ? '<div id="root">' + html + '</div>'
                : html;
            finalDoc = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n' + headContent + '\n</head>\n<body>\n' + bodyWrapper + '\n' + bodyScripts + '\n</body>\n</html>';
        }

        if (!hasDocType && !finalDoc.startsWith('<!DOCTYPE html>')) {
            finalDoc = '<!DOCTYPE html>\n' + finalDoc;
        }

        return finalDoc;
    }

    function buildPreviewDocument() {
        var fileMap = Object.assign({}, _files);
        var rawHtml = _html || fileMap['index.html'] || fileMap['index.htm'] || '';
        
        var cssPieces = [];
        if (_css && _css.trim()) cssPieces.push(_css.trim());
        Object.keys(fileMap).forEach(function (name) {
            if (name.endsWith('.css')) {
                var content = (fileMap[name] || '').trim();
                if (content && cssPieces.indexOf(content) === -1) cssPieces.push(content);
            }
        });
        var combinedCss = cssPieces.join('\n\n');

        var isReactProject = false;
        var reactFiles = [];
        var jsFiles = [];

        Object.keys(fileMap).forEach(function (name) {
            var content = fileMap[name] || '';
            if (name.endsWith('.jsx') || name.endsWith('.tsx')) {
                isReactProject = true;
                reactFiles.push({ name: name, content: content });
            } else if (name.endsWith('.js')) {
                if (/\b(?:import\s+React|React\.useState|React\.useEffect|ReactDOM|from\s+['"]react['"]|className=|<[A-Z][A-Za-z0-9]*[\s/>])/i.test(content)) {
                    isReactProject = true;
                    reactFiles.push({ name: name, content: content });
                } else {
                    jsFiles.push({ name: name, content: content });
                }
            }
        });

        if (!isReactProject && _js) {
            if (/\b(?:import\s+React|React\.useState|React\.useEffect|ReactDOM|from\s+['"]react['"]|className=|<[A-Z][A-Za-z0-9]*[\s/>])/i.test(_js)) {
                isReactProject = true;
                reactFiles.push({ name: 'script.js', content: _js });
            }
        }

        return prepareHtmlDocument(rawHtml, combinedCss, jsFiles, reactFiles, isReactProject);
    }

    /* ── Public API ────────────────────────────────────── */
    window.NexusPreviewStore = {
        /**
         * Set the website HTML content.
         * @param {string} html
         */
        setHtml: function (html) { _html = html || ''; _notify(); },

        /**
         * Set the website CSS content.
         * @param {string} css
         */
        setCss: function (css) { _css = css || ''; _notify(); },

        /**
         * Set the website JavaScript content.
         * @param {string} js
         */
        setJs: function (js) { _js = js || ''; _notify(); },

        /**
         * Set all website content at once.
         * @param {Object} files - { html, css, javascript } or { index.html, styles.css, script.js }
         */
        setContent: function (files) {
            if (!files) return;
            _files = Object.assign({}, files);
            _html = files.html || files['index.html'] || files['index.htm'] || _html || '';
            _css = files.css || files.stylesheet || files['styles.css'] || files['style.css'] || _css || '';
            _js = files.javascript || files.js || files['script.js'] || files['main.js'] || _js || '';
            _notify();
        },

        /**
         * Set from a full website state object (like currentWebsiteState).
         * @param {Object} state - { html, css, javascript, files, website_name, project_id }
         */
        setState: function (state) {
            if (!state) return;
            _files = Object.assign({}, state.files || {});
            _html = state.html || '';
            _css = state.css || '';
            _js = state.javascript || '';
            if (state.files) {
                _html = _html || state.files['index.html'] || state.files['index.htm'] || '';
                _css = _css || state.files['styles.css'] || state.files['style.css'] || '';
                _js = _js || state.files['script.js'] || state.files['main.js'] || '';
            }
            _projectName = state.website_name || _projectName;
            _projectId = state.project_id || _projectId;
            _notify();
        },

        setProjectName: function (name) { _projectName = name || _projectName; _notify(); },
        setProjectId: function (id) { _projectId = id || _projectId; _notify(); },
        setGenerating: function (val) { _generating = val; _notify(); },
        setError: function (err) { _error = err; _notify(); },
        clearError: function () { _error = null; _notify(); },

        /** Get the full state snapshot. */
        getState: _getState,

        /** Get the built preview document HTML. */
        getPreviewDocument: buildPreviewDocument,

        /** Get the current HTML content. */
        getHtml: function () { return _html; },

        /** Get the current CSS content. */
        getCss: function () { return _css; },

        /** Get the current JS content. */
        getJs: function () { return _js; },

        /** Get all files. */
        getFiles: function () { return Object.assign({}, _files); },

        /** Get the project ID. */
        getProjectId: function () { return _projectId; },

        /** Check if there is content to preview. */
        hasContent: function () { return Boolean(_html || _css || _js || Object.keys(_files).length > 0); },

        /** Subscribe to state changes. Returns an unsubscribe function. */
        subscribe: function (fn) {
            if (typeof fn !== 'function') return function () {};
            _listeners.push(fn);
            return function () {
                var idx = _listeners.indexOf(fn);
                if (idx !== -1) _listeners.splice(idx, 1);
            };
        },

        /** Clear all state. */
        reset: function () {
            _html = '';
            _css = '';
            _js = '';
            _files = {};
            _projectName = 'My AI Website';
            _projectId = '';
            _generating = false;
            _error = null;
            _notify();
        }
    };

})();
