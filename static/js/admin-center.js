document.addEventListener("DOMContentLoaded", () => {

    // --- Toast ---
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
            toast.style.borderLeftColor = "var(--accent)";
            toastIcon.className = "fa-solid fa-circle-check";
            toastIcon.style.color = "var(--accent)";
        }
        toast.classList.add("show");
        setTimeout(() => toast.classList.remove("show"), 3500);
    }

    // --- User search ---
    const userSearch = document.getElementById("userSearch");
    if (userSearch) {
        let debounce;
        userSearch.addEventListener("input", () => {
            clearTimeout(debounce);
            debounce = setTimeout(() => {
                const q = userSearch.value.trim();
                window.location.href = "/admin/users" + (q ? "?search=" + encodeURIComponent(q) : "");
            }, 500);
        });
    }

    // --- Log search ---
    const logSearch = document.getElementById("logSearch");
    if (logSearch) {
        let debounce;
        logSearch.addEventListener("input", () => {
            clearTimeout(debounce);
            debounce = setTimeout(() => {
                const rows = document.querySelectorAll("#logsTable tbody tr");
                const q = logSearch.value.toLowerCase().trim();
                rows.forEach(row => {
                    const text = row.textContent.toLowerCase();
                    row.style.display = text.includes(q) ? "" : "none";
                });
            }, 300);
        });
    }

    // --- Delete user ---
    let pendingDeleteUserId = null;

    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".ac-row-delete");
        if (btn) {
            pendingDeleteUserId = btn.getAttribute("data-id");
            const name = btn.getAttribute("data-name");
            document.getElementById("deleteUserName").textContent = name;
            document.getElementById("deleteUserModal").classList.add("active");
        }
    });

    const closeDeleteModal = document.getElementById("closeDeleteModal");
    const cancelDeleteBtn = document.getElementById("cancelDeleteBtn");
    if (closeDeleteModal) closeDeleteModal.addEventListener("click", () => document.getElementById("deleteUserModal").classList.remove("active"));
    if (cancelDeleteBtn) cancelDeleteBtn.addEventListener("click", () => document.getElementById("deleteUserModal").classList.remove("active"));

    const confirmDeleteBtn = document.getElementById("confirmDeleteBtn");
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener("click", async () => {
            if (!pendingDeleteUserId) return;
            try {
                const resp = await fetch("/admin/api/user/" + pendingDeleteUserId + "/delete", { method: "POST" });
                const result = await resp.json();
                if (result.success) {
                    showToast(result.message);
                    document.getElementById("deleteUserModal").classList.remove("active");
                    const row = document.getElementById("user-row-" + pendingDeleteUserId);
                    if (row) row.remove();
                } else {
                    showToast(result.message || result.error || "Failed to delete user", true);
                }
            } catch (err) {
                console.error("Delete user error:", err);
                showToast("Error deleting user", true);
            }
            pendingDeleteUserId = null;
        });
    }

    // --- Test provider connection ---
    document.addEventListener("click", async (e) => {
        const btn = e.target.closest(".ac-test-provider");
        if (btn) {
            const provider = btn.getAttribute("data-provider");
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Testing...';
            try {
                const resp = await fetch("/admin/api/provider/test", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ provider: provider })
                });
                const result = await resp.json();
                if (result.success) {
                    showToast(provider + ": " + result.message);
                } else {
                    showToast(result.message || "Connection failed", true);
                }
            } catch (err) {
                showToast("Error testing " + provider, true);
            }
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-plug"></i> Test Connection';
        }
    });

    // --- Modal overlay click-to-close ---
    document.querySelectorAll(".ac-modal-overlay").forEach(overlay => {
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) overlay.classList.remove("active");
        });
    });

});
