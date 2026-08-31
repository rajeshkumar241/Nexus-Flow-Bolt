/* =========================================================
   NEXUS FLOW AI - NOTIFICATIONS DROPDOWN SCRIPT
   Bell toggle, fetch + render notifications, mark read/all read.
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {
    const toggleBtn = document.getElementById("notifToggleBtn");
    const dropdown = document.getElementById("notifDropdown");
    const badge = document.getElementById("notifBadge");
    const list = document.getElementById("notifList");
    const markAllBtn = document.getElementById("notifMarkAllBtn");

    if (!toggleBtn || !dropdown) return;

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function updateBadge(count) {
        if (!badge) return;
        if (count > 0) {
            badge.textContent = count > 99 ? "99+" : String(count);
            badge.style.display = "flex";
        } else {
            badge.textContent = "";
            badge.style.display = "none";
        }
    }

    function timeAgo(iso) {
        if (!iso) return "Just now";
        const then = new Date(iso);
        if (isNaN(then.getTime())) return "Just now";
        const delta = Math.max(0, (Date.now() - then.getTime()) / 1000);
        if (delta < 60) return "Just now";
        if (delta < 3600) return Math.floor(delta / 60) + "m ago";
        if (delta < 86400) return Math.floor(delta / 3600) + "h ago";
        const days = Math.floor(delta / 86400);
        if (days < 7) return days + "d ago";
        return then.toLocaleDateString();
    }

    function iconFor(type) {
        switch (type) {
            case "success": return "fa-circle-check";
            case "warning": return "fa-triangle-exclamation";
            case "error": return "fa-circle-xmark";
            default: return "fa-circle-info";
        }
    }

    function render(items) {
        if (!list) return;
        list.innerHTML = "";
        if (!items.length) {
            list.innerHTML = '<div class="notif-empty"><i class="fa-solid fa-bell-slash"></i><span>No notifications yet.</span></div>';
            return;
        }
        items.forEach((n) => {
            const row = document.createElement("div");
            row.className = "notif-item " + (n.read ? "is-read" : "unread");
            row.innerHTML =
                '<div class="notif-icon type-' + escapeHtml(n.type || "info") + '">' +
                    '<i class="fa-solid ' + iconFor(n.type || "info") + '"></i>' +
                '</div>' +
                '<div class="notif-body">' +
                    '<div class="notif-text">' + escapeHtml(n.title || "") + "</div>" +
                    (n.message ? '<div class="notif-msg">' + escapeHtml(n.message) + "</div>" : "") +
                    '<div class="notif-time">' + timeAgo(n.created_at) + "</div>" +
                "</div>";
            if (!n.read) {
                row.addEventListener("click", () => markRead(n.id, row));
            }
            list.appendChild(row);
        });
    }

    function loadNotifications() {
        fetch("/notifications")
            .then((res) => res.json())
            .then((data) => {
                if (data.success) {
                    updateBadge(data.unread_count || 0);
                    render(data.notifications || []);
                }
            })
            .catch(() => {});
    }

    function markRead(id, row) {
        fetch("/notifications/read/" + encodeURIComponent(id), { method: "POST" })
            .then((res) => res.json())
            .then((data) => {
                if (data.success) {
                    row.classList.remove("unread");
                    row.classList.add("is-read");
                    updateBadge(data.unread_count);
                }
            })
            .catch(() => {});
    }

    function markAllRead() {
        fetch("/notifications/read-all", { method: "POST" })
            .then((res) => res.json())
            .then((data) => {
                if (data.success) {
                    updateBadge(0);
                    if (list) {
                        list.querySelectorAll(".notif-item").forEach((el) => {
                            el.classList.remove("unread");
                            el.classList.add("is-read");
                        });
                    }
                }
            })
            .catch(() => {});
    }

    function toggleDropdown() {
        const isOpen = dropdown.classList.contains("open");
        if (!isOpen) loadNotifications();
        dropdown.classList.toggle("open");
    }

    toggleBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleDropdown();
    });

    if (markAllBtn) {
        markAllBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            markAllRead();
        });
    }

    document.addEventListener("click", (e) => {
        if (!e.target.closest(".nav-notifications-wrap")) {
            dropdown.classList.remove("open");
        }
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            dropdown.classList.remove("open");
        }
    });

    // Keep the badge fresh without opening the panel
    setInterval(() => {
        fetch("/notifications")
            .then((res) => res.json())
            .then((data) => {
                if (data.success) updateBadge(data.unread_count || 0);
            })
            .catch(() => {});
    }, 30000);
});