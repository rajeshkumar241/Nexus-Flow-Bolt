document.addEventListener("DOMContentLoaded", () => {

    // --- 1. Tab Navigation Logic ---
    const tabButtons = document.querySelectorAll(".nx-nav-item");
    const tabPanes = document.querySelectorAll(".nx-tab-pane");

    tabButtons.forEach(button => {
        button.addEventListener("click", () => {
            const targetTabId = button.getAttribute("data-tab");

            tabButtons.forEach(btn => btn.classList.remove("active"));
            tabPanes.forEach(pane => pane.classList.remove("active"));

            button.classList.add("active");
            const targetPane = document.getElementById(targetTabId);
            if (targetPane) {
                targetPane.classList.add("active");
            }
        });
    });

    // --- 2. Password Toggle Visibility ---
    const togglePwdIcons = document.querySelectorAll(".nx-toggle-pwd");
    togglePwdIcons.forEach(icon => {
        icon.addEventListener("click", () => {
            const targetId = icon.getAttribute("data-target");
            const input = document.getElementById(targetId);
            const iconEl = icon.querySelector("i");

            if (input && iconEl) {
                if (input.type === "password") {
                    input.type = "text";
                    iconEl.classList.remove("fa-eye");
                    iconEl.classList.add("fa-eye-slash");
                } else {
                    input.type = "password";
                    iconEl.classList.remove("fa-eye-slash");
                    iconEl.classList.add("fa-eye");
                }
            }
        });
    });

    // --- 3. Theme Color Selection Logic ---
    const themeCards = document.querySelectorAll(".nx-theme-card");
    themeCards.forEach(card => {
        card.addEventListener("click", () => {
            themeCards.forEach(c => c.classList.remove("selected"));
            card.classList.add("selected");
            const radio = card.querySelector("input[type='radio']");
            if (radio) radio.checked = true;

            const customColorWrapper = document.getElementById("customColorWrapper");
            if (customColorWrapper) {
                customColorWrapper.style.display = card.getAttribute("data-theme-color") === "custom" ? "flex" : "none";
            }
        });
    });

    // --- 3b. Theme Mode Selection Logic (Dark/Light/System) ---
    const modeCards = document.querySelectorAll(".nx-mode-card");
    modeCards.forEach(card => {
        card.addEventListener("click", () => {
            modeCards.forEach(c => c.classList.remove("selected"));
            card.classList.add("selected");
            const radio = card.querySelector("input[type='radio']");
            if (radio) radio.checked = true;

            // Instant preview
            const mode = card.getAttribute("data-theme-mode");
            if (typeof window.applyNexusThemeMode === "function") {
                window.applyNexusThemeMode(mode);
            }
        });
    });

    const themeValueInput = document.getElementById("theme_color_value");
    const colorCodeDisplay = document.getElementById("colorCodeDisplay");

    if (themeValueInput && colorCodeDisplay) {
        themeValueInput.addEventListener("input", (e) => {
            colorCodeDisplay.textContent = e.target.value.toUpperCase();
            const customSwatch = document.getElementById("customSwatch");
            if (customSwatch) customSwatch.style.background = e.target.value;
        });
    }

    // --- 4. Toast Notification Function ---
    function showToast(message, isError = false) {
        const toast = document.getElementById("toastNotification");
        const toastIcon = document.getElementById("toastIcon");
        const toastMessage = document.getElementById("toastMessage");

        if (!toast) return;

        toastMessage.textContent = message;
        if (isError) {
            toast.style.borderLeftColor = "#ef4444";
            toastIcon.className = "fa-solid fa-circle-xmark";
            toastIcon.style.color = "#ef4444";
        } else {
            toast.style.borderLeftColor = "var(--nx-accent)";
            toastIcon.className = "fa-solid fa-circle-check";
            toastIcon.style.color = "var(--nx-accent)";
        }

        toast.classList.remove("hidden");

        setTimeout(() => {
            toast.classList.add("hidden");
        }, 3500);
    }

    // Make showToast globally available
    window.showToast = showToast;

    // --- 5. AJAX Form Handlers ---
    async function submitSettingsForm(formElement, actionName) {
        const formData = new FormData(formElement);
        const data = { action: actionName };

        formData.forEach((value, key) => {
            if (key !== "action") {
                if (key === "email_alerts" || key === "project_updates" || key === "ai_updates" || key === "feature_updates") {
                    data[key] = true;
                } else {
                    data[key] = value;
                }
            }
        });

        // Unchecked switches handler for notifications form
        if (actionName === "notifications") {
            data["email_alerts"] = formData.has("email_alerts");
            data["project_updates"] = formData.has("project_updates");
            data["ai_updates"] = formData.has("ai_updates");
            data["feature_updates"] = formData.has("feature_updates");
        }

        try {
            const response = await fetch("/settings", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                showToast(result.message || "Settings updated successfully!", false);

                // Apply the new theme color instantly across the app
                if (actionName === "theme_color" && typeof window.applyNexusTheme === "function") {
                    const colorValue = document.getElementById("theme_color_value");
                    const customHex = colorValue && colorValue.value ? colorValue.value : "";
                    window.applyNexusTheme(data.theme_color || "blue", result.theme_color_value || (data.theme_color === "custom" ? customHex : ""));

                    // Apply theme mode
                    if (typeof window.applyNexusThemeMode === "function") {
                        window.applyNexusThemeMode(data.theme_mode || "dark");
                    }
                }

                // Update sidebar details live if profile tab was updated
                if (actionName === "profile") {
                    const sidebarName = document.querySelector(".nx-user-name");
                    const sidebarEmail = document.querySelector(".nx-user-email");
                    if (sidebarName && data.fullname) sidebarName.textContent = data.fullname;
                    if (sidebarEmail && data.email) sidebarEmail.textContent = data.email;

                    // Update profile hero section
                    const profileName = document.querySelector(".nx-profile-details h3");
                    const profileEmail = document.querySelector(".nx-profile-details p");
                    if (profileName && data.fullname) profileName.textContent = data.fullname;
                    if (profileEmail && data.email) profileEmail.textContent = data.email;
                }

                // Reset password fields if password form was updated
                if (actionName === "password") {
                    formElement.reset();
                }
            } else {
                showToast(result.error || "Failed to update settings.", true);
            }
        } catch (err) {
            console.error("Settings Update Error:", err);
            // Fallback to normal form submission if AJAX fails
            formElement.submit();
        }
    }

    const forms = [
        { id: "profileForm", action: "profile" },
        { id: "passwordForm", action: "password" },
        { id: "appearanceForm", action: "theme_color" },
        { id: "notificationsForm", action: "notifications" },
        { id: "aiPreferencesForm", action: "ai_preferences" }
    ];

    forms.forEach(item => {
        const form = document.getElementById(item.id);
        if (form) {
            form.addEventListener("submit", (e) => {
                e.preventDefault();
                submitSettingsForm(form, item.action);
            });
        }
    });

    // --- 6. Delete Account Modal Logic ---
    const openDeleteModalBtn = document.getElementById("openDeleteModalBtn");
    const deleteAccountModal = document.getElementById("deleteAccountModal");
    const deleteAccountForm = document.getElementById("deleteAccountForm");

    if (openDeleteModalBtn && deleteAccountModal) {
        openDeleteModalBtn.addEventListener("click", () => {
            deleteAccountModal.classList.remove("hidden");
        });
    }

    // Close modal via any [data-close-modal] button
    document.querySelectorAll("[data-close-modal]").forEach(btn => {
        btn.addEventListener("click", () => {
            const modalId = btn.getAttribute("data-close-modal");
            const modal = document.getElementById(modalId);
            if (modal) modal.classList.add("hidden");
        });
    });

    if (deleteAccountModal) {
        deleteAccountModal.addEventListener("click", (e) => {
            if (e.target === deleteAccountModal) {
                deleteAccountModal.classList.add("hidden");
            }
        });
    }

    if (deleteAccountForm) {
        deleteAccountForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const password = document.getElementById("deleteConfirmPassword").value;

            try {
                const response = await fetch("/delete_account", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ password: password })
                });

                const result = await response.json();

                if (result.success) {
                    showToast("Account deleted. Redirecting...", false);
                    setTimeout(() => {
                        window.location.href = result.redirect || "/";
                    }, 1200);
                } else {
                    showToast(result.error || "Incorrect password.", true);
                }
            } catch (err) {
                console.error("Delete Account Error:", err);
                deleteAccountForm.submit();
            }
        });
    }

    // --- 7. AI Provider Test Connection ---
    window.testProvider = async function(providerName) {
        const statusEl = document.getElementById(providerName + "Status");
        const dotEl = statusEl ? statusEl.querySelector(".nx-status-dot") : null;
        const labelEl = statusEl ? statusEl.querySelector("span:last-child") : null;

        if (statusEl) {
            if (dotEl) { dotEl.className = "nx-status-dot"; dotEl.style.background = "var(--nx-orange)"; }
            if (labelEl) labelEl.textContent = "Testing...";
        }

        try {
            const response = await fetch("/api/ai/providers/test-connection", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ provider: providerName })
            });

            const result = await response.json();

            if (result.success) {
                if (dotEl) { dotEl.className = "nx-status-dot nx-status-active"; }
                if (labelEl) labelEl.textContent = "Connected";
                showToast(result.message || providerName + " connected successfully!", false);
            } else {
                if (dotEl) { dotEl.className = "nx-status-dot nx-status-inactive"; }
                if (labelEl) labelEl.textContent = "Failed";
                showToast(result.error || "Connection failed for " + providerName, true);
            }
        } catch (err) {
            console.error("Provider test error:", err);
            if (dotEl) { dotEl.className = "nx-status-dot nx-status-inactive"; }
            if (labelEl) labelEl.textContent = "Error";
            showToast("Network error testing " + providerName, true);
        }
    };

    // --- 8. AI Provider Configure (placeholder) ---
    window.configureProvider = function(providerName) {
        showToast("Configuration panel for " + providerName + " — coming soon!", false);
    };

    // --- 9. Load workspace stats ---
    async function loadStats() {
        try {
            const response = await fetch("/api/user/stats", { headers: { "Accept": "application/json" } });
            if (!response.ok) return;
            const data = await response.json();
            if (data.success) {
                const s = data.stats || {};
                const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
                el("statWebsites", s.websites_generated ?? "--");
                el("statProjects", s.projects_created ?? "--");
                el("statRequests", s.ai_requests ?? "--");
                el("statLastActivity", s.last_activity ?? "--");
            }
        } catch (_) { /* silent */ }
    }
    loadStats();

    // --- 10. AI Model Selector ---
    const modelOptions = document.querySelectorAll(".nx-model-option");
    modelOptions.forEach(option => {
        option.addEventListener("click", () => {
            modelOptions.forEach(o => o.classList.remove("selected"));
            option.classList.add("selected");
            const radio = option.querySelector("input[type='radio']");
            if (radio) radio.checked = true;
        });
    });

    // --- 11. Coding Level Selector ---
    const levelOptions = document.querySelectorAll(".nx-level-option");
    levelOptions.forEach(option => {
        option.addEventListener("click", () => {
            levelOptions.forEach(o => o.classList.remove("selected"));
            option.classList.add("selected");
            const radio = option.querySelector("input[type='radio']");
            if (radio) radio.checked = true;
        });
    });

    // --- 12. Sticky Action Bar ---
    const saveAllBtn = document.getElementById("saveAllSettingsBtn");
    const resetBtn = document.getElementById("resetSettingsBtn");

    if (saveAllBtn) {
        saveAllBtn.addEventListener("click", () => {
            // Find the currently active tab and submit its form
            const activePane = document.querySelector(".nx-tab-pane.active");
            if (activePane) {
                const form = activePane.querySelector("form");
                if (form) {
                    const action = form.querySelector('input[name="action"]');
                    if (action) {
                        submitSettingsForm(form, action.value);
                    }
                }
            }
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener("click", () => {
            if (confirm("Reset all unsaved changes?")) {
                window.location.reload();
            }
        });
    }

});
