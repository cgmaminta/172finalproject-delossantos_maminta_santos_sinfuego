import dash_bootstrap_components as dbc
from dash import html


def nav_link(label, icon, href, extra=""):
    return dbc.NavLink(
        [
            html.I(className=f"bi bi-{icon} sidebar-icon"),
            html.Span(label, className="sidebar-label"),
        ],
        href=href,
        className=f"sidebar-link {extra}".strip(),
    )


navbar = html.Div(
    [
        html.Div(
            [
                html.Span(html.I(className="bi bi-list"), className="sidebar-toggle"),
                html.Span("Feeding Program DBMS", className="sidebar-brand"),
            ],
            className="sidebar-header",
        ),
        nav_link("Home", "house-fill", "/home"),
        nav_link("Health Records", "card-checklist",
                 "/school_health_records/health_records_management"),
        nav_link("Daily Log", "calendar-check", "/daily_log/daily_log_management"),
        nav_link("Class Profiles", "people", "/class_profiles/class_profiles_management"),
        nav_link("Meal Plans", "basket", "/meal_plans/meal_plans_management"),
        nav_link("Reports", "bar-chart-line", "/reports/report"),
        nav_link("Logout", "box-arrow-right", "/logout", extra="sidebar-logout"),
    ],
    className="app-sidebar",
)