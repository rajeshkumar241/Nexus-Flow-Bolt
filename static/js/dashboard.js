document.addEventListener("DOMContentLoaded", function () {

    // Fetch live data from the API and update stats
    fetch("/dashboard/data")
        .then(function (resp) { return resp.json(); })
        .then(function (result) {
            if (!result.success || !result.data) return;
            var d = result.data;

            // Update stat numbers
            var el;
            el = document.getElementById("dsStatProjects");
            if (el) el.textContent = d.total_projects;

            el = document.getElementById("dsStatSaved");
            if (el) el.textContent = d.total_projects;

            el = document.getElementById("dsStatAI");
            if (el) el.textContent = d.ai_generations;

            el = document.getElementById("dsStatDownloads");
            if (el) el.textContent = d.total_downloads;

            el = document.getElementById("dsStatStorage");
            if (el) el.innerHTML = d.storage_mb + ' <small>MB</small>';

            // Update storage bar
            var barFill = document.querySelector(".ds-stat-bar-fill");
            if (barFill) barFill.style.width = Math.min(100, d.storage_pct) + "%";

            // Update tags with week counts
            var tags = document.querySelectorAll(".ds-stat-tag");
            if (tags[0]) tags[0].textContent = d.new_projects_week + " this week";
            if (tags[3]) tags[3].textContent = d.new_downloads_week + " this week";

            // Update dev activity
            el = document.getElementById("dsDevGenerated");
            if (el) el.textContent = d.total_projects;

            el = document.getElementById("dsDevImproved");
            if (el) el.textContent = d.ai_generations;

            // Update storage ring
            var ringFill = document.querySelector(".ds-ring-fill");
            if (ringFill) {
                var circumference = 2 * Math.PI * 50;
                var offset = (d.storage_pct / 100) * circumference;
                ringFill.style.strokeDasharray = offset + " " + circumference;
            }

            var ringPct = document.querySelector(".ds-ring-pct");
            if (ringPct) ringPct.textContent = d.storage_pct + "%";

            // Update storage info text
            var storageInfo = document.querySelector(".ds-storage-info span:first-child");
            if (storageInfo) storageInfo.textContent = d.storage_mb + " MB of 50 MB";

            // Update storage status
            var storageStatus = document.querySelector(".ds-storage-status");
            if (storageStatus) {
                if (d.storage_pct > 80) {
                    storageStatus.textContent = "Warning";
                    storageStatus.className = "ds-storage-status warning";
                } else {
                    storageStatus.textContent = "Healthy";
                    storageStatus.className = "ds-storage-status";
                }
            }

            // Update timeline if activity data is available
            if (d.activity && d.activity.length > 0) {
                var timelineContainer = document.querySelector(".ds-timeline");
                if (timelineContainer) {
                    var html = "";
                    var items = d.activity.slice(0, 5);
                    for (var i = 0; i < items.length; i++) {
                        var a = items[i];
                        html += '<div class="ds-timeline-row">';
                        html += '<div class="ds-timeline-dot ' + (a.color || 'purple') + '"></div>';
                        html += '<div class="ds-timeline-info">';
                        html += '<span class="ds-timeline-title">' + escapeHtml(a.title) + '</span>';
                        html += '<span class="ds-timeline-desc">' + escapeHtml(a.desc) + '</span>';
                        html += '</div>';
                        html += '<span class="ds-timeline-time">' + escapeHtml(a.time) + '</span>';
                        html += '</div>';
                    }
                    timelineContainer.innerHTML = html;
                }
            }
        })
        .catch(function (err) {
            console.error("Dashboard data fetch error:", err);
        });

    function escapeHtml(str) {
        if (!str) return "";
        var div = document.createElement("div");
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

});
