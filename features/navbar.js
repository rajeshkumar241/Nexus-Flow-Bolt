/**
 * Nexus Flow - Responsive Navigation Feature Module
 * Mobile menu toggle and closes menu after selecting a link.
 * 
 * Required HTML:
 *   <header class="navbar">
 *     <nav class="nav-container">
 *       <a href="index.html" class="logo">Logo</a>
 *       <nav class="nav-links">
 *         <a href="index.html">Home</a>
 *         <a href="menu.html">Menu</a>
 *       </nav>
 *       <button class="nav-toggle" id="navToggle" aria-label="Toggle navigation">
 *         <i class="fa-solid fa-bars"></i>
 *       </button>
 *     </nav>
 *   </header>
 * 
 * The nav-links container gets class 'active' when the mobile menu is open.
 */
(function () {
  'use strict';

  const TOGGLE_ID = 'navToggle';
  const NAV_LINKS_SELECTOR = '.nav-links';

  function initNavbar() {
    const toggle = document.getElementById(TOGGLE_ID);
    const navLinks = document.querySelector(NAV_LINKS_SELECTOR);

    if (!toggle || !navLinks) return;

    // Toggle menu
    toggle.addEventListener('click', function () {
      navLinks.classList.toggle('active');
      toggle.classList.toggle('active');
      const isOpen = navLinks.classList.contains('active');
      toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      toggle.setAttribute('aria-label', isOpen ? 'Close navigation' : 'Open navigation');
      const icon = toggle.querySelector('i');
      if (icon) {
        icon.className = isOpen ? 'fa-solid fa-xmark' : 'fa-solid fa-bars';
      }
    });

    // Close menu when a link is clicked
    navLinks.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        navLinks.classList.remove('active');
        toggle.classList.remove('active');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.setAttribute('aria-label', 'Open navigation');
        const icon = toggle.querySelector('i');
        if (icon) {
          icon.className = 'fa-solid fa-bars';
        }
      });
    });

    // Close menu when clicking outside
    document.addEventListener('click', function (e) {
      if (navLinks.classList.contains('active')) {
        const isInside = navLinks.contains(e.target) || toggle.contains(e.target);
        if (!isInside) {
          navLinks.classList.remove('active');
          toggle.classList.remove('active');
          toggle.setAttribute('aria-expanded', 'false');
        }
      }
    });
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNavbar);
  } else {
    initNavbar();
  }
})();