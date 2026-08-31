/* =========================================================
   NEXUS FLOW AI - AI BUILDER ENHANCEMENTS
   Handles: Code Preview, AI Chat, Code Explanation, Code Quality
   ========================================================= */

(function () {
    "use strict";

    // =========================================================
    // STATE
    // =========================================================
    let currentFiles = {
        "index.html": "",
        "style.css": "",
        "script.js": ""
    };
    let currentProjectId = null;
    let currentFsProjectId = null;
    let currentChatHistory = [];

    // =========================================================
    // DOM REFERENCES
    // =========================================================

    // Code Preview
    const codeEditorHtml = document.getElementById("codeEditorHtml");
    const codeEditorCss = document.getElementById("codeEditorCss");
    const codeEditorJs = document.getElementById("codeEditorJs");
    const codeLineNumbersHtml = document.getElementById("codeLineNumbersHtml");
    const codeLineNumbersCss = document.getElementById("codeLineNumbersCss");
    const codeLineNumbersJs = document.getElementById("codeLineNumbersJs");
    const explainCodeBtn = document.getElementById("explainCodeBtn");
    const checkCodeBtn = document.getElementById("checkCodeBtn");
    const copyCodeBtn = document.getElementById("copyCodeBtn");
    const downloadFileBtn = document.getElementById("downloadFileBtn");
    const codeAnalysisResult = document.getElementById("codeAnalysisResult");
    const fileExplorerTree = document.getElementById("fileExplorerTree");
    const editorTabs = document.getElementById("editorTabs");
    const codeFullscreenBtn = document.getElementById("codeFullscreenBtn");
    const refreshFilesBtn = document.getElementById("refreshFilesBtn");
    const codeSearchInput = document.getElementById("codeSearchInput");
    const vscodeEditor = document.querySelector(".vscode-editor");
    let activeFileKey = "index.html";
    const FILES_GROUPS = [
        { group: "Frontend", files: ["index.html", "style.css", "script.js"] }
    ];
    let allFiles = {};
    let isFullscreen = false;

    // AI Chat
    const aiChatHistory = document.getElementById("aiChatHistory");
    const aiChatInput = document.getElementById("aiChatInput");
    const aiChatSendBtn = document.getElementById("aiChatSendBtn");

    // =========================================================
    // HELPER FUNCTIONS
    // =========================================================

    function escapeHtml(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    function showToast(message) {
        const saveToast = document.getElementById("saveToast");
        if (!saveToast) return;
        saveToast.querySelector("span").textContent = message || "Success";
        saveToast.classList.add("show");
        setTimeout(() => saveToast.classList.remove("show"), 3000);
    }

    function addChatBubble(container, role, text) {
        if (!container) return;
        const bubble = document.createElement("div");
        bubble.className = `chat-bubble ${role}`;
        const strong = document.createElement("strong");
        strong.textContent = role === "user" ? "You" : "Nexus AI";
        const p = document.createElement("p");
        p.textContent = text;
        bubble.appendChild(strong);
        bubble.appendChild(p);
        container.appendChild(bubble);
        container.scrollTop = container.scrollHeight;
    }

    // =========================================================
    // PROGRESS INDICATOR
    // =========================================================

    function showAnalysisResult(title, content, type) {
        if (!codeAnalysisResult) return;
        codeAnalysisResult.style.display = "block";
        codeAnalysisResult.innerHTML = `
            <div class="analysis-header">
                <h4><i class="fa-solid fa-${type === 'error' ? 'circle-exclamation' : type === 'check' ? 'circle-check' : 'wand-magic-sparkles'}"></i> ${escapeHtml(title)}</h4>
                <button class="analysis-close" onclick="this.parentElement.parentElement.style.display='none'">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>
            <div class="analysis-body">${content}</div>
        `;
    }

    // =========================================================
    // CODE PREVIEW - POPULATE EDITORS
    // =========================================================

    function extractGeneratedFiles(state) {
        // Build files object from current state
        const files = {};

        // Extract HTML
        let html = state.html || "";
        if (!html) {
            // Try to get iframe content
            const previewFrame = document.getElementById("previewFrame");
            if (previewFrame && previewFrame.contentDocument) {
                html = previewFrame.contentDocument.documentElement.outerHTML;
            }
        }

        let css = state.css || "";
        let js = state.javascript || "";

        // Extract embedded CSS from HTML if no separate CSS
        if (!css && html) {
            const styleMatch = html.match(/<style[^>]*>([\s\S]*?)<\/style>/i);
            if (styleMatch) css = styleMatch[1];
        }

        // Extract embedded JS from HTML if no separate JS
        if (!js && html) {
            const scriptMatches = html.match(/<script[^>]*>([\s\S]*?)<\/script>/gi);
            if (scriptMatches) {
                js = scriptMatches
                    .map(s => s.replace(/<\/?script[^>]*>/gi, '').trim())
                    .filter(s => s.length > 0)
                    .join('\n\n');
            }
        }

        files["index.html"] = html;
        files["style.css"] = css;
        files["script.js"] = js;

        return files;
    }

    function populateCodeEditors(files) {
        if (!files) return;
        currentFiles = files;

        if (codeEditorHtml) codeEditorHtml.value = files["index.html"] || files["home.html"] || "";
        if (codeEditorCss) codeEditorCss.value = files["style.css"] || files["styles.css"] || "";
        if (codeEditorJs) codeEditorJs.value = files["script.js"] || files["app.js"] || "";
    }

    function getActiveCodeEditor() {
        const fileKey = activeFileKey || "index.html";
        const lang = getFileLanguage(fileKey);

        if (lang === "html") return { editor: codeEditorHtml, type: "html" };
        if (lang === "css") return { editor: codeEditorCss, type: "css" };
        if (lang === "javascript") return { editor: codeEditorJs, type: "javascript" };
        return { editor: codeEditorHtml, type: "html" };
    }

    // =========================================================
    // CODE FILE TAB SWITCHING
    // =========================================================

    function initCodeFileTabs() {
        document.querySelectorAll(".code-file-tab").forEach(tab => {
            tab.addEventListener("click", () => {
                document.querySelectorAll(".code-file-tab").forEach(t => t.classList.remove("active"));
                document.querySelectorAll(".code-editor-textarea").forEach(e => e.classList.remove("active"));
                tab.classList.add("active");

                const fileType = tab.getAttribute("data-file");
                const editor = document.getElementById(`codeEditor${fileType.charAt(0).toUpperCase() + fileType.slice(1)}`);
                if (editor) editor.classList.add("active");
            });
        });
    }

    // =========================================================
    // CODE EXPLANATION
    // =========================================================

    async function explainCode() {
        const { editor, type } = getActiveCodeEditor();
        const code = editor ? editor.value : "";

        if (!code || !code.trim()) {
            showAnalysisResult("No Code to Explain", "Please generate a website first before using the code explanation feature.", "error");
            return;
        }

        explainCodeBtn.disabled = true;
        explainCodeBtn.innerHTML = '<div class="spinner" style="width:18px;height:18px;border-width:2px;"></div> Explaining...';

        try {
            const response = await fetch("/api/ai/explain-code", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    code: code,
                    language: type
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || "Failed to explain code");
            }

            // Format explanation with markdown-like headers
            const explanation = escapeHtml(data.explanation)
                .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
                .replace(/\n/g, "<br>");

            showAnalysisResult("Code Explanation", `<div class="code-explanation-content">${explanation}</div>`);

        } catch (error) {
            console.error("Explain code error:", error);
            showAnalysisResult("Error", "Unable to explain the code. Please try again.", "error");
        } finally {
            explainCodeBtn.disabled = false;
            explainCodeBtn.innerHTML = '<i class="fa-solid fa-graduation-cap"></i> Explain Code';
        }
    }

    // =========================================================
    // CODE QUALITY CHECK
    // =========================================================

    async function checkCodeQuality() {
        const files = currentFiles;

        if (!files || Object.keys(files).length === 0) {
            showAnalysisResult("No Code to Check", "Please generate a website first before using the code quality check.", "error");
            return;
        }

        checkCodeBtn.disabled = true;
        checkCodeBtn.innerHTML = '<div class="spinner" style="width:18px;height:18px;border-width:2px;"></div> Checking...';

        try {
            const response = await fetch("/api/ai/check-code", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ files: files })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || "Failed to check code");
            }

            const report = data.report || {};
            const issues = report.issues || [];
            const score = report.score || 70;
            const summary = report.summary || "Code review complete.";

            const severityIcons = {
                critical: '<i class="fa-solid fa-circle-exclamation" style="color:#ef4444;"></i>',
                warning: '<i class="fa-solid fa-triangle-exclamation" style="color:#f59e0b;"></i>',
                suggestion: '<i class="fa-solid fa-circle-info" style="color:#3b82f6;"></i>'
            };

            let issuesHtml = "";
            if (issues.length === 0) {
                issuesHtml = '<div class="quality-good"><i class="fa-solid fa-circle-check"></i> No significant issues found!</div>';
            } else {
                issues.forEach(issue => {
                    issuesHtml += `
                        <div class="quality-issue severity-${issue.severity || 'suggestion'}">
                            <div class="quality-issue-header">
                                ${severityIcons[issue.severity] || severityIcons.suggestion}
                                <span class="quality-category">${escapeHtml(issue.category || 'general')}</span>
                            </div>
                            <p>${escapeHtml(issue.message || '')}</p>
                            ${issue.suggestion ? `<div class="quality-suggestion"><strong>Fix:</strong> ${escapeHtml(issue.suggestion)}</div>` : ''}
                        </div>
                    `;
                });
            }

            showAnalysisResult(
                `Code Quality Report - Score: ${score}/100`,
                `<div class="quality-summary">${escapeHtml(summary)}</div>${issuesHtml}`
            );

        } catch (error) {
            console.error("Check code error:", error);
            showAnalysisResult("Error", "Unable to check the code. Please try again.", "error");
        } finally {
            checkCodeBtn.disabled = false;
            checkCodeBtn.innerHTML = '<i class="fa-solid fa-shield-halved"></i> Check Code Quality';
        }
    }

    // =========================================================
    // COPY CODE
    // =========================================================

    async function copyActiveCode() {
        const { editor } = getActiveCodeEditor();
        const code = editor ? editor.value : "";

        if (!code) {
            showToast("No code to copy");
            return;
        }

        try {
            await navigator.clipboard.writeText(code);
            showToast("Code copied to clipboard");
        } catch (error) {
            // Fallback for older browsers
            editor.select();
            document.execCommand("copy");
            showToast("Code copied to clipboard");
        }
    }

    // =========================================================
    // VS CODE STYLE CODE PREVIEW - FILE EXPLORER
    // =========================================================

    function getFileIconClass(filename) {
        if (filename.endsWith(".html")) return "fa-brands fa-html5 file-icon-html";
        if (filename.endsWith(".css")) return "fa-brands fa-css3-alt file-icon-css";
        if (filename.endsWith(".js")) return "fa-brands fa-js file-icon-js";
        if (filename.endsWith(".py")) return "fa-brands fa-python file-icon-py";
        if (filename.endsWith(".json")) return "fa-solid fa-brackets-curly file-icon-json";
        if (filename.endsWith(".md")) return "fa-solid fa-file-lines file-icon-md";
        if (filename.endsWith(".env.example") || filename.endsWith(".env")) return "fa-solid fa-key file-icon-env";
        if (filename.endsWith(".txt")) return "fa-solid fa-file-lines file-icon-txt";
        if (filename.endsWith(".py")) return "fa-brands fa-python file-icon-py";
        return "fa-solid fa-file file-icon-config";
    }

    function getFileLanguage(filename) {
        if (filename.endsWith(".html")) return "html";
        if (filename.endsWith(".css")) return "css";
        if (filename.endsWith(".js")) return "javascript";
        if (filename.endsWith(".py")) return "python";
        if (filename.endsWith(".json")) return "json";
        return "text";
    }

    function getEditorByFile(filename) {
        const lang = getFileLanguage(filename);
        if (lang === "html") return codeEditorHtml;
        if (lang === "css") return codeEditorCss;
        if (lang === "javascript") return codeEditorJs;
        return null;
    }

    function getLineNumbersByFile(filename) {
        const lang = getFileLanguage(filename);
        if (lang === "html") return codeLineNumbersHtml;
        if (lang === "css") return codeLineNumbersCss;
        if (lang === "javascript") return codeLineNumbersJs;
        return null;
    }

    function renderFileExplorer(filterText = "") {
        if (!fileExplorerTree) return;
        fileExplorerTree.innerHTML = "";

        const filter = (filterText || "").toLowerCase();

        FILES_GROUPS.forEach(group => {
            const groupDiv = document.createElement("div");
            groupDiv.className = "explorer-group";

            const groupTitle = document.createElement("div");
            groupTitle.className = "explorer-group-title";
            groupTitle.textContent = group.group;
            groupDiv.appendChild(groupTitle);

            group.files.forEach(filename => {
                if (filter && !filename.toLowerCase().includes(filter)) return;

                const fileItem = document.createElement("div");
                fileItem.className = "explorer-file" + (filename === activeFileKey ? " active" : "");
                fileItem.setAttribute("data-file", filename);
                fileItem.innerHTML = `<i class="${getFileIconClass(filename)}"></i><span>${filename}</span>`;

                fileItem.addEventListener("click", () => {
                    selectFile(filename);
                });

                groupDiv.appendChild(fileItem);
            });

            if (groupDiv.children.length > 1) {
                fileExplorerTree.appendChild(groupDiv);
            }
        });
    }

    function renderEditorTabs() {
        if (!editorTabs) return;

        // Only show tabs for files that have content
        const activeFiles = Object.keys(allFiles).filter(f => (allFiles[f] || "").trim().length > 0);

        if (activeFiles.length === 0) {
            editorTabs.innerHTML = `<div class="editor-tab-item active" data-file="index.html"><i class="${getFileIconClass("index.html")}"></i> index.html<span class="editor-tab-close"><i class="fa-solid fa-xmark"></i></span></div>`;
            return;
        }

        editorTabs.innerHTML = "";
        activeFiles.forEach(filename => {
            const tab = document.createElement("div");
            tab.className = "editor-tab-item" + (filename === activeFileKey ? " active" : "");
            tab.setAttribute("data-file", filename);
            tab.innerHTML = `<i class="${getFileIconClass(filename)}"></i> <span>${filename}</span><span class="editor-tab-close"><i class="fa-solid fa-xmark"></i></span>`;

            tab.addEventListener("click", (e) => {
                if (e.target.closest(".editor-tab-close")) {
                    // Close tab
                    hideFile(filename);
                    e.stopPropagation();
                    return;
                }
                selectFile(filename);
            });

            tab.querySelector(".editor-tab-close").addEventListener("click", (e) => {
                e.stopPropagation();
                hideFile(filename);
            });

            editorTabs.appendChild(tab);
        });
    }

    function hideFile(filename) {
        if (!allFiles[filename]) return;
        // Remove from allFiles and currentFiles
        delete allFiles[filename];
        delete currentFiles[filename];

        // If the active file was closed, switch to first available
        if (filename === activeFileKey) {
            const keys = Object.keys(allFiles);
            if (keys.length > 0) {
                selectFile(keys[0]);
            } else {
                activeFileKey = "index.html";
                renderFileExplorer();
                renderEditorTabs();
            }
        } else {
            renderFileExplorer();
            renderEditorTabs();
        }

        // Refresh line numbers for the current view
        updateLineNumbers();
    }

    function selectFile(filename) {
        if (!allFiles[filename]) {
            // Check if we have the file in currentFiles
            if (currentFiles[filename]) {
                allFiles[filename] = currentFiles[filename];
            } else {
                return;
            }
        }

        activeFileKey = filename;
        const editor = getEditorByFile(filename);
        const lineNumbers = getLineNumbersByFile(filename);
        const lang = getFileLanguage(filename);

        // Hide all editors, show the active one
        document.querySelectorAll(".code-editor-textarea").forEach(e => e.classList.remove("active"));
        document.querySelectorAll(".code-line-numbers").forEach(e => e.classList.remove("active"));

        if (editor) {
            editor.value = allFiles[filename] || "";
            editor.classList.add("active");
        }
        if (lineNumbers) {
            lineNumbers.classList.add("active");
        }

        // Update status bar language
        const statusLang = document.querySelector(".vscode-statusbar span:nth-child(3)");
        if (statusLang) {
            statusLang.innerHTML = `<i class="fa-solid fa-language"></i> ${lang.toUpperCase()}`;
        }

        renderFileExplorer();
        renderEditorTabs();
        updateLineNumbers();
    }

    function updateLineNumbers() {
        const editor = getEditorByFile(activeFileKey);
        const lineNumbers = getLineNumbersByFile(activeFileKey);
        if (!editor || !lineNumbers) return;

        const code = editor.value || "";
        const lines = code.split("\n").length;
        let lineNumbersHtml = "";
        for (let i = 1; i <= lines; i++) {
            lineNumbersHtml += i + "\n";
        }
        lineNumbers.textContent = lineNumbersHtml;
    }

    function mergeAllFiles() {
        allFiles = { ...currentFiles };
        // Ensure at least the three main files exist
        if (!allFiles["index.html"]) allFiles["index.html"] = "";
        if (!allFiles["style.css"]) allFiles["style.css"] = "";
        if (!allFiles["script.js"]) allFiles["script.js"] = "";
    }

    function refreshCodePreview() {
        mergeAllFiles();
        renderFileExplorer();
        renderEditorTabs();
        selectFile(activeFileKey);
    }

    // =========================================================
    // DOWNLOAD FILE
    // =========================================================

    function downloadActiveFile() {
        const editor = getEditorByFile(activeFileKey);
        const code = editor ? editor.value : "";
        if (!code) {
            showToast("No code to download");
            return;
        }

        const blob = new Blob([code], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = activeFileKey;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast(`${activeFileKey} downloaded`);
    }

    // =========================================================
    // FULLSCREEN MODE
    // =========================================================

    function toggleFullscreen() {
        if (!vscodeEditor) return;
        isFullscreen = !isFullscreen;
        vscodeEditor.classList.toggle("fullscreen", isFullscreen);

        if (codeFullscreenBtn) {
            codeFullscreenBtn.innerHTML = isFullscreen
                ? '<i class="fa-solid fa-compress"></i>'
                : '<i class="fa-solid fa-expand"></i>';
        }
    }

    // =========================================================
    // AI CHAT
    // =========================================================

    async function sendAiChat() {
        if (!aiChatInput) return;
        const message = (aiChatInput.value || "").trim();

        if (!message) {
            aiChatInput.focus();
            return;
        }

        addChatBubble(aiChatHistory, "user", message);
        aiChatInput.value = "";

        if (aiChatSendBtn) {
            aiChatSendBtn.disabled = true;
            aiChatSendBtn.innerHTML = '<div class="spinner" style="width:18px;height:18px;border-width:2px;"></div>';
        }

        // Add a loading indicator
        const loadingBubble = document.createElement("div");
        loadingBubble.className = "chat-bubble assistant";
        loadingBubble.id = "aiChatLoading";
        loadingBubble.innerHTML = '<strong>Nexus AI</strong><p class="typing-indicator">Generating website with Qwen AI...</p>';
        if (aiChatHistory) {
            aiChatHistory.appendChild(loadingBubble);
            aiChatHistory.scrollTop = aiChatHistory.scrollHeight;
        }

        try {
            const response = await fetch("/api/generate-website", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    prompt: message,
                    website_name: "My AI Website"
                })
            });

            const data = await response.json();

            // Remove loading indicator
            const loading = document.getElementById("aiChatLoading");
            if (loading) loading.remove();

            if (!response.ok || !data.success) {
                throw new Error(data.error || data.message || "Failed to generate website");
            }

            const reply = data.reply || data.message || "Your website is ready!";
            addChatBubble(aiChatHistory, "assistant", reply);

            // Save to chat history
            currentChatHistory.push({ role: "user", content: message });
            currentChatHistory.push({ role: "assistant", content: reply });

            // Update generated files and code editors
            const files = {
                "index.html": data.html || "",
                "style.css": data.css || "",
                "script.js": data.javascript || data.js || ""
            };
            populateCodeEditors(files);
            currentFiles = files;

            if (data.project_id) currentProjectId = data.project_id;

            // Update the shared current state
            const state = window.__nexusCurrentState || {};
            state.html = files["index.html"];
            state.css = files["style.css"];
            state.javascript = files["script.js"];
            state.project_id = data.project_id || state.project_id || null;
            window.__nexusCurrentState = state;

            // Display the preview inside the live preview iframe
            const previewFrame = document.getElementById("previewFrame");
            if (previewFrame) {
                if (data.preview) {
                    previewFrame.srcdoc = data.preview;
                } else if (typeof window.renderPreview === "function") {
                    window.renderPreview();
                }
            }

            // Update builder state through custom event
            document.dispatchEvent(new CustomEvent("websiteUpdatedFromAI", {
                detail: {
                    html: files["index.html"],
                    css: files["style.css"],
                    javascript: files["script.js"],
                    project_id: data.project_id
                }
            }));

            showToast("Website generated!");
            // Switch to preview tab
            const previewTab = document.querySelector('.workspace-tab[data-tab="preview"]');
            if (previewTab) previewTab.click();

        } catch (error) {
            console.error("AI chat error:", error);
            const loading = document.getElementById("aiChatLoading");
            if (loading) loading.remove();
            addChatBubble(aiChatHistory, "assistant", "I'm having trouble connecting right now. Please try again in a moment.");
        } finally {
            if (aiChatSendBtn) {
                aiChatSendBtn.disabled = false;
                aiChatSendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i>';
            }
        }
    }

    // =========================================================
    // LISTEN FOR WEBSITE GENERATION / UPDATE EVENTS
    // =========================================================

    function listenForWebsiteEvents() {
        // Listen for website generation (dispatched by the modified builder.js)
        document.addEventListener("websiteGenerated", (event) => {
            const state = event.detail || {};
            const files = extractGeneratedFiles(state);

            // Also store full generated file list if available from API
            if (state.files) {
                // Use the multi-file structure when available
                const mergedFiles = { ...files, ...state.files };
                currentFiles = mergedFiles;
                populateCodeEditors(mergedFiles);
            } else {
                currentFiles = files;
                populateCodeEditors(files);
            }

            currentProjectId = state.project_id || null;
            currentFsProjectId = state.fs_project_id || null;
            currentChatHistory = [];

            // Reset AI chat
            if (aiChatHistory) {
                aiChatHistory.innerHTML = `
                    <div class="chat-bubble assistant">
                        <strong>Nexus AI</strong>
                        <p>Hello! I'm your website building assistant. I can help you modify your generated website, explain code, or answer questions about your project. Try asking me to add dark mode, change colors, or add a new page.</p>
                    </div>`;
            }
        });

        // Listen for website updates from AI chat
        document.addEventListener("websiteUpdated", (event) => {
            const state = event.detail || {};
            const files = extractGeneratedFiles(state);
            populateCodeEditors(files);
            currentFiles = files;
            if (state.project_id) currentProjectId = state.project_id;
        });
    }

    // =========================================================
    // EVENT LISTENERS
    // =========================================================

    document.addEventListener("DOMContentLoaded", () => {
        initCodeFileTabs();
        listenForWebsiteEvents();

        // Code tools
        if (explainCodeBtn) explainCodeBtn.addEventListener("click", explainCode);
        if (checkCodeBtn) checkCodeBtn.addEventListener("click", checkCodeQuality);
        if (copyCodeBtn) copyCodeBtn.addEventListener("click", copyActiveCode);
        if (downloadFileBtn) downloadFileBtn.addEventListener("click", downloadActiveFile);
        if (codeFullscreenBtn) codeFullscreenBtn.addEventListener("click", toggleFullscreen);
        if (refreshFilesBtn) refreshFilesBtn.addEventListener("click", refreshCodePreview);

        if (codeSearchInput) {
            codeSearchInput.addEventListener("input", () => {
                renderFileExplorer(codeSearchInput.value);
            });
        }

        // Listen for editor input to update line numbers
        [codeEditorHtml, codeEditorCss, codeEditorJs].forEach(editor => {
            if (editor) {
                editor.addEventListener("input", () => {
                    if (editor === getEditorByFile(activeFileKey)) {
                        updateLineNumbers();
                        allFiles[activeFileKey] = editor.value;
                    }
                });
                editor.addEventListener("scroll", () => {
                    const lineNumbers = getLineNumbersByFile(activeFileKey);
                    if (lineNumbers) lineNumbers.scrollTop = editor.scrollTop;
                });
            }
        });

        // AI Chat
        if (aiChatSendBtn) {
            aiChatSendBtn.addEventListener("click", sendAiChat);
        }
        if (aiChatInput) {
            aiChatInput.addEventListener("keydown", (e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                    e.preventDefault();
                    sendAiChat();
                }
            });
        }

        // Listen for tab switching to populate editors when Code tab is opened
        document.querySelectorAll(".workspace-tab").forEach(tab => {
            tab.addEventListener("click", () => {
                const tabName = tab.getAttribute("data-tab");
                if (tabName === "code") {
                    // Refresh the code editors from current state
                    const state = window.__nexusCurrentState || {};
                    if (state && (state.html || state.css || state.javascript)) {
                        populateCodeEditors(extractGeneratedFiles(state));
                    }
                    currentFiles = {
                        "index.html": codeEditorHtml ? codeEditorHtml.value : "",
                        "style.css": codeEditorCss ? codeEditorCss.value : "",
                        "script.js": codeEditorJs ? codeEditorJs.value : ""
                    };
                    refreshCodePreview();
                }
            });
        });

        // Initialize file explorer
        refreshCodePreview();
    });

})();