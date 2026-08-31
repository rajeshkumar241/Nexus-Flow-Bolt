/* =========================================================
   NEXUS FLOW - LIVE WEBSITE PREVIEW COMPONENT
   Reusable preview panel that reads from NexusPreviewStore.
   Mount into any container: NexusLiveWebsitePreview.mount(el, opts)
   ========================================================= */
(function () {
    'use strict';

    var $ = function (sel, root) { return (root || document).querySelector(sel); };
    function escHtml(s) { var d = document.createElement('div'); d.appendChild(document.createTextNode(s)); return d.innerHTML; }

    /* ── Active instances ───────────────────────────────── */
    var _instances = [];

    /**
     * Mount a LiveWebsitePreview into a container element.
     * @param {HTMLElement} container - DOM element to render into
     * @param {Object} opts - Options: { showGenerating, showEmpty, emptyMessage, compact }
     */
    function mount(container, opts) {
        if (!container) return null;
        opts = opts || {};

        var inst = {
            container: container,
            opts: opts,
            _els: {},
            _unsubscribe: null,
            _currentDevice: 'desktop'
        };

        _buildDOM(inst);
        _render(inst, window.NexusPreviewStore ? window.NexusPreviewStore.getState() : { hasContent: false });

        // Subscribe to store changes
        if (window.NexusPreviewStore) {
            inst._unsubscribe = window.NexusPreviewStore.subscribe(function (state) {
                _render(inst, state);
            });
        }

        _instances.push(inst);
        return inst;
    }

    /**
     * Unmount a preview instance and clean up.
     * @param {Object} inst - The instance returned by mount()
     */
    function unmount(inst) {
        if (!inst) return;
        if (inst._unsubscribe) inst._unsubscribe();
        inst.container.innerHTML = '';
        var idx = _instances.indexOf(inst);
        if (idx !== -1) _instances.splice(idx, 1);
    }

    /* ── DOM Construction ───────────────────────────────── */

    function _buildDOM(inst) {
        var c = inst.container;
        c.innerHTML = '';
        c.classList.add('lwp-preview');

        // Toolbar
        var toolbar = _el('div', 'lwp-toolbar');

        var devices = _el('div', 'lwp-devices');
        var deviceBtns = [
            { device: 'desktop', icon: 'fa-desktop', title: 'Desktop (1440px)' },
            { device: 'tablet', icon: 'fa-tablet-screen-button', title: 'Tablet (768px)' },
            { device: 'mobile', icon: 'fa-mobile-screen-button', title: 'Mobile (390px)' }
        ];
        inst._els.deviceBtns = [];
        deviceBtns.forEach(function (d) {
            var btn = _el('button', 'lwp-device-btn' + (d.device === 'desktop' ? ' active' : ''));
            btn.setAttribute('data-device', d.device);
            btn.setAttribute('title', d.title);
            btn.innerHTML = '<i class="fa-solid ' + d.icon + '"></i>';
            btn.addEventListener('click', function () { _setDevice(inst, d.device); });
            devices.appendChild(btn);
            inst._els.deviceBtns.push(btn);
        });

        var actions = _el('div', 'lwp-actions');
        var refreshBtn = _el('button', 'lwp-icon-btn');
        refreshBtn.setAttribute('title', 'Refresh preview');
        refreshBtn.innerHTML = '<i class="fa-solid fa-rotate"></i>';
        refreshBtn.addEventListener('click', function () { _refresh(inst); });
        var openBtn = _el('button', 'lwp-icon-btn');
        openBtn.setAttribute('title', 'Open in new tab');
        openBtn.innerHTML = '<i class="fa-solid fa-arrow-up-right-from-square"></i>';
        openBtn.addEventListener('click', function () { _openTab(inst); });

        actions.appendChild(refreshBtn);
        actions.appendChild(openBtn);
        toolbar.appendChild(devices);
        toolbar.appendChild(actions);

        // Stage
        var stage = _el('div', 'lwp-stage');

        var frameWrap = _el('div', 'lwp-frame-wrap');
        frameWrap.setAttribute('data-device', 'desktop');
        var frame = _el('iframe', 'lwp-frame');
        frame.setAttribute('title', 'Live Website Preview');
        frame.setAttribute('sandbox', 'allow-scripts allow-forms allow-popups allow-modals allow-downloads allow-presentation');
        frameWrap.appendChild(frame);

        var emptyState = _el('div', 'lwp-empty');
        emptyState.innerHTML = '<i class="fa-solid fa-globe"></i>' +
            '<p>' + (opts.emptyMessage || 'Your live preview will appear here.<br>Describe your website to get started.') + '</p>';

        var generatingState = _el('div', 'lwp-generating');
        generatingState.style.display = 'none';
        generatingState.innerHTML =
            '<div class="lwp-gen-skeleton">' +
            '<div class="lwp-skel-nav"><div class="lwp-skel-bar w80"></div><div class="lwp-skel-bar w40"></div></div>' +
            '<div class="lwp-skel-hero">' +
            '<div class="lwp-skel-line w60 h2"></div>' +
            '<div class="lwp-skel-line w90 h1"></div>' +
            '<div class="lwp-skel-line w40 h1"></div>' +
            '</div>' +
            '<div class="lwp-skel-cards">' +
            '<div class="lwp-skel-card"><div class="lwp-skel-bar w100"></div><div class="lwp-skel-bar w70"></div></div>' +
            '<div class="lwp-skel-card"><div class="lwp-skel-bar w100"></div><div class="lwp-skel-bar w60"></div></div>' +
            '<div class="lwp-skel-card"><div class="lwp-skel-bar w100"></div><div class="lwp-skel-bar w80"></div></div>' +
            '</div>' +
            '</div>' +
            '<div class="lwp-gen-status">' +
            '<div class="lwp-gen-dot"></div>' +
            '<span class="lwp-gen-text">Generating website...</span>' +
            '</div>';

        var errorState = _el('div', 'lwp-error');
        errorState.style.display = 'none';
        errorState.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i>' +
            '<span class="lwp-error-msg"></span>';

        stage.appendChild(frameWrap);
        stage.appendChild(emptyState);
        stage.appendChild(generatingState);
        stage.appendChild(errorState);

        c.appendChild(toolbar);
        c.appendChild(stage);

        inst._els.frame = frame;
        inst._els.frameWrap = frameWrap;
        inst._els.emptyState = emptyState;
        inst._els.generatingState = generatingState;
        inst._els.errorState = errorState;
        inst._els.errorMsg = errorState.querySelector('.lwp-error-msg');
        inst._els.stage = stage;
    }

    /* ── Rendering ──────────────────────────────────────── */

    function _render(inst, state) {
        if (!inst._els.frame) return;

        var hasContent = state.hasContent;
        var generating = state.generating;
        var error = state.error;

        // Error state
        if (error) {
            inst._els.errorState.style.display = '';
            inst._els.errorMsg.textContent = error;
            inst._els.frameWrap.style.display = 'none';
            inst._els.emptyState.style.display = 'none';
            inst._els.generatingState.style.display = 'none';
            return;
        }

        // Generating state
        if (generating && !hasContent) {
            inst._els.generatingState.style.display = '';
            inst._els.frameWrap.style.display = 'none';
            inst._els.emptyState.style.display = 'none';
            inst._els.errorState.style.display = 'none';
            return;
        }

        // Empty state
        if (!hasContent) {
            inst._els.emptyState.style.display = '';
            inst._els.frameWrap.style.display = 'none';
            inst._els.generatingState.style.display = 'none';
            inst._els.errorState.style.display = 'none';
            return;
        }

        // Show preview
        inst._els.emptyState.style.display = 'none';
        inst._els.generatingState.style.display = 'none';
        inst._els.errorState.style.display = 'none';
        inst._els.frameWrap.style.display = '';

        // Update iframe using Blob URL
        try {
            var doc = window.NexusPreviewStore ? window.NexusPreviewStore.getPreviewDocument() : '';
            if (doc) {
                if (inst._currentBlobUrl) {
                    try { URL.revokeObjectURL(inst._currentBlobUrl); } catch (e) {}
                }
                var blob = new Blob([doc], { type: 'text/html;charset=utf-8' });
                inst._currentBlobUrl = URL.createObjectURL(blob);
                inst._els.frame.src = inst._currentBlobUrl;
            }
        } catch (err) {
            console.error('[LiveWebsitePreview] Render error:', err);
            var msg = 'Preview generation failed: ' + (err.message || err);
            inst._els.errorState.style.display = '';
            inst._els.errorMsg.textContent = msg;
            inst._els.frameWrap.style.display = 'none';
        }
    }

    /* ── Device switching ───────────────────────────────── */

    function _setDevice(inst, device) {
        inst._currentDevice = device;
        inst._els.frameWrap.setAttribute('data-device', device);
        inst._els.deviceBtns.forEach(function (btn) {
            btn.classList.toggle('active', btn.getAttribute('data-device') === device);
        });
    }

    /* ── Refresh ────────────────────────────────────────── */

    function _refresh(inst) {
        if (!window.NexusPreviewStore) return;
        var state = window.NexusPreviewStore.getState();
        if (!state.hasContent) return;
        _render(inst, state);
    }

    /* ── Open in new tab ────────────────────────────────── */

    function _openTab(inst) {
        if (!window.NexusPreviewStore || !window.NexusPreviewStore.hasContent()) return;
        try {
            var doc = window.NexusPreviewStore.getPreviewDocument();
            var blob = new Blob([doc], { type: 'text/html;charset=utf-8' });
            var url = URL.createObjectURL(blob);
            var win = window.open(url, '_blank');
            if (!win) { URL.revokeObjectURL(url); return; }
            setTimeout(function () { URL.revokeObjectURL(url); }, 60000);
        } catch (err) {
            console.error('[LiveWebsitePreview] Open tab error:', err);
        }
    }

    /* ── Helpers ────────────────────────────────────────── */

    function _el(tag, className) {
        var e = document.createElement(tag);
        if (className) e.className = className;
        return e;
    }

    /* ── Expose globally ───────────────────────────────── */
    window.NexusLiveWebsitePreview = {
        mount: mount,
        unmount: unmount
    };

})();
