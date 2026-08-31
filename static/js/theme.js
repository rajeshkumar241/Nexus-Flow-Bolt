/* =========================================================
   NEXUS FLOW AI - GLOBAL THEME SCRIPT
   Handles accent color (blue/purple/green/red/custom) AND
   dark/light/system mode switching.
   Runs in <head> to prevent flash-of-wrong-theme.
   ========================================================= */

(function () {
    const THEME_COLOR_KEY = "nexus_theme_color";
    const THEME_VALUE_KEY = "nexus_theme_value";
    const THEME_MODE_KEY  = "nexus_theme_mode";

    /* --- Helpers --- */
    function hexToRgb(hex) {
        const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec((hex || "").trim());
        if (!m) return [59, 130, 246];
        return [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)];
    }

    function getServerAttr(name) {
        return document.documentElement.getAttribute(name) || "";
    }

    /* --- Read saved preferences --- */
    function getThemeColor() {
        return getServerAttr("data-theme-color") || localStorage.getItem(THEME_COLOR_KEY) || "blue";
    }

    function getThemeValue() {
        return getServerAttr("data-theme-value") || localStorage.getItem(THEME_VALUE_KEY) || "";
    }

    function getThemeMode() {
        var server = getServerAttr("data-theme-mode");
        if (server) return server;
        var stored = localStorage.getItem(THEME_MODE_KEY);
        if (stored) return stored;
        // Default: respect OS preference
        return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "dark";
    }

    /* --- Apply accent color --- */
    function applyAccentColor(color, value) {
        var root = document.documentElement;
        var themeColor = color || "blue";
        root.setAttribute("data-theme-color", themeColor);

        if (value) {
            root.style.setProperty("--custom-accent", value);
            root.style.setProperty("--custom-accent-rgb", hexToRgb(value).join(", "));
            localStorage.setItem(THEME_VALUE_KEY, value);
        }
        localStorage.setItem(THEME_COLOR_KEY, themeColor);

        // Sync Settings UI theme cards
        var themeRadios = document.querySelectorAll(".nx-theme-card");
        themeRadios.forEach(function (card) {
            var isActive = card.getAttribute("data-theme-color") === themeColor;
            card.classList.toggle("selected", isActive);
            var radio = card.querySelector("input[type='radio']");
            if (radio) radio.checked = isActive;
        });

        var customWrapper = document.getElementById("customColorWrapper");
        if (customWrapper) customWrapper.style.display = themeColor === "custom" ? "flex" : "none";

        var customSwatch = document.getElementById("customSwatch");
        if (customSwatch) customSwatch.style.background = value || "#3b82f6";
    }

    /* --- Apply dark/light/system mode --- */
    function applyThemeMode(mode) {
        var root = document.documentElement;
        var resolved = mode || "dark";

        if (mode === "system") {
            resolved = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
        }

        root.setAttribute("data-theme", resolved);
        localStorage.setItem(THEME_MODE_KEY, mode || "dark");

        // Sync Settings UI mode selector
        document.querySelectorAll(".nx-mode-card").forEach(function (card) {
            card.classList.toggle("selected", card.getAttribute("data-theme-mode") === mode);
        });

        // Update theme meta tag for mobile browsers
        var meta = document.querySelector('meta[name="theme-color"]');
        if (meta) {
            meta.content = resolved === "dark" ? "#070b16" : "#f8fafc";
        }
    }

    /* --- Apply immediately (before DOMContentLoaded) --- */
    applyThemeMode(getThemeMode());
    applyAccentColor(getThemeColor(), getThemeValue());

    /* --- Re-apply on DOM ready --- */
    document.addEventListener("DOMContentLoaded", function () {
        applyThemeMode(getThemeMode());
        applyAccentColor(getThemeColor(), getThemeValue());

        // Listen for OS theme changes when in system mode
        window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
            if (getThemeMode() === "system") {
                applyThemeMode("system");
            }
        });
    });

    /* --- Exposed globally for Settings page --- */
    window.applyNexusTheme = function (color, value) {
        applyAccentColor(color || "blue", value || "");
    };

    window.applyNexusThemeMode = function (mode) {
        applyThemeMode(mode || "dark");
    };
})();
