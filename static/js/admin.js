/* =========================================================
   NEXUS FLOW AI - ADMIN DASHBOARD JAVASCRIPT
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {
    const adminUserSearch = document.getElementById("adminUserSearch");
    const clearSearchBtn = document.getElementById("clearSearchBtn");
    const usersTableBody = document.getElementById("usersTableBody");
    const refreshLogsBtn = document.getElementById("refreshLogsBtn");
    const logsTableBody = document.getElementById("logsTableBody");
    const userCountBadge = document.getElementById("userCountBadge");

    // Modal Elements
    const deleteModal = document.getElementById("deleteModal");
    const deleteUserEmailTarget = document.getElementById("deleteUserEmailTarget");
    const cancelDeleteBtn = document.getElementById("cancelDeleteBtn");
    const confirmDeleteBtn = document.getElementById("confirmDeleteBtn");

    let pendingDeleteUserId = null;
    let pendingDeleteEmail = null;

    // Live Search Users
    if (adminUserSearch) {
        adminUserSearch.addEventListener("input", function () {
            const query = this.value.trim().toLowerCase();
            filterUserRows(query);
        });
    }

    if (clearSearchBtn) {
        clearSearchBtn.addEventListener("click", function () {
            if (adminUserSearch) {
                adminUserSearch.value = "";
                filterUserRows("");
            }
        });
    }

    /**
     * Filter User Table Rows Locally in Realtime
     */
    function filterUserRows(query) {
        const rows = usersTableBody.querySelectorAll("tr:not(.empty-row)");
        let visibleCount = 0;

        rows.forEach(row => {
            const fullnameEl = row.querySelector(".user-fullname");
            const emailEl = row.querySelector(".user-email-cell");

            const fullname = fullnameEl ? fullnameEl.textContent.toLowerCase() : "";
            const email = emailEl ? emailEl.textContent.toLowerCase() : "";

            if (fullname.includes(query) || email.includes(query)) {
                row.style.display = "";
                visibleCount++;
            } else {
                row.style.display = "none";
            }
        });

        if (userCountBadge) {
            userCountBadge.textContent = `${visibleCount} Records Shown`;
        }
    }

    // Delegate Click Handler for Delete User Buttons
    if (usersTableBody) {
        usersTableBody.addEventListener("click", function (e) {
            const deleteBtn = e.target.closest(".btn-delete-user");
            if (deleteBtn) {
                const userId = deleteBtn.getAttribute("data-id");
                const email = deleteBtn.getAttribute("data-email");
                openDeleteModal(userId, email);
            }
        });
    }

    /**
     * Open Delete Confirmation Modal
     */
    function openDeleteModal(userId, email) {
        pendingDeleteUserId = userId;
        pendingDeleteEmail = email;

        if (deleteUserEmailTarget) deleteUserEmailTarget.textContent = email;
        if (deleteModal) deleteModal.classList.remove("hidden");
    }

    /**
     * Close Delete Confirmation Modal
     */
    function closeDeleteModal() {
        pendingDeleteUserId = null;
        pendingDeleteEmail = null;
        if (deleteModal) deleteModal.classList.add("hidden");
    }

    if (cancelDeleteBtn) {
        cancelDeleteBtn.addEventListener("click", closeDeleteModal);
    }

    if (deleteModal) {
        deleteModal.addEventListener("click", function (e) {
            if (e.target === deleteModal) closeDeleteModal();
        });
    }

    // Confirm Delete Action
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener("click", async function () {
            if (!pendingDeleteUserId) return;

            confirmDeleteBtn.disabled = true;
            confirmDeleteBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Deleting...`;

            try {
                const response = await fetch(`/admin/delete_user/${pendingDeleteUserId}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" }
                });

                const data = await response.json();
                closeDeleteModal();

                if (data.success) {
                    const rowToRemove = document.getElementById(`user-row-${pendingDeleteUserId}`);
                    if (rowToRemove) rowToRemove.remove();

                    showToast(data.message || "User account deleted successfully.");
                    refreshLogsList();
                } else {
                    showToast(data.error || "Failed to delete user.", true);
                }
            } catch (err) {
                closeDeleteModal();
                showToast("Network error deleting user.", true);
            } finally {
                confirmDeleteBtn.disabled = false;
                confirmDeleteBtn.textContent = "Confirm Delete";
            }
        });
    }

    // Refresh Audit Logs (Clear Logs)
    if (refreshLogsBtn) {
        refreshLogsBtn.addEventListener("click", clearAuditLogs);
    }

    /**
     * Clear All Audit Logs via POST, show empty state
     */
    async function clearAuditLogs() {
        if (!logsTableBody || !refreshLogsBtn) return;

        const originalHTML = refreshLogsBtn.innerHTML;
        refreshLogsBtn.disabled = true;
        refreshLogsBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Clearing Logs...`;

        try {
            const response = await fetch("/admin/logs/clear", {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            });

            const data = await response.json();

            if (data.success) {
                logsTableBody.innerHTML = `
                    <tr>
                        <td colspan="5" class="empty-table-cell">
                            <i class="fa-solid fa-file-excel"></i>
                            <p>No audit logs available</p>
                            <span class="empty-table-sub">System activity records will appear here.</span>
                        </td>
                    </tr>
                `;
                const badge = document.querySelector(".log-count-badge");
                if (badge) badge.textContent = "0 Audit Records";
                showToast("Audit logs cleared successfully");
            } else {
                showToast(data.error || "Failed to clear audit logs", true);
            }
        } catch (err) {
            showToast("Failed to clear audit logs", true);
        } finally {
            refreshLogsBtn.disabled = false;
            refreshLogsBtn.innerHTML = originalHTML;
        }
    }

    /**
     * Refresh logs list (fetch only, no clear)
     */
    async function refreshLogsList() {
        if (!logsTableBody) return;

        try {
            const response = await fetch("/admin/logs");
            const data = await response.json();

            if (data.success && data.logs) {
                renderLogsTable(data.logs);
            }
        } catch (err) {
            // silent
        }
    }

    /**
     * Render Logs Array into Table
     */
    function renderLogsTable(logs) {
        if (!logsTableBody) return;

        if (logs.length === 0) {
            logsTableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-table-cell">
                        <i class="fa-solid fa-file-excel"></i>
                        <p>No system audit logs recorded.</p>
                    </td>
                </tr>
            `;
            return;
        }

        logsTableBody.innerHTML = logs.map(l => {
            let statusBadge = `<span class="status-pill success"><i class="fa-solid fa-circle-check"></i> SUCCESS</span>`;
            if (l.status === 'WARNING') {
                statusBadge = `<span class="status-pill warning"><i class="fa-solid fa-triangle-exclamation"></i> WARNING</span>`;
            } else if (l.status === 'ERROR') {
                statusBadge = `<span class="status-pill error"><i class="fa-solid fa-circle-xmark"></i> ERROR</span>`;
            }

            return `
                <tr>
                    <td class="log-time-cell"><i class="fa-regular fa-clock"></i> ${l.timestamp}</td>
                    <td class="log-user-cell">${escapeHtml(l.user)}</td>
                    <td><span class="action-tag">${escapeHtml(l.action)}</span></td>
                    <td class="log-details-cell">${escapeHtml(l.details)}</td>
                    <td>${statusBadge}</td>
                </tr>
            `;
        }).join("");
    }

    /**
     * Escape HTML special characters
     */
    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    /**
     * Toast Notification Function
     */
    function showToast(msg, isError = false) {
        const toast = document.getElementById("toastNotification");
        const toastMessage = document.getElementById("toastMessage");
        const toastIcon = document.getElementById("toastIcon");

        if (!toast || !toastMessage) return;

        toastMessage.textContent = msg;
        toast.className = `toast ${isError ? 'error' : 'success'}`;
        toastIcon.className = isError ? "fa-solid fa-circle-xmark" : "fa-solid fa-circle-check";

        toast.style.display = "flex";

        setTimeout(() => {
            toast.style.display = "none";
        }, 3500);
    }
});
