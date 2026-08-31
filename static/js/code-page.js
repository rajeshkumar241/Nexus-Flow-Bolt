/* =========================================================
   NEXUS FLOW - CODE PAGE
   Dedicated code editor workspace with Monaco, file tree,
   SSE live streaming, and preview.
   ========================================================= */
(function () {
    'use strict';

    var $ = function (sel, root) { return (root || document).querySelector(sel); };
    var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

    var API = {
        save: '/builder/save',
        project: function (id) { return '/builder/project/' + encodeURIComponent(id); },
        generateStream: '/api/generate/stream',
        qualityAnalyze: '/api/code-quality/analyze',
    };

    var FILE_ICONS = { html: 'fa-html5', css: 'fa-css3-alt', js: 'fa-square-js', json: 'fa-brackets-curly', md: 'fa-file-lines', default: 'fa-file' };
    var CORE_FILES = ['index.html', 'styles.css', 'script.js'];

    /* ── State ──────────────────────────────────────────── */
    var activeProjectId = window.__INITIAL_PROJECT_ID || localStorage.getItem('nexus_current_project') || '';
    var files = [];          // [{id, name, language, content}]
    var activeFile = 'index.html';
    var activeFileId = null;
    var openTabs = {};
    var dirtyFiles = {};
    var monaco = null, monacoReady = false, monacoEditor = null, monacoLoadAttempted = false;
    var models = {};
    var currentModel = null;
    var suppressDirty = false;
    var nextIdCounter = 1;

    /* ── DOM refs ───────────────────────────────────────── */
    var el = {
        projectName: $('#nbCodeProjectName'),
        projectBadge: $('#nbCodeProjectBadge'),
        saveBtn: $('#nbCodeSaveBtn'),
        downloadBtn: $('#nbCodeDownloadBtn'),
        fileTree: $('#nbFileTree'),
        fileCount: $('#nbFileCount'),
        editorTabs: $('#nbEditorTabs'),
        activeFileName: $('#nbActiveFileName'),
        monaco: $('#nbMonaco'),
        fallbackEditor: $('#nbFallbackEditor'),
        fallbackTextarea: $('#nbFallbackTextarea'),
        statusLanguage: $('#nbStatusLanguage'),
        statusLn: $('#nbStatusLn'),
        unsavedBadge: $('#nbUnsavedBadge'),
        applyCodeBtn: $('#nbApplyCodeBtn'),
        copyCodeBtn: $('#nbCopyCodeBtn'),
        formatBtn: $('#nbFormatBtn'),
        renameFileBtn: $('#nbRenameFileBtn'),
        deleteFileBtn: $('#nbDeleteFileBtn'),
        addFileBtn: $('#nbAddFileBtn'),
        newFileModal: $('#nbNewFileModal'),
        newFileNameInput: $('#nbNewFileNameInput'),
        newFileTypeSelect: $('#nbNewFileTypeSelect'),
        newFileCreateBtn: $('#nbNewFileCreateBtn'),
        previewContainer: $('#nbCodePreviewContainer'),
        emptyState: $('#nbCodeEmpty'),
        toast: $('#nbToast'),
        toastMsg: $('#nbToastMsg'),
    };

    /* ── Shared Preview ─────────────────────────────────── */
    var _previewInstance = null;

    /* ── Helpers ────────────────────────────────────────── */
    function escHtml(s) { var d = document.createElement('div'); d.appendChild(document.createTextNode(s)); return d.innerHTML; }

    function fileIcon(name) {
        var ext = (name || '').split('.').pop().toLowerCase();
        return FILE_ICONS[ext] || FILE_ICONS.default;
    }

    function fileNameLang(name) {
        var ext = (name || '').split('.').pop().toLowerCase();
        var map = { html: 'html', css: 'css', js: 'javascript', json: 'json', md: 'markdown' };
        return map[ext] || 'plaintext';
    }

    function toast(msg, isError) {
        if (!el.toast) return;
        el.toast.className = 'nb-toast' + (isError ? ' nb-toast-error' : '');
        el.toastMsg.textContent = msg;
        el.toast.style.display = 'flex';
        clearTimeout(el.toast._t);
        el.toast._t = setTimeout(function () { el.toast.style.display = 'none'; }, 3000);
    }

    function nextId() { return 'f_' + (nextIdCounter++); }

    function fileList() { return files.map(function (f) { return f.name; }).sort(); }
    function openedFileList() { return Object.keys(openTabs); }
    function getFile(name) { return files.find(function (f) { return f.name === name; }) || null; }

    function readFileContent(name) {
        if (monaco && monacoReady && models[name]) return models[name].getValue();
        var f = getFile(name);
        return f ? f.content : '';
    }

    function syncStateFromEditors() {
        files.forEach(function (f) {
            if (monaco && monacoReady && models[f.name]) {
                f.content = models[f.name].getValue();
            }
        });
    }

    function markDirty(name) {
        if (suppressDirty) return;
        dirtyFiles[name] = true;
        el.unsavedBadge.style.display = '';
        renderFileTree();
        renderTabs();
    }

    function markClean(name) {
        delete dirtyFiles[name];
        el.unsavedBadge.style.display = Object.keys(dirtyFiles).length ? '' : 'none';
        renderFileTree();
        renderTabs();
    }

    /* ── File Tree ──────────────────────────────────────── */
    function renderFileTree() {
        var names = fileList();
        el.fileTree.innerHTML = '';
        names.forEach(function (name) {
            var item = document.createElement('div');
            item.className = 'nb-file-item' + (name === activeFile ? ' active' : '');
            var dirty = dirtyFiles[name] ? '<span class="nb-file-dirty" title="Unsaved"><i class="fa-solid fa-circle"></i></span>' : '';
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
            if (opened.length) { openFile(opened[opened.length - 1]); }
            else { var all = fileList(); openFile(all[all.length - 1] || 'index.html'); }
        } else { renderTabs(); }
    }

    function deleteFile(name) {
        if (CORE_FILES.indexOf(name) !== -1) { toast('Core files cannot be deleted', true); return; }
        var f = getFile(name);
        if (!f) return;
        if (!window.confirm('Delete ' + name + '?')) return;
        files = files.filter(function (x) { return x.name !== name; });
        delete openTabs[name];
        delete dirtyFiles[name];
        if (monaco && monacoReady && models[name]) { models[name].dispose(); delete models[name]; }
        if (activeFile === name) {
            var opened = openedFileList();
            if (opened.length) { openFile(opened[opened.length - 1]); }
            else { var all = fileList(); openFile(all.length ? all[all.length - 1] : 'index.html'); }
        } else { renderFileTree(); renderTabs(); }
        toast('Deleted ' + name);
    }

    function renameFile(name, newName) {
        if (!newName || newName === name) return;
        if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(newName)) { toast('Invalid file name', true); return; }
        var f = getFile(name);
        if (!f || getFile(newName)) { toast('File exists', true); return; }
        var content = readFileContent(name);
        f.name = newName;
        f.language = fileNameLang(newName);
        delete dirtyFiles[name];
        if (monaco && monacoReady) {
            if (models[name]) { models[name].dispose(); delete models[name]; }
            models[newName] = monaco.editor.createModel(content, f.language, monaco.Uri.parse('file:///' + newName));
            models[newName].onDidChangeContent(function () { markDirty(newName); });
        }
        if (openTabs[name]) { delete openTabs[name]; openTabs[newName] = true; }
        if (activeFile === name) {
            activeFile = newName;
            currentModel = models[newName] || null;
            if (monacoEditor && currentModel) monacoEditor.setModel(currentModel);
            if (!monacoReady) el.fallbackTextarea.value = content;
            updateStatusLanguage();
        }
        renderFileTree();
        renderTabs();
        toast('Renamed to ' + newName);
    }

    /* ── Monaco Editor ──────────────────────────────────── */
    function initMonaco() {
        if (monacoLoadAttempted) return;
        monacoLoadAttempted = true;
        if (typeof window.require === 'undefined') { useFallbackEditor(); return; }
        window.require.config({ paths: { vs: '/static/vendor/monaco/min/vs' } });
        var loaded = false;
        var failTimer = setTimeout(function () { if (!loaded) useFallbackEditor(); }, 9000);
        window.require(['vs/editor/editor.main'], function () {
            loaded = true;
            clearTimeout(failTimer);
            monaco = window.monaco;
            monacoReady = true;
            el.fallbackEditor.style.display = 'none';
            el.monaco.style.display = 'block';
            el.monaco.innerHTML = '';
            monaco.editor.defineTheme('nb-dark', {
                base: 'vs-dark', inherit: true, rules: [],
                colors: { 'editor.background': '#0d1220' }
            });
            monaco.editor.setTheme('nb-dark');
            rebuildModels();
            monacoEditor = monaco.editor.create(el.monaco, {
                model: currentModel || models[activeFile] || null,
                automaticLayout: true, fontSize: 13,
                minimap: { enabled: true }, scrollBeyondLastLine: false,
                wordWrap: 'off', tabSize: 2, theme: 'nb-dark',
                language: fileNameLang(activeFile)
            });
            if (currentModel) monacoEditor.setModel(currentModel);
            monacoEditor.onCursorPositionChanged(function (e) {
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
                    models[name] = monaco.editor.createModel(content, fileNameLang(name), monaco.Uri.parse('file:///' + name));
                    models[name].onDidChangeContent(function () { markDirty(name); });
                } else {
                    if (models[name].getValue() !== content) models[name].setValue(content);
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
            if (activeFile && fb) el.fallbackTextarea.value = fb.content || '';
        }
        renderFileTree();
        renderTabs();
    }

    function updateStatusLanguage() {
        var lang = fileNameLang(activeFile);
        var labels = { html: 'HTML', css: 'CSS', javascript: 'JavaScript', json: 'JSON', markdown: 'Markdown' };
        el.statusLanguage.innerHTML = '<i class="fa-solid fa-code"></i> ' + (labels[lang] || lang);
    }

    /* ── File operations ────────────────────────────────── */
    function openNewFileDialog() {
        el.newFileNameInput.value = '';
        el.newFileTypeSelect.value = 'html';
        el.newFileModal.style.display = 'flex';
        setTimeout(function () { el.newFileNameInput.focus(); }, 50);
    }

    function createFile() {
        var name = el.newFileNameInput.value.trim();
        var type = el.newFileTypeSelect.value || 'html';
        if (!name) { toast('Enter a file name', true); return; }
        if (name.indexOf('.') === -1) {
            var ext = { html: 'html', css: 'css', javascript: 'js', json: 'json' }[type] || 'html';
            name += '.' + ext;
        }
        if (getFile(name)) { toast('File already exists', true); return; }
        var newFile = { id: nextId(), name: name, language: fileNameLang(name), content: '' };
        files.push(newFile);
        if (monaco && monacoReady) {
            models[name] = monaco.editor.createModel('', newFile.language, monaco.Uri.parse('file:///' + name));
            models[name].onDidChangeContent(function () { markDirty(name); });
        }
        el.newFileModal.style.display = 'none';
        openFile(name);
        toast('Created ' + name);
    }

    function formatActiveFile() {
        var content = readFileContent(activeFile);
        if (!content) { toast('Nothing to format', true); return; }
        var lang = fileNameLang(activeFile);
        var formatted = content;
        if (lang === 'json') {
            try { formatted = JSON.stringify(JSON.parse(content), null, 2); }
            catch (e) { toast('Invalid JSON', true); return; }
        } else {
            formatted = content.split('\n').map(function (l) { return l.replace(/\s+$/, ''); }).join('\n');
        }
        if (monaco && monacoReady && models[activeFile]) { models[activeFile].setValue(formatted); }
        else { var f = getFile(activeFile); if (f) f.content = formatted; }
        markDirty(activeFile);
        toast('Formatted ' + activeFile);
    }

    function copyActiveFileCode() {
        var content = readFileContent(activeFile);
        if (!content) { toast('Nothing to copy', true); return; }
        var done = function () { toast('Copied to clipboard'); };
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(content).then(done).catch(function () { fallbackCopy(content, done); });
        } else { fallbackCopy(content, done); }
    }

    function fallbackCopy(text, done) {
        var ta = document.createElement('textarea');
        ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
        document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy'); } catch (e) { /* ignore */ }
        document.body.removeChild(ta);
        if (done) done();
    }

    /* ── Preview ────────────────────────────────────────── */
    function renderPreview() {
        // Sync all files to the shared store — the component will update automatically
        if (window.NexusPreviewStore) {
            var fileMap = {};
            files.forEach(function (f) { fileMap[f.name] = readFileContent(f.name); });
            window.NexusPreviewStore.setContent(fileMap);
        }
    }

    /* ── Save / Apply / Download ────────────────────────── */
    function syncState() {
        syncStateFromEditors();
        var state = {
            files: {},
            html: readFileContent('index.html') || '',
            css: readFileContent('styles.css') || '',
            javascript: readFileContent('script.js') || '',
            project_id: activeProjectId
        };
        files.forEach(function (f) { state.files[f.name] = readFileContent(f.name); });
        return state;
    }

    function applyCodeChanges() {
        syncStateFromEditors();
        renderPreview();
        var state = syncState();
        fetch(API.save, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ state: state, project_id: activeProjectId || null })
        })
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
            .then(function (res) {
                if (!res.ok || !res.j.success) { toast((res.j && res.j.error) || 'Save failed', true); return; }
                activeProjectId = res.j.project_id;
                localStorage.setItem('nexus_current_project', activeProjectId);
                Object.keys(dirtyFiles).forEach(function (k) { markClean(k); });
                toast('Code applied and saved');
            })
            .catch(function (err) { toast('Save error: ' + err.message, true); });
    }

    function saveProject() {
        syncStateFromEditors();
        var state = syncState();
        fetch(API.save, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ state: state, project_id: activeProjectId || null })
        })
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
            .then(function (res) {
                if (!res.ok || !res.j.success) { toast((res.j && res.j.error) || 'Save failed', true); return; }
                activeProjectId = res.j.project_id;
                localStorage.setItem('nexus_current_project', activeProjectId);
                Object.keys(dirtyFiles).forEach(function (k) { markClean(k); });
                renderPreview();
                toast('Project saved');
            })
            .catch(function (err) { toast('Save error: ' + err.message, true); });
    }

    function downloadProject() {
        if (!activeProjectId) { toast('Save the project first', true); return; }
        window.location.href = '/download/zip/' + encodeURIComponent(activeProjectId);
    }

    /* ── Load Project ───────────────────────────────────── */
    function loadProject(id) {
        fetch(API.project(id))
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
            .then(function (res) {
                if (!res.ok || !res.j.success) { toast((res.j && res.j.error) || 'Could not load project', true); return; }
                applyStateToUI(res.j.state);
                toast('Project loaded');
            })
            .catch(function (err) { toast('Load error: ' + err.message, true); });
    }

    function applyStateToUI(state) {
        if (!state) return;
        files = [];
        nextIdCounter = 1;
        var src = state.files || {};
        if (!Object.keys(src).length && state.html) {
            src = { 'index.html': state.html, 'styles.css': state.css || '', 'script.js': state.javascript || '' };
        }
        Object.keys(src).sort().forEach(function (name) {
            files.push({ id: nextId(), name: name, language: fileNameLang(name), content: src[name] || '' });
        });
        if (!files.length) {
            CORE_FILES.forEach(function (name) {
                files.push({ id: nextId(), name: name, language: fileNameLang(name), content: '' });
            });
        }
        activeFile = 'index.html';
        openTabs = {};
        dirtyFiles = {};
        models = {};
        el.unsavedBadge.style.display = 'none';
        rebuildModels();
        openFile('index.html');
        // Sync to shared preview store
        renderPreview();
        if (state.website_name) el.projectName.textContent = state.website_name;
        el.projectBadge.textContent = activeProjectId ? 'Loaded' : 'New';
        el.emptyState.style.display = 'none';
    }

    /* ── Init ───────────────────────────────────────────── */
    function init() {
        // Mount shared preview component
        if (window.NexusLiveWebsitePreview && el.previewContainer) {
            _previewInstance = window.NexusLiveWebsitePreview.mount(el.previewContainer, {
                emptyMessage: 'No project loaded. Generate a website in the Builder, then come here to edit the code.'
            });
        }

        // Wire up buttons
        el.saveBtn.addEventListener('click', saveProject);
        el.downloadBtn.addEventListener('click', downloadProject);
        el.applyCodeBtn.addEventListener('click', applyCodeChanges);
        el.copyCodeBtn.addEventListener('click', copyActiveFileCode);
        el.formatBtn.addEventListener('click', formatActiveFile);
        el.addFileBtn.addEventListener('click', openNewFileDialog);
        el.newFileCreateBtn.addEventListener('click', createFile);

        // Close new file modal
        $$('[data-close-newfile]').forEach(function (btn) {
            btn.addEventListener('click', function () { el.newFileModal.style.display = 'none'; });
        });

        // Rename file
        el.renameFileBtn.addEventListener('click', function () {
            var newName = window.prompt('Rename ' + activeFile + ' to:', activeFile);
            if (newName) renameFile(activeFile, newName);
        });

        // Delete file
        el.deleteFileBtn.addEventListener('click', function () { deleteFile(activeFile); });

        // Monaco
        initMonaco();

        // Load project if we have an ID
        if (activeProjectId) {
            loadProject(activeProjectId);
        }
    }

    document.addEventListener('DOMContentLoaded', init);
})();
