"""Nexus Flow AI - Design Pattern Library: Dashboard Patterns

Contains design architecture patterns for:
1. Analytics Dashboard
2. Admin Panel
"""

from typing import Dict, Any

DASHBOARD_PATTERNS: Dict[str, Dict[str, Any]] = {
    "analytics": {
        "id": "dash_analytics",
        "name": "Real-Time Analytics & Telemetry Dashboard",
        "category": "dashboard",
        "description": "Information-rich telemetry and data visualization platform with real-time KPI metrics, chart breakdowns, and funnel analytics.",
        "layout": {
            "type": "dashboard_shell",
            "sidebar_width": "260px",
            "topbar_height": "64px",
        },
        "sections": [
            {"name": "App Topbar", "type": "topbar", "components": ["Search bar", "Date Range Picker (Last 30 Days)", "Export Report button", "Notifications Bell with badge", "User avatar"]},
            {"name": "Summary KPI Cards", "type": "kpis", "components": [
                "Total Revenue ($128,420, +18.2% vs last month)",
                "Active Users (42,890, +8.4%)",
                "Conversion Rate (4.62%, +0.8%)",
                "Average Session Duration (4m 32s, +12s)"
            ]},
            {"name": "Revenue & Traffic Chart", "type": "main_chart", "components": ["Interactive line/area chart with hover tooltip data points", "Legend toggle (Pageviews, Unique Visitors, Conversions)"]},
            {"name": "Traffic Sources & Geographics", "type": "secondary_charts", "components": ["Donut chart of traffic sources (Organic, Direct, Social, Referral)", "Country breakdown list with progress bars"]},
            {"name": "Recent Events Log", "type": "live_log", "components": ["Real-time event stream table with user tags, actions, IP geolocation, and timestamp"]},
        ],
        "design_hints": {
            "palette": "Deep dark navy/slate background with neon blue, cyan, and emerald data lines",
            "typography": "Tabular numbers with monospace alignment for stat values",
        }
    },
    "admin_panel": {
        "id": "dash_admin_panel",
        "name": "Enterprise Admin & Operations Panel",
        "category": "dashboard",
        "description": "Comprehensive administrative control center with user permissions, system health telemetry, role management, and audit logs.",
        "layout": {
            "type": "admin_layout",
            "sidebar_width": "250px",
        },
        "sections": [
            {"name": "Admin Sidebar", "type": "sidebar", "components": ["Admin Badge", "Navigation (Overview, Users, Roles, Database, Logs, Settings)", "System Status Widget (CPU: 24%, Mem: 48%)"]},
            {"name": "System Health Overview", "type": "health_cards", "components": ["Database latency (12ms - Healthy)", "API error rate (0.01% - Normal)", "Active Workers (8/8 Online)", "Daily Storage Growth (+2.4GB)"]},
            {"name": "User Management Table", "type": "user_table", "components": ["Filter by Role (Admin, Editor, Viewer)", "Status Filter (Active, Suspended, Pending)", "Batch action bar (Delete, Change Role, Export)", "User table rows with avatar, email, 2FA status, last login, and action dropdown menu"]},
            {"name": "Security & Audit Stream", "type": "audit_trail", "components": ["Audit trail log showing admin email, action type, IP address, and timestamp", "Severity badges (Info, Warning, Critical)"]},
            {"name": "Quick Configuration Drawer", "type": "config_modal", "components": ["Feature flags toggle switches", "Maintenance mode toggle", "API key regeneration form"]},
        ],
        "design_hints": {
            "clarity": "High-contrast borders, clear status badges, warning confirmation modals on destructive actions",
            "density": "Compact table padding and fast keyboard navigation support",
        }
    }
}
