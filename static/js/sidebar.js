/* =========================================================
   NEXUS FLOW AI - REFACTORED SIDEBAR INTERACTIVE SCRIPT
   ========================================================= */

(function () {
    const SIDEBAR_KEY = "nexus_sidebar_collapsed";

    function initSidebar() {
        const sidebar = document.getElementById("appSidebar") || document.querySelector(".app-sidebar") || document.querySelector(".sidebar");
        const hamburgerBtn = document.getElementById("hamburgerBtn") || document.querySelector(".hamburger-toggle-btn");
        const collapseBtn = document.getElementById("sidebarCollapseBtn");
        const mobileMenuBtn = document.getElementById("mobileMenuBtn");
        const overlay = document.getElementById("sidebarOverlay") || document.querySelector(".sidebar-overlay");

        if (!sidebar) return;

        // Restore collapsed state from localStorage on Desktop
        function applySavedState() {
            const isCollapsed = localStorage.getItem(SIDEBAR_KEY) === "true";
            if (window.innerWidth >= 768) {
                sidebar.classList.toggle("collapsed", isCollapsed);
                document.body.classList.toggle("sidebar-collapsed", isCollapsed);
            } else {
                sidebar.classList.remove("collapsed");
                document.body.classList.remove("sidebar-collapsed");
            }
        }

        applySavedState();

        function toggleSidebar() {
            if (window.innerWidth < 768) {
                // Mobile: Drawer slide-in
                const isMobileOpen = sidebar.classList.toggle("mobile-open");
                if (overlay) overlay.classList.toggle("active", isMobileOpen);
            } else {
                // Desktop: Toggle collapsed width (280px <-> 80px)
                const isCollapsed = sidebar.classList.toggle("collapsed");
                document.body.classList.toggle("sidebar-collapsed", isCollapsed);
                localStorage.setItem(SIDEBAR_KEY, isCollapsed ? "true" : "false");

                // Trigger window resize event for Monaco Editor & responsive components
                window.dispatchEvent(new Event('resize'));
            }
        }

        // Attach listeners to all toggle buttons
        [hamburgerBtn, collapseBtn, mobileMenuBtn].forEach(btn => {
            if (btn) {
                btn.addEventListener("click", (e) => {
                    e.preventDefault();
                    toggleSidebar();
                });
            }
        });

        // Close Mobile Drawer when clicking overlay
        if (overlay) {
            overlay.addEventListener("click", () => {
                sidebar.classList.remove("mobile-open");
                overlay.classList.remove("active");
            });
        }

        // Handle Responsive Window Resize
        let resizeTimer;
        window.addEventListener("resize", () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                if (window.innerWidth >= 768) {
                    sidebar.classList.remove("mobile-open");
                    if (overlay) overlay.classList.remove("active");
                    const isCollapsed = localStorage.getItem(SIDEBAR_KEY) === "true";
                    sidebar.classList.toggle("collapsed", isCollapsed);
                    document.body.classList.toggle("sidebar-collapsed", isCollapsed);
                } else {
                    sidebar.classList.remove("collapsed");
                    document.body.classList.remove("sidebar-collapsed");
                }
            }, 100);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initSidebar);
    } else {
        initSidebar();
    }
})();
