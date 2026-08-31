document.addEventListener('DOMContentLoaded', () => {
  const state = window.NEXUS_WORKSPACE_STATE || {};
  const previewFrame = document.getElementById('previewFrame');
  const generationInput = document.getElementById('builderPrompt');
  const websiteNameInput = document.getElementById('websiteNameInput');
  const generateBtn = document.getElementById('generateBtn');
  const aiPromptInput = document.getElementById('aiPromptInput');
  const sendAiBtn = document.getElementById('sendAiBtn');
  const monacoEditorContainer = document.getElementById('monacoEditorContainer');
  const saveEditorBtn = document.getElementById('saveEditorBtn');
  const formatEditorBtn = document.getElementById('formatEditorBtn');
  const copyEditorBtn = document.getElementById('copyEditorBtn');
  const downloadHtmlBtn = document.getElementById('downloadHtmlBtn');
  const downloadZipBtn = document.getElementById('downloadZipBtn');
  const autosaveToggle = document.getElementById('autosaveToggle');
  const autocompleteToggle = document.getElementById('autocompleteToggle');
  const lineNumbersToggle = document.getElementById('lineNumbersToggle');

  let editor = null;
  let activeLanguage = 'html';
  let editorModels = {};
  let currentState = {
    website_name: state.website_name || 'My AI Website',
    prompt: state.prompt || '',
    html: state.html || '',
    css: state.css || '',
    javascript: state.javascript || '',
    chat_history: Array.isArray(state.chat_history) ? state.chat_history : []
  };

  function sanitizeClientCode(codeStr) {
    if (!codeStr || typeof codeStr !== "string") return "";
    let str = codeStr.trim();
    str = str.replace(/^```[a-zA-Z0-9_-]*\s*\n?/g, "");
    str = str.replace(/\n?```\s*$/g, "");
    str = str.replace(/```/g, "");
    return str.trim();
  }

  function stripClientTypeScript(jsStr) {
    if (!jsStr || typeof jsStr !== "string") return "";
    let text = jsStr;
    text = text.replace(/interface\s+[A-Za-z0-9_]+\s*\{[^}]*\}/g, "");
    text = text.replace(/type\s+[A-Za-z0-9_]+\s*=[^;]+;/g, "");
    text = text.replace(/enum\s+[A-Za-z0-9_]+\s*\{[^}]*\}/g, "");
    text = text.replace(/\s+as\s+[A-Za-z0-9_<>[\]]+/g, "");
    text = text.replace(/(\b[a-zA-Z0-9_]+)\s*:\s*([A-Za-z0-9_<>[\]|&\s]+)(?=[=,\)\n;])/g, "$1");
    text = text.replace(/\)\s*:\s*([A-Za-z0-9_<>[\]|&\s]+)\s*=>/g, ") =>");
    text = text.replace(/\)\s*:\s*([A-Za-z0-9_<>[\]|&\s]+)\s*\{/g, ") {");
    return text;
  }

  function balanceClientHtmlTags(htmlStr) {
    if (!htmlStr) return "";
    let lines = htmlStr.split("\n");
    let cleanedLines = [];
    lines.forEach(line => {
      let stripped = line.trim();
      if (stripped.startsWith("```")) return;
      cleanedLines.push(line);
    });
    let text = cleanedLines.join("\n");

    const voidTags = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);
    const tagRegex = /<\/?([a-zA-Z0-9-]+)(?:\s+[^>]*?)?>/g;
    const stack = [];
    let match;

    while ((match = tagRegex.exec(text)) !== null) {
      let fullTag = match[0];
      let tagName = match[1].toLowerCase();

      if (voidTags.has(tagName) || fullTag.endsWith('/>')) continue;

      if (fullTag.startsWith('</')) {
        if (stack.length && stack[stack.length - 1] === tagName) {
          stack.pop();
        } else if (stack.includes(tagName)) {
          while (stack.length && stack[stack.length - 1] !== tagName) {
            stack.pop();
          }
          if (stack.length) stack.pop();
        }
      } else {
        stack.push(tagName);
      }
    }

    while (stack.length) {
      let missingTag = stack.pop();
      text += `\n</${missingTag}>`;
    }

    return text;
  }

  // Nexus Flow routes that must never be navigated to from generated websites
  const NEXUS_FLOW_ROUTES = [
    "/builder", "/dashboard", "/login", "/register", "/profile", "/settings",
    "/projects", "/chat", "/admin", "/preview", "/code-editor", "/website-ai",
    "/download", "/upload", "/generate", "/save", "/delete", "/website_state",
    "/home", "/logout", "/templates", "/downloads", "/camera"
  ];

  function buildIsolationLayer() {
    return `
(function() {
  'use strict';
  var NEXUS_ROUTES = ${JSON.stringify(NEXUS_FLOW_ROUTES)};
  function isNexusRoute(url) {
    if (!url) return false;
    var path = url;
    try { var u = new URL(url, window.location.href); path = u.pathname; } catch(e) {}
    var lower = path.toLowerCase();
    for (var i = 0; i < NEXUS_ROUTES.length; i++) {
      if (lower === NEXUS_ROUTES[i] || lower.startsWith(NEXUS_ROUTES[i] + '/')) return true;
    }
    if (lower.startsWith('/') && !lower.includes('.') && !lower.startsWith('/#')) {
      if (lower.startsWith('/static/') || lower.startsWith('/uploads/')) return false;
      return true;
    }
    return false;
  }
  function showIsolationNotice(message) {
    var existing = document.getElementById('nexus-isolation-notice');
    if (existing) existing.remove();
    var notice = document.createElement('div');
    notice.id = 'nexus-isolation-notice';
    notice.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:rgba(var(--accent-rgb),0.95);color:#fff;padding:12px 24px;border-radius:12px;font-family:system-ui,sans-serif;font-size:14px;font-weight:600;z-index:99999;box-shadow:0 8px 32px rgba(0,0,0,0.4);max-width:90%;text-align:center;';
    notice.textContent = message || 'This action is part of your generated website preview.';
    document.body.appendChild(notice);
    setTimeout(function() { notice.remove(); }, 3000);
  }
  document.addEventListener('click', function(e) {
    var link = e.target.closest ? e.target.closest('a') : null;
    if (!link) return;
    var href = link.getAttribute('href') || '';
    var target = link.getAttribute('target') || '';
    if (/^https?:\\/\\//i.test(href)) {
      if (target !== '_blank') { e.preventDefault(); window.open(href, '_blank'); }
      return;
    }
    if (href.startsWith('#')) return;
    if (isNexusRoute(href)) {
      e.preventDefault();
      showIsolationNotice('This link is part of your generated website preview and cannot navigate to the Nexus Flow application.');
      return;
    }
    if (!href.startsWith('/') && !href.startsWith('#')) {
      e.preventDefault();
      var pageName = href.split('/').pop().replace(/\\.html?$/i, '').replace(/[-_]/g, ' ');
      var sectionId = pageName.toLowerCase().replace(/[^a-z0-9]+/g, '-');
      var section = document.getElementById(sectionId) || document.querySelector('[data-page="' + pageName.toLowerCase() + '"]');
      if (section) { section.scrollIntoView({ behavior: 'smooth' }); }
      else { showIsolationNotice('"' + pageName + '" page is part of your generated website. This section is available in the full version.'); }
      return;
    }
    if (href.startsWith('/')) {
      e.preventDefault();
      showIsolationNotice('This link is part of your generated website preview.');
    }
  }, true);
  document.addEventListener('submit', function(e) {
    var form = e.target;
    if (!form || form.tagName !== 'FORM') return;
    var action = form.getAttribute('action') || '';
    if (isNexusRoute(action) || action.startsWith('/')) {
      e.preventDefault();
      showIsolationNotice('Form submitted successfully! (Preview mode - data is not sent to a server)');
      var submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
      if (submitBtn) {
        var original = submitBtn.textContent;
        submitBtn.textContent = '✓ Submitted';
        submitBtn.disabled = true;
        setTimeout(function() { submitBtn.textContent = original; submitBtn.disabled = false; form.reset(); }, 2000);
      }
    }
  }, true);
  var originalLocation = window.location;
  Object.defineProperty(window, 'location', {
    get: function() { return originalLocation; },
    set: function(value) {
      if (typeof value === 'string' && isNexusRoute(value)) {
        showIsolationNotice('Navigation blocked: This would leave your generated website.');
        return;
      }
      originalLocation.href = value;
    }
  });
  var originalOpen = window.open;
  window.open = function(url, name, features) {
    if (typeof url === 'string' && isNexusRoute(url)) {
      showIsolationNotice('Navigation blocked: This would leave your generated website.');
      return null;
    }
    return originalOpen.call(window, url, name, features);
  };
  console.log('Nexus Flow isolation layer active - generated website is fully isolated.');
})();
`;
  }

  function buildPreviewDocument() {
    let html = sanitizeClientCode(currentState.html || '');
    let css = sanitizeClientCode(currentState.css || '');
    let js = sanitizeClientCode(currentState.javascript || '');

    // Extract CSS from <style> tags if no separate CSS
    if (!css || css.trim() === "") {
      const styleMatches = html.match(/<style[^>]*>([\s\S]*?)<\/style>/gi);
      if (styleMatches) {
        css = styleMatches.map(s => s.replace(/<\/?style[^>]*>/gi, '').trim()).join('\n\n');
      }
    }

    // Remove <style> tags from HTML
    html = html.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
    
    // Remove <script> tags from HTML (we'll add them back separately)
    html = html.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');

    // Clean up the HTML - extract body content only
    let bodyContent = html;
    bodyContent = bodyContent.replace(/<!DOCTYPE[^>]*>/gi, '');
    bodyContent = bodyContent.replace(/<\/?html[^>]*>/gi, '');
    bodyContent = bodyContent.replace(/<head[^>]*>[\s\S]*?<\/head>/gi, '');
    bodyContent = bodyContent.replace(/<\/?body[^>]*>/gi, '');
    bodyContent = bodyContent.trim();

    // Clean CSS
    css = css.replace(/<\/?style[^>]*>/gi, '').trim();
    if (css.includes("/*") && !css.slice(css.lastIndexOf("/*")).includes("*/")) {
      css += " */";
    }
    let openB = (css.match(/{/g) || []).length;
    let closeB = (css.match(/}/g) || []).length;
    if (openB > closeB) {
      css += '\n' + '}'.repeat(openB - closeB);
    }

    // Add base reset if not present
    const baseReset = `*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif; line-height: 1.6; -webkit-text-size-adjust: 100%; scroll-behavior: smooth; }
body { margin: 0; padding: 0; width: 100%; min-height: 100vh; background-color: #090d16; color: #f8fafc; overflow-x: hidden; }
section, header, footer, nav, main, article, aside { display: block; position: relative; width: 100%; clear: both; box-sizing: border-box; }
.container, .wrapper, .section-container { width: 100%; max-width: 1240px; margin-left: auto; margin-right: auto; padding-left: 1.5rem; padding-right: 1.5rem; box-sizing: border-box; }
img, video, svg, iframe, canvas { max-width: 100%; height: auto; display: block; }
a { text-decoration: none; color: inherit; transition: all 0.2s ease; }
button, input, select, textarea { font-family: inherit; font-size: inherit; }`;

    if (!css.includes("box-sizing")) {
      css = baseReset + "\n\n" + css;
    }

    // Clean JavaScript
    let cleanJs = js.replace(/<\/?script[^>]*>/gi, '').trim();
    cleanJs = stripClientTypeScript(cleanJs);
    
    // Dynamically strip DOMContentLoaded wrapper from AI's code to prevent race conditions
    cleanJs = cleanJs.replace(/document\.addEventListener\s*\(\s*['"]DOMContentLoaded['"]\s*,\s*(?:function\s*\([^)]*\)\s*\{|\(\)\s*=>\s*\{)([\s\S]*?)\}\s*\)\s*;/g, '$1');
    cleanJs = cleanJs.replace(/window\.addEventListener\s*\(\s*['"]DOMContentLoaded['"]\s*,\s*(?:function\s*\([^)]*\)\s*\{|\(\)\s*=>\s*\{)([\s\S]*?)\}\s*\)\s*;/g, '$1');

    cleanJs = cleanJs.replace(/<\/script>/gi, '<\\/script>');

    // Build the complete isolated HTML document - NO NEXUS FLOW UI
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${currentState.website_name || 'Generated Website'}</title>
  <link rel="stylesheet" href="/static/vendor/fontawesome/css/all.min.css">
  <link rel="stylesheet" href="/static/vendor/fonts/fonts.css">
<style>
${css}
  </style>
</head>
<body>
${bodyContent}
  <script>
${buildIsolationLayer()}
  <\/script>
  <script>
  try {
${cleanJs}
  } catch(e) {
    console.error('Execution Error:', e);
  }
  <\/script>
</body>
</html>`;
  }

  var _workspaceBlobUrl = null;
  function renderPreview() {
    if (!previewFrame) return;
    try {
      var doc = buildPreviewDocument();
      if (_workspaceBlobUrl) {
        try { URL.revokeObjectURL(_workspaceBlobUrl); } catch (e) {}
      }
      var blob = new Blob([doc], { type: 'text/html;charset=utf-8' });
      _workspaceBlobUrl = URL.createObjectURL(blob);
      previewFrame.src = _workspaceBlobUrl;
    } catch (err) {
      console.error('[Workspace] Preview render error:', err);
      try { previewFrame.srcdoc = buildPreviewDocument(); } catch(e) {}
    }
  }

  async function pushStateToServer(projectId = null) {
    try {
      const res = await fetch('/website_state/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, ...currentState })
      });
      const result = await res.json();
      if (result && result.project_id) {
        window.currentProjectId = result.project_id;
      }
      return result;
    } catch (err) {
      console.error('State sync failed', err);
    }
  }

  function updateStateFromEditors() {
    currentState.html = editorModels.html ? editorModels.html.getValue() : currentState.html;
    currentState.css = editorModels.css ? editorModels.css.getValue() : currentState.css;
    currentState.javascript = editorModels.javascript ? editorModels.javascript.getValue() : currentState.javascript;
    renderPreview();
    if (autosaveToggle && autosaveToggle.checked) {
      pushStateToServer(window.currentProjectId || null);
    }
  }

  function initializeMonaco() {
    if (!monacoEditorContainer || typeof require === 'undefined') {
      setTimeout(initializeMonaco, 200);
      return;
    }

    require.config({ paths: { vs: '/static/vendor/monaco/min/vs' } });
    require(['vs/editor/editor.main'], () => {
      const htmlModel = monaco.editor.createModel(currentState.html || '', 'html');
      const cssModel = monaco.editor.createModel(currentState.css || '', 'css');
      const jsModel = monaco.editor.createModel(currentState.javascript || '', 'javascript');
      editorModels = { html: htmlModel, css: cssModel, javascript: jsModel };

      editor = monaco.editor.create(monacoEditorContainer, {
        model: htmlModel,
        theme: 'vs-dark',
        automaticLayout: true,
        lineNumbers: lineNumbersToggle ? (lineNumbersToggle.checked ? 'on' : 'off') : 'on',
        wordWrap: 'on',
        minimap: { enabled: false },
        fontSize: 13,
        autoClosingBrackets: 'always',
        autoClosingTags: true,
        tabSize: 2,
        suggestOnTriggerCharacters: true,
        quickSuggestions: autocompleteToggle ? (autocompleteToggle.checked ? true : false) : true
      });

      ['html', 'css', 'javascript'].forEach(lang => {
        editorModels[lang].onDidChangeContent(() => {
          updateStateFromEditors();
        });
      });

      renderPreview();
    });
  }

  function setActiveEditor(lang) {
    activeLanguage = lang;
    document.querySelectorAll('.editor-tab').forEach(tab => tab.classList.toggle('active', tab.dataset.lang === lang));
    if (editor && editorModels[lang]) {
      editor.setModel(editorModels[lang]);
    }
  }

  document.querySelectorAll('.editor-tab').forEach(tab => {
    tab.addEventListener('click', () => setActiveEditor(tab.dataset.lang));
  });

  if (generateBtn) {
    generateBtn.addEventListener('click', async () => {
      const prompt = generationInput ? generationInput.value.trim() : '';
      const websiteName = websiteNameInput ? websiteNameInput.value.trim() : 'My AI Website';

      if (!prompt) {
        alert('Please enter a website prompt.');
        return;
      }

      currentState.website_name = websiteName;
      currentState.prompt = prompt;
      generateBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Generating...</span>';

      const res = await fetch('/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, website_name: websiteName })
      });
      const result = await res.json();
      if (result.success) {
        currentState.html = result.html || currentState.html;
        currentState.css = result.css || currentState.css;
        currentState.javascript = result.js || currentState.javascript;
        renderPreview();
        if (editorModels.html) editorModels.html.setValue(currentState.html);
        if (editorModels.css) editorModels.css.setValue(currentState.css);
        if (editorModels.javascript) editorModels.javascript.setValue(currentState.javascript);
        await pushStateToServer(result.project_id || null);
      }
      generateBtn.innerHTML = '<i class="fa-solid fa-bolt"></i><span>Generate Website</span>';
    });
  }

  document.querySelectorAll('.suggestion-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      const prompt = btn.dataset.prompt;
      if (generationInput && prompt) {
        generationInput.value = prompt;
      }
    });
  });

  if (previewFrame) {
    renderPreview();
  }

  document.querySelectorAll('.device-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.device-btn').forEach(item => item.classList.remove('active'));
      btn.classList.add('active');
      if (previewFrame) {
        previewFrame.style.width = btn.dataset.device === 'mobile' ? '380px' : btn.dataset.device === 'tablet' ? '768px' : '100%';
        previewFrame.style.maxWidth = '100%';
      }
    });
  });

  const refreshPreviewBtn = document.getElementById('refreshPreviewBtn');
  if (refreshPreviewBtn) {
    refreshPreviewBtn.addEventListener('click', renderPreview);
  }

  const fullscreenPreviewBtn = document.getElementById('fullscreenPreviewBtn');
  if (fullscreenPreviewBtn && previewFrame) {
    fullscreenPreviewBtn.addEventListener('click', () => {
      if (previewFrame.requestFullscreen) previewFrame.requestFullscreen();
    });
  }

  const newTabPreviewBtn = document.getElementById('newTabPreviewBtn');
  if (newTabPreviewBtn) {
    newTabPreviewBtn.addEventListener('click', () => {
      const blob = new Blob([buildPreviewDocument()], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
  }

  if (sendAiBtn && aiPromptInput) {
    sendAiBtn.addEventListener('click', async () => {
      const message = aiPromptInput.value.trim();
      if (!message) return;
      currentState.chat_history.push({ role: 'user', message });
      const chatMessages = document.getElementById('chatMessages');
      if (chatMessages) {
        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble user';
        bubble.innerHTML = `<strong>You</strong><p>${message}</p>`;
        chatMessages.appendChild(bubble);
      }
      aiPromptInput.value = '';

      const response = await fetch('/ai-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, html: currentState.html, css: currentState.css, js: currentState.javascript })
      });
      const result = await response.json();
      if (result.success) {
        currentState.html = result.html || currentState.html;
        currentState.css = result.css || currentState.css;
        currentState.javascript = result.js || currentState.javascript;
        currentState.chat_history.push({ role: 'assistant', message: result.reply || 'Updated successfully.' });
        renderPreview();
        if (editorModels.html) editorModels.html.setValue(currentState.html);
        if (editorModels.css) editorModels.css.setValue(currentState.css);
        if (editorModels.javascript) editorModels.javascript.setValue(currentState.javascript);
        if (chatMessages) {
          const bubble = document.createElement('div');
          bubble.className = 'chat-bubble assistant';
          bubble.innerHTML = `<strong>Nexus Flow AI</strong><p>${result.reply || 'Updated successfully.'}</p>`;
          chatMessages.appendChild(bubble);
        }
      }
    });
  }

  if (saveEditorBtn) {
    saveEditorBtn.addEventListener('click', () => {
      updateStateFromEditors();
      pushStateToServer(window.currentProjectId || null);
    });
  }

  if (formatEditorBtn) {
    formatEditorBtn.addEventListener('click', () => {
      if (editor) {
        editor.getAction('editor.action.formatDocument').run();
      }
    });
  }

  if (copyEditorBtn) {
    copyEditorBtn.addEventListener('click', () => {
      if (editor) {
        navigator.clipboard.writeText(editor.getValue());
      }
    });
  }

  if (downloadHtmlBtn) {
    downloadHtmlBtn.addEventListener('click', () => {
      const blob = new Blob([currentState.html || ''], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'index.html';
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  if (downloadZipBtn) {
    downloadZipBtn.addEventListener('click', async () => {
      const projectId = window.currentProjectId || null;
      if (projectId) {
        window.location.href = `/download/zip/${projectId}`;
      }
    });
  }

  [lineNumbersToggle, autocompleteToggle].forEach(toggle => {
    toggle && toggle.addEventListener('change', () => {
      if (editor) {
        editor.updateOptions({ lineNumbers: lineNumbersToggle && lineNumbersToggle.checked ? 'on' : 'off', quickSuggestions: autocompleteToggle ? autocompleteToggle.checked : true });
      }
    });
  });

  initializeMonaco();
});
