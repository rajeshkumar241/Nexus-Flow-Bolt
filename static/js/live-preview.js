/* =========================================================
   NEXUS FLOW - LIVE CODE GENERATION PREVIEW
   Real-time AI code streaming with file tree, typewriter
   effect, and live preview during website generation.
   ========================================================= */
(function () {
    'use strict';

    var $ = function (sel, root) { return (root || document).querySelector(sel); };
    var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

    /* ── State ──────────────────────────────────────────── */
    var _active = false;
    var _container = null;
    var _sse = null;
    var _files = {};          // filename -> accumulated content
    var _fileOrder = [];      // ordered list of filenames as they arrive
    var _currentFile = null;  // which file is currently being "typed"
    var _typeTimer = null;
    var _charIndex = 0;
    var _steps = [];
    var _onComplete = null;   // callback when streaming finishes
    var _onFileReady = null;  // callback(filename, content) for each completed file
    var _previewFrame = null;

    /* ── DOM refs (created dynamically) ────────────────── */
    var _els = {};

    /* ── Configuration ─────────────────────────────────── */
    var CHARS_PER_TICK = 3;       // characters added per animation frame
    var TICK_INTERVAL = 12;       // ms between characters (~250 chars/sec)
    var FILE_DELAY_MS = 80;       // pause between files

    /* ── File type icons ───────────────────────────────── */
    var FILE_ICONS = {
        html: 'fa-html5',
        css: 'fa-css3-alt',
        js: 'fa-square-js',
        json: 'fa-brackets-curly',
        md: 'fa-file-lines',
        default: 'fa-file-code'
    };

    function _iconFor(filename) {
        var ext = (filename || '').split('.').pop().toLowerCase();
        return FILE_ICONS[ext] || FILE_ICONS.default;
    }

    /* ── Public API ────────────────────────────────────── */

    /**
     * Mount the live preview into a container element.
     * @param {HTMLElement} container - The DOM element to render into
     * @param {Object} opts - Options: { onComplete, onFileReady, previewFrame }
     */
    function mount(container, opts) {
        _container = container;
        _onComplete = (opts && opts.onComplete) || null;
        _onFileReady = (opts && opts.onFileReady) || null;
        _previewFrame = (opts && opts.previewFrame) || null;

        _buildDOM();
    }

    /**
     * Start streaming generation via SSE.
     * @param {Object} payload - { prompt, website_name, website_type, project_id, generation_mode }
     */
    function startStream(payload) {
        if (_active) stopStream();

        _active = true;
        _files = {};
        _fileOrder = [];
        _currentFile = null;
        _steps = [];
        _charIndex = 0;

        _clearDOM();
        _showState('streaming');

        // Build SSE URL with query params for POST body
        var url = '/api/generate/stream';

        // Use fetch + ReadableStream for SSE (supports POST)
        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(function (response) {
            if (!response.ok) {
                throw new Error('Server returned ' + response.status);
            }
            var reader = response.body.getReader();
            var decoder = new TextDecoder();
            var buffer = '';

            function read() {
                return reader.read().then(function (result) {
                    if (result.done) {
                        _finishStreaming();
                        return;
                    }

                    buffer += decoder.decode(result.value, { stream: true });

                    // Process complete SSE messages
                    var lines = buffer.split('\n');
                    buffer = lines.pop(); // Keep incomplete line in buffer

                    var eventType = '';
                    var dataLines = [];

                    for (var i = 0; i < lines.length; i++) {
                        var line = lines[i];
                        if (line.indexOf('event: ') === 0) {
                            eventType = line.substring(7).trim();
                        } else if (line.indexOf('data: ') === 0) {
                            dataLines.push(line.substring(6));
                        } else if (line === '' && eventType && dataLines.length) {
                            // End of SSE message
                            _handleEvent(eventType, dataLines.join('\n'));
                            eventType = '';
                            dataLines = [];
                        }
                    }

                    return read();
                });
            }

            return read();
        }).catch(function (err) {
            console.error('[LivePreview] Stream error:', err);
            _showError(err.message || 'Connection failed');
        });
    }

    /**
     * Stop the current stream and clean up.
     */
    function stopStream() {
        _active = false;
        if (_typeTimer) { clearInterval(_typeTimer); _typeTimer = null; }
        if (_sse) { _sse.close(); _sse = null; }
    }

    /**
     * Get the current state.
     */
    function isActive() { return _active; }
    function getFiles() { return Object.assign({}, _files); }

    /* ── Event handling ────────────────────────────────── */

    function _handleEvent(type, dataStr) {
        var data;
        try {
            data = JSON.parse(dataStr);
        } catch (e) {
            console.warn('[LivePreview] Failed to parse SSE data:', dataStr.substring(0, 100));
            return;
        }

        switch (type) {
            case 'start':
                _onStart(data);
                break;
            case 'step':
                _onStep(data);
                break;
            case 'file':
                _onFile(data);
                break;
            case 'preview':
                _onPreview(data);
                break;
            case 'done':
                _onDone(data);
                break;
            case 'error':
                _onError(data);
                break;
        }
    }

    function _onStart(data) {
        _updateStatus('Analyzing your request...', 'fa-solid fa-magnifying-glass');
        _addStep('Analyzing request', 'running');
    }

    function _onStep(data) {
        var label = data.label || data.step || '';
        var icon = data.icon || 'fa-solid fa-cog';
        _updateStatus(label, icon);

        // Update step states
        var completedSteps = data.completed_steps || [];
        _steps.forEach(function (s) {
            if (completedSteps.indexOf(s.id) !== -1) {
                s.status = 'completed';
            } else if (s.id === data.step) {
                s.status = 'running';
            } else {
                s.status = 'pending';
            }
        });
        _renderSteps();

        // Show progress percentage
        if (data.percentage !== undefined) {
            _updateProgress(data.percentage);
        }
    }

    function _onFile(data) {
        var filename = data.filename;
        var content = data.content;
        var index = data.index || 0;
        var total = data.total || 1;

        // Add file to tree
        if (_fileOrder.indexOf(filename) === -1) {
            _fileOrder.push(filename);
        }
        _files[filename] = content;

        _renderFileTree();
        _updateFileProgress(index + 1, total);

        // Start typewriter effect for this file
        _typeFile(filename, content);
    }

    var _currentStreamBlobUrl = null;

    function _onPreview(data) {
        var previewHtml = data.preview;
        if (previewHtml && _previewFrame) {
            try {
                if (_currentStreamBlobUrl) {
                    try { URL.revokeObjectURL(_currentStreamBlobUrl); } catch (e) {}
                }
                var blob = new Blob([previewHtml], { type: 'text/html;charset=utf-8' });
                _currentStreamBlobUrl = URL.createObjectURL(blob);
                _previewFrame.src = _currentStreamBlobUrl;
            } catch (e) {
                _previewFrame.srcdoc = previewHtml;
            }
        }
    }

    function _onDone(data) {
        // Finish any remaining typewriter
        if (_typeTimer) { clearInterval(_typeTimer); _typeTimer = null; }

        // Show all files complete
        _fileOrder.forEach(function (f) {
            _markFileComplete(f);
        });
        _renderFileTree();

        _updateStatus('Generation complete!', 'fa-solid fa-check-circle');
        _updateProgress(100);
        _showState('done');

        _active = false;

        if (_onComplete) {
            _onComplete(data);
        }
    }

    function _onError(data) {
        _showError(data.error || 'Generation failed');
        _active = false;
    }

    /* ── Typewriter effect & Progress display ─────────────────────────────── */

    function _renderAsciiBar(pct) {
        var totalBlocks = 10;
        var filled = Math.min(totalBlocks, Math.max(0, Math.round((pct / 100) * totalBlocks)));
        var empty = totalBlocks - filled;
        var bar = '';
        for (var i = 0; i < filled; i++) bar += '█';
        for (var j = 0; j < empty; j++) bar += '░';
        return bar + ' ' + pct + '%';
    }

    var _fileProgressMap = {};

    function _updateCurrentlyCreating(filename, pct) {
        if (!_els.creatingList) return;
        _fileProgressMap[filename] = pct;

        var html = '';
        Object.keys(_fileProgressMap).forEach(function (f) {
            var p = _fileProgressMap[f];
            var isCurrent = f === _currentFile;
            html += '<div class="lc-creating-row' + (isCurrent ? ' active' : '') + '">';
            html += '<div class="lc-creating-file-meta"><i class="fa-solid fa-file-code"></i> <span class="lc-c-fname">' + _escHtml(f) + '</span></div>';
            html += '<div class="lc-creating-bar-wrap"><span class="lc-c-ascii">' + _renderAsciiBar(p) + '</span></div>';
            html += '</div>';
        });
        _els.creatingList.innerHTML = html;
    }

    function _typeFile(filename, content) {
        // Stop previous typewriter
        if (_typeTimer) { clearInterval(_typeTimer); _typeTimer = null; }

        _currentFile = filename;
        _charIndex = 0;
        _markFileActive(filename);
        _updateCurrentlyCreating(filename, 0);

        // Clear the code viewer for this file
        _setCodeContent('');

        // Type character by character
        _typeTimer = setInterval(function () {
            if (_charIndex >= content.length) {
                clearInterval(_typeTimer);
                _typeTimer = null;
                _markFileComplete(filename);
                _renderFileTree();
                _updateCurrentlyCreating(filename, 100);
                return;
            }

            var chunk = content.substring(_charIndex, _charIndex + CHARS_PER_TICK);
            _charIndex += CHARS_PER_TICK;
            _appendCodeContent(chunk);

            var pct = Math.min(99, Math.round((_charIndex / (content.length || 1)) * 100));
            _updateCurrentlyCreating(filename, pct);

            // Auto-scroll to bottom of code viewer
            _scrollCodeToBottom();
        }, TICK_INTERVAL);
    }

    /* ── DOM construction ──────────────────────────────── */

    function _buildDOM() {
        _container.innerHTML = '';
        _container.classList.add('lc-live-container');

        // Status bar
        _els.statusBar = _el('div', 'lc-status-bar');
        _els.statusIcon = _el('i', 'lc-status-icon');
        _els.statusText = _el('span', 'lc-status-text');
        _els.statusText.textContent = 'Waiting to generate...';
        _els.statusBar.appendChild(_els.statusIcon);
        _els.statusBar.appendChild(_els.statusText);

        // Progress bar
        _els.progressWrap = _el('div', 'lc-progress-wrap');
        _els.progressFill = _el('div', 'lc-progress-fill');
        _els.progressWrap.appendChild(_els.progressFill);
        _els.progressLabel = _el('span', 'lc-progress-label');
        _els.progressWrap.appendChild(_els.progressLabel);

        // Steps timeline
        _els.stepsContainer = _el('div', 'lc-steps');

        // File progress
        _els.fileProgress = _el('div', 'lc-file-progress');
        _els.fileProgressText = _el('span', 'lc-file-progress-text');
        _els.fileProgress.appendChild(_els.fileProgressText);

        // Currently creating panel (real-time generation display)
        _els.creatingPanel = _el('div', 'lc-creating-panel');
        _els.creatingTitle = _el('div', 'lc-creating-title');
        _els.creatingTitle.innerHTML = '<i class="fa-solid fa-code"></i> Currently creating:';
        _els.creatingList = _el('div', 'lc-creating-list');
        _els.creatingPanel.appendChild(_els.creatingTitle);
        _els.creatingPanel.appendChild(_els.creatingList);

        // Main split: file tree + code viewer
        _els.split = _el('div', 'lc-split');

        // File tree
        _els.fileTreeWrap = _el('div', 'lc-filetree');
        _els.fileTreeHead = _el('div', 'lc-filetree-head');
        _els.fileTreeHead.innerHTML = '<i class="fa-solid fa-folder-tree"></i> Files';
        _els.fileTreeBody = _el('div', 'lc-filetree-body');
        _els.fileTreeWrap.appendChild(_els.fileTreeHead);
        _els.fileTreeWrap.appendChild(_els.fileTreeBody);

        // Code viewer
        _els.codeViewerWrap = _el('div', 'lc-code-viewer');
        _els.codeViewerHead = _el('div', 'lc-code-head');
        _els.codeFileName = _el('span', 'lc-code-filename');
        _els.codeFileName.textContent = 'Waiting for files...';
        _els.codeViewerHead.appendChild(_els.codeFileName);
        _els.codeViewerBody = _el('div', 'lc-code-body');
        _els.codeContent = _el('pre', 'lc-code-content');
        _els.codeViewerBody.appendChild(_els.codeContent);

        _els.codeViewerWrap.appendChild(_els.codeViewerHead);
        _els.codeViewerWrap.appendChild(_els.codeViewerBody);

        _els.split.appendChild(_els.fileTreeWrap);
        _els.split.appendChild(_els.codeViewerWrap);

        // Assemble
        _container.appendChild(_els.statusBar);
        _container.appendChild(_els.progressWrap);
        _container.appendChild(_els.stepsContainer);
        _container.appendChild(_els.creatingPanel);
        _container.appendChild(_els.fileProgress);
        _container.appendChild(_els.split);
    }

    function _clearDOM() {
        if (_els.stepsContainer) _els.stepsContainer.innerHTML = '';
        if (_els.creatingList) _els.creatingList.innerHTML = '';
        if (_els.fileTreeBody) _els.fileTreeBody.innerHTML = '';
        if (_els.codeContent) _els.codeContent.textContent = '';
        if (_els.codeFileName) _els.codeFileName.textContent = 'Generating...';
        if (_els.progressFill) _els.progressFill.style.width = '0%';
        if (_els.progressLabel) _els.progressLabel.textContent = '';
        if (_els.statusText) _els.statusText.textContent = 'Starting...';
        if (_els.fileProgressText) _els.fileProgressText.textContent = '';
        _steps = [];
    }

    /* ── DOM helpers ───────────────────────────────────── */

    function _el(tag, className) {
        var e = document.createElement(tag);
        if (className) e.className = className;
        return e;
    }

    /* ── UI updates ────────────────────────────────────── */

    function _updateStatus(text, iconClass) {
        if (_els.statusText) _els.statusText.textContent = text;
        if (_els.statusIcon) {
            _els.statusIcon.className = 'lc-status-icon ' + (iconClass || '');
        }
    }

    function _updateProgress(pct) {
        if (_els.progressFill) _els.progressFill.style.width = pct + '%';
        if (_els.progressLabel) _els.progressLabel.textContent = pct + '%';
    }

    function _updateFileProgress(current, total) {
        if (_els.fileProgressText) {
            _els.fileProgressText.textContent = 'File ' + current + ' of ' + total;
        }
    }

    function _addStep(label, status) {
        _steps.push({ id: label, label: label, status: status });
        _renderSteps();
    }

    function _renderSteps() {
        if (!_els.stepsContainer) return;
        var html = '';
        _steps.forEach(function (s) {
            var cls = 'lc-step lc-step-' + s.status;
            var icon = s.status === 'completed' ? 'fa-solid fa-check' :
                       s.status === 'running' ? 'fa-solid fa-spinner fa-spin' :
                       'fa-regular fa-circle';
            html += '<div class="' + cls + '">';
            html += '<i class="' + icon + '"></i>';
            html += '<span>' + _escHtml(s.label) + '</span>';
            html += '</div>';
        });
        _els.stepsContainer.innerHTML = html;
    }

    function _renderFileTree() {
        if (!_els.fileTreeBody) return;
        var html = '';
        _fileOrder.forEach(function (fname) {
            var isActive = fname === _currentFile;
            var isComplete = _files[fname] && fname !== _currentFile;
            var icon = _iconFor(fname);
            var cls = 'lc-ft-item';
            if (isActive) cls += ' lc-ft-active';
            if (isComplete) cls += ' lc-ft-done';

            html += '<div class="' + cls + '" data-file="' + _escHtml(fname) + '">';
            html += '<i class="fa-brands ' + icon + ' lc-ft-icon"></i>';
            html += '<span class="lc-ft-name">' + _escHtml(fname) + '</span>';
            if (isActive) {
                html += '<span class="lc-ft-badge">typing</span>';
            } else if (isComplete) {
                html += '<i class="fa-solid fa-check lc-ft-check"></i>';
            }
            html += '</div>';
        });
        _els.fileTreeBody.innerHTML = html;
    }

    function _markFileActive(filename) {
        if (_els.codeFileName) _els.codeFileName.textContent = filename;
    }

    function _markFileComplete(filename) {
        // Visual indicator only — tree re-renders on next call
    }

    function _setCodeContent(text) {
        if (_els.codeContent) _els.codeContent.textContent = text;
    }

    function _appendCodeContent(text) {
        if (_els.codeContent) {
            _els.codeContent.textContent += text;
        }
    }

    function _scrollCodeToBottom() {
        if (_els.codeViewerBody) {
            _els.codeViewerBody.scrollTop = _els.codeViewerBody.scrollHeight;
        }
    }

    function _showState(state) {
        if (!_container) return;
        _container.setAttribute('data-state', state);
    }

    function _showError(msg) {
        _updateStatus('Error: ' + msg, 'fa-solid fa-exclamation-triangle');
        _showState('error');
    }

    function _finishStreaming() {
        // Stop any active typewriter
        if (_typeTimer) { clearInterval(_typeTimer); _typeTimer = null; }

        // Mark all files complete
        _fileOrder.forEach(function (f) {
            _markFileComplete(f);
        });
        _renderFileTree();

        // Update UI to completion state
        _updateStatus('Generation complete!', 'fa-solid fa-check-circle');
        _updateProgress(100);
        _showState('done');

        _active = false;

        // Notify caller
        if (_onComplete) {
            var f = Object.assign({}, _files);
            _onComplete({
                success: true,
                files: f,
                html: f['index.html'] || f['index.htm'] || '',
                css: f['styles.css'] || f['style.css'] || '',
                js: f['script.js'] || f['main.js'] || ''
            });
        }
    }

    function _escHtml(str) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    /* ── Expose globally ───────────────────────────────── */
    window.NexusLivePreview = {
        mount: mount,
        startStream: startStream,
        stopStream: stopStream,
        isActive: isActive,
        getFiles: getFiles,
    };

})();
