/* =========================================================
   NEXUS FLOW - AI BUILDER v2
   Unified AI builder: single source of truth currentWebsiteState,
   single prompt box (generate -> modify), Monaco code editor,
   live preview with device switcher, save / download / restore.
   ========================================================= */
(function () {
    'use strict';

    var $ = function (sel, root) { return (root || document).querySelector(sel); };
    var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

    var DEFAULT_FILES = function () {
        return { 'index.html': '', 'styles.css': '', 'script.js': '' };
    };

    var DEFAULT_STATE = function () {
        return {
            website_name: 'My AI Website',
            prompt: '',
            website_type: 'auto',
            tech_stack: 'auto',
            html: '',
            css: '',
            javascript: '',
            files: DEFAULT_FILES(),
            images: [],
            sections: [],
            chat_history: [],
            design_spec: null,
            project_id: '',
            last_modified: null
        };
    };

    var API = {
        generate: '/api/builder/generate',
        modify: '/api/builder/modify',
        debug: '/api/builder/debug',
        project: function (id) { return '/api/builder/project/' + encodeURIComponent(id); },
        preview: function (id) { return '/api/builder/preview/' + encodeURIComponent(id); },
        stopPreview: function (id) { return '/api/builder/stop/' + encodeURIComponent(id); },
        stopGeneration: function (id) { return '/api/generation/stop/' + encodeURIComponent(id); },
        save: '/builder/save',
        versionCreate: '/builder/version/create',
        versions: function (id) { return '/builder/versions/' + encodeURIComponent(id); },
        versionRestore: function (id) { return '/builder/version/' + encodeURIComponent(id) + '/restore'; },
        qualityAnalyze: '/api/code-quality/analyze',
    };

    var FILE_ICONS = { html: 'fa-html5', css: 'fa-css3-alt', js: 'fa-square-js', json: 'fa-brackets-curly', md: 'fa-file-lines', default: 'fa-file' };

    /* ---------- DOM refs ---------- */
    var el = {
        shell: $('#nbShell'),
        landingView: $('#nbLandingView'),
        landingPrompt: $('#nbLandingPrompt'),
        landingGenerateBtn: $('#nbLandingGenerateBtn'),
        builderWorkspace: $('#nbBuilderWorkspace'),
        projectName: $('#nbProjectName'),
        saveBtn: $('#nbSaveBtn'),
        saveVersionBtn: $('#nbSaveVersionBtn'),
        versionsBtn: $('#nbVersionsBtn'),
        previewBtn: $('#nbPreviewBtn'),
        downloadBtn: $('#nbDownloadBtn'),
        deployBtn: $('#nbDeployBtn'),
        railBtns: $$('.nb-ws-tab'),
        chatPane: $('#nbWorkflowPane'),
        codePane: $('#nbCodePane'),
        qualityPane: $('#nbQualityPane'),
        chatHistory: $('#nbChatHistory'),
        prompt: $('#nbPrompt'),
        sendBtn: $('#nbSendBtn'),
        chips: $$('.nb-chip'),
        fileTree: $('#nbFileTree'),
        fileCount: $('#nbFileCount'),
        editorTabs: $('#nbEditorTabs'),
        activeFileName: $('#nbActiveFileName'),
        editToggleBtn: $('#nbEditToggleBtn'),
        saveCodeBtn: $('#nbSaveCodeBtn'),
        formatBtn: $('#nbFormatBtn'),
        renameFileBtn: $('#nbRenameFileBtn'),
        deleteFileBtn: $('#nbDeleteFileBtn'),
        addFileBtn: $('#nbAddFileBtn'),
        newFileModal: $('#nbNewFileModal'),
        newFileNameInput: $('#nbNewFileNameInput'),
        newFileTypeSelect: $('#nbNewFileTypeSelect'),
        newFileCreateBtn: $('#nbNewFileCreateBtn'),
        monaco: $('#nbMonaco'),
        fallbackEditor: $('#nbFallbackEditor'),
        fallbackTextarea: $('#nbFallbackTextarea'),
        statusLanguage: $('#nbStatusLanguage'),
        statusLn: $('#nbStatusLn'),
        unsavedBadge: $('#nbUnsavedBadge'),
        applyCodeBtn: $('#nbApplyCodeBtn'),
        copyCodeBtn: $('#nbCopyCodeBtn'),
        previewFrame: $('#nbPreviewFrame'),
        previewStage: $('#nbPreviewStage'),
        previewEmpty: $('#nbPreviewEmpty'),
        previewFrameWrap: null,
        refreshPreviewBtn: $('#nbRefreshPreviewBtn'),
        openPreviewBtn: $('#nbOpenPreviewBtn'),
        deviceBtns: $$('.nb-device-btn'),
        loadingOverlay: $('#nbLoadingOverlay'),
        loadingTitle: $('#nbLoadingTitle'),
        loadingSub: $('#nbLoadingSub'),
        toast: $('#nbToast'),
        toastMsg: $('#nbToastMsg'),
        versionsModal: $('#nbVersionsModal'),
        versionsList: $('#nbVersionsList'),
        restoreModal: $('#nbRestoreModal'),
        restoreConfirmBtn: $('#nbRestoreConfirmBtn'),
        newFileInput: $('#nbNewFileInput'),
        analyzeBtn: $('#nbAnalyzeBtn'),
        improveBtn: $('#nbImproveBtn'),
        qualityFocus: $('#nbQualityFocus'),
        qualityScore: $('#nbQualityScore'),
        qualityLevel: $('#nbQualityLevel'),
        qualityConf: $('#nbQualityConf'),
        qualityCompare: $('#nbQualityCompare'),
        qualitySections: $('#nbQualitySections'),
        qualityIssues: $('#nbQualityIssues'),
        qualityMeta: $('#nbQualityMeta'),
        aiStatus: $('#nbAiStatus'),
        modelBadge: $('#nbModelBadge'),
        currentModel: $('#nbCurrentModel'),
        designModal: null,
        designModalClose: null,
        designLoading: null,
        designLoadingTitle: null,
        designLoadingSub: null,
        designContent: null,
        designHero: null,
        designGrid: null,
        designFooter: null,
        designApproveBtn: null,
        designReviseBtn: null,
        designReviseModal: null,
        designReviseClose: null,
        designReviseInput: null,
        designReviseCancel: null,
        designReviseSubmit: null,
        previewDone: $('#nbPreviewDone'),
        previewError: $('#nbPreviewError'),
        previewGenerating: $('#nbPreviewGenerating'),
        previewGenTitle: $('#nbPreviewGenTitle'),
        previewGenSteps: $('#nbPreviewGenerating .nb-pgen-status-steps'),
        previewRetryBtn: $('#nbPreviewRetryBtn'),
        previewEditPromptBtn: $('#nbPreviewEditPromptBtn'),
    };

    el.previewFrameWrap = $('#nbPreviewFrameWrap');
    if (!el.previewFrameWrap) {
        el.previewFrameWrap = document.createElement('div');
        el.previewFrameWrap.className = 'nb-preview-frame-wrap';
        el.previewFrameWrap.setAttribute('data-device', 'desktop');
        el.previewStage.insertBefore(el.previewFrameWrap, el.previewFrame);
        el.previewFrameWrap.appendChild(el.previewFrame);
    }

    /* ---------- State ---------- */
    var isStarted = false;
    var currentWebsiteState = DEFAULT_STATE();
    var hasSite = false;
    var activeProjectId = '';

    /* Generation control state */
    var isGenerating = false;
    var _abortController = null;
    var _activeProjectIdForCancel = null;
    var _livePreviewActive = false;
    var currentGenerationId = null;
    var _genStepNames = ["Analyzing prompt...","Planning website architecture...","Generating components...","Generating code...","Creating files...","Installing dependencies...","Validating build...","Starting preview..."];

    /* File workspace state (VS Code style).
       `files` is a single array of file objects:
         { id, name, language, content }
       `activeFile` / `activeFileId` track the currently selected file.
       `openTabs` records which files currently have an editor tab open. */
    var files = [];
    var activeFile = 'index.html';
    var activeFileId = null;
    var openTabs = {};
    var nextFileId = 1;

    var dirtyFiles = {};
    var monaco = null;
    var monacoEditor = null;
    var monacoReady = false;
    var monacoLoadAttempted = false;
    var currentModel = null;
    var suppressDirty = false;
    var currentMode = 'workflow';

    /* Code quality analyzer state */
    var lastQuality = null;
    var qualityImproveActive = false;
    var lastQualityBeforeImprove = null;

    /* ---------- Helpers ---------- */
    function escHtml(str) {
        var d = document.createElement('div');
        d.textContent = str == null ? '' : String(str);
        return d.innerHTML;
    }

    function nowTime() {
        var d = new Date();
        var hh = d.getHours(), mm = d.getMinutes();
        return (hh < 10 ? '0' + hh : hh) + ':' + (mm < 10 ? '0' + mm : mm);
    }

    function toast(msg, isError) {
        el.toastMsg.textContent = msg;
        el.toast.classList.toggle('nb-toast-error', !!isError);
        el.toast.classList.add('show');
        clearTimeout(toast._t);
        toast._t = setTimeout(function () { el.toast.classList.remove('show'); }, 2600);
    }

    /* Turn raw network/LLM errors into friendly, demo-safe messages.
       Raw strings like "AI Service Unavailable" or "Failed to fetch" are
       never shown to the user - they get a clear, actionable equivalent. */
    function showLoading(title, sub) {
        el.loadingTitle.textContent = title || 'Working...';
        el.loadingSub.textContent = sub || '';
        el.loadingOverlay.style.display = 'flex';
    }

    function hideLoading() {
        el.loadingOverlay.style.display = 'none';
    }

    /* ---------- Generation cancellation helpers ---------- */
    function _generateId() {
        return 'gen_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 8);
    }
    function setGenerating(isGen, genId) {
        // Abort previous request if another generation starts
        if (isGen && _abortController) {
            try { _abortController.abort(); } catch(e) {}
        }
        isGenerating = isGen;
        currentGenerationId = isGen ? genId : null;
        if (isGen) _abortController = new AbortController();
        else _abortController = null;
        // Toggle Generate buttons
        if (el.sendBtn) el.sendBtn.disabled = isGen;
        if (el.landingGenerateBtn) el.landingGenerateBtn.disabled = isGen;
        // Toggle Stop buttons
        var stop1 = document.getElementById('nbStopGenerationBtn');
        var stop2 = document.getElementById('nbStopGenerationBtnPreview');
        if (stop1) stop1.style.display = isGen ? 'inline-flex' : 'none';
        if (stop2) stop2.style.display = isGen ? 'inline-flex' : 'none';
        if (isGen && genId) {
            // Show initial step
            updateGenStepUI(1);
        }
    }
    function updateGenStepUI(stepNum) {
        var total = 8;
        var label = _genStepNames[stepNum - 1] || ('Step ' + stepNum + '/' + total);
        var text = 'Step ' + stepNum + '/' + total + ': ' + label;
        var ls = document.getElementById('nbLoadingStep');
        var ps = document.getElementById('nbPreviewGenStep');
        if (ls) ls.textContent = text;
        if (ps) ps.textContent = text;
        // Also drive preview step UI
        if (typeof updatePreviewStep === 'function' && el.previewGenSteps) {
            // mark previous done, current active
            for (var i = 1; i <= 9; i++) {
                if (i < stepNum) updatePreviewStep(i, 'done');
                else if (i === stepNum) updatePreviewStep(i, 'active');
                else updatePreviewStep(i, 'pending');
            }
        }
    }
    function showCancelledUI() {
        hideLoading();
        hidePreviewGenerating();
        hideGenStatus();
        // show preview error as cancelled, but also toast
        var cancelMsg = 'Generation cancelled';
        // Update loading title if still visible briefly
        if (el.loadingTitle) el.loadingTitle.textContent = cancelMsg;
        if (el.loadingSub) el.loadingSub.textContent = 'You stopped the generation.';
        var ls = document.getElementById('nbLoadingStep');
        if (ls) ls.textContent = cancelMsg;
        var ps = document.getElementById('nbPreviewGenStep');
        if (ps) ps.textContent = cancelMsg;
        // Re-enable buttons
        setGenerating(false, null);
        toast(cancelMsg);
        // Also show in preview pane as cancelled, not error
        var errEl = document.getElementById('nbPreviewError');
        var msgEl = document.getElementById('nbPreviewErrMsg');
        if (errEl && msgEl) {
            msgEl.textContent = cancelMsg;
            errEl.style.display = 'flex';
            // hide retry, keep edit prompt
        }
        // Ensure preview empty is hidden
        if (el.previewFrame) el.previewFrame.style.display = 'none';
    }
    function handleStopGeneration() {
        if (!isGenerating || !currentGenerationId) return;
        var genId = currentGenerationId;
        // Abort fetch immediately
        if (_abortController) {
            try { _abortController.abort(); } catch(e) {}
        }
        // Tell backend to cancel remaining stages
        fetch(API.stopGeneration(genId), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        }).catch(function(){ /* ignore network error */ });
        // Immediately update UI
        showCancelledUI();
        // Also abort preview polling
        clearInterval(_genStepTimer);
    }

    function _fmtSec(s) {
        if (!s || s <= 0) return '0s';
        if (s < 60) return s.toFixed(1) + 's';
        var m = Math.floor(s / 60);
        var rem = s - m * 60;
        return m + 'm ' + rem.toFixed(1) + 's';
    }

    function setProjectId(id) {
        activeProjectId = id || '';
        currentWebsiteState.project_id = id || '';
    }

    /* ---------- Preview generating state ---------- */
    var _genStepTimer = null;

    /* No-op stubs for removed functions still referenced elsewhere */
    function hidePreviewGenerating() { clearInterval(_genStepTimer); if (el.previewGenerating) el.previewGenerating.style.display = 'none'; }
    function hidePreviewDone() { var e = document.getElementById('nbPreviewDone'); if (e) e.style.display = 'none'; }
    function updateSendButton() {}
    function removeAIThinking() { var t = document.getElementById('nbThinking'); if (t) t.remove(); }
    function openFigmaModal() {}
    function analyzeFigmaDesign() {}
    function generateFromFigma() {}
    function approveDesign() {}
    function runAutonomousDevWorkflow() {}
    function openProviderModal() {
        var modal = document.getElementById('nbProviderModal');
        if (!modal) {
            console.warn('[Nexus] Provider modal not found in DOM');
            return;
        }
        modal.style.display = 'flex';
        loadProviderSettings();
    }

    function closeProviderModal() {
        var modal = document.getElementById('nbProviderModal');
        if (modal) modal.style.display = 'none';
    }

    function loadProviderSettings() {
        // Fetch providers from backend
        fetch('/api/builder/providers')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (!data.success) {
                    console.warn('[Nexus] Failed to load providers:', data.error);
                    return;
                }
                renderProviderList(data.providers);
                updateCurrentProvider(data.active_provider, data.active_model);
            })
            .catch(function(err) {
                console.error('[Nexus] Failed to load provider settings:', err);
            });
    }

    function renderProviderList(providers) {
        var select = document.getElementById('nbProviderSelect');
        if (!select) return;
        
        // Clear and populate
        select.innerHTML = '<option value="">Select a provider...</option>';
        
        providers.forEach(function(prov) {
            var opt = document.createElement('option');
            opt.value = prov.provider;
            opt.textContent = prov.provider.charAt(0).toUpperCase() + prov.provider.slice(1);
            if (!prov.has_key) opt.textContent += ' (no key)';
            if (!prov.enabled) opt.textContent += ' (disabled)';
            select.appendChild(opt);
        });
        
        // Restore saved selection if any
        var savedProvider = localStorage.getItem('nb_selected_provider');
        if (savedProvider) {
            select.value = savedProvider;
            onProviderChange({ target: select });
        }
    }

    function onProviderChange(e) {
        var provider = e.target.value;
        var modelSelect = document.getElementById('nbModelSelect');
        var apiKeyField = document.getElementById('nbApiKeyField');
        var apiKeyInput = document.getElementById('nbApiKeyInput');
        var apiKeyHint = document.getElementById('nbApiKeyHint');
        
        if (!modelSelect) return;
        
        // Clear model dropdown
        modelSelect.innerHTML = '<option value="">Select a model...</option>';
        
        // Fetch models for this provider
        if (provider) {
            fetch('/api/builder/providers')
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (!data.success) return;
                    var prov = data.providers.find(function(p) { return p.provider === provider; });
                    if (prov && prov.models) {
                        prov.models.forEach(function(m) {
                            var opt = document.createElement('option');
                            opt.value = m.id;
                            opt.textContent = m.name + (m.is_active ? ' (active)' : '');
                            if (m.is_active) opt.selected = true;
                            modelSelect.appendChild(opt);
                        });
                    }
                })
                .catch(function(err) {
                    console.error('[Nexus] Failed to load models:', err);
                });
        }
        
        // Toggle API key field visibility
        if (provider && provider !== 'emergent') {
            if (apiKeyField) apiKeyField.style.display = 'block';
            if (apiKeyHint) apiKeyHint.textContent = 'Required for this provider.';
        } else {
            if (apiKeyField) apiKeyField.style.display = 'none';
        }
        
        // Load saved API key
        if (provider) {
            var savedKey = localStorage.getItem('nb_api_key_' + provider);
            if (apiKeyInput && savedKey) {
                apiKeyInput.value = savedKey;
            }
        }
    }

    function saveProviderSettings() {
        var providerEl = document.getElementById('nbProviderSelect');
        var modelEl = document.getElementById('nbModelSelect');
        var provider = providerEl ? providerEl.value : '';
        var model = modelEl ? modelEl.value : '';
        
        if (!provider) {
            toast('Please select a provider', true);
            return;
        }
        if (provider === 'emergent') {
            // No API key needed for Emergent
            saveProvider(provider, null, model);
            return;
        }
        
        var apiKeyInput = document.getElementById('nbApiKeyInput');
        var apiKey = apiKeyInput ? apiKeyInput.value.trim() : '';
        if (!apiKey) {
            toast('API key is required for ' + provider, true);
            return;
        }
        
        saveProvider(provider, apiKey, model);
    }

    function saveProvider(provider, apiKey, model) {
        var saveApiKey = function(cb) {
            if (provider === 'emergent' || !apiKey) {
                cb(true);
                return;
            }
            fetch('/api/builder/provider/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider: provider, api_key: apiKey })
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.success) {
                    if (apiKey) try { localStorage.setItem('nb_api_key_' + provider, apiKey); } catch(e) {}
                    cb(true);
                } else {
                    toast('Failed to save API key: ' + (data.error || 'Unknown error'), true);
                    cb(false);
                }
            })
            .catch(function(err) {
                console.error('[Nexus] Save provider failed:', err);
                toast('Failed to save provider', true);
                cb(false);
            });
        };
        
        saveApiKey(function(apiOk) {
            if (!apiOk) return;
            // Now select provider/model
            var payload = { provider: provider, model: model || '' };
            // If no model selected, get first model for provider
            if (!payload.model) {
                var modelSelect = document.getElementById('nbModelSelect');
                if (modelSelect && modelSelect.options.length > 1) {
                    payload.model = modelSelect.options[1].value;
                }
            }
            if (!payload.model) {
                toast('Please select a model', true);
                return;
            }
            fetch('/api/builder/provider/select', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.success) {
                    toast('Provider saved: ' + provider + '/' + payload.model);
                    localStorage.setItem('nb_selected_provider', provider);
                    localStorage.setItem('nb_selected_model', payload.model);
                    closeProviderModal();
                    // Update UI badge
                    var badge = document.getElementById('nbProviderCurrent');
                    var modelBadge = document.getElementById('nbCurrentModel');
                    if (badge) badge.innerHTML = '<i class="fa-solid fa-circle-check"></i> ' + provider.charAt(0).toUpperCase() + provider.slice(1);
                    if (modelBadge) modelBadge.textContent = payload.model;
                } else {
                    toast('Failed to select model: ' + (data.error || 'Unknown error'), true);
                }
            })
            .catch(function(err) {
                console.error('[Nexus] Select provider failed:', err);
                toast('Failed to select provider', true);
            });
        });
    }

    function testConnection() {
        var provider = document.getElementById('nbProviderSelect').value;
        var model = document.getElementById('nbModelSelect').value;
        var resultEl = document.getElementById('nbTestResult');
        
        if (!provider) {
            toast('Please select a provider first', true);
            return;
        }
        
        var btn = document.getElementById('nbTestConnBtn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Testing...</span>';
        }
        
        fetch('/api/builder/provider/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider: provider, model: model || '' })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                if (resultEl) {
                    resultEl.className = 'nb-test-result success';
                    resultEl.textContent = data.message || 'Connected';
                    resultEl.style.display = 'block';
                }
                toast('Connection successful (' + (data.latency_ms || 0) + 'ms)');
            } else {
                if (resultEl) {
                    resultEl.className = 'nb-test-result error';
                    resultEl.textContent = data.error || 'Connection failed';
                    resultEl.style.display = 'block';
                }
                toast('Connection failed: ' + (data.error || 'Unknown error'), true);
            }
        })
        .catch(function(err) {
            console.error('[Nexus] Test connection failed:', err);
            if (resultEl) {
                resultEl.className = 'nb-test-result error';
                resultEl.textContent = 'Network error: ' + err.message;
                resultEl.style.display = 'block';
            }
            toast('Test failed: ' + err.message, true);
        })
        .finally(function() {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-plug"></i><span>Test Connection</span>';
            }
        });
    }
    // testConnection is implemented above
    // saveProviderSettings implemented via saveProvider
    // loadProviderSettings implemented above
    // onProviderChange implemented as onProviderChange handler
    function onApiKeyInput(e) {
        var input = e.target;
        var provider = document.getElementById('nbProviderSelect');
        provider = provider ? provider.value : '';
        if (provider && input.value.trim()) {
            try { localStorage.setItem('nb_api_key_' + provider, input.value.trim()); } catch(err) {}
        }
        // Toggle save button state based on input
        var saveBtn = document.getElementById('nbSaveProviderBtn');
        if (saveBtn) {
            var hasProvider = !!provider;
            var needsKey = provider && provider !== 'emergent';
            var hasKey = !needsKey || (input.value && input.value.trim().length > 0);
            saveBtn.disabled = !(hasProvider && hasKey);
        }
    }
    function startAiHealthPolling() {}

    function showPreviewError(msg) {
        hidePreviewGenerating();
        hidePreviewDone();
        var el2 = document.getElementById('nbPreviewError');
        var msgEl = document.getElementById('nbPreviewErrMsg');
        var text = msg || 'Preview generation failed';
        if (!text.toLowerCase().startsWith('preview generation failed') && !text.toLowerCase().startsWith('error:')) {
            text = 'Preview generation failed: ' + text;
        }
        if (msgEl) msgEl.textContent = text;
        if (el2) el2.style.display = 'flex';
        if (el.previewFrame) el.previewFrame.style.display = 'none';
        if (el.previewEmpty) el.previewEmpty.classList.add('hidden');
        // Sync error to shared preview store
        if (window.NexusPreviewStore) {
            window.NexusPreviewStore.setError(text);
        }
    }

    function hidePreviewError() {
        var el2 = document.getElementById('nbPreviewError');
        if (el2) el2.style.display = 'none';
    }

    function switchToBuilder(initialMessage) {
        if (isStarted) return;
        isStarted = true;
        el.landingView.style.display = 'none';
        el.builderWorkspace.style.display = 'flex';
        if (initialMessage) {
            el.prompt.value = initialMessage;
        }
        el.prompt.focus();
        syncFilesFromState();
        renderFileTree();
        renderTabs();
        initMonaco();
    }

    function fileNameLang(name) {
        var ext = (name || '').split('.').pop().toLowerCase();
        var map = { html: 'html', htm: 'html', css: 'css', js: 'javascript', mjs: 'javascript', json: 'json', md: 'markdown', txt: 'plaintext' };
        return map[ext] || 'plaintext';
    }

    function fileIcon(name) {
        var ext = (name || '').split('.').pop().toLowerCase();
        return FILE_ICONS[ext] || FILE_ICONS.default;
    }

    function nextId() {
        var id = nextFileId;
        while (files.some(function (f) { return f.id === id; })) { id++; }
        nextFileId = id + 1;
        return id;
    }

    function getFile(name) {
        for (var i = 0; i < files.length; i++) {
            if (files[i].name === name) return files[i];
        }
        return null;
    }

    function syncStateFromFiles() {
        // Reflect the files array into the server-facing state object.
        currentWebsiteState.files = {};
        files.forEach(function (f) {
            currentWebsiteState.files[f.name] = f.content || '';
        });
        currentWebsiteState.html = currentWebsiteState.files['index.html'] || '';
        currentWebsiteState.css = currentWebsiteState.files['styles.css'] || '';
        currentWebsiteState.javascript = currentWebsiteState.files['script.js'] || '';
        // Sync to shared preview store
        if (window.NexusPreviewStore) {
            window.NexusPreviewStore.setContent(currentWebsiteState.files);
            window.NexusPreviewStore.setProjectName(currentWebsiteState.website_name);
            window.NexusPreviewStore.setProjectId(activeProjectId);
        }
    }

    function syncFilesFromState() {
        // Rebuild the files array from currentWebsiteState.files, preserving
        // ids / open tabs for files that still exist.
        var existing = {};
        files.forEach(function (f) { existing[f.name] = f; });
        var next = [];
        var activeExists = false;
        Object.keys(currentWebsiteState.files || {}).forEach(function (name) {
            var ex = existing[name];
            next.push({
                id: ex ? ex.id : nextId(),
                name: name,
                language: ex ? ex.language : fileNameLang(name),
                content: currentWebsiteState.files[name]
            });
            if (name === activeFile) activeExists = true;
        });
        files = next;
        if (!activeExists) {
            var names = fileList();
            activeFile = names.length ? names[0] : 'index.html';
        }
        activeFileId = getFile(activeFile) ? getFile(activeFile).id : null;
        if (!openTabs[activeFile]) {
            openTabs = {};
            openTabs[activeFile] = true;
        }
    }

    function syncEditorsFromFiles(newFiles) {
        // Replace currentWebsiteState.files, rebuild the files array,
        // and push content into Monaco models so the editors update live.
        currentWebsiteState.files = newFiles || {};
        syncFilesFromState();

        // Push content to Monaco models
        if (monaco && monacoReady) {
            files.forEach(function (f) {
                if (models[f.name]) {
                    var val = models[f.name].getValue();
                    if (val !== f.content) {
                        models[f.name].setValue(f.content || '');
                    }
                } else {
                    _createMonacoModel(f.name, f.content || '');
                }
            });
        }

        renderFileTree();
        renderTabs();
        openFile(activeFile);
    }

    function _createMonacoModel(name, content) {
        if (!monaco) return null;
        var lang = fileNameLang(name);
        var uri = monaco.Uri.parse('file:///' + encodeURIComponent(name));
        var existing = monaco.editor.getModel(uri);
        if (existing) {
            existing.setValue(content || '');
            return existing;
        }
        var model = monaco.editor.createModel(content || '', lang, uri);
        models[name] = model;
        return model;
    }

    function syncStateFromEditors() {
        files.forEach(function (f) {
            if (monaco && monacoReady && models[f.name]) {
                f.content = models[f.name].getValue();
            } else if (f.name === activeFile && !monacoReady && el.fallbackEditor.style.display !== 'none') {
                f.content = el.fallbackTextarea.value;
            }
        });
        syncStateFromFiles();
    }

    function readFileContent(name) {
        var f = getFile(name);
        if (!f) return '';
        if (monaco && monacoReady && models[name]) {
            return models[name].getValue();
        }
        if (name === activeFile && !monacoReady && el.fallbackEditor.style.display !== 'none') {
            return el.fallbackTextarea.value;
        }
        return f.content;
    }

    function updateStatusLanguage() {
        if (!el.statusLanguage) return;
        el.statusLanguage.innerHTML = '<i class="fa-solid fa-code"></i> ' + escHtml(fileNameLang(activeFile).toUpperCase());
    }

    function markDirty(name) {
        if (suppressDirty) return;
        dirtyFiles[name] = true;
        renderFileTree();
        renderTabs();
        el.unsavedBadge.style.display = 'inline-flex';
    }

    function markClean(name) {
        delete dirtyFiles[name];
        renderFileTree();
        renderTabs();
        var any = Object.keys(dirtyFiles).length > 0;
        el.unsavedBadge.style.display = any ? 'inline-flex' : 'none';
    }

    function normalizeFiles(files, html, css, js) {
        var f = {};
        (Object.keys(files || {})).forEach(function (k) {
            if (typeof files[k] === 'string') f[k] = files[k];
        });
        if (typeof html === 'string') f['index.html'] = html;
        if (typeof css === 'string') f['styles.css'] = css;
        if (typeof js === 'string') f['script.js'] = js;
        if (!('index.html' in f)) f['index.html'] = '';
        if (!('styles.css' in f)) f['styles.css'] = '';
        if (!('script.js' in f)) f['script.js'] = '';
        return f;
    }

    /* ---------- Preview ---------- */
    // Guard injected into the preview document so relative links / form
    // submissions never navigate the iframe to a non-existent route (404).
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

    var _currentPreviewBlobUrl = null;

    function buildPreviewDocument() {
        // Collect all files from memory / models
        var fileMap = {};
        if (files && files.length) {
            files.forEach(function (f) {
                fileMap[f.name] = readFileContent(f.name) || f.content || '';
            });
        }
        if (currentWebsiteState.files) {
            Object.keys(currentWebsiteState.files).forEach(function (name) {
                if (!(name in fileMap) || !fileMap[name]) {
                    fileMap[name] = currentWebsiteState.files[name] || '';
                }
            });
        }

        // 1. Determine base HTML content
        var rawHtml = fileMap['index.html'] || fileMap['index.htm'] || currentWebsiteState.html || '';

        // 2. Aggregate all CSS styles
        var cssPieces = [];
        if (currentWebsiteState.css && currentWebsiteState.css.trim()) {
            cssPieces.push(currentWebsiteState.css.trim());
        }
        Object.keys(fileMap).forEach(function (name) {
            if (name.endsWith('.css')) {
                var content = (fileMap[name] || '').trim();
                if (content && cssPieces.indexOf(content) === -1) {
                    cssPieces.push(content);
                }
            }
        });
        var combinedCss = cssPieces.join('\n\n');

        // 3. Check for React / JSX files
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

        if (!isReactProject && currentWebsiteState.javascript) {
            if (/\b(?:import\s+React|React\.useState|React\.useEffect|ReactDOM|from\s+['"]react['"]|className=|<[A-Z][A-Za-z0-9]*[\s/>])/i.test(currentWebsiteState.javascript)) {
                isReactProject = true;
                reactFiles.push({ name: 'script.js', content: currentWebsiteState.javascript });
            }
        }

        if (!rawHtml && isReactProject) {
            rawHtml = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>' + escHtml(currentWebsiteState.website_name || 'React App') + '</title></head><body><div id="root"></div></body></html>';
        }

        // 4. Assemble complete HTML document
        return prepareHtmlDocument(rawHtml, combinedCss, jsFiles, reactFiles, isReactProject);
    }

    function prepareHtmlDocument(rawHtml, combinedCss, jsFiles, reactFiles, isReactProject) {
        var html = (rawHtml || '').trim();
        if (!html) {
            html = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head><body><div id="root"></div></body></html>';
        }

        // Strip relative stylesheet links (assets are inlined below) while preserving external CDN links
        html = html.replace(/<link\b[^>]*\bhref=["']([^"']+)["'][^>]*>/gi, function (all, href) {
            var h = href.trim();
            if (/^(?:https?:|\/\/|data:)/i.test(h)) return all;
            return '';
        });

        // Strip relative script tags (assets are inlined below) while preserving external CDN scripts
        html = html.replace(/<script\b[^>]*\bsrc=["']([^"']+)["'][^>]*>\s*<\/script>/gi, function (all, src) {
            var s = src.trim();
            if (/^(?:https?:|\/\/|data:)/i.test(s)) return all;
            return '';
        });

        // Replace relative media srcs (img, video, audio, source, iframe) with transparent SVG placeholder to avoid 404s
        var ph = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><rect width="100" height="100" fill="#1e293b"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#64748b" font-family="sans-serif" font-size="12">Image</text></svg>');
        html = html.replace(/(<(?:img|source|video|audio|iframe)\b[^>]*\bsrc=["'])([^"']+)(["'][^>]*>)/gi, function (all, pre, src, post) {
            var s = src.trim();
            if (/^(?:https?:|\/\/|data:|blob:|#)/i.test(s)) return all;
            return pre + ph + post;
        });

        // Build Head elements
        var headInjections = [];
        headInjections.push('<script>\n' + PREVIEW_GUARD_JS + '\n</' + 'script>');

        // If React project, inject React 18, ReactDOM, and Babel Standalone (local vendor to avoid CDN tracking prevention)
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

        // Fonts and Icons (local vendor to avoid CDN tracking prevention)
        if (!html.includes('font-awesome') && !html.includes('/static/vendor/fontawesome')) {
            headInjections.push('<link rel="stylesheet" href="/static/vendor/fontawesome/css/all.min.css">');
        }
        if (!html.includes('/static/vendor/fonts/fonts.css') && !html.includes('fonts.googleapis.com')) {
            headInjections.push('<link rel="stylesheet" href="/static/vendor/fonts/fonts.css">');
        }

        // Combined CSS
        if (combinedCss && combinedCss.trim()) {
            headInjections.push('<style id="nexus-injected-styles">\n' + combinedCss + '\n</style>');
        }

        var headContent = headInjections.join('\n');

        // Build Body / Script elements
        var bodyInjections = [];

        // Standard JS files
        var standardJs = [];
        if (currentWebsiteState.javascript && !isReactProject) {
            standardJs.push(currentWebsiteState.javascript);
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

        // React code transpilation via Babel
        if (isReactProject && reactFiles.length > 0) {
            var reactCode = reactFiles.map(function (rf) {
                var code = rf.content || '';
                // Transform ES module imports/exports for in-browser standalone execution
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

        // Assemble into the HTML document
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

    function renderPreview() {
        try {
            syncStateFromEditors();

            var hasAnyContent = Boolean(
                (currentWebsiteState.html && currentWebsiteState.html.trim()) ||
                (currentWebsiteState.css && currentWebsiteState.css.trim()) ||
                (currentWebsiteState.javascript && currentWebsiteState.javascript.trim()) ||
                (files && files.some(function (f) { return f.content && f.content.trim(); })) ||
                (currentWebsiteState.files && Object.keys(currentWebsiteState.files).some(function (k) { return currentWebsiteState.files[k] && currentWebsiteState.files[k].trim(); }))
            );

            if (!hasSite && !hasAnyContent) {
                if (el.previewEmpty) el.previewEmpty.classList.remove('hidden');
                if (el.previewFrame) el.previewFrame.style.display = 'none';
                hidePreviewGenerating();
                hidePreviewDone();
                hidePreviewError();
                return;
            }

            if (el.previewEmpty) el.previewEmpty.classList.add('hidden');
            hidePreviewGenerating();
            hidePreviewDone();
            hidePreviewError();

            var docHtml = buildPreviewDocument();
            if (!docHtml || !docHtml.trim()) {
                throw new Error('Generated preview document is empty');
            }

            // Create Blob URL for reliable standalone rendering
            var blob = new Blob([docHtml], { type: 'text/html;charset=utf-8' });
            var blobUrl = URL.createObjectURL(blob);

            if (_currentPreviewBlobUrl) {
                try { URL.revokeObjectURL(_currentPreviewBlobUrl); } catch (e) {}
            }
            _currentPreviewBlobUrl = blobUrl;

            if (el.previewFrame) {
                el.previewFrame.style.display = 'block';
                el.previewFrame.src = blobUrl;
            }

            // Sync to shared preview store
            if (window.NexusPreviewStore) {
                window.NexusPreviewStore.setContent(currentWebsiteState.files);
                window.NexusPreviewStore.setProjectName(currentWebsiteState.website_name);
                window.NexusPreviewStore.setProjectId(activeProjectId);
                window.NexusPreviewStore.clearError();
            }
        } catch (err) {
            console.error('[Nexus Preview] renderPreview failed:', err);
            var errMsg = err && err.message ? err.message : String(err);
            showPreviewError('Preview generation failed: ' + errMsg);
            if (el.previewFrame) {
                el.previewFrame.style.display = 'none';
            }
        }
    }

    // Expose renderPreview globally
    window.renderPreview = renderPreview;

    function updatePreviewIncremental(onlyCss) {
        syncStateFromEditors();
        if (!hasSite || !el.previewFrame || !el.previewFrame.contentDocument) {
            renderPreview();
            return;
        }
        try {
            var doc = el.previewFrame.contentDocument;
            if (onlyCss) {
                var styleTag = doc.querySelector('#nexus-injected-styles') || doc.querySelector('style');
                if (styleTag) {
                    styleTag.textContent = currentWebsiteState.css || '';
                    return;
                }
            }
            renderPreview();
        } catch (e) {
            renderPreview();
        }
    }

    function refreshPreview() {
        try {
            renderPreview();
            toast('Preview refreshed');
        } catch (err) {
            showPreviewError('Preview generation failed: ' + (err.message || err));
        }
    }

    /* ── Figma Import ──────────────────────────────────────── */
    var _figmaBlueprint = null;

    function closeFigmaModal() {
        var modal = $('#nbFigmaModal');
        if (modal) modal.style.display = 'none';
        _figmaBlueprint = null;
    }

    /* Expose Figma functions for onclick handlers */
    window.openFigmaModal = openFigmaModal;
    window.closeFigmaModal = closeFigmaModal;
    window.analyzeFigmaDesign = analyzeFigmaDesign;
    window.generateFromFigma = generateFromFigma;

    function openPreviewTab() {
        try {
            syncStateFromEditors();
            var hasAnyContent = Boolean(
                (currentWebsiteState.html && currentWebsiteState.html.trim()) ||
                (currentWebsiteState.css && currentWebsiteState.css.trim()) ||
                (currentWebsiteState.javascript && currentWebsiteState.javascript.trim()) ||
                (files && files.some(function (f) { return f.content && f.content.trim(); }))
            );
            if (!hasSite && !hasAnyContent) { toast('Generate a website first', true); return; }
            var doc = buildPreviewDocument();
            var blob = new Blob([doc], { type: 'text/html;charset=utf-8' });
            var url = URL.createObjectURL(blob);
            var win = window.open(url, '_blank');
            if (!win) { toast('Popup blocked - allow popups to preview', true); URL.revokeObjectURL(url); return; }
            setTimeout(function () { URL.revokeObjectURL(url); }, 60000);
        } catch (err) {
            toast('Failed to open preview: ' + (err.message || err), true);
        }
    }

    function setDevice(device) {
        el.deviceBtns.forEach(function (b) {
            b.classList.toggle('active', b.getAttribute('data-device') === device);
        });
        el.previewFrameWrap.setAttribute('data-device', device);
    }

    /* ---------- Chat ---------- */
    function addBubble(text, role) {
        var wrap = document.createElement('div');
        wrap.className = 'nb-bubble ' + (role === 'user' ? 'nb-bubble-user' : '');
        wrap.innerHTML =
            '<div class="nb-bubble-avatar"><i class="fa-solid ' + (role === 'user' ? 'fa-user' : 'fa-wand-magic-sparkles') + '"></i></div>' +
            '<div class="nb-bubble-body">' +
            '<div class="nb-bubble-name">' + (role === 'user' ? 'You' : 'Nexus AI') + '</div>' +
            '<p>' + escHtml(text) + '</p>' +
            '<div class="nb-bubble-time">' + nowTime() + '</div>' +
            '</div>';
        el.chatHistory.appendChild(wrap);
        el.chatHistory.scrollTop = el.chatHistory.scrollHeight;
    }

    function renderChatHistory() {
        el.chatHistory.innerHTML = '';
        var history = currentWebsiteState.chat_history || [];
        if (history.length === 0) {
            addBubble("Hi! I'm your AI website builder. Describe the website you want to build and I'll generate it for you. After that, you can keep chatting to add sections, change colors, or adjust anything.", 'assistant');
            return;
        }
        history.forEach(function (item) {
            if (item && item.message) addBubble(item.message, item.role === 'user' ? 'user' : 'assistant');
        });
    }

    function setProjectName(name) {
        if (name) el.projectName.value = name;
    }

    /* ---------- File tree & editor tabs ---------- */
    function fileList() {
        return files.map(function (f) { return f.name; }).sort(function (a, b) {
            var score = { 'index.html': 0, 'styles.css': 1, 'script.js': 2 };
            var sa = score[a] !== undefined ? score[a] : 10;
            var sb = score[b] !== undefined ? score[b] : 10;
            if (sa !== sb) return sa - sb;
            return a.localeCompare(b);
        });
    }

    function openedFileList() {
        return fileList().filter(function (name) { return openTabs[name]; });
    }

    function renderFileTree() {
        var names = fileList();
        el.fileTree.innerHTML = '';
        names.forEach(function (name) {
            var item = document.createElement('div');
            item.className = 'nb-file-item' + (name === activeFile ? ' active' : '');
            var dirty = dirtyFiles[name] ? '<span class="nb-file-dirty" title="Unsaved changes"><i class="fa-solid fa-circle"></i></span>' : '';
            item.innerHTML =
                '<i class="fa-solid ' + fileIcon(name) + ' nb-file-icon"></i>' +
                '<span class="nb-file-name">' + escHtml(name) + '</span>' + dirty;
            item.addEventListener('click', function () { openFile(name); });
            el.fileTree.appendChild(item);
        });
        el.fileCount.textContent = names.length + ' file' + (names.length === 1 ? '' : 's');
    }

    function renderTabs() {
        var names = openedFileList();
        el.editorTabs.innerHTML = '';
        names.forEach(function (name) {
            var tab = document.createElement('button');
            tab.className = 'nb-editor-tab' + (name === activeFile ? ' active' : '');
            var dirty = dirtyFiles[name] ? ' *' : '';
            tab.innerHTML = '<i class="fa-solid ' + fileIcon(name) + '"></i><span>' + escHtml(name) + dirty + '</span>' +
                '<span class="nb-tab-close" title="Close tab"><i class="fa-solid fa-xmark"></i></span>';
            tab.addEventListener('click', function (e) {
                if (e.target.closest('.nb-tab-close')) { closeTab(name); return; }
                openFile(name);
            });
            el.editorTabs.appendChild(tab);
        });
        el.activeFileName.textContent = activeFile;
    }

    function openFile(name) {
        var f = getFile(name);
        if (!f) return;
        // Preserve edits in the currently shown editor before switching.
        syncStateFromEditors();
        activeFile = name;
        activeFileId = f.id;
        openTabs[name] = true;
        if (monaco && monacoReady) {
            if (models[name]) {
                currentModel = models[name];
                if (monacoEditor) monacoEditor.setModel(currentModel);
            }
            updateStatusLanguage();
        } else {
            el.fallbackTextarea.value = f.content || '';
            updateStatusLanguage();
        }
        renderFileTree();
        renderTabs();
    }

    function closeTab(name) {
        if (!openTabs[name]) return;
        delete openTabs[name];
        if (activeFile === name) {
            var opened = openedFileList();
            if (opened.length) {
                openFile(opened[opened.length - 1]);
            } else {
                var all = fileList();
                openFile(all[all.length - 1] || 'index.html');
            }
        } else {
            renderTabs();
        }
    }

    function deleteFile(name) {
        if (name === 'index.html' || name === 'styles.css' || name === 'script.js') {
            toast('Core files cannot be deleted', true);
            return;
        }
        var f = getFile(name);
        if (!f) return;
        if (dirtyFiles[name] && !window.confirm('Discard unsaved changes to ' + name + '?')) return;
        if (!window.confirm('Delete ' + name + '? This cannot be undone.')) return;

        files = files.filter(function (x) { return x.name !== name; });
        delete currentWebsiteState.files[name];
        delete openTabs[name];
        delete dirtyFiles[name];
        if (monaco && monacoReady && models[name]) { models[name].dispose(); delete models[name]; }
        syncStateFromFiles();

        if (activeFile === name) {
            var opened = openedFileList();
            if (opened.length) {
                openFile(opened[opened.length - 1]);
            } else {
                var all = fileList();
                openFile(all.length ? all[all.length - 1] : 'index.html');
            }
        } else {
            renderFileTree();
            renderTabs();
        }
        toast('Deleted ' + name);
    }

    function renameFile(name, newName) {
        if (!newName || newName === name) return;
        if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(newName)) {
            toast('File name can only contain letters, numbers, dots, dashes and underscores', true);
            return;
        }
        var f = getFile(name);
        if (!f) return;
        if (getFile(newName)) {
            toast('A file named ' + newName + ' already exists', true);
            return;
        }
        var content = readFileContent(name);
        f.name = newName;
        f.language = fileNameLang(newName);
        delete currentWebsiteState.files[name];
        currentWebsiteState.files[newName] = content;
        delete dirtyFiles[name];
        if (monaco && monacoReady) {
            if (models[name]) { models[name].dispose(); delete models[name]; }
            models[newName] = monaco.editor.createModel(content, f.language, monaco.Uri.parse('file:///' + newName));
            models[newName].onDidChangeContent(function () { markDirty(newName); });
        }
        if (openTabs[name]) { delete openTabs[name]; openTabs[newName] = true; }
        if (activeFile === name) {
            activeFile = newName;
            activeFileId = f.id;
            currentModel = models[newName] || null;
            if (monacoEditor && currentModel) monacoEditor.setModel(currentModel);
            if (!monacoReady) el.fallbackTextarea.value = content;
            updateStatusLanguage();
        }
        renderFileTree();
        renderTabs();
        toast('Renamed to ' + newName);
    }

    /* ---------- New file dialog ---------- */
    function openNewFileDialog() {
        el.newFileNameInput.value = '';
        el.newFileTypeSelect.value = 'html';
        el.newFileModal.style.display = 'flex';
        setTimeout(function () { el.newFileNameInput.focus(); }, 50);
    }

    function hideNewFileModal() {
        el.newFileModal.style.display = 'none';
    }

    function createFile() {
        var name = el.newFileNameInput.value.trim();
        var type = el.newFileTypeSelect.value || 'html';
        if (!name) { toast('Enter a file name', true); return; }
        if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(name)) {
            toast('File name can only contain letters, numbers, dots, dashes and underscores', true);
            return;
        }
        if (name.indexOf('.') === -1) {
            var ext = { html: 'html', css: 'css', javascript: 'js', json: 'json', markdown: 'md', plaintext: 'txt' }[type] || 'html';
            name += '.' + ext;
        }
        if (getFile(name)) {
            toast('A file named ' + name + ' already exists', true);
            return;
        }
        var newFile = { id: nextId(), name: name, language: fileNameLang(name), content: '' };
        files.push(newFile);
        currentWebsiteState.files[name] = '';
        if (monaco && monacoReady) {
            models[name] = monaco.editor.createModel('', newFile.language, monaco.Uri.parse('file:///' + name));
            models[name].onDidChangeContent(function () { markDirty(name); });
        }
        hideNewFileModal();
        openFile(name);
        toast('Created ' + name);
    }

    /* ---------- State application & Monaco ---------- */
    var models = {};

    function applyStateToUI(state) {
        var base = DEFAULT_STATE();
        var keys = Object.keys(state || {});
        keys.forEach(function (k) { base[k] = state[k]; });
        currentWebsiteState = base;
        activeProjectId = currentWebsiteState.project_id || '';
        hasSite = !!(currentWebsiteState.html || currentWebsiteState.javascript || currentWebsiteState.css);
        currentWebsiteState.files = normalizeFiles(
            currentWebsiteState.files,
            currentWebsiteState.html,
            currentWebsiteState.css,
            currentWebsiteState.javascript
        );
        dirtyFiles = {};
        setProjectName(currentWebsiteState.website_name || 'My AI Website');
        syncFilesFromState();
        rebuildModels();
        renderChatHistory();
        renderPreview();
        updateSendButton();
        renderFileTree();
        renderTabs();
    }

    function initMonaco() {
        if (monacoLoadAttempted) return;
        monacoLoadAttempted = true;
        if (typeof window.require === 'undefined') {
            useFallbackEditor();
            return;
        }
        window.require.config({
            paths: { vs: '/static/vendor/monaco/min/vs' }
        });
        var loaded = false;
        var failTimer = setTimeout(function () {
            if (!loaded) useFallbackEditor();
        }, 9000);
        window.require(['vs/editor/editor.main'], function () {
            loaded = true;
            clearTimeout(failTimer);
            monaco = window.monaco;
            monacoReady = true;
            el.fallbackEditor.style.display = 'none';
            el.monaco.style.display = 'block';
            el.monaco.innerHTML = '';
            monaco.editor.defineTheme('nb-dark', {
                base: 'vs-dark',
                inherit: true,
                rules: [],
                colors: { 'editor.background': '#0d1220' }
            });
            monaco.editor.setTheme('nb-dark');
            rebuildModels();
            monacoEditor = monaco.editor.create(el.monaco, {
                model: currentModel || models[activeFile] || null,
                automaticLayout: true,
                fontSize: 13,
                minimap: { enabled: true },
                scrollBeyondLastLine: false,
                wordWrap: 'off',
                tabSize: 2,
                theme: 'nb-dark',
                language: fileNameLang(activeFile)
            });
            if (currentModel) monacoEditor.setModel(currentModel);
            monacoEditor.onDidChangeCursorPosition(function (e) {
                el.statusLn.textContent = 'Ln ' + e.position.lineNumber + ', Col ' + e.position.column;
            });
            rebuildModels();
            openFile(activeFile);
        });
    }

    function useFallbackEditor() {
        el.monaco.style.display = 'none';
        el.fallbackEditor.style.display = 'block';
        var f = getFile(activeFile);
        el.fallbackTextarea.value = f ? f.content : '';
        el.fallbackTextarea.addEventListener('input', function () {
            var fileObj = getFile(activeFile);
            if (fileObj) fileObj.content = el.fallbackTextarea.value;
            if (currentWebsiteState.files) currentWebsiteState.files[activeFile] = el.fallbackTextarea.value;
            markDirty(activeFile);
        });
    }

    function rebuildModels() {
        if (monaco && monacoReady) {
            suppressDirty = true;
            var keep = {};
            fileList().forEach(function (name) {
                var f = getFile(name);
                var content = f ? f.content : '';
                if (!models[name]) {
                    models[name] = monaco.editor.createModel(
                        content,
                        fileNameLang(name),
                        monaco.Uri.parse('file:///' + name)
                    );
                    models[name].onDidChangeContent(function () {
                        markDirty(name);
                    });
                } else {
                    var cur = models[name].getValue();
                    if (cur !== content) models[name].setValue(content);
                }
                keep[name] = true;
            });
            Object.keys(models).forEach(function (name) {
                if (!keep[name]) { models[name].dispose(); delete models[name]; }
            });
            if (!getFile(activeFile)) {
                var names = fileList();
                activeFile = names.length ? names[0] : 'index.html';
            }
            activeFileId = getFile(activeFile) ? getFile(activeFile).id : null;
            currentModel = models[activeFile] || null;
            if (monacoEditor && currentModel) monacoEditor.setModel(currentModel);
            suppressDirty = false;
        }
        if (!monacoReady) {
            var fb = getFile(activeFile);
            if (activeFile && fb) {
                el.fallbackTextarea.value = fb.content || '';
            }
        }
        renderFileTree();
        renderTabs();
    }

    function applyCodeChanges() {
        syncStateFromEditors();
        if (!hasSite && (currentWebsiteState.html || currentWebsiteState.css || currentWebsiteState.javascript)) {
            hasSite = true;
        }
        if (!hasSite) { toast('Nothing to apply yet - generate a website first', true); return; }

        // Refresh the live preview immediately with the edited code
        renderPreview();

        // Persist the edited code so it survives a reload
        currentWebsiteState.website_name = el.projectName.value.trim() || 'My AI Website';
        currentWebsiteState.files = normalizeFiles(currentWebsiteState.files, currentWebsiteState.html, currentWebsiteState.css, currentWebsiteState.javascript);
        currentWebsiteState.project_id = activeProjectId;

        showLoading('Saving changes...', 'Storing your edited code');
        fetch(API.save, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ state: currentWebsiteState, project_id: activeProjectId || null })
        })
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
            .then(function (res) {
                hideLoading();
                if (!res.ok || !res.j.success) {
                    toast((res.j && res.j.error) || 'Could not save code changes', true);
                    return;
                }
                setProjectId(res.j.project_id);
                Object.keys(dirtyFiles).forEach(function (k) { markClean(k); });
                toast('Code applied and saved - preview updated');
            })
            .catch(function (err) {
                hideLoading();
                toast('Save error: ' + err.message, true);
            });
    }

    function formatActiveFile() {
        var name = activeFile;
        var content = readFileContent(name);
        if (!content) { toast('Nothing to format', true); return; }
        var lang = fileNameLang(name);
        var formatted = content;
        if (lang === 'json') {
            try {
                formatted = JSON.stringify(JSON.parse(content), null, 2);
            } catch (e) {
                toast('Invalid JSON - cannot format', true);
                return;
            }
        } else {
            formatted = content.split('\n').map(function (line) { return line.replace(/\s+$/, ''); }).join('\n');
        }
        if (monaco && monacoReady && models[name]) {
            models[name].setValue(formatted);
        } else {
            var f = getFile(name);
            if (f) f.content = formatted;
            if (currentWebsiteState.files) currentWebsiteState.files[name] = formatted;
            if (name === activeFile) el.fallbackTextarea.value = formatted;
        }
        markDirty(name);
        toast('Formatted ' + name);
    }

    function copyActiveFileCode() {
        var content = readFileContent(activeFile);
        if (!content) { toast('Nothing to copy', true); return; }
        var done = function () { toast('Copied ' + activeFile + ' to clipboard'); };
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(content).then(done).catch(function () { fallbackCopy(content, done); });
        } else {
            fallbackCopy(content, done);
        }
    }

    function fallbackCopy(text, done) {
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand('copy'); } catch (e) { /* ignore */ }
        document.body.removeChild(ta);
        if (done) done();
    }

    /* ---------- Code quality analyzer ---------- */
    function qualityLevelClass(level) {
        var lv = String(level || '').toLowerCase();
        if (lv.indexOf('high') !== -1) return 'nb-q-high';
        if (lv.indexOf('medium') !== -1) return 'nb-q-medium';
        return 'nb-q-low';
    }

    function issueIcon(severity) {
        var map = { high: 'fa-triangle-exclamation', medium: 'fa-circle-exclamation', low: 'fa-circle-info' };
        return map[severity] || 'fa-circle-info';
    }

    function sectionIcon(key) {
        var map = { html: 'fa-html5', css: 'fa-css3-alt', javascript: 'fa-square-js', accessibility: 'fa-universal-access' };
        return map[key] || 'fa-cube';
    }

    function renderQualityResult(result) {
        lastQuality = result;

        var score = result.quality_score != null ? result.quality_score : '--';
        el.qualityScore.textContent = score;
        el.qualityScore.className = 'nb-quality-score ' + qualityLevelClass(result.quality_level);
        el.qualityLevel.textContent = result.quality_level || 'Not analyzed';
        el.qualityLevel.className = 'nb-quality-level ' + qualityLevelClass(result.quality_level);
        el.qualityConf.textContent = (result.quality_level && typeof result.confidence === 'number')
            ? 'Model confidence ' + Math.round(result.confidence * 100) + '%'
            : '';
        el.qualityConf.style.display = result.quality_level ? '' : 'none';

        renderQualitySections(result.sections);

        var issues = result.issues || [];
        if (!issues.length) {
            el.qualityIssues.innerHTML = '<p class="nb-quality-empty nb-quality-clean">' +
                '<i class="fa-solid fa-circle-check"></i> No issues detected - great job!</p>';
        } else {
            el.qualityIssues.innerHTML = issues.map(function (i) {
                var sev = (i.severity || 'info').toLowerCase();
                var issueTitle = i.issue || i.message || 'Quality Issue';
                var explanation = i.explanation || i.message || '';
                var aiFix = i.ai_fix || '';
                var itype = i.type || 'Quality';

                var html = '<div class="nb-issue nb-issue-' + escHtml(sev) + '">';
                html += '<div class="nb-issue-top">';
                html += '<div class="nb-issue-title-wrap"><span class="nb-issue-sev"><i class="fa-solid ' + issueIcon(sev) + '"></i> ' + escHtml(sev.toUpperCase()) + '</span>';
                html += '<strong class="nb-issue-name">' + escHtml(issueTitle) + '</strong></div>';
                html += '<span class="nb-issue-type">' + escHtml(itype) + '</span>';
                html += '</div>';
                html += '<p class="nb-issue-msg">' + escHtml(explanation) + '</p>';
                if (aiFix) {
                    html += '<div class="nb-issue-aifix"><i class="fa-solid fa-wand-magic-sparkles"></i> <strong>AI Fix:</strong> <span>' + escHtml(aiFix) + '</span></div>';
                }
                html += '</div>';
                return html;
            }).join('');
        }

        var now = new Date();
        el.qualityMeta.textContent = 'Analyzed at ' +
            ('0' + now.getHours()).slice(-2) + ':' +
            ('0' + now.getMinutes()).slice(-2) + ':' +
            ('0' + now.getSeconds()).slice(-2);
    }

    function renderQualitySections(sections) {
        if (!sections || !sections.length) { el.qualitySections.innerHTML = ''; return; }
        el.qualitySections.innerHTML = sections.map(function (s) {
            return '<div class="nb-qsection nb-qsection-' + escHtml(s.status || 'ok') + '">' +
                '<div class="nb-qsection-title"><i class="fa-solid ' + sectionIcon(s.key) + '"></i> ' + escHtml(s.title) + '</div>' +
                '<div class="nb-qsection-status">' + escHtml(s.status_label || '') + '</div>' +
                '<p class="nb-qsection-summary">' + escHtml(s.summary || '') + '</p>' +
                '</div>';
        }).join('');
    }

    function renderQualityComparison() {
        var before = lastQualityBeforeImprove;
        var after = lastQuality;
        if (!before || !after) return;
        qualityImproveActive = false;
        lastQualityBeforeImprove = null;

        var bs = before.quality_score != null ? before.quality_score : '--';
        var as = after.quality_score != null ? after.quality_score : '--';
        var delta = null;
        if (typeof before.quality_score === 'number' && typeof after.quality_score === 'number') {
            delta = after.quality_score - before.quality_score;
        }
        var arrow = delta === null
            ? '<i class="fa-solid fa-equals nb-cmp-eq"></i>'
            : (delta > 0
                ? '<i class="fa-solid fa-arrow-trend-up nb-cmp-up"></i>'
                : (delta < 0
                    ? '<i class="fa-solid fa-arrow-trend-down nb-cmp-down"></i>'
                    : '<i class="fa-solid fa-equals nb-cmp-eq"></i>'));
        var deltaLabel = delta === null ? '' : (delta > 0 ? '+' + delta : String(delta));

        el.qualityCompare.innerHTML =
            '<div class="nb-cmp-head"><i class="fa-solid fa-arrow-right-arrow-left"></i> Before vs After</div>' +
            '<div class="nb-cmp-cols">' +
            '<div class="nb-cmp-col">' +
            '<div class="nb-cmp-label">Before</div>' +
            '<div class="nb-cmp-score ' + qualityLevelClass(before.quality_level) + '">' + escHtml(bs) + '</div>' +
            '<div class="nb-cmp-level">' + escHtml(before.quality_level || '') + '</div>' +
            '</div>' +
            '<div class="nb-cmp-arrow">' + arrow + (deltaLabel ? ' <span class="nb-cmp-delta">' + deltaLabel + '</span>' : '') + '</div>' +
            '<div class="nb-cmp-col">' +
            '<div class="nb-cmp-label">After</div>' +
            '<div class="nb-cmp-score ' + qualityLevelClass(after.quality_level) + '">' + escHtml(as) + '</div>' +
            '<div class="nb-cmp-level">' + escHtml(after.quality_level || '') + '</div>' +
            '</div>' +
            '</div>';
        el.qualityCompare.style.display = 'block';

        if (delta !== null && delta > 0) {
            addBubble('Code quality improved from ' + bs + ' to ' + as + ' (' + deltaLabel + ').', 'assistant');
        } else if (delta !== null && delta === 0) {
            addBubble('Code quality stayed at ' + as + '. No regressions detected.', 'assistant');
        }
    }

    function analyzeQuality(isAuto) {
        syncStateFromEditors();
        var html = currentWebsiteState.html || '';
        var css = currentWebsiteState.css || '';
        var js = currentWebsiteState.javascript || '';
        if (!html && !css && !js) {
            if (!isAuto) {
                el.qualityLevel.textContent = 'No code to analyze';
                el.qualityScore.textContent = '--';
                toast('Generate a website first', true);
            }
            return;
        }

        if (!isAuto) {
            el.analyzeBtn.disabled = true;
            el.qualityScore.textContent = '...';
            el.qualityScore.className = 'nb-quality-score';
            el.qualityLevel.textContent = 'Analyzing...';
            el.qualityLevel.className = 'nb-quality-level';
            el.qualityConf.textContent = '';
            el.qualityIssues.innerHTML = '<p class="nb-quality-empty">Running the ML analyzer...</p>';
            el.qualityMeta.textContent = '';
        }

        fetch(API.qualityAnalyze, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ html: html, css: css, javascript: js, project_id: activeProjectId || null })
        })
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
            .then(function (res) {
                el.analyzeBtn.disabled = false;
                if (!res.ok || !res.j.success) {
                    var err = (res.j && (res.j.message || res.j.error)) || 'Analysis failed';
                    console.error('[QualityAnalyzer] Backend error:', err, res.j);
                    el.qualityLevel.textContent = 'Analysis failed';
                    el.qualityScore.textContent = '--';
                    el.qualityScore.className = 'nb-quality-score nb-q-low';
                    el.qualityIssues.innerHTML =
                        '<div class="nb-quality-empty">' +
                        '<i class="fa-solid fa-circle-exclamation"></i>' +
                        '<p>' + escHtml(err) + '</p>' +
                        '<button class="nb-btn nb-btn-ghost nb-quality-retry-btn" onclick="document.getElementById(\'nbAnalyzeBtn\').click()">' +
                        '<i class="fa-solid fa-rotate-right"></i> Retry</button>' +
                        '</div>';
                    if (!isAuto) toast(err, true);
                    return;
                }
                renderQualityResult(res.j);
                if (isAuto && qualityImproveActive) {
                    renderQualityComparison();
                } else if (isAuto) {
                    toast('Code quality: ' + res.j.quality_score + '/100 - ' + res.j.quality_level);
                }
            })
            .catch(function (err) {
                el.analyzeBtn.disabled = false;
                console.error('[QualityAnalyzer] Network error:', err);
                el.qualityLevel.textContent = 'Analysis failed';
                el.qualityScore.textContent = '--';
                el.qualityScore.className = 'nb-quality-score nb-q-low';
                el.qualityIssues.innerHTML =
                    '<div class="nb-quality-empty">' +
                    '<i class="fa-solid fa-plug-circle-xmark"></i>' +
                    '<p>Connection error: ' + escHtml(err.message || 'Could not reach server') + '</p>' +
                    '<button class="nb-btn nb-btn-ghost nb-quality-retry-btn" onclick="document.getElementById(\'nbAnalyzeBtn\').click()">' +
                    '<i class="fa-solid fa-rotate-right"></i> Retry</button>' +
                    '</div>';
                if (!isAuto) toast('Analysis error: ' + err.message, true);
            });
    }

    function buildImprovePrompt(focus) {
        var prompt = 'Improve the code quality of the current website. ';
        if (focus) prompt += 'Focus on: ' + focus + '. ';
        if (lastQuality && lastQuality.issues && lastQuality.issues.length) {
            prompt += 'The code-quality analyzer reported these issues:\n' +
                lastQuality.issues.slice(0, 20).map(function (i) {
                    return '- [' + (i.severity || 'info') + '] ' + i.message;
                }).join('\n') + '\n';
        }
        prompt += 'Fix these issues while preserving the existing visual design and functionality, then confirm what you changed.';
        return prompt;
    }

    function improveWithAI() {
        syncStateFromEditors();
        if (!hasSite) { toast('Generate a website first', true); return; }
        if (!lastQuality) {
            toast('Run an analysis first so the AI knows what to improve', true);
            return;
        }
        var focus = el.qualityFocus.value;
        qualityImproveActive = true;
        lastQualityBeforeImprove = lastQuality;
        switchMode('chat');
        el.prompt.value = buildImprovePrompt(focus);
        sendPrompt();
    }

    /* ---------- Generation Status Panel (Preview Panel) ---------- */
    var _genTimerInterval = null;
    var _genStartTime = 0;
    var _genCurrentStage = null;
    var _genIsModify = false;
    var _genOriginalPayload = null;

    // All generation stages in order (matches preview panel steps)
    var GEN_STAGES = [
        { id: 'prompt_analysis', label: 'Analyzing prompt...', icon: 'fa-magnifying-glass', previewStep: 1 },
        { id: 'ai_planning', label: 'Planning website architecture...', icon: 'fa-diagram-project', previewStep: 2 },
        { id: 'component_generation', label: 'Generating components...', icon: 'fa-puzzle-piece', previewStep: 3 },
        { id: 'code_generation', label: 'Generating code...', icon: 'fa-code', previewStep: 4 },
        { id: 'file_creation', label: 'Creating files...', icon: 'fa-file-lines', previewStep: 5 },
        { id: 'dependency_installation', label: 'Installing dependencies...', icon: 'fa-boxes-stacked', previewStep: 6 },
        { id: 'build_validation', label: 'Validating build...', icon: 'fa-check-double', previewStep: 7 },
        { id: 'preview_startup', label: 'Starting preview...', icon: 'fa-play', previewStep: 8 },
    ];

    function _initGenStatus() {
        // Bind preview panel retry button
        if (el.previewRetryBtn) {
            el.previewRetryBtn.onclick = function () {
                retryGeneration();
            };
        }
        // Bind edit prompt button
        if (el.previewEditPromptBtn) {
            el.previewEditPromptBtn.onclick = function () {
                // Focus the prompt input in chat area
                if (el.prompt) {
                    el.prompt.focus();
                }
                // Hide error state
                hidePreviewError();
            };
        }
    }

    function showGenStatus(isModify, payload) {
        _genIsModify = isModify;
        _genOriginalPayload = payload; // Store for retry

        // Hide idle/empty state
        if (el.previewEmpty) el.previewEmpty.classList.add('hidden');
        // Hide done/error states
        hidePreviewDone();
        hidePreviewError();
        // Hide iframe
        if (el.previewFrame) el.previewFrame.style.display = 'none';

        // Show generating state
        if (el.previewGenerating) {
            el.previewGenerating.style.display = 'flex';
        }

        // Update title
        if (el.previewGenTitle) {
            el.previewGenTitle.textContent = isModify ? 'Modifying your website...' : 'Generating your website...';
        }

        _genStartTime = Date.now();
        _genCurrentStage = 0;
        clearInterval(_genTimerInterval);
        _genTimerInterval = setInterval(function () {
            var elapsed = ((Date.now() - _genStartTime) / 1000).toFixed(1);
            // Update timer in preview generating state if needed
        }, 100);

        // Reset all preview steps to pending
        GEN_STAGES.forEach(function (stage) {
            updatePreviewStep(stage.previewStep, 'pending');
        });

        // Start with first stage
        setPreviewStepActive('prompt_analysis');
    }

    function updatePreviewStep(stepNum, status) {
        if (!el.previewGenSteps) return;
        var step = el.previewGenSteps.querySelector('[data-step="' + stepNum + '"]');
        if (!step) return;

        // Update step classes
        step.className = 'nb-pgen-step ' + status;
        
        // Update icon
        var icon = step.querySelector('i');
        if (icon) {
            var stage = GEN_STAGES.find(function (s) { return s.previewStep === stepNum; });
            var iconClass = stage ? stage.icon : 'fa-magnifying-glass';
            
            if (status === 'active') {
                icon.className = 'fa-solid fa-spinner fa-spin';
            } else if (status === 'done') {
                icon.className = 'fa-solid fa-check';
            } else if (status === 'failed') {
                icon.className = 'fa-solid fa-xmark';
            } else if (status === 'skipped') {
                icon.className = 'fa-solid fa-forward-step';
            } else {
                icon.className = 'fa-solid ' + iconClass;
            }
        }
    }

    function setPreviewStepActive(id) {
        _genCurrentStage = GEN_STAGES.findIndex(function (s) { return s.id === id; });
        if (_genCurrentStage >= 0) {
            updatePreviewStep(GEN_STAGES[_genCurrentStage].previewStep, 'active');
        }
    }

    function completePreviewStep(id, timeSec) {
        var idx = GEN_STAGES.findIndex(function (s) { return s.id === id; });
        if (idx >= 0) {
            updatePreviewStep(GEN_STAGES[idx].previewStep, 'done');
        }

        // Auto-advance to next stage
        var nextIdx = _genCurrentStage + 1;
        if (nextIdx < GEN_STAGES.length) {
            setPreviewStepActive(GEN_STAGES[nextIdx].id);
        }
    }

    function completeGenStep(id, timeSec) {
        // Missing function fix — delegates to preview panel (single source of truth)
        // Previously caused "completeGenStep is not defined" and masked as "Could not reach server"
        if (typeof completePreviewStep === 'function') {
            return completePreviewStep(id, timeSec);
        }
        var idx = GEN_STAGES.findIndex(function (s) { return s.id === id; });
        if (idx >= 0) {
            updatePreviewStep(GEN_STAGES[idx].previewStep, 'done');
        }
    }

    function failPreviewStep(id, errorMsg) {
        var idx = GEN_STAGES.findIndex(function (s) { return s.id === id; });
        if (idx >= 0) {
            updatePreviewStep(GEN_STAGES[idx].previewStep, 'failed');
        }

        // Show error state in preview panel
        showPreviewError('Generation failed at: ' + (GEN_STAGES[idx] ? GEN_STAGES[idx].label : id), errorMsg);
    }

    function skipPreviewStep(id, reason) {
        var idx = GEN_STAGES.findIndex(function (s) { return s.id === id; });
        if (idx >= 0) {
            updatePreviewStep(GEN_STAGES[idx].previewStep, 'skipped');
        }

        // Auto-advance to next stage
        var nextIdx = GEN_STAGES.findIndex(function (s) { return s.id === id; }) + 1;
        if (nextIdx < GEN_STAGES.length) {
            setPreviewStepActive(GEN_STAGES[nextIdx].id);
        }
    }

    function hideGenStatus() {
        clearInterval(_genTimerInterval);
        // Hide generating state
        if (el.previewGenerating) {
            el.previewGenerating.style.display = 'none';
        }
    }

    function showPreviewError(message, details) {
        clearInterval(_genTimerInterval);
        hidePreviewGenerating();
        hidePreviewDone();
        
        if (el.previewError) {
            var msgEl = el.previewError.querySelector('#nbPreviewErrMsg');
            if (msgEl) msgEl.textContent = message || 'Generation failed';
            
            // Store details for potential display
            if (details) {
                el.previewError.setAttribute('data-error-details', details);
            }
            el.previewError.style.display = 'flex';
        }
    }

    function showGenError(message, details) {
        // Alias for preview error - keeps "Preparing preview" from sticking
        return showPreviewError(message, details);
    }

    function retryGeneration() {
        if (!_genOriginalPayload) return;

        // Hide error state
        hidePreviewError();

        // Reset all stages to pending
        GEN_STAGES.forEach(function (stage) {
            updatePreviewStep(stage.previewStep, 'pending');
        });
        _genCurrentStage = 0;
        setPreviewStepActive('prompt_analysis');

        // Restart timer
        _genStartTime = Date.now();
        clearInterval(_genTimerInterval);
        _genTimerInterval = setInterval(function () {
            var elapsed = ((Date.now() - _genStartTime) / 1000).toFixed(1);
        }, 100);

        // Show generating state again
        if (el.previewEmpty) el.previewEmpty.classList.add('hidden');
        if (el.previewGenerating) el.previewGenerating.style.display = 'flex';
        if (el.previewFrame) el.previewFrame.style.display = 'none';

        // Resend the request
        var endpoint = _genIsModify ? API.modify : API.generate;
        fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(_genOriginalPayload)
        })
        .then(function (r) {
            var ct = r.headers.get('content-type') || '';
            if (!r.ok) {
                return r.text().then(function(text){
                    var errJson;
                    try { errJson = JSON.parse(text); } catch(e) { errJson = { success:false, error: text ? text.slice(0,300) : ('HTTP '+r.status) }; }
                    return Promise.reject(new Error(errJson.error || errJson.message || ('HTTP '+r.status)));
                });
            }
            return r.text().then(function(text){
                try { return text ? JSON.parse(text) : {}; } catch(e) { throw new Error('Builder error: invalid JSON response'); }
            });
        })
        .then(function (data) {
            handleGenerationResponse(data);
        })
        .catch(function (err) {
            hidePreviewGenerating();
            hideLoading();
            var msg = (err && err.message) ? err.message : String(err);
            var isJS = err && (err.name === 'ReferenceError' || (msg && msg.indexOf('is not defined') !== -1));
            var isNetwork = msg && (msg.indexOf('Failed to fetch') !== -1 || msg.indexOf('NetworkError') !== -1);
            if (isJS) {
                var fnMatch = msg.match(/(\w+) is not defined/);
                var fnName = fnMatch ? fnMatch[1] : 'unknown function';
                showPreviewError('Builder error: ' + fnName + ' is missing', msg);
            } else if (isNetwork) {
                showPreviewError('Cannot connect to server', msg);
            } else {
                showPreviewError('Connection error: ' + msg, msg);
            }
            // Don't add error to chat - keep chat clean (preview panel only)
        });
    }

    /* ---------- Chat send ---------- */
    function sendPrompt() {
        // Prevent multiple generation clicks while running
        if (isGenerating) {
            toast('Generation in progress — please wait or Stop it.', true);
            return;
        }
        var message;
        if (!isStarted) {
            message = (el.landingPrompt.value || '').trim();
        } else {
            message = el.prompt.value.trim();
        }
        if (!message) {
            toast('Please describe your website idea.', true);
            return;
        }

        if (!isStarted) {
            switchToBuilder(message);
        }

        syncStateFromEditors();
        addBubble(message, 'user');
        if (!isStarted) { el.landingPrompt.value = ''; }
        el.prompt.value = '';

        var endpoint = hasSite ? API.modify : API.generate;
        var genId = _generateId();
        var payload;
        if (hasSite) {
            payload = { message: message, project_id: activeProjectId || null, generation_id: genId };
        } else {
            payload = { prompt: message, website_name: el.projectName.value.trim() || 'My AI Website', generation_id: genId };
        }

        // Preview panel status (not chat) with Stop button
        setGenerating(true, genId);
        showGenStatus(hasSite, payload);
        showLoading(hasSite ? 'Modifying...' : 'Generating...', hasSite ? 'AI is modifying your website' : 'Generating your website...');
        var _simStep = 1;
        clearInterval(_genStepTimer);
        _genStepTimer = setInterval(function(){ if(_simStep<8){ _simStep++; updateGenStepUI(_simStep); } }, 2500);

        fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: _abortController ? _abortController.signal : undefined
        })
        .then(function (r) {
            var ct = r.headers.get('content-type') || '';
            if (!r.ok) {
                return r.text().then(function(text){
                    var errJson;
                    try { errJson = JSON.parse(text); } catch(e) { errJson = { success:false, error: (text && text.trim()) ? text.slice(0,300) : ('HTTP '+r.status), status:r.status }; }
                    return {status:r.status, ok:false, j:errJson};
                });
            }
            return r.text().then(function(text){
                try {
                    var j = text ? JSON.parse(text) : {};
                    return {status:r.status, ok:true, j:j};
                } catch(e) {
                    return {status:r.status, ok:false, j:{success:false, error:'Invalid server response (not JSON): '+e.message, raw:text ? text.slice(0,400) : ''}};
                }
            });
        })
        .then(function (res) {
            clearInterval(_genStepTimer);
            var data = res.j;
            if (res.status === 499 || (data && data.cancelled)) {
                showCancelledUI();
                setGenerating(false, null);
                return;
            }
            if (!res.ok || (data && data.success === false)) {
                var errMsg = (data && (data.error || data.message)) || ('Request failed ('+res.status+')');
                var details = (data && (data.details || data.error)) || errMsg;
                hideLoading();
                // Preview panel error (not chat status)
                if (typeof showPreviewError === 'function') showPreviewError(errMsg, details);
                addBubble('Generation failed: ' + errMsg, 'ai');
                setGenerating(false, null);
                hideGenStatus();
                return;
            }
            if (data) data.generation_id = genId;
            handleGenerationResponse(data);
            setGenerating(false, null);
        })
        .catch(function (err) {
            clearInterval(_genStepTimer);
            if (err && err.name === 'AbortError') {
                showCancelledUI();
                return;
            }
            setGenerating(false, null);
            hideGenStatus();
            hideLoading();
            var msg = (err && err.message) ? err.message : String(err);
            var isJS = err && (err.name === 'ReferenceError' || (msg && msg.indexOf('is not defined') !== -1) || (msg && msg.indexOf('is not a function') !== -1));
            var isNetwork = msg && (msg.indexOf('Failed to fetch') !== -1 || msg.indexOf('NetworkError') !== -1 || msg.indexOf('Load failed') !== -1 || msg.indexOf('Network request failed') !== -1);
            if (isJS) {
                var fnMatch = msg.match(/(\w+) is not defined/);
                var fnName = fnMatch ? fnMatch[1] : 'unknown function';
                var jsMsg = 'Builder error: ' + fnName + ' is missing';
                if (typeof showPreviewError === 'function') showPreviewError(jsMsg, msg);
                addBubble(jsMsg + ' (' + msg + ')', 'ai');
            } else if (isNetwork) {
                if (typeof showPreviewError === 'function') showPreviewError('Cannot connect to server', msg);
                addBubble('Cannot connect to server. Please check your connection and try again.', 'ai');
            } else {
                if (typeof showPreviewError === 'function') showPreviewError('Connection error: ' + msg, msg);
                else if (typeof showGenError === 'function') showGenError('Connection error: ' + msg, msg);
                addBubble('Could not reach the server. Check your connection and try again. ('+msg+')', 'ai');
            }
        });
    }

    function handleGenerationResponse(data) {
        hideLoading();

        if (data.success) {
            activeProjectId = data.project_id || activeProjectId;
            hasSite = true;

            // Update website state with generated files
            if (data.files) {
                currentWebsiteState.files = data.files;
                syncEditorsFromFiles(data.files);
            }

            // Complete all stages based on timing data
            if (data.timing) {
                var t = data.timing;

                // Complete stages in order
                if (t.planning_seconds > 0) completeGenStep('prompt_analysis', 0);
                completeGenStep('ai_planning', t.planning_seconds);

                if (t.code_generation_seconds > 0) {
                    completeGenStep('component_generation', t.code_generation_seconds / 2);
                    completeGenStep('code_generation', t.code_generation_seconds / 2);
                }

                if (t.file_creation_seconds > 0) completeGenStep('file_creation', t.file_creation_seconds);

                if (t.dependency_install_seconds > 0) completePreviewStep('dependency_installation', t.dependency_install_seconds);
                else skipPreviewStep('dependency_installation', 'Static project');

                if (t.build_seconds > 0) completePreviewStep('build_validation', t.build_seconds);
                else skipPreviewStep('build_validation', 'Static project');

                if (t.preview_seconds > 0) completePreviewStep('preview_startup', t.preview_seconds);
                else skipPreviewStep('preview_startup', 'N/A');

                // Stop the timer with final time
                clearInterval(_genTimerInterval);
            } else {
                // No timing data, just complete all stages
                GEN_STAGES.forEach(function (stage) {
                    completePreviewStep(stage.id, 0);
                });
                clearInterval(_genTimerInterval);
            }

            // AI conversational response in chat (keep it clean)
            var aiMsg = data.message || 'Your website is ready!';
            if (data.plan) {
                var pages = data.plan.pages ? data.plan.pages.length : 0;
                var comps = data.plan.components ? data.plan.components.length : 0;
                aiMsg += ' I created ' + pages + ' pages and ' + comps + ' components.';
            }
            if (data.build_status === 'passed') {
                aiMsg += ' Build validation passed — the preview should load shortly.';
            } else if (data.build_status === 'failed') {
                var errMsgs = (data.build_errors || []).slice(0, 2).join('; ');
                aiMsg += ' There were some build issues: ' + errMsgs;
            }
            addBubble(aiMsg, 'ai');

            // Hide generating overlay and load preview automatically via Flask (no CORS)
            hideGenStatus();
            hidePreviewGenerating();
            hideGenStatus();
            if (data.preview_url && data.preview_url.indexOf('/preview/') === 0) {
                // Flask-served production dist - iframe-safe, no CORS, no Vite dev server
                if (el.previewEmpty) el.previewEmpty.classList.add('hidden');
                hidePreviewError();
                hidePreviewGenerating();
                if (el.previewFrame) {
                    el.previewFrame.style.display = 'block';
                    // Use absolute URL per spec http://127.0.0.1:5000/preview/{project_id}/index.html if needed
                    var previewSrc = data.preview_url;
                    // Ensure it points to index.html
                    if (previewSrc.indexOf('/index.html') === -1 && previewSrc.charAt(previewSrc.length-1) === '/') {
                        previewSrc += 'index.html';
                    }
                    el.previewFrame.src = previewSrc;
                }
                if (el.previewDone) el.previewDone.style.display = 'flex';
                completePreviewStep('preview_startup', 0);
                completeGenStep('preview_startup', 0);
                // Ensure preview stage is marked done
                updatePreviewStep(9, 'done');
                // Also complete file creation if needed
                if (typeof hidePreviewGenerating === 'function') hidePreviewGenerating();
            } else {
                // Fallback: legacy Vite dev server polling
                _refreshPreview();
            }
        } else {
            // Show failure in preview panel with retry
            var failedStageId = mapFailedStage(data.failed_stage);
            var stageInfo = GEN_STAGES.find(function (s) { return s.id === failedStageId; });
            var stageLabel = stageInfo ? stageInfo.label : (data.failed_stage || 'Unknown stage');
            var failMsg = 'Generation failed at: ' + stageLabel;
            var details = data.error || 'Unknown error';
            if (data.failed_stage) {
                failMsg += ' (' + data.failed_stage.replace('_', ' ') + ')';
            }
            showPreviewError(failMsg, details);

            // Mark the failed stage in preview panel
            if (failedStageId) {
                failPreviewStep(failedStageId, details);
            }

            // Don't show error in chat - keep chat clean for conversational responses only
            // The preview panel shows the error details with retry button
            // Handle cancelled specifically (already handled in sendPrompt, but safe)
            if (data && data.cancelled) {
                showCancelledUI();
                return;
            }
            setGenerating(false, null);
        }
        // Ensure generating off after success too
        if (data && data.success) setGenerating(false, null);
    }

    function mapFailedStage(backendStage) {
        // Map backend stage names to frontend stage IDs
        var stageMap = {
            'planning': 'ai_planning',
            'code_gen': 'code_generation',
            'file_creation': 'file_creation',
            'npm_install': 'dependency_installation',
            'build': 'build_validation',
            'preview': 'preview_startup',
            'unknown': 'code_generation',
        };
        return stageMap[backendStage] || 'code_generation';
    }

    function _refreshPreview() {
        if (!activeProjectId) return;

        // Show loading state in preview
        if (el.previewEmpty) el.previewEmpty.classList.add('hidden');
        hidePreviewError();

        // Show a "server starting" message in the preview area
        var previewOverlay = document.getElementById('nbPreviewOverlay');
        if (!previewOverlay) {
            previewOverlay = document.createElement('div');
            previewOverlay.id = 'nbPreviewOverlay';
            previewOverlay.style.cssText = 'position:absolute;top:0;left:0;right:0;bottom:0;display:flex;align-items:center;justify-content:center;background:rgba(15,23,42,0.9);z-index:10;flex-direction:column;gap:12px;';
            var parent = el.previewFrame ? el.previewFrame.parentNode : null;
            if (parent) {
                parent.style.position = 'relative';
                parent.appendChild(previewOverlay);
            }
        }
        previewOverlay.innerHTML =
            '<div style="color:#6366f1;font-size:18px;font-weight:600;"><i class="fa-solid fa-spinner fa-spin" style="margin-right:8px;"></i>Starting preview server...</div>' +
            '<div style="color:#94a3b8;font-size:13px;">Installing dependencies and starting Vite dev server</div>';
        previewOverlay.style.display = 'flex';

        fetch(API.preview(activeProjectId))
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success && data.url) {
                    // Flask preview ( /preview/vite/... ) - load directly without CORS polling
                    if (data.url.indexOf('/preview/vite/') === 0 || data.url.indexOf('/preview/') === 0) {
                        if (previewOverlay) previewOverlay.style.display = 'none';
                        if (el.previewFrame) {
                            el.previewFrame.style.display = 'block';
                            el.previewFrame.src = data.url;
                        }
                        hidePreviewGenerating();
                        if (el.previewDone) el.previewDone.style.display = 'flex';
                        if (el.previewEmpty) el.previewEmpty.classList.add('hidden');
                        return;
                    }
                    // Legacy Vite dev server - poll until responding
                    _pollPreviewReady(data.url, 0);
                } else {
                    // Preview server failed to start — show error, NOT raw content
                    var errMsg = (data.message || 'Preview server failed to start');
                    previewOverlay.innerHTML =
                        '<div style="color:#ef4444;font-size:16px;font-weight:600;"><i class="fa-solid fa-triangle-exclamation" style="margin-right:8px;"></i>Preview Failed</div>' +
                        '<div style="color:#94a3b8;font-size:13px;max-width:400px;text-align:center;">' + escHtml(errMsg) + '</div>' +
                        '<button onclick="window._retryPreview()" style="margin-top:8px;padding:6px 16px;border-radius:8px;border:1px solid rgba(99,102,241,0.3);background:rgba(99,102,241,0.1);color:#818cf8;cursor:pointer;font-size:13px;">Retry</button>';
                }
            })
            .catch(function (err) {
                previewOverlay.innerHTML =
                    '<div style="color:#ef4444;font-size:16px;font-weight:600;"><i class="fa-solid fa-triangle-exclamation" style="margin-right:8px;"></i>Preview Connection Error</div>' +
                    '<div style="color:#94a3b8;font-size:13px;">' + escHtml(err.message || 'Failed to connect to preview server') + '</div>';
            });
    }

    window._retryPreview = function () {
        _refreshPreview();
    };

    function _pollPreviewReady(url, attempt) {
        var maxAttempts = 20;
        var previewOverlay = document.getElementById('nbPreviewOverlay');

        if (attempt >= maxAttempts) {
            // Give up polling — show error instead of loading broken URL
            if (previewOverlay) {
                previewOverlay.innerHTML =
                    '<div style="color:#ef4444;font-size:16px;font-weight:600;"><i class="fa-solid fa-clock" style="margin-right:8px;"></i>Preview Timeout</div>' +
                    '<div style="color:#94a3b8;font-size:13px;">Server started but is not responding. The project may have build errors.</div>' +
                    '<button onclick="window._retryPreview()" style="margin-top:8px;padding:6px 16px;border-radius:8px;border:1px solid rgba(99,102,241,0.3);background:rgba(99,102,241,0.1);color:#818cf8;cursor:pointer;font-size:13px;">Retry</button>';
            }
            return;
        }

        // Update status message
        if (previewOverlay) {
            var dots = '.'.repeat((attempt % 3) + 1);
            previewOverlay.innerHTML =
                '<div style="color:#6366f1;font-size:18px;font-weight:600;"><i class="fa-solid fa-spinner fa-spin" style="margin-right:8px;"></i>Starting preview server' + dots + '</div>' +
                '<div style="color:#94a3b8;font-size:13px;">Attempt ' + (attempt + 1) + '/' + maxAttempts + '</div>';
        }

        // Try fetching the URL to see if it's up
        fetch(url, { mode: 'no-cors' })
            .then(function () {
                // Server is up — load in iframe
                if (previewOverlay) previewOverlay.style.display = 'none';
                if (el.previewFrame) {
                    el.previewFrame.style.display = 'block';
                    el.previewFrame.src = url;
                }
                hasSite = true;
            })
            .catch(function () {
                // Not ready yet, wait and retry
                setTimeout(function () { _pollPreviewReady(url, attempt + 1); }, 1500);
            });
    }

    /* ---------- Save / Download / Load ---------- */
    function saveProject() {
        syncStateFromEditors();
        currentWebsiteState.website_name = el.projectName.value.trim() || 'My AI Website';
        currentWebsiteState.files = normalizeFiles(currentWebsiteState.files, currentWebsiteState.html, currentWebsiteState.css, currentWebsiteState.javascript);
        currentWebsiteState.project_id = activeProjectId;

        showLoading('Saving project...', 'Storing your website state and conversation');
        fetch(API.save, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ state: currentWebsiteState, project_id: activeProjectId || null })
        })
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
            .then(function (res) {
                hideLoading();
                if (!res.ok || !res.j.success) {
                    toast((res.j && res.j.error) || 'Save failed', true);
                    return;
                }
                setProjectId(res.j.project_id);
                Object.keys(dirtyFiles).forEach(function (k) { markClean(k); });
                renderPreview();
                toast('Project saved successfully!');
            })
            .catch(function (err) {
                hideLoading();
                toast('Save error: ' + err.message, true);
            });
    }

    function downloadProject() {
        if (!hasSite) { toast('Generate a website first', true); return; }
        syncStateFromEditors();
        if (!activeProjectId) {
            toast('Saving first...');
            fetch(API.save, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ state: currentWebsiteState, project_id: null })
            })
                .then(function (r) { return r.json(); })
                .then(function (j) {
                    if (j.success) {
                        setProjectId(j.project_id);
                        window.location.href = '/download/zip/' + encodeURIComponent(j.project_id);
                    } else {
                        toast((j.error) || 'Could not save before download', true);
                    }
                })
                .catch(function () { toast('Download failed', true); });
            return;
        }
        window.location.href = '/download/zip/' + encodeURIComponent(activeProjectId);
    }

    function deployProject() {
        if (!hasSite) { toast('Generate a website first', true); return; }
        syncStateFromEditors();
        if (!activeProjectId) {
            toast('Saving first...');
            fetch(API.save, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ state: currentWebsiteState, project_id: null })
            })
                .then(function (r) { return r.json(); })
                .then(function (j) {
                    if (j.success) {
                        setProjectId(j.project_id);
                        window.location.href = '/download/deploy/' + encodeURIComponent(j.project_id);
                    } else {
                        toast((j.error) || 'Could not save before deploy', true);
                    }
                })
                .catch(function () { toast('Deploy download failed', true); });
            return;
        }
        window.location.href = '/download/deploy/' + encodeURIComponent(activeProjectId);
    }

    function loadProject(id) {
        showLoading('Loading project...', 'Restoring your website state and conversation');
        fetch(API.project(id))
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
            .then(function (res) {
                hideLoading();
                if (!res.ok || !res.j.success) {
                    toast((res.j && res.j.error) || 'Could not load project', true);
                    return;
                }
                applyStateToUI(res.j.state);
                toast('Project restored');
            })
            .catch(function (err) {
                hideLoading();
                toast('Load error: ' + err.message, true);
            });
    }

    /* ---------- Version History ---------- */
    function saveVersion() {
        if (!activeProjectId) {
            toast('Save the project first before creating a version', true);
            return;
        }
        syncStateFromEditors();
        currentWebsiteState.website_name = el.projectName.value.trim() || 'My AI Website';
        currentWebsiteState.files = normalizeFiles(currentWebsiteState.files, currentWebsiteState.html, currentWebsiteState.css, currentWebsiteState.javascript);
        currentWebsiteState.project_id = activeProjectId;

        var description = window.prompt('Describe this version (optional):', '');
        if (description === null) return;

        showLoading('Saving version...', 'Creating a snapshot of your current work');
        fetch(API.versionCreate, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ state: currentWebsiteState, project_id: activeProjectId, description: description || '' })
        })
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
            .then(function (res) {
                hideLoading();
                if (!res.ok || !res.j.success) {
                    toast((res.j && res.j.error) || 'Could not save version', true);
                    return;
                }
                toast('Version ' + res.j.version + ' saved successfully!');
            })
            .catch(function (err) {
                hideLoading();
                toast('Version save error: ' + err.message, true);
            });
    }

    function openVersionHistory() {
        if (!activeProjectId) {
            toast('Save the project first to view version history', true);
            return;
        }
        showLoading('Loading versions...', 'Fetching version history');
        fetch(API.versions(activeProjectId))
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
            .then(function (res) {
                hideLoading();
                if (!res.ok || !res.j.success) {
                    toast((res.j && res.j.error) || 'Could not load versions', true);
                    return;
                }
                renderVersionList(res.j.versions || []);
                el.versionsModal.style.display = 'flex';
            })
            .catch(function (err) {
                hideLoading();
                toast('Versions load error: ' + err.message, true);
            });
    }

    function renderVersionList(versions) {
        var list = el.versionsList;
        if (!versions.length) {
            list.innerHTML = '<div class="nb-versions-empty">No versions yet. Save a version to keep a snapshot.</div>';
            return;
        }
        var html = '';
        versions.forEach(function (v, idx) {
            var isLatest = idx === 0;
            html +=
                '<div class="nb-version-row' + (isLatest ? ' nb-version-current' : '') + '">' +
                '<div class="nb-version-info">' +
                '<div class="nb-version-title">' +
                '<i class="fa-solid fa-code-branch"></i> Version ' + escHtml(v.version) +
                (isLatest ? ' <span class="nb-version-badge">Latest</span>' : '') +
                '</div>' +
                '<div class="nb-version-desc">' + escHtml(v.description) + '</div>' +
                '<div class="nb-version-date"><i class="fa-solid fa-calendar"></i> ' + escHtml(v.created_at) + '</div>' +
                '</div>' +
                '<button type="button" class="nb-btn nb-btn-ghost nb-version-restore" data-version="' + escHtml(v.id) + '" data-label="Version ' + escHtml(v.version) + '">' +
                '<i class="fa-solid fa-rotate-left"></i><span>Restore</span>' +
                '</button>' +
                '</div>';
        });
        list.innerHTML = html;
    }

    var pendingRestoreId = '';
    var pendingRestoreLabel = '';

    function askRestoreVersion(versionId, label) {
        pendingRestoreId = versionId;
        pendingRestoreLabel = label || 'this version';
        document.getElementById('nbRestoreText').textContent = 'Restore ' + pendingRestoreLabel + '?';
        el.restoreModal.style.display = 'flex';
    }

    function restoreVersion() {
        if (!pendingRestoreId) return;
        var versionId = pendingRestoreId;
        pendingRestoreId = '';
        el.restoreModal.style.display = 'none';

        showLoading('Restoring version...', 'Updating your project and preview');
        fetch(API.versionRestore(versionId), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        })
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
            .then(function (res) {
                hideLoading();
                if (!res.ok || !res.j.success) {
                    toast((res.j && res.j.error) || 'Restore failed', true);
                    return;
                }
                applyStateToUI(res.j.state);
                toast('Version restored - project updated');
            })
            .catch(function (err) {
                hideLoading();
                toast('Restore error: ' + err.message, true);
            });
    }

    /**
     * Populate the provider dropdown with available providers.
     */
    /**
     * On provider dropdown change, reload models for that provider.
     */
    /**
     * Populate model dropdown based on selected provider.
     * Uses default models since each provider has different model lists.
     * @param {string} [savedModel] - model id to pre-select (from MongoDB)
     */
    /**
     * When the API key input changes, debounce-reload models using that key.
     */
    /* ---------- Mode switching ---------- */
    function switchMode(mode) {
        currentMode = mode || 'workflow';
        el.railBtns.forEach(function (b) {
            b.classList.toggle('active', b.getAttribute('data-mode') === currentMode);
        });
        if (el.chatPane) el.chatPane.classList.toggle('active', currentMode === 'workflow' || currentMode === 'chat');
        if (el.codePane) el.codePane.classList.toggle('active', currentMode === 'code');
        if (el.qualityPane) el.qualityPane.classList.toggle('active', currentMode === 'quality');
        if (el.activityPane) el.activityPane.classList.toggle('active', currentMode === 'activity');
        if (el.jarvisPane) el.jarvisPane.classList.toggle('active', currentMode === 'jarvis');
        if (currentMode === 'jarvis' && window.NexusJarvis && !window.__jarvisMounted) {
            window.__jarvisMounted = true;
            window.NexusJarvis.mount(el.jarvisMount, {
                getProjectId: function () { return activeProjectId; },
                getState: function () { return currentWebsiteState; },
                onProjectChanged: function (payload) {
                    if (payload && payload.state) {
                        applyStateToUI(payload.state);
                    }
                }
            });
        }
        if (currentMode === 'code') {
            if (monacoReady && monacoEditor) {
                monacoEditor.layout();
                if (currentModel) monacoEditor.setModel(currentModel);
            } else if (el.fallbackEditor && el.fallbackEditor.style.display !== 'none') {
                var fb = getFile(activeFile);
                el.fallbackTextarea.value = fb ? fb.content : '';
            }
        }
    }

    /* ===========================================================
       EVENT WIRING — Landing View
       =========================================================== */

    /* --- Generate Button Event System (Cleaner) --- */
    function handleGenerateClick(e) {
        if (e) e.preventDefault();
        if (isGenerating) {
            toast('Generation in progress — please wait or Stop it.', true);
            return;
        }
        sendPrompt();
    }
    function handleLandingKeydown(e) {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            handleGenerateClick(e);
        }
    }
    function bindGenerateEvents() {
        if (el.landingGenerateBtn) {
            el.landingGenerateBtn.removeEventListener('click', handleGenerateClick);
            el.landingGenerateBtn.addEventListener('click', handleGenerateClick);
        } else {
            console.warn('[Nexus] #nbLandingGenerateBtn not found in DOM');
        }
        if (el.landingPrompt) {
            el.landingPrompt.removeEventListener('keydown', handleLandingKeydown);
            el.landingPrompt.addEventListener('keydown', handleLandingKeydown);
        } else {
            console.warn('[Nexus] #nbLandingPrompt not found');
        }
        if (el.sendBtn) {
            el.sendBtn.removeEventListener('click', handleGenerateClick);
            el.sendBtn.addEventListener('click', handleGenerateClick);
        }
        var stopBtn = document.getElementById('nbStopGenerationBtn');
        var stopBtnPreview = document.getElementById('nbStopGenerationBtnPreview');
        if (stopBtn) {
            stopBtn.removeEventListener('click', handleStopGeneration);
            stopBtn.addEventListener('click', handleStopGeneration);
        }
        if (stopBtnPreview) {
            stopBtnPreview.removeEventListener('click', handleStopGeneration);
            stopBtnPreview.addEventListener('click', handleStopGeneration);
        }
    }
    // Initial bind for cleaner system
    bindGenerateEvents();

    /* --- AI Provider Button --- */
    (function bindProviderEvents() {
        var providerBtn = document.getElementById('nbProviderBtn');
        if (providerBtn) {
            providerBtn.removeEventListener('click', openProviderModal);
            providerBtn.addEventListener('click', openProviderModal);
        } else {
            console.warn('[Nexus] #nbProviderBtn not found in DOM');
        }
        // Provider modal wiring
        var providerSelect = document.getElementById('nbProviderSelect');
        var modelSelect = document.getElementById('nbModelSelect');
        var apiKeyInput = document.getElementById('nbApiKeyInput');
        var testBtn = document.getElementById('nbTestConnBtn');
        var saveBtn = document.getElementById('nbSaveProviderBtn');
        var closeBtns = document.querySelectorAll('[data-close-provider]');
        var modal = document.getElementById('nbProviderModal');
        if (providerSelect) {
            providerSelect.removeEventListener('change', onProviderChange);
            providerSelect.addEventListener('change', onProviderChange);
        }
        if (apiKeyInput) {
            apiKeyInput.removeEventListener('input', onApiKeyInput);
            apiKeyInput.addEventListener('input', onApiKeyInput);
        }
        if (testBtn) {
            testBtn.removeEventListener('click', testConnection);
            testBtn.addEventListener('click', testConnection);
        }
        if (saveBtn) {
            saveBtn.removeEventListener('click', saveProviderSettings);
            saveBtn.addEventListener('click', saveProviderSettings);
        }
        closeBtns.forEach(function(btn) {
            btn.removeEventListener('click', closeProviderModal);
            btn.addEventListener('click', closeProviderModal);
        });
        if (modal) {
            modal.addEventListener('click', function(e) {
                if (e.target === modal) closeProviderModal();
            });
        }
    })();

    /* --- Category template chips (landing view) --- */
    var _activeLandingChip = null;
    var landingChips = $$('#nbLandingView .nb-chip');
    console.log('[Nexus] Landing chips found:', landingChips.length);

    landingChips.forEach(function (chip) {
        chip.addEventListener('click', function () {
            var templateName = (chip.textContent || '').trim();
            var prompt = chip.getAttribute('data-prompt') || '';
            console.log('[Nexus] Template selected:', templateName);
            console.log('[Nexus] Prompt text:', prompt.substring(0, 60) + '...');

            /* Remove previous selection */
            if (_activeLandingChip) {
                _activeLandingChip.classList.remove('nb-chip-active');
            }
            /* Set new selection with animation */
            chip.classList.add('nb-chip-active');
            _activeLandingChip = chip;

            /* Set value IMMEDIATELY so the textarea updates right away */
            el.landingPrompt.value = prompt;
            el.landingPrompt.focus();

            /* Trigger input event so any listeners see the change */
            try { el.landingPrompt.dispatchEvent(new Event('input', { bubbles: true })); } catch (e) {}

            /* Pulse animation on the chip */
            chip.style.transform = 'scale(0.95)';
            setTimeout(function () { chip.style.transform = ''; }, 150);
        });
    });

    /* --- Builder send + Stop buttons handled by bindGenerateEvents() above (cleaner system) --- */

    /* --- Generation retry button --- */
    var _retryBtn = document.getElementById('nbGenRetryBtn');
    if (_retryBtn) {
        _retryBtn.addEventListener('click', function () {
            hideGenStatus();
            sendPrompt();
        });
    }

    el.saveBtn.addEventListener('click', saveProject);
    el.saveVersionBtn.addEventListener('click', saveVersion);
    el.versionsBtn.addEventListener('click', openVersionHistory);
    el.downloadBtn.addEventListener('click', downloadProject);
    el.deployBtn.addEventListener('click', deployProject);
    el.previewBtn.addEventListener('click', openPreviewTab);
    el.refreshPreviewBtn.addEventListener('click', refreshPreview);
    el.openPreviewBtn.addEventListener('click', openPreviewTab);
    if (el.editToggleBtn) {
        el.editToggleBtn.addEventListener('click', function () {
            switchMode('code');
            if (monacoEditor) {
                monacoEditor.focus();
            } else if (el.fallbackTextarea) {
                el.fallbackTextarea.focus();
            }
            toast('Code editor active');
        });
    }
    if (el.saveCodeBtn) {
        el.saveCodeBtn.addEventListener('click', function () {
            applyCodeChanges();
            saveProject();
        });
    }
    el.applyCodeBtn.addEventListener('click', applyCodeChanges);
    if (el.copyCodeBtn) {
        el.copyCodeBtn.addEventListener('click', copyActiveFileCode);
    }
    el.analyzeBtn.addEventListener('click', function () { analyzeQuality(false); });
    el.improveBtn.addEventListener('click', improveWithAI);
    el.addFileBtn.addEventListener('click', openNewFileDialog);
    el.formatBtn.addEventListener('click', formatActiveFile);
    el.renameFileBtn.addEventListener('click', function () {
        var current = activeFile;
        var newName = window.prompt('Rename file:', current);
        if (newName && newName.trim() && newName.trim() !== current) {
            renameFile(current, newName.trim());
        }
    });
    el.deleteFileBtn.addEventListener('click', function () { deleteFile(activeFile); });

    /* New-file modal */
    $$('[data-close-newfile]').forEach(function (btn) {
        btn.addEventListener('click', hideNewFileModal);
    });
    el.newFileModal.addEventListener('click', function (e) {
        if (e.target === el.newFileModal) hideNewFileModal();
    });
    el.newFileCreateBtn.addEventListener('click', createFile);
    el.newFileNameInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') { e.preventDefault(); createFile(); }
    });

    /* --- Builder workspace prompt: Enter sends, Ctrl+Enter also sends --- */
    if (el.prompt) {
        el.prompt.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                console.log('[Nexus] Ctrl+Enter on builder prompt');
                sendPrompt();
            } else if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                console.log('[Nexus] Enter on builder prompt');
                sendPrompt();
            }
        });
    }

    /* --- Builder workspace chips --- */
    el.chips.forEach(function (chip) {
        chip.addEventListener('click', function () {
            var templateName = (chip.textContent || '').trim();
            var prompt = chip.getAttribute('data-prompt') || '';
            console.log('[Nexus] Builder chip selected:', templateName);

            /* Remove previous selection in the same group */
            var parent = chip.parentElement;
            if (parent) {
                parent.querySelectorAll('.nb-chip-active').forEach(function (c) {
                    c.classList.remove('nb-chip-active');
                });
            }
            chip.classList.add('nb-chip-active');
            el.prompt.value = prompt;
            el.prompt.focus();
            /* Pulse animation */
            chip.style.transform = 'scale(0.95)';
            setTimeout(function () { chip.style.transform = ''; }, 150);
        });
    });

    el.deviceBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            setDevice(btn.getAttribute('data-device'));
        });
    });

    el.railBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            switchMode(btn.getAttribute('data-mode'));
        });
    });

    el.projectName.addEventListener('input', function () {
        currentWebsiteState.website_name = el.projectName.value.trim() || 'My AI Website';
    });

    /* ---------- Version modals ---------- */
    $$('[data-close-versions]').forEach(function (btn) {
        btn.addEventListener('click', function () { el.versionsModal.style.display = 'none'; });
    });
    $$('[data-close-restore]').forEach(function (btn) {
        btn.addEventListener('click', function () { el.restoreModal.style.display = 'none'; pendingRestoreId = ''; });
    });
    el.versionsModal.addEventListener('click', function (e) {
        if (e.target === el.versionsModal) el.versionsModal.style.display = 'none';
    });
    el.restoreModal.addEventListener('click', function (e) {
        if (e.target === el.restoreModal) el.restoreModal.style.display = 'none';
    });
    el.versionsList.addEventListener('click', function (e) {
        var btn = e.target.closest('.nb-version-restore');
        if (btn) askRestoreVersion(btn.getAttribute('data-version'), btn.getAttribute('data-label'));
    });
    el.restoreConfirmBtn.addEventListener('click', restoreVersion);

    /* ---------- Init ---------- */

    // Initialize generation status (preview panel)
    _initGenStatus();

    var initialProjectId = window.__INITIAL_PROJECT_ID || '';
    if (initialProjectId) {
        switchToBuilder();
        loadProject(initialProjectId);
    } else if (el.landingPrompt) {
        el.landingPrompt.focus();
    }

    renderChatHistory();
    syncFilesFromState();
    renderFileTree();
    renderTabs();
    setDevice('desktop');

    console.log('[Nexus] Builder v2 initialized successfully');
})();