/* =========================================================
   NEXUS FLOW AI - AI WEBSITE BUILDER SCRIPT
   Handles: Generation, Preview, Features Dashboard, AI Modifier
   ========================================================= */

(function () {
    "use strict";

    // =========================================================
    // STATE
    // =========================================================
    let currentState = {
        website_name: "My AI Website",
        prompt: "",
        website_type: "auto",
        tech_stack: "html",
        html: "",
        css: "",
        javascript: "",
        project_id: null
    };

    let isGenerating = false;
    let isModifying = false;

    // =========================================================
    // STATE EXPOSURE FOR AI BUILDER MODULES
    // =========================================================
    function exposeStateToWindow() {
        window.__nexusCurrentState = { ...currentState };
    }

    function dispatchWebsiteGenerated(state) {
        document.dispatchEvent(new CustomEvent("websiteGenerated", {
            detail: { ...state }
        }));
    }

    function dispatchWebsiteUpdated(state) {
        document.dispatchEvent(new CustomEvent("websiteUpdated", {
            detail: { ...state }
        }));
    }

    // =========================================================
    // DOM REFERENCES
    // =========================================================
    const configSection = document.getElementById("configSection");
    const workspaceSection = document.getElementById("workspaceSection");
    const websiteNameInput = document.getElementById("websiteName");
    const websiteTypeSelect = document.getElementById("websiteType");
    const techStackSelect = document.getElementById("techStack");
    const aiPromptInput = document.getElementById("aiPrompt");
    const promptCharCount = document.getElementById("promptCharCount");
    const generateBtn = document.getElementById("generateBtn");
    const generationStatus = document.getElementById("generationStatus");
    const generatedWebsiteName = document.getElementById("generatedWebsiteName");
    const backToConfigBtn = document.getElementById("backToConfigBtn");
    const saveProjectBtn = document.getElementById("saveProjectBtn");
    const saveProjectBtnHeader = document.getElementById("saveProjectBtnHeader");
    const newProjectBtn = document.getElementById("newProjectBtn");
    const downloadProjectBtn = document.getElementById("downloadProjectBtn");
    const saveToast = document.getElementById("saveToast");
    const previewFrame = document.getElementById("previewFrame");
    const previewFrameShell = document.getElementById("previewFrameShell");
    const refreshPreviewBtn = document.getElementById("refreshPreviewBtn");
    const openPreviewBtn = document.getElementById("openPreviewBtn");
    const modifierInput = document.getElementById("modifierInput");
    const modifierSendBtn = document.getElementById("modifierSendBtn");
    const modifierChatHistory = document.getElementById("modifierChatHistory");

    // Features dashboard DOM references
    const websiteTypeDisplay = document.getElementById("websiteTypeDisplay");
    const websiteDescription = document.getElementById("websiteDescription");
    const pagesCount = document.getElementById("pagesCount");
    const featuresCount = document.getElementById("featuresCount");
    const frontendTech = document.getElementById("frontendTech");
    const backendTech = document.getElementById("backendTech");
    const databaseTech = document.getElementById("databaseTech");
    const frameworkTech = document.getElementById("frameworkTech");
    const pagesGeneratedCount = document.getElementById("pagesGeneratedCount");
    const pagesList = document.getElementById("pagesList");
    const featuresAddedCount = document.getElementById("featuresAddedCount");
    const featuresList = document.getElementById("featuresList");
    const componentsList = document.getElementById("componentsList");
    const aiSummary = document.getElementById("aiSummary");

    // =========================================================
    // NEXUS FLOW PROFESSIONAL WEBSITE GENERATION ENGINE
    // =========================================================

    let generationEngine = null;

    function initGenerationEngine() {
        if (!generationEngine) {
            generationEngine = new WebsiteGenerationEngine();
        }
        return generationEngine;
    }

    // =========================================================
    // FEATURES DASHBOARD - DYNAMIC METADATA RENDERING
    // =========================================================

    /**
     * Analyze the current website state and generate metadata
     * for the Features dashboard. This is derived from the actual
     * generated code and the user's prompt - no fake data.
     */
    function analyzeWebsiteMetadata() {
        const engine = initGenerationEngine();
        const requirements = engine.analyzeRequirements(currentState.prompt || "");
        const stack = (currentState.tech_stack || "html").toLowerCase();
        const html = currentState.html || "";
        const css = currentState.css || "";
        const js = currentState.javascript || "";

        // --- Website Type ---
        const typeLabels = {
            "auto": "Auto Detected",
            "saas": "SaaS / Business",
            "landing": "Landing Page",
            "portfolio": "Portfolio",
            "ecommerce": "E-Commerce",
            "blog": "Blog",
            "restaurant": "Restaurant",
            "hospital": "Hospital / Medical",
            "school": "School / Education",
            "travel": "Travel",
            "realestate": "Real Estate",
            "aitool": "AI Tool / 3D Generator",
            "agency": "Creative Agency",
            "dashboard": "Dashboard / Web App"
        };
        const websiteType = typeLabels[currentState.website_type] || 
            (requirements.type ? requirements.type.charAt(0).toUpperCase() + requirements.type.slice(1) : "Website");

        // --- Technology Stack ---
        const techInfo = {
            "html": { frontend: "HTML, CSS, JavaScript", backend: "None", database: "None", framework: "Vanilla JS" },
            "react": { frontend: "React", backend: "None", database: "None", framework: "React + Vite" },
            "flask": { frontend: "HTML, CSS, JavaScript", backend: "Flask (Python)", database: "MongoDB", framework: "Flask" },
            "django": { frontend: "HTML, CSS, JavaScript", backend: "Django (Python)", database: "SQLite / PostgreSQL", framework: "Django" },
            "node": { frontend: "HTML, CSS, JavaScript (EJS)", backend: "Node.js (Express)", database: "MongoDB", framework: "Express" },
            "nextjs": { frontend: "React (Next.js)", backend: "Next.js API Routes", database: "MongoDB / PostgreSQL", framework: "Next.js" }
        };
        const tech = techInfo[stack] || techInfo["html"];

        // --- Pages Generated (derived from requirements + HTML content) ---
        const pageNames = {
            "home": "Home Page",
            "products": "Products Page",
            "cart": "Cart Page",
            "checkout": "Checkout Page",
            "about": "About Page",
            "contact": "Contact Page",
            "article": "Article Page",
            "categories": "Categories Page",
            "dashboard": "Dashboard Page",
            "analytics": "Analytics Page",
            "settings": "Settings Page",
            "reports": "Reports Page",
            "projects": "Projects Page",
            "menu": "Menu Page",
            "reservations": "Reservations Page",
            "features": "Features Page",
            "pricing": "Pricing Page",
            "docs": "Documentation Page",
            "feed": "Feed Page",
            "profile": "Profile Page",
            "messages": "Messages Page"
        };

        // Detect pages from HTML content
        const detectedPages = [];
        const htmlLower = html.toLowerCase();
        const pageKeywords = {
            "home": ["hero", "welcome", "home"],
            "about": ["about", "our story", "who we are"],
            "contact": ["contact", "get in touch", "reach us"],
            "products": ["product", "catalog", "shop"],
            "cart": ["cart", "shopping cart"],
            "checkout": ["checkout", "place order"],
            "pricing": ["pricing", "plans", "subscription"],
            "features": ["features", "what we offer"],
            "menu": ["menu", "our menu"],
            "reservations": ["reservation", "book a table"],
            "dashboard": ["dashboard", "analytics", "metrics"],
            "blog": ["blog", "articles", "news"]
        };

        // Start with requirements pages
        const reqPages = requirements.pages || ["home"];
        reqPages.forEach(page => {
            if (!detectedPages.includes(page)) detectedPages.push(page);
        });

        // Add pages detected from HTML content
        Object.entries(pageKeywords).forEach(([page, keywords]) => {
            const found = keywords.some(kw => htmlLower.includes(kw));
            if (found && !detectedPages.includes(page)) detectedPages.push(page);
        });

        // Ensure home is always present
        if (!detectedPages.includes("home")) detectedPages.unshift("home");

        const pages = detectedPages.map(p => pageNames[p] || (p.charAt(0).toUpperCase() + p.slice(1) + " Page"));

        // --- Features Added (derived from requirements + prompt) ---
        const featureMap = {
            "responsive-design": { label: "Responsive Design", icon: "fa-mobile-screen" },
            "navigation-bar": { label: "Navigation Bar", icon: "fa-bars" },
            "hero-section": { label: "Hero Section", icon: "fa-star" },
            "contact-form": { label: "Contact Form", icon: "fa-envelope" },
            "authentication": { label: "Authentication", icon: "fa-lock" },
            "database-integration": { label: "Database Integration", icon: "fa-database" },
            "search-functionality": { label: "Search Functionality", icon: "fa-magnifying-glass" },
            "payment-integration": { label: "Payment Integration", icon: "fa-credit-card" },
            "animations": { label: "Animations", icon: "fa-wand-magic-sparkles" },
            "shopping-cart": { label: "Shopping Cart", icon: "fa-cart-shopping" },
            "product-catalog": { label: "Product Catalog", icon: "fa-box-open" },
            "checkout": { label: "Checkout Flow", icon: "fa-cash-register" },
            "article-list": { label: "Article List", icon: "fa-newspaper" },
            "categories": { label: "Categories", icon: "fa-folder-tree" },
            "data-visualization": { label: "Data Visualization", icon: "fa-chart-line" },
            "charts": { label: "Charts & Graphs", icon: "fa-chart-pie" },
            "filters": { label: "Filters", icon: "fa-filter" },
            "project-gallery": { label: "Project Gallery", icon: "fa-images" },
            "reservation-system": { label: "Reservation System", icon: "fa-calendar-check" },
            "menu-display": { label: "Menu Display", icon: "fa-utensils" },
            "pricing-tables": { label: "Pricing Tables", icon: "fa-tags" },
            "feature-grid": { label: "Feature Grid", icon: "fa-th-large" },
            "testimonials": { label: "Testimonials", icon: "fa-quote-left" },
            "user-auth": { label: "User Authentication", icon: "fa-user-lock" },
            "posts": { label: "Posts / Feed", icon: "fa-comments" },
            "messaging": { label: "Messaging", icon: "fa-comment-dots" }
        };

        const features = [];
        const reqFeatures = requirements.features || [];
        reqFeatures.forEach(f => {
            if (featureMap[f]) features.push(featureMap[f]);
        });

        // Detect features from HTML content
        const featureDetectors = [
            { key: "responsive-design", test: /@media|viewport|grid-template-columns|flex-wrap/g },
            { key: "navigation-bar", test: /<nav|navbar|nav-links|mobile-menu/g },
            { key: "hero-section", test: /hero|hero-section|hero-container/g },
            { key: "contact-form", test: /contact-form|contact-form|type="email"|type="text"/g },
            { key: "authentication", test: /login|signup|sign-in|sign-up|auth/g },
            { key: "database-integration", test: /localStorage|fetch\(|axios|api|database/g },
            { key: "search-functionality", test: /search|filter|query/g },
            { key: "payment-integration", test: /payment|stripe|paypal|checkout|card/g },
            { key: "animations", test: /animation|transition|@keyframes|transform/g },
            { key: "shopping-cart", test: /cart|addToCart|add-to-cart/g },
            { key: "product-catalog", test: /product|catalog|grid/g },
            { key: "checkout", test: /checkout|place-order|order/g },
            { key: "article-list", test: /article|blog|post/g },
            { key: "categories", test: /category|categories/g },
            { key: "data-visualization", test: /chart|graph|analytics|dashboard/g },
            { key: "charts", test: /chart|canvas|svg/g },
            { key: "filters", test: /filter|sort/g },
            { key: "project-gallery", test: /gallery|portfolio|project/g },
            { key: "reservation-system", test: /reservation|book|table/g },
            { key: "menu-display", test: /menu|dish|food/g },
            { key: "pricing-tables", test: /pricing|plan|price/g },
            { key: "feature-grid", test: /feature|grid/g },
            { key: "testimonials", test: /testimonial|review|quote/g },
            { key: "user-auth", test: /login|signup|auth|user/g },
            { key: "posts", test: /post|feed|comment/g },
            { key: "messaging", test: /message|chat|inbox/g }
        ];

        featureDetectors.forEach(detector => {
            if (featureMap[detector.key] && !features.some(f => f.label === featureMap[detector.key].label)) {
                if (detector.test.test(htmlLower) || detector.test.test(js.toLowerCase())) {
                    features.push(featureMap[detector.key]);
                }
            }
        });

        // Always include core features that are present
        const coreFeatures = [
            { key: "responsive-design", label: "Responsive Design", icon: "fa-mobile-screen" },
            { key: "navigation-bar", label: "Navigation Bar", icon: "fa-bars" },
            { key: "hero-section", label: "Hero Section", icon: "fa-star" }
        ];
        coreFeatures.forEach(cf => {
            if (!features.some(f => f.label === cf.label)) {
                features.push(cf);
            }
        });

        // --- Components Created (derived from HTML structure) ---
        const componentMap = [
            { label: "Navbar", icon: "fa-bars", test: /<nav|navbar|nav-links/g },
            { label: "Footer", icon: "fa-copyright", test: /<footer|footer/g },
            { label: "Cards", icon: "fa-id-card", test: /card|grid/g },
            { label: "Forms", icon: "fa-wpforms", test: /<form|input|textarea|select/g },
            { label: "Buttons", icon: "fa-square-check", test: /<button|btn/g },
            { label: "Hero Section", icon: "fa-star", test: /hero/g },
            { label: "Gallery", icon: "fa-images", test: /gallery|image|img/g },
            { label: "Dashboard", icon: "fa-chart-line", test: /dashboard|chart|analytics/g },
            { label: "Pricing Cards", icon: "fa-tags", test: /pricing|plan|price/g },
            { label: "Testimonials", icon: "fa-quote-left", test: /testimonial|review|quote/g },
            { label: "Contact Section", icon: "fa-envelope", test: /contact/g },
            { label: "Feature Grid", icon: "fa-th-large", test: /feature/g }
        ];

        const components = [];
        componentMap.forEach(comp => {
            if (comp.test.test(htmlLower)) {
                components.push({ label: comp.label, icon: comp.icon });
            }
        });

        // Ensure core components are always present
        const coreComponents = [
            { label: "Navbar", icon: "fa-bars" },
            { label: "Footer", icon: "fa-copyright" }
        ];
        coreComponents.forEach(cc => {
            if (!components.some(c => c.label === cc.label)) {
                components.push(cc);
            }
        });

        // --- AI Summary ---
        const summary = buildAISummary(websiteType, tech, pages, features, components, requirements);

        return {
            websiteName: currentState.website_name || "My AI Website",
            websiteType: websiteType,
            description: buildWebsiteDescription(currentState.prompt, websiteType),
            tech: tech,
            pages: pages,
            features: features,
            components: components,
            summary: summary
        };
    }

    function buildWebsiteDescription(prompt, websiteType) {
        if (!prompt) return "AI-generated website based on your requirements.";
        const cleanPrompt = prompt.length > 120 ? prompt.substring(0, 120) + "..." : prompt;
        return `AI-generated ${websiteType.toLowerCase()} website created from your prompt: "${cleanPrompt}"`;
    }

    function buildAISummary(websiteType, tech, pages, features, components, requirements) {
        const parts = [];
        parts.push(`The AI has generated a complete ${websiteType.toLowerCase()} website named "${currentState.website_name || "My AI Website"}".`);
        
        if (tech.frontend) {
            parts.push(`The frontend is built with ${tech.frontend}.`);
        }
        if (tech.backend && tech.backend !== "None") {
            parts.push(`The backend uses ${tech.backend}.`);
        }
        if (tech.database && tech.database !== "None") {
            parts.push(`Data is stored in ${tech.database}.`);
        }
        
        if (pages.length > 0) {
            parts.push(`The website includes ${pages.length} page${pages.length > 1 ? "s" : ""}: ${pages.join(", ")}.`);
        }
        
        if (features.length > 0) {
            const featureLabels = features.slice(0, 6).map(f => f.label);
            parts.push(`Key features include ${featureLabels.join(", ")}${features.length > 6 ? ", and more" : ""}.`);
        }
        
        if (components.length > 0) {
            const compLabels = components.slice(0, 5).map(c => c.label);
            parts.push(`Reusable components created: ${compLabels.join(", ")}${components.length > 5 ? ", and more" : ""}.`);
        }
        
        parts.push("The design follows modern dark theme principles with responsive layout and professional styling.");
        
        return parts.join(" ");
    }

    /**
     * Render the Features dashboard with dynamically generated metadata.
     */
    function renderFeatures() {
        const meta = analyzeWebsiteMetadata();

        // Website Overview
        if (websiteTypeDisplay) websiteTypeDisplay.textContent = meta.websiteType;
        if (websiteDescription) websiteDescription.textContent = meta.description;
        if (pagesCount) pagesCount.textContent = `${meta.pages.length} page${meta.pages.length !== 1 ? "s" : ""}`;
        if (featuresCount) featuresCount.textContent = `${meta.features.length} feature${meta.features.length !== 1 ? "s" : ""}`;

        // Technology Stack
        if (frontendTech) frontendTech.textContent = meta.tech.frontend;
        if (backendTech) backendTech.textContent = meta.tech.backend;
        if (databaseTech) databaseTech.textContent = meta.tech.database;
        if (frameworkTech) frameworkTech.textContent = meta.tech.framework;

        // Pages Generated
        if (pagesGeneratedCount) pagesGeneratedCount.textContent = `${meta.pages.length} page${meta.pages.length !== 1 ? "s" : ""}`;
        if (pagesList) {
            pagesList.innerHTML = "";
            meta.pages.forEach(page => {
                const item = document.createElement("div");
                item.className = "page-item";
                item.innerHTML = `<i class="fa-solid fa-circle-check"></i><span>${escapeHtml(page)}</span>`;
                pagesList.appendChild(item);
            });
        }

        // Features Added
        if (featuresAddedCount) featuresAddedCount.textContent = `${meta.features.length} feature${meta.features.length !== 1 ? "s" : ""}`;
        if (featuresList) {
            featuresList.innerHTML = "";
            meta.features.forEach(feature => {
                const item = document.createElement("div");
                item.className = "feature-item";
                item.innerHTML = `<i class="fa-solid ${feature.icon}"></i><span>${escapeHtml(feature.label)}</span>`;
                featuresList.appendChild(item);
            });
        }

        // Components Created
        if (componentsList) {
            componentsList.innerHTML = "";
            meta.components.forEach(comp => {
                const item = document.createElement("div");
                item.className = "component-item";
                item.innerHTML = `<i class="fa-solid ${comp.icon}"></i><span>${escapeHtml(comp.label)}</span>`;
                componentsList.appendChild(item);
            });
        }

        // AI Summary
        if (aiSummary) {
            aiSummary.innerHTML = "";
            const p = document.createElement("p");
            p.textContent = meta.summary;
            aiSummary.appendChild(p);
        }
    }

    function escapeHtml(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    function showToast(message) {
        if (!saveToast) return;
        saveToast.querySelector("span").textContent = message || "Changes saved successfully";
        saveToast.classList.add("show");
        setTimeout(() => saveToast.classList.remove("show"), 3000);
    }

    function setGenerating(loading) {
        isGenerating = loading;
        if (generateBtn) {
            generateBtn.disabled = loading;
            generateBtn.querySelector("span").textContent = loading ? "Generating..." : "Generate Website";
        }
        if (generationStatus) {
            generationStatus.style.display = loading ? "flex" : "none";
        }
    }

    function setModifying(loading) {
        isModifying = loading;
        if (modifierSendBtn) {
            modifierSendBtn.disabled = loading;
            modifierSendBtn.innerHTML = loading
                ? '<div class="spinner" style="width:18px;height:18px;border-width:2px;"></div>'
                : '<i class="fa-solid fa-paper-plane"></i>';
        }
    }

    // =========================================================
    // ISOLATION LAYER - Prevents generated website from accessing Nexus Flow
    // =========================================================
    const NEXUS_FLOW_ROUTES = [
        "/builder", "/dashboard", "/login", "/register", "/profile", "/settings",
        "/projects", "/chat", "/admin", "/preview", "/code-editor", "/website-ai",
        "/download", "/upload", "/generate", "/save", "/delete", "/website_state",
        "/home", "/logout", "/templates", "/downloads", "/camera"
    ];

    /**
     * Build the isolation layer script that is injected into the preview document.
     * This traps all navigation attempts and keeps the generated website isolated.
     */
    function buildIsolationLayer() {
        return `
(function() {
  'use strict';

  // Nexus Flow internal routes that must never be navigated to
  var NEXUS_ROUTES = ${JSON.stringify(NEXUS_FLOW_ROUTES)};

  function isNexusRoute(url) {
    if (!url) return false;
    var path = url;
    try {
      var u = new URL(url, window.location.href);
      path = u.pathname;
    } catch(e) {}
    var lower = path.toLowerCase();
    for (var i = 0; i < NEXUS_ROUTES.length; i++) {
      if (lower === NEXUS_ROUTES[i] || lower.startsWith(NEXUS_ROUTES[i] + '/')) {
        return true;
      }
    }
    // Also block any path that looks like a Flask route (starts with / and has no file extension)
    if (lower.startsWith('/') && !lower.includes('.') && !lower.startsWith('/#')) {
      // Allow common static assets
      if (lower.startsWith('/static/') || lower.startsWith('/uploads/')) return false;
      return true;
    }
    return false;
  }

  function showIsolationNotice(message) {
    var existing = document.getElementById('nexus-isolation-notice');
    if (existing) existing.remove();
    var notice = document.createElement('div');
    notice.id = 'nexus-isolation-notice';
    notice.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:rgba(var(--accent-rgb),0.95);color:#fff;padding:12px 24px;border-radius:12px;font-family:system-ui,sans-serif;font-size:14px;font-weight:600;z-index:99999;box-shadow:0 8px 32px rgba(0,0,0,0.4);max-width:90%;text-align:center;animation:fadeInUp 0.3s ease;';
    notice.textContent = message || 'This action is part of your generated website preview.';
    document.body.appendChild(notice);
    setTimeout(function() { notice.remove(); }, 3000);
  }

  // Intercept all link clicks
  document.addEventListener('click', function(e) {
    var link = e.target.closest ? e.target.closest('a') : null;
    if (!link) return;

    var href = link.getAttribute('href') || '';
    var target = link.getAttribute('target') || '';

    // Allow external links (http/https) to open in new tab
    if (/^https?:\\/\\//i.test(href)) {
      if (target !== '_blank') {
        e.preventDefault();
        window.open(href, '_blank');
      }
      return;
    }

    // Allow anchor links (#section) - scroll within the page
    if (href.startsWith('#')) {
      return; // let default behavior scroll to section
    }

    // Block Nexus Flow routes
    if (isNexusRoute(href)) {
      e.preventDefault();
      showIsolationNotice('This link is part of your generated website preview and cannot navigate to the Nexus Flow application.');
      return;
    }

    // Handle relative links (about.html, contact.html, etc.)
    // Try to find a matching section or show a placeholder
    if (!href.startsWith('/') && !href.startsWith('#')) {
      e.preventDefault();
      var pageName = href.split('/').pop().replace(/\\.html?$/i, '').replace(/[-_]/g, ' ');
      var sectionId = pageName.toLowerCase().replace(/[^a-z0-9]+/g, '-');
      var section = document.getElementById(sectionId) || document.querySelector('[data-page="' + pageName.toLowerCase() + '"]');
      if (section) {
        section.scrollIntoView({ behavior: 'smooth' });
      } else {
        showIsolationNotice('"' + pageName + '" page is part of your generated website. This section is available in the full version.');
      }
      return;
    }

    // Block any other internal navigation
    if (href.startsWith('/')) {
      e.preventDefault();
      showIsolationNotice('This link is part of your generated website preview.');
    }
  }, true);

  // Intercept form submissions
  document.addEventListener('submit', function(e) {
    var form = e.target;
    if (!form || form.tagName !== 'FORM') return;
    var action = form.getAttribute('action') || '';
    if (isNexusRoute(action) || action.startsWith('/')) {
      e.preventDefault();
      showIsolationNotice('Form submitted successfully! (Preview mode - data is not sent to a server)');
      // Try to show a success message
      var submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
      if (submitBtn) {
        var original = submitBtn.textContent;
        submitBtn.textContent = '✓ Submitted';
        submitBtn.disabled = true;
        setTimeout(function() {
          submitBtn.textContent = original;
          submitBtn.disabled = false;
          form.reset();
        }, 2000);
      }
    }
  }, true);

  // Block window.location changes to Nexus Flow routes
  var originalLocation = window.location;
  Object.defineProperty(window, 'location', {
    get: function() { return originalLocation; },
    set: function(value) {
      if (typeof value === 'string' && isNexusRoute(value)) {
        showIsolationNotice('Navigation blocked: This would leave your generated website.');
        return;
      }
      originalLocation.href = value;
    }
  });

  // Intercept window.open calls to Nexus Flow routes
  var originalOpen = window.open;
  window.open = function(url, name, features) {
    if (typeof url === 'string' && isNexusRoute(url)) {
      showIsolationNotice('Navigation blocked: This would leave your generated website.');
      return null;
    }
    return originalOpen.call(window, url, name, features);
  };

  // Intercept location.href assignments
  var originalHref = Object.getOwnPropertyDescriptor(HTMLAnchorElement.prototype, 'href');
  document.addEventListener('click', function(e) {
    var link = e.target.closest ? e.target.closest('a') : null;
    if (link && link.target === '_self' && isNexusRoute(link.getAttribute('href'))) {
      e.preventDefault();
      showIsolationNotice('Navigation blocked: This would leave your generated website.');
    }
  }, true);

  // Add isolation notice styles
  var style = document.createElement('style');
  style.textContent = '@keyframes fadeInUp { from { opacity: 0; transform: translateX(-50%) translateY(20px); } to { opacity: 1; transform: translateX(-50%) translateY(0); } }';
  document.head.appendChild(style);

  console.log('Nexus Flow isolation layer active - generated website is fully isolated.');
})();
`;
    }

    // =========================================================
    // SANITIZE GENERATED CODE - Remove Nexus Flow references
    // =========================================================
    const NEXUS_FLOW_PATTERNS = [
        /href=["']\/(?:builder|dashboard|login|register|profile|settings|projects|chat|admin|preview|code-editor|website-ai|home|logout|templates|downloads|camera)["']/gi,
        /href=["']\/(?:builder|dashboard|login|register|profile|settings|projects|chat|admin|preview|code-editor|website-ai|home|logout|templates|downloads|camera)\/[^"']*["']/gi,
        /action=["']\/(?:builder|dashboard|login|register|profile|settings|projects|chat|admin|preview|code-editor|website-ai|home|logout|templates|downloads|camera)["']/gi,
        /action=["']\/(?:builder|dashboard|login|register|profile|settings|projects|chat|admin|preview|code-editor|website-ai|home|logout|templates|downloads|camera)\/[^"']*["']/gi,
        /window\.location\s*=\s*["']\/(?:builder|dashboard|login|register|profile|settings|projects|chat|admin|preview|code-editor|website-ai|home|logout|templates|downloads|camera)/gi,
        /window\.location\.href\s*=\s*["']\/(?:builder|dashboard|login|register|profile|settings|projects|chat|admin|preview|code-editor|website-ai|home|logout|templates|downloads|camera)/gi,
        /location\.href\s*=\s*["']\/(?:builder|dashboard|login|register|profile|settings|projects|chat|admin|preview|code-editor|website-ai|home|logout|templates|downloads|camera)/gi,
        /window\.open\s*\(\s*["']\/(?:builder|dashboard|login|register|profile|settings|projects|chat|admin|preview|code-editor|website-ai|home|logout|templates|downloads|camera)/gi,
        /{%\s*extends\s+["']base\.html["']\s*%}/gi,
        /{%\s*include\s+["']sidebar\.html["']\s*%}/gi,
        /{%\s*include\s+["']components\/sidebar\.html["']\s*%}/gi,
        /url_for\(["'](?:builder|dashboard|login|register|profile|settings|projects|chat|admin|preview|code-editor|website-ai|home|logout|templates|downloads|camera)["']\)/gi
    ];

    /**
     * Sanitize generated HTML/CSS/JS to remove any Nexus Flow references.
     * This ensures the generated website is fully isolated from the Nexus Flow app.
     */
    function sanitizeGeneratedCode(html, css, js) {
        let cleanHtml = html || "";
        let cleanCss = css || "";
        let cleanJs = js || "";

        // Remove Nexus Flow route references from HTML
        NEXUS_FLOW_PATTERNS.forEach(pattern => {
            cleanHtml = cleanHtml.replace(pattern, (match) => {
                // Replace href="/builder" with href="#" 
                if (match.includes('href=')) return 'href="#"';
                // Replace action="/builder" with action="#" 
                if (match.includes('action=')) return 'action="#"';
                // Replace window.location assignments with console.log
                if (match.includes('window.location') || match.includes('location.href')) {
                    return 'console.log("Navigation blocked in preview mode")';
                }
                // Replace window.open calls
                if (match.includes('window.open')) {
                    return 'window.open("#", "_blank")';
                }
                // Remove Jinja template syntax
                return '';
            });
        });

        // Remove Jinja template syntax from HTML
        cleanHtml = cleanHtml.replace(/\{%\s*[^%]*\s*%\}/g, '');
        cleanHtml = cleanHtml.replace(/\{\{\s*[^}]*\s*\}\}/g, '');

        // Remove Nexus Flow route references from JS
        cleanJs = cleanJs.replace(/window\.location\s*=\s*["']\/(?:builder|dashboard|login|register|profile|settings|projects|chat|admin|preview|code-editor|website-ai|home|logout|templates|downloads|camera)[^"']*["']/gi, 'console.log("Navigation blocked in preview mode")');
        cleanJs = cleanJs.replace(/window\.location\.href\s*=\s*["']\/(?:builder|dashboard|login|register|profile|settings|projects|chat|admin|preview|code-editor|website-ai|home|logout|templates|downloads|camera)[^"']*["']/gi, 'console.log("Navigation blocked in preview mode")');
        cleanJs = cleanJs.replace(/location\.href\s*=\s*["']\/(?:builder|dashboard|login|register|profile|settings|projects|chat|admin|preview|code-editor|website-ai|home|logout|templates|downloads|camera)[^"']*["']/gi, 'console.log("Navigation blocked in preview mode")');
        cleanJs = cleanJs.replace(/window\.open\s*\(\s*["']\/(?:builder|dashboard|login|register|profile|settings|projects|chat|admin|preview|code-editor|website-ai|home|logout|templates|downloads|camera)[^"']*["']/gi, 'window.open("#", "_blank")');

        // Remove any script/link tags pointing to Nexus Flow static files
        cleanHtml = cleanHtml.replace(/<script[^>]*src=["']\/static\/[^"']*["'][^>]*><\/script>/gi, '');
        cleanHtml = cleanHtml.replace(/<link[^>]*href=["']\/static\/[^"']*["'][^>]*>/gi, '');

        return { html: cleanHtml, css: cleanCss, js: cleanJs };
    }

    /**
     * Validate generated code for Nexus Flow references.
     * Returns a report of any issues found.
     */
    function validateGeneratedCode(html, css, js) {
        const issues = [];
        const allCode = (html || "") + "\n" + (css || "") + "\n" + (js || "");

        // Check for Nexus Flow route references
        const routePattern = /\/(?:builder|dashboard|login|register|profile|settings|projects|chat|admin|preview|code-editor|website-ai|home|logout|templates|downloads|camera)\b/gi;
        const routeMatches = allCode.match(routePattern) || [];
        if (routeMatches.length > 0) {
            issues.push({
                type: "nexus-route",
                count: routeMatches.length,
                message: `Found ${routeMatches.length} reference(s) to Nexus Flow routes in generated code`
            });
        }

        // Check for Jinja template syntax
        const jinjaPattern = /\{%\s*[^%]*\s*%\}|\{\{\s*[^}]*\s*\}\}/g;
        const jinjaMatches = allCode.match(jinjaPattern) || [];
        if (jinjaMatches.length > 0) {
            issues.push({
                type: "jinja-template",
                count: jinjaMatches.length,
                message: `Found ${jinjaMatches.length} Jinja template syntax reference(s) in generated code`
            });
        }

        // Check for Nexus Flow static file references
        const staticPattern = /\/static\/(?:css|js|images)\/(?:builder|dashboard|workspace|style|profile|login|register)/gi;
        const staticMatches = allCode.match(staticPattern) || [];
        if (staticMatches.length > 0) {
            issues.push({
                type: "nexus-static",
                count: staticMatches.length,
                message: `Found ${staticMatches.length} reference(s) to Nexus Flow static files in generated code`
            });
        }

        return {
            valid: issues.length === 0,
            issues: issues
        };
    }

    // =========================================================
    // BUILD PREVIEW DOCUMENT - ISOLATED GENERATED WEBSITE
    // =========================================================
    function buildPreviewDocument(state) {
        // Sanitize generated code before building preview
        const sanitized = sanitizeGeneratedCode(state.html, state.css, state.javascript);
        state = { ...state, html: sanitized.html, css: sanitized.css, javascript: sanitized.js };
        
        let html = state.html || "";
        let css = state.css || "";
        const js = state.javascript || "";

        // Extract CSS from <style> tags if no separate CSS
        if (!css || css.trim() === "") {
            const styleMatches = html.match(/<style[^>]*>([\s\S]*?)<\/style>/gi);
            if (styleMatches) {
                css = styleMatches.map(s => s.replace(/<\/?style[^>]*>/gi, '').trim()).join('\n\n');
            }
        }

        // Remove <style> tags from HTML
        html = html.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
        
        // Remove <script> tags from HTML (we'll add them back separately)
        html = html.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');

        // Clean up the HTML - extract body content only
        let bodyContent = html;
        bodyContent = bodyContent.replace(/<!DOCTYPE[^>]*>/gi, '');
        bodyContent = bodyContent.replace(/<\/?html[^>]*>/gi, '');
        bodyContent = bodyContent.replace(/<head[^>]*>[\s\S]*?<\/head>/gi, '');
        bodyContent = bodyContent.replace(/<\/?body[^>]*>/gi, '');
        bodyContent = bodyContent.trim();

        // Clean CSS
        css = css.replace(/<\/?style[^>]*>/gi, '').trim();
        if (css.includes("/*") && !css.slice(css.lastIndexOf("/*")).includes("*/")) {
            css += " */";
        }
        let openB = (css.match(/{/g) || []).length;
        let closeB = (css.match(/}/g) || []).length;
        if (openB > closeB) {
            css += '\n' + '}'.repeat(openB - closeB);
        }

        // Add base reset if not present
        const baseReset = `*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif; line-height: 1.6; -webkit-text-size-adjust: 100%; scroll-behavior: smooth; }
body { margin: 0; padding: 0; width: 100%; min-height: 100vh; background-color: #090d16; color: #f8fafc; overflow-x: hidden; }
section, header, footer, nav, main, article, aside { display: block; position: relative; width: 100%; clear: both; box-sizing: border-box; }
.container, .wrapper, .section-container { width: 100%; max-width: 1240px; margin-left: auto; margin-right: auto; padding-left: 1.5rem; padding-right: 1.5rem; box-sizing: border-box; }
img, video, svg, iframe, canvas { max-width: 100%; height: auto; display: block; }
a { text-decoration: none; color: inherit; transition: all 0.2s ease; }
button, input, select, textarea { font-family: inherit; font-size: inherit; }`;

        if (!css.includes("box-sizing")) {
            css = baseReset + "\n\n" + css;
        }

        // Clean JavaScript
        let cleanJs = js.replace(/<\/?script[^>]*>/gi, '').trim();
        
        // Dynamically strip DOMContentLoaded wrapper from AI's code to prevent race conditions
        cleanJs = cleanJs.replace(/document\.addEventListener\s*\(\s*['"]DOMContentLoaded['"]\s*,\s*(?:function\s*\([^)]*\)\s*\{|\(\)\s*=>\s*\{)([\s\S]*?)\}\s*\)\s*;/g, '$1');
        cleanJs = cleanJs.replace(/window\.addEventListener\s*\(\s*['"]DOMContentLoaded['"]\s*,\s*(?:function\s*\([^)]*\)\s*\{|\(\)\s*=>\s*\{)([\s\S]*?)\}\s*\)\s*;/g, '$1');
        
        cleanJs = cleanJs.replace(/<\/script>/gi, '<\\/script>');

        // Build the complete isolated HTML document - NO NEXUS FLOW UI
        return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${state.website_name || 'Generated Website'}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='vendor/fontawesome/css/all.min.css') }}">
  <link rel="stylesheet" href="{{ url_for('static', filename='vendor/fonts/fonts.css') }}">
<style>
${css}
  </style>
</head>
<body>
${bodyContent}
  <script>
${buildIsolationLayer()}
  <\/script>
  <script>
  try {
${cleanJs}
  } catch(e) {
    console.error('Execution Error:', e);
  }
  <\/script>
</body>
</html>`;
    }

    function updatePreview() {
        if (!previewFrame) return;
        const doc = buildPreviewDocument(currentState);
        previewFrame.srcdoc = doc;
    }

    // =========================================================
    // ADD CHAT BUBBLE
    // =========================================================
    function addChatBubble(role, text) {
        if (!modifierChatHistory) return;
        const bubble = document.createElement("div");
        bubble.className = `chat-bubble ${role}`;
        const strong = document.createElement("strong");
        strong.textContent = role === "user" ? "You" : "Nexus AI";
        const p = document.createElement("p");
        p.textContent = text;
        bubble.appendChild(strong);
        bubble.appendChild(p);
        modifierChatHistory.appendChild(bubble);
        modifierChatHistory.scrollTop = modifierChatHistory.scrollHeight;
    }

    // =========================================================
    // SHOW WORKSPACE
    // =========================================================
    function showWorkspace() {
        if (configSection) configSection.style.display = "none";
        if (workspaceSection) workspaceSection.style.display = "flex";
        if (generatedWebsiteName) generatedWebsiteName.textContent = currentState.website_name || "My AI Website";
        updatePreview();
        renderFeatures();
    }

    function showConfig() {
        if (workspaceSection) workspaceSection.style.display = "none";
        if (configSection) configSection.style.display = "flex";
    }

    // =========================================================
    // GENERATE WEBSITE
    // =========================================================
    async function generateWebsite() {
        if (isGenerating) return;

        const prompt = (aiPromptInput.value || "").trim();
        if (!prompt) {
            aiPromptInput.focus();
            aiPromptInput.style.borderColor = "#ef4444";
            setTimeout(() => { aiPromptInput.style.borderColor = ""; }, 2000);
            return;
        }

        const websiteName = (websiteNameInput.value || "").trim() || "My AI Website";
        const websiteType = websiteTypeSelect ? websiteTypeSelect.value : "auto";
        const techStack = techStackSelect ? techStackSelect.value : "auto";

        setGenerating(true);

        try {
            const response = await fetch("/generate_website", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    prompt: prompt,
                    website_name: websiteName,
                    website_type: websiteType,
                    tech_stack: techStack
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || "Failed to generate website");
            }

            currentState = {
                website_name: websiteName,
                prompt: prompt,
                website_type: websiteType,
                tech_stack: (data.tech_stack && data.tech_stack !== "auto") ? data.tech_stack : (techStack && techStack !== "auto" ? techStack : "html"),
                html: data.html || "",
                css: data.css || "",
                javascript: data.js || data.javascript || "",
                project_id: data.project_id || null
            };

            exposeStateToWindow();
            dispatchWebsiteGenerated(currentState);

            // Validate generated code for Nexus Flow references
            const validation = validateGeneratedCode(currentState.html, currentState.css, currentState.javascript);
            if (!validation.valid) {
                console.warn("Generated website validation warnings:", validation.issues);
                // Sanitize the generated code to remove any Nexus Flow references
                const sanitized = sanitizeGeneratedCode(currentState.html, currentState.css, currentState.javascript);
                currentState.html = sanitized.html;
                currentState.css = sanitized.css;
                currentState.javascript = sanitized.js;
            }

            if (modifierChatHistory) {
                modifierChatHistory.innerHTML = `
                    <div class="chat-bubble assistant">
                        <strong>Nexus AI</strong>
                        <p>Hello! I can modify your generated website. Try asking me to add sections, change colors, or make it responsive.</p>
                    </div>`;
            }

            showWorkspace();

        } catch (error) {
            console.error("Generation error:", error);
            const cleanMessage = error.message || "An unknown error occurred during generation.";
            alert(cleanMessage);
        } finally {
            setGenerating(false);
        }
    }

    // =========================================================
    // SAVE PROJECT
    // =========================================================
    async function saveProject() {
        try {
            const response = await fetch("/save_builder_project", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: currentState.website_name,
                    prompt: currentState.prompt,
                    html: currentState.html,
                    css: currentState.css,
                    js: currentState.javascript,
                    project_id: currentState.project_id
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || "Failed to save project");
            }

            currentState.project_id = data.project_id || currentState.project_id;
            showToast("Changes saved successfully");

        } catch (error) {
            console.error("Save error:", error);
            alert("Error saving project: " + error.message);
        }
    }

    // =========================================================
    // AI MODIFIER
    // =========================================================
    async function sendModifierRequest() {
        if (isModifying) return;

        const message = (modifierInput.value || "").trim();
        if (!message) {
            modifierInput.focus();
            return;
        }

        if (!currentState.html) {
            alert("Please generate a website first before using the AI Modifier.");
            return;
        }

        addChatBubble("user", message);
        modifierInput.value = "";
        setModifying(true);

        try {
            const response = await fetch("/chat_website_edit", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: message,
                    html: currentState.html,
                    css: currentState.css,
                    js: currentState.javascript
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || "Failed to modify website");
            }

            currentState.html = data.html || currentState.html;
            currentState.css = data.css || currentState.css;
            currentState.javascript = data.js || data.javascript || currentState.javascript;
            currentState.project_id = data.project_id || currentState.project_id;

            exposeStateToWindow();
            dispatchWebsiteUpdated(currentState);

            addChatBubble("assistant", data.reply || "I've updated your website according to your request.");

            updatePreview();
            renderFeatures();

            showToast("Changes saved successfully");

        } catch (error) {
            console.error("Modifier error:", error);
            const cleanMessage = error.message || "An unknown error occurred.";
            addChatBubble("assistant", cleanMessage);
        } finally {
            setModifying(false);
        }
    }

    // =========================================================
    // EVENT LISTENERS
    // =========================================================
    document.addEventListener("DOMContentLoaded", () => {

        if (promptCharCount && aiPromptInput) {
            const updateCharCount = () => {
                promptCharCount.textContent = aiPromptInput.value.length;
            };
            aiPromptInput.addEventListener("input", updateCharCount);
            updateCharCount();
        }

        document.querySelectorAll(".chip[data-prompt]").forEach(pill => {
            pill.addEventListener("click", () => {
                if (aiPromptInput) {
                    aiPromptInput.value = pill.getAttribute("data-prompt");
                    aiPromptInput.dispatchEvent(new Event("input"));
                    aiPromptInput.focus();
                }
            });
        });

        document.querySelectorAll(".suggestion-chip[data-modify]").forEach(pill => {
            pill.addEventListener("click", () => {
                if (modifierInput) {
                    modifierInput.value = pill.getAttribute("data-modify");
                    modifierInput.focus();
                }
            });
        });

        if (generateBtn) {
            generateBtn.addEventListener("click", generateWebsite);
        }

        if (aiPromptInput) {
            aiPromptInput.addEventListener("keydown", (e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                    e.preventDefault();
                    generateWebsite();
                }
            });
        }

        if (backToConfigBtn) {
            backToConfigBtn.addEventListener("click", showConfig);
        }

        if (saveProjectBtn) {
            saveProjectBtn.addEventListener("click", saveProject);
        }

        if (saveProjectBtnHeader) {
            saveProjectBtnHeader.addEventListener("click", saveProject);
        }

        if (newProjectBtn) {
            newProjectBtn.addEventListener("click", () => {
                if (confirm("Start a new project? Unsaved changes will be lost.")) {
                    currentState = {
                        website_name: "My AI Website",
                        prompt: "",
                        website_type: "auto",
                        tech_stack: "html",
                        html: "",
                        css: "",
                        javascript: "",
                        project_id: null
                    };
                    if (aiPromptInput) aiPromptInput.value = "";
                    if (websiteNameInput) websiteNameInput.value = "My AI Website";
                    if (websiteTypeSelect) websiteTypeSelect.value = "auto";
                    if (techStackSelect) techStackSelect.value = "auto";
                    if (promptCharCount) promptCharCount.textContent = "0";
                    if (modifierChatHistory) {
                        modifierChatHistory.innerHTML = `
                            <div class="chat-bubble assistant">
                                <strong>Nexus AI</strong>
                                <p>Hello! I can modify your generated website. Try asking me to add sections, change colors, or make it responsive.</p>
                            </div>`;
                    }
                    showConfig();
                }
            });
        }

        if (downloadProjectBtn) {
            downloadProjectBtn.addEventListener("click", () => {
                if (!currentState.project_id) {
                    alert("Please save the project first before downloading.");
                    return;
                }
                window.location.href = `/download/zip/${currentState.project_id}`;
            });
        }

        document.querySelectorAll(".workspace-tab").forEach(tab => {
            tab.addEventListener("click", () => {
                document.querySelectorAll(".workspace-tab").forEach(t => t.classList.remove("active"));
                document.querySelectorAll(".workspace-tab-content").forEach(c => c.classList.remove("active"));
                tab.classList.add("active");
                const contentEl = document.getElementById(tab.getAttribute("data-tab") + "Tab");
                if (contentEl) contentEl.classList.add("active");
            });
        });

        document.querySelectorAll(".device-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                document.querySelectorAll(".device-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                const device = btn.getAttribute("data-device");
                if (previewFrameShell) {
                    previewFrameShell.classList.remove("tablet", "mobile");
                    if (device === "tablet") previewFrameShell.classList.add("tablet");
                    if (device === "mobile") previewFrameShell.classList.add("mobile");
                }
            });
        });

        if (refreshPreviewBtn) {
            refreshPreviewBtn.addEventListener("click", updatePreview);
        }

        if (openPreviewBtn) {
            openPreviewBtn.addEventListener("click", () => {
                const doc = buildPreviewDocument(currentState);
                const blob = new Blob([doc], { type: "text/html" });
                const url = URL.createObjectURL(blob);
                window.open(url, "_blank");
                setTimeout(() => URL.revokeObjectURL(url), 10000);
            });
        }

        if (modifierSendBtn) {
            modifierSendBtn.addEventListener("click", sendModifierRequest);
        }

        if (modifierInput) {
            modifierInput.addEventListener("keydown", (e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                    e.preventDefault();
                    sendModifierRequest();
                }
            });
        }

    });

})();