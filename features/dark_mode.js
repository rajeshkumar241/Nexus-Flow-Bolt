/**
 * Nexus Flow - Dark Mode Feature Module
 * Toggles light/dark mode and persists the user's choice using localStorage.
 * 
 * Required HTML:
 *   <button id="darkModeToggle" aria-label="Toggle dark mode">
 *     <i class="fa-solid fa-moon"></i>
 *   </button>
 * 
 * The body element gets a 'dark-mode' class when dark mode is active.
 * CSS should define [data-theme="dark"] or body.dark-mode overrides.
 */
(function () {
  'use strict';

  const STORAGE_KEY = 'nexus-dark-mode';
  const TOGGLE_ID = 'darkModeToggle';

  function getStoredPreference() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored !== null) {
        return stored === 'true';
      }
    } catch (e) {
      // localStorage unavailable
    }
    // Default to system preference
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function applyDarkMode(isDark) {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    document.body.classList.toggle('dark-mode', isDark);

    // Update toggle icon
    const toggle = document.getElementById(TOGGLE_ID);
    if (toggle) {
      const icon = toggle.querySelector('i');
      if (icon) {
        icon.className = isDark ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
      }
      toggle.setAttribute('aria-pressed', isDark ? 'true' : 'false');
      toggle.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
    }
  }

  function initDarkMode() {
    const toggle = document.getElementById(TOGGLE_ID);
    if (!toggle) return;

    // Apply stored preference on load
    applyDarkMode(getStoredPreference());

    toggle.addEventListener('click', function () {
      const isDark = !document.body.classList.contains('dark-mode');
      applyDarkMode(isDark);
      try {
        localStorage.setItem(STORAGE_KEY, isDark ? 'true' : 'false');
      } catch (e) {
        // localStorage unavailable
      }
    });
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDarkMode);
  } else {
    initDarkMode();
  }
})();