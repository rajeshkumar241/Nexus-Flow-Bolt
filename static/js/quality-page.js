/* =========================================================
   NEXUS FLOW - QUALITY PAGE
   Dedicated code quality dashboard with ML analysis,
   issue tracking, and AI improvement.
   ========================================================= */
(function () {
    'use strict';

    var $ = function (sel, root) { return (root || document).querySelector(sel); };
    var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

    var API = {
        qualityAnalyze: '/api/code-quality/analyze',
        project: function (id) { return '/builder/project/' + encodeURIComponent(id); },
        generate: '/api/generate-website',
    };

    /* ── State ──────────────────────────────────────────── */
    var activeProjectId = window.__INITIAL_PROJECT_ID || localStorage.getItem('nexus_current_project') || '';
    var lastQuality = null;
    var lastQualityBeforeImprove = null;
    var qualityImproveActive = false;

    /* ── DOM refs ───────────────────────────────────────── */
    var el = {
        projectName: $('#nbQualityProjectName'),
        projectBadge: $('#nbQualityProjectBadge'),
        analyzeBtn: $('#nbQualityAnalyzeBtn'),
        improveBtn: $('#nbQualityImproveBtn'),
        focus: $('#nbQualityFocus'),
        score: $('#nbQualityScore'),
        level: $('#nbQualityLevel'),
        conf: $('#nbQualityConf'),
        ringFill: $('#nbQualityRingFill'),
        modelName: $('#nbQualityModelName'),
        modelStatus: $('#nbQualityModelStatus'),
        sections: $('#nbQualitySections'),
        issues: $('#nbQualityIssues'),
        issueCount: $('#nbQualityIssueCount'),
        compare: $('#nbQualityCompare'),
        meta: $('#nbQualityMeta'),
        previewContainer: $('#nbQualityPreviewContainer'),
        toast: $('#nbToast'),
        toastMsg: $('#nbToastMsg'),
    };

    /* ── Shared Preview ─────────────────────────────────── */
    var _previewInstance = null;

    /* ── Helpers ────────────────────────────────────────── */
    function escHtml(s) { var d = document.createElement('div'); d.appendChild(document.createTextNode(s)); return d.innerHTML; }

    function toast(msg, isError) {
        if (!el.toast) return;
        el.toast.className = 'nb-toast' + (isError ? ' nb-toast-error' : '');
        el.toastMsg.textContent = msg;
        el.toast.style.display = 'flex';
        clearTimeout(el.toast._t);
        el.toast._t = setTimeout(function () { el.toast.style.display = 'none'; }, 3000);
    }

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

    /* ── Ring Animation ─────────────────────────────────── */
    function setRing(score) {
        var circumference = 2 * Math.PI * 54; // r=54
        var pct = Math.max(0, Math.min(100, score || 0));
        var offset = circumference - (pct / 100) * circumference;
        if (el.ringFill) el.ringFill.style.strokeDashoffset = offset;
    }

    /* ── Quality Rendering ──────────────────────────────── */
    function renderQualityResult(result) {
        lastQuality = result;
        var score = result.quality_score != null ? result.quality_score : '--';
        var scoreNum = typeof result.quality_score === 'number' ? result.quality_score : 0;

        el.score.textContent = score;
        el.score.className = 'nb-quality-score ' + qualityLevelClass(result.quality_level);
        el.level.textContent = result.quality_level || 'Not analyzed';
        el.level.className = 'nb-quality-level ' + qualityLevelClass(result.quality_level);
        el.conf.textContent = (result.quality_level && typeof result.confidence === 'number')
            ? 'Model confidence ' + Math.round(result.confidence * 100) + '%'
            : '';
        setRing(scoreNum);

        // Update ring color class
        var ringCard = el.score.closest('.nb-quality-score-card');
        if (ringCard) {
            ringCard.className = 'nb-quality-score-card ' + qualityLevelClass(result.quality_level);
        }

        renderQualitySections(result.sections);
        renderIssues(result.issues || []);

        var now = new Date();
        el.meta.textContent = 'Analyzed at ' +
            ('0' + now.getHours()).slice(-2) + ':' +
            ('0' + now.getMinutes()).slice(-2) + ':' +
            ('0' + now.getSeconds()).slice(-2);

        el.improveBtn.disabled = false;
    }

    function renderQualitySections(sections) {
        if (!sections || !sections.length) {
            el.sections.innerHTML = '<div class="nb-q-section nb-q-section-pending"><i class="fa-solid fa-minus-circle"></i><span>No data</span></div>';
            return;
        }
        el.sections.innerHTML = sections.map(function (s) {
            var cls = 'nb-q-section';
            if (s.status === 'good' || s.status === 'ok') cls += ' nb-q-section-good';
            else if (s.status === 'warning' || s.status === 'warn') cls += ' nb-q-section-warn';
            else if (s.status === 'error' || s.status === 'bad') cls += ' nb-q-section-bad';
            else cls += ' nb-q-section-pending';
            return '<div class="' + cls + '">' +
                '<i class="fa-solid ' + sectionIcon(s.key) + '"></i>' +
                '<span>' + escHtml(s.title || s.key) + '</span>' +
                '</div>';
        }).join('');
    }

    function renderIssues(issues) {
        if (!issues.length) {
            el.issues.innerHTML = '<div class="nb-quality-empty"><i class="fa-solid fa-circle-check"></i><p>No issues detected - great job!</p></div>';
            el.issueCount.textContent = '';
            return;
        }
        el.issueCount.textContent = issues.length + ' issue' + (issues.length === 1 ? '' : 's');
        el.issues.innerHTML = issues.map(function (i) {
            var sev = i.severity || 'info';
            return '<div class="nb-issue nb-issue-' + escHtml(sev) + '">' +
                '<div class="nb-issue-icon"><i class="fa-solid ' + issueIcon(sev) + '"></i></div>' +
                '<div class="nb-issue-body">' +
                '<div class="nb-issue-msg">' + escHtml(i.message) + '</div>' +
                (i.file ? '<div class="nb-issue-file">' + escHtml(i.file) + '</div>' : '') +
                (i.section ? '<span class="nb-issue-section">' + escHtml(i.section) + '</span>' : '') +
                '</div></div>';
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
            : (delta > 0 ? '<i class="fa-solid fa-arrow-trend-up nb-cmp-up"></i>'
                : (delta < 0 ? '<i class="fa-solid fa-arrow-trend-down nb-cmp-down"></i>'
                    : '<i class="fa-solid fa-equals nb-cmp-eq"></i>'));
        var deltaLabel = delta === null ? '' : (delta > 0 ? '+' + delta : String(delta));

        el.compare.innerHTML =
            '<div class="nb-cmp-head"><i class="fa-solid fa-arrow-right-arrow-left"></i> Before vs After</div>' +
            '<div class="nb-cmp-cols">' +
            '<div class="nb-cmp-col"><div class="nb-cmp-label">Before</div>' +
            '<div class="nb-cmp-score ' + qualityLevelClass(before.quality_level) + '">' + escHtml(bs) + '</div>' +
            '<div class="nb-cmp-level">' + escHtml(before.quality_level || '') + '</div></div>' +
            '<div class="nb-cmp-arrow">' + arrow + (deltaLabel ? ' <span class="nb-cmp-delta">' + deltaLabel + '</span>' : '') + '</div>' +
            '<div class="nb-cmp-col"><div class="nb-cmp-label">After</div>' +
            '<div class="nb-cmp-score ' + qualityLevelClass(after.quality_level) + '">' + escHtml(as) + '</div>' +
            '<div class="nb-cmp-level">' + escHtml(after.quality_level || '') + '</div></div>' +
            '</div>';
        el.compare.style.display = 'block';
    }

    /* ── Analyze ────────────────────────────────────────── */
    function analyzeQuality(isAuto) {
        // Read code from the shared preview store
        var html = '', css = '', js = '';
        if (window.NexusPreviewStore) {
            html = window.NexusPreviewStore.getHtml();
            css = window.NexusPreviewStore.getCss();
            js = window.NexusPreviewStore.getJs();
        }

        if (!html && !css && !js) {
            el.level.textContent = 'No code to analyze';
            el.score.textContent = '--';
            if (!isAuto) toast('No code to analyze - generate a website first', true);
            return;
        }

        if (!isAuto) {
            el.analyzeBtn.disabled = true;
            el.score.textContent = '...';
            el.score.className = 'nb-quality-score';
            el.level.textContent = 'Analyzing...';
            el.level.className = 'nb-quality-level';
            el.conf.textContent = '';
            el.issues.innerHTML = '<div class="nb-quality-empty"><p>Running the ML analyzer...</p></div>';
            el.meta.textContent = '';
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
                    console.error('[QualityPage] Backend error:', err, res.j);
                    el.level.textContent = 'Analysis failed';
                    el.score.textContent = '--';
                    el.score.className = 'nb-quality-score nb-q-low';
                    el.issues.innerHTML =
                        '<div class="nb-quality-empty">' +
                        '<i class="fa-solid fa-circle-exclamation"></i>' +
                        '<p>' + escHtml(err) + '</p>' +
                        '<button class="nb-btn nb-btn-ghost nb-quality-retry-btn" onclick="document.getElementById(\'nbQualityAnalyzeBtn\').click()">' +
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
                console.error('[QualityPage] Network error:', err);
                el.level.textContent = 'Analysis failed';
                el.score.textContent = '--';
                el.score.className = 'nb-quality-score nb-q-low';
                el.issues.innerHTML =
                    '<div class="nb-quality-empty">' +
                    '<i class="fa-solid fa-plug-circle-xmark"></i>' +
                    '<p>Connection error: ' + escHtml(err.message || 'Could not reach server') + '</p>' +
                    '<button class="nb-btn nb-btn-ghost nb-quality-retry-btn" onclick="document.getElementById(\'nbQualityAnalyzeBtn\').click()">' +
                    '<i class="fa-solid fa-rotate-right"></i> Retry</button>' +
                    '</div>';
                if (!isAuto) toast('Analysis error: ' + err.message, true);
            });
    }

    /* ── Init ───────────────────────────────────────────── */
    function init() {
        // Mount shared preview component
        if (window.NexusLiveWebsitePreview && el.previewContainer) {
            _previewInstance = window.NexusLiveWebsitePreview.mount(el.previewContainer, {
                emptyMessage: 'Generate a website in the Builder to see a live preview here.'
            });
        }

        el.analyzeBtn.addEventListener('click', function () { analyzeQuality(false); });

        if (activeProjectId) {
            el.projectBadge.textContent = 'Project loaded';
        }
    }

    document.addEventListener('DOMContentLoaded', init);
})();
