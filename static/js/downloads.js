document.addEventListener("DOMContentLoaded", () => {

    // --- Storage progress bar init ---
    const storageBarFill = document.querySelector(".dl-stat-bar-fill");
    if (storageBarFill) {
        const pct = Number.parseFloat(storageBarFill.dataset.storagePct);
        const safe = Number.isFinite(pct) ? Math.min(100, Math.max(0, pct)) : 0;
        storageBarFill.style.width = safe + "%";
    }

    // --- 1. Toast Notification ---
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

    // --- 2. Modal Open / Close Logic ---
    function openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.add("active");
    }

    function closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.remove("active");
    }

    document.querySelectorAll(".dl-modal-close, .closeModalBtn").forEach(btn => {
        btn.addEventListener("click", () => {
            const modalId = btn.getAttribute("data-modal");
            closeModal(modalId);
        });
    });

    document.querySelectorAll(".dl-modal-overlay").forEach(overlay => {
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) {
                overlay.classList.remove("active");
            }
        });
    });

    // --- 3. Real-time Search Filtering ---
    const searchInput = document.getElementById("downloadSearch");
    function filterTable() {
        if (!searchInput) return;
        const query = searchInput.value.toLowerCase().trim();
        const activeFilter = document.querySelector(".dl-filter-btn.active");
        const filterType = activeFilter ? activeFilter.getAttribute("data-filter") : "all";
        const rows = document.querySelectorAll("#downloadTable tbody tr");
        let visibleCount = 0;

        rows.forEach(row => {
            const name = row.getAttribute("data-name") || "";
            const title = row.getAttribute("data-title") || "";
            const type = row.getAttribute("data-type") || "";

            const matchesSearch = name.includes(query) || title.includes(query);
            let matchesFilter = filterType === "all";
            if (!matchesFilter) {
                if (filterType === "zip") matchesFilter = type.includes("zip");
                else if (filterType === "html") matchesFilter = type.includes("html") || type.includes("standalone");
                else if (filterType === "deploy") matchesFilter = type.includes("deploy");
            }

            if (matchesSearch && matchesFilter) {
                row.style.display = "";
                visibleCount++;
            } else {
                row.style.display = "none";
            }
        });

        const noMatches = document.getElementById("noMatchingDownloads");
        if (noMatches) {
            noMatches.style.display = visibleCount === 0 && rows.length > 0 ? "" : "none";
        }
    }

    if (searchInput) {
        searchInput.addEventListener("input", filterTable);
    }

    // --- 4. Filter Buttons ---
    document.querySelectorAll(".dl-filter-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".dl-filter-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            filterTable();
        });
    });

    // --- 5. Delete Single Download History Record ---
    document.addEventListener("click", async (e) => {
        const deleteBtn = e.target.closest(".btn-delete-row");
        if (deleteBtn) {
            const downloadId = deleteBtn.getAttribute("data-id");

            try {
                const response = await fetch("/downloads/delete/" + downloadId, {
                    method: "POST"
                });

                const result = await response.json();
                if (result.success) {
                    showToast(result.message);
                    const row = document.getElementById("row-" + downloadId);
                    if (row) {
                        row.remove();
                    }

                    const remainingRows = document.querySelectorAll("#downloadTable tbody tr");
                    if (remainingRows.length === 0) {
                        setTimeout(() => window.location.reload(), 500);
                    }
                } else {
                    showToast(result.error || "Failed to delete record", true);
                }
            } catch (err) {
                console.error("Delete Download Error:", err);
                showToast("Error deleting history record", true);
            }
        }
    });

    // --- 6. Clear All History Modal & Handler ---
    const clearHistoryBtn = document.getElementById("clearHistoryBtn");
    const confirmClearHistoryBtn = document.getElementById("confirmClearHistoryBtn");

    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener("click", () => {
            openModal("clearHistoryModal");
        });
    }

    if (confirmClearHistoryBtn) {
        confirmClearHistoryBtn.addEventListener("click", async () => {
            try {
                const response = await fetch("/downloads/clear", {
                    method: "POST"
                });

                const result = await response.json();
                if (result.success) {
                    showToast(result.message);
                    closeModal("clearHistoryModal");
                    setTimeout(() => window.location.reload(), 800);
                } else {
                    showToast(result.error || "Failed to clear history", true);
                }
            } catch (err) {
                console.error("Clear History Error:", err);
                showToast("Error clearing download history", true);
            }
        });
    }

});
