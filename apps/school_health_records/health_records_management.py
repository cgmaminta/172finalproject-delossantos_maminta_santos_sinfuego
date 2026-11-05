
from datetime import date
import re
import pandas as pd
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

from app import app
from apps import dbconnect as db

PAGE_PATH = "/school_health_records/health_records_management"
PROFILE_PATH = "/school_health_records/health_records_management_profile"
QUARTERS = ["1st Quarter", "2nd Quarter", "3rd Quarter", "4th Quarter"]


def clean_text(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    value = str(value).strip()
    return value or None


def current_school_year():
    """Assumes the Philippine school-year cycle begins in June."""
    today = date.today()
    start_year = today.year if today.month >= 6 else today.year - 1
    return f"{start_year}-{start_year + 1}"


def school_year_from_label(label):
    """Extract 2026-2027 from a legacy semester value."""
    value = clean_text(label) or ""
    match = re.search(r"(20\d{2}\s*-\s*20\d{2})", value)
    return re.sub(r"\s+", "", match.group(1)) if match else None


def get_school_year_options():

    today = date.today()
    start_year = today.year if today.month >= 6 else today.year - 1

    years = [
        f"{start_year + i}-{start_year + i + 1}"
        for i in range(5)
    ]

    return [
        {"label": year, "value": year}
        for year in years
    ]


def ensure_quarter_cycles(school_year):
    """Create missing quarter rows; preserve existing cycle IDs and class links."""
    for quarter in QUARTERS:
        label = f"{school_year} - {quarter}"
        existing = db.getDataFromDB(
            """SELECT cycle_id FROM program_cycle
               WHERE LOWER(BTRIM(semester)) = LOWER(BTRIM(%s))
               LIMIT 1""",
            [label], ["cycle_id"]
        )
        if existing is None or existing.empty:
            db.modifyDB(
                "INSERT INTO program_cycle (semester) VALUES (%s)",
                [label]
            )


layout = html.Div([
    dcc.Store(id="pem_refresh", data=0),

    html.H2("Health Records Management", className="fw-bold text-primary"),
    html.P(
        "Monitor and manage students' health records throughout the School Feeding Program.",
        className="text-muted"
    ),
    dbc.Alert(id="pem_page_alert", is_open=False, dismissable=True, duration=5000),

    dbc.Row([
        dbc.Col([
            dbc.Label("Select School Year", className="fw-bold"),
            dbc.Select(
                id="pem_school_year",
                options=[],
                value=None,
                placeholder="Select school year",
                style={"maxWidth": "260px"}
            )
        ], width="auto"),
        dbc.Col(
            html.Div(id="pem_current_cycle", className="text-muted fw-semibold text-end"),
            className="d-flex align-items-end justify-content-end"
        )
    ], className="mb-3 align-items-end justify-content-between"),

    dbc.Alert([
        html.Strong("Select a quarter"),
        html.Div("Choose a quarter below to view its active classes and enrolled students' health records.")
    ], color="light", className="mb-3"),

    html.Div(id="pem_cycle_list")
])


@app.callback(
    [
        Output("pem_school_year", "options"),
        Output("pem_school_year", "value"),
        Output("pem_cycle_list", "children"),
        Output("pem_current_cycle", "children"),
        Output("pem_page_alert", "children"),
        Output("pem_page_alert", "color"),
        Output("pem_page_alert", "is_open"),
    ],
    [
        Input("url", "pathname"),
        Input("pem_school_year", "value"),
        Input("pem_refresh", "data"),
    ],
)


def render_quarters(pathname, selected_year, _refresh):

    if not pathname or pathname.rstrip("/") != PAGE_PATH.rstrip("/"):
        raise PreventUpdate

    try:
        options = get_school_year_options()
        valid_years = [item["value"] for item in options]
        year = selected_year if selected_year in valid_years else current_school_year()
        if year not in valid_years:
            options.insert(0, {"label": year, "value": year})

        ensure_quarter_cycles(year)

        df = db.getDataFromDB(
            """SELECT cycle_id, semester
               FROM program_cycle
               WHERE semester LIKE %s
               ORDER BY cycle_id""",
            [f"{year} - %"], ["cycle_id", "semester"]
        )

        cycle_by_quarter = {}
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                label = clean_text(row["semester"]) or ""
                for quarter in QUARTERS:
                    if label.lower() == f"{year} - {quarter}".lower():
                        cycle_by_quarter[quarter] = int(row["cycle_id"])
                        break

        cards = []
        for quarter in QUARTERS:
            cycle_id = cycle_by_quarter.get(quarter)
            count = 0
            if cycle_id is not None:
                count_df = db.getDataFromDB(
                    """SELECT COUNT(*) AS class_count
                       FROM student_class
                       WHERE cycle_id = %s
                         AND COALESCE(class_delete_ind, FALSE) = FALSE
                         AND COALESCE(class_archive_ind, FALSE) = FALSE""",
                    [cycle_id], ["class_count"]
                )
                if count_df is not None and not count_df.empty:
                    count = int(count_df.iloc[0]["class_count"] or 0)

            cards.append(
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            html.H5(quarter, className="fw-bold"),
                            html.P(f"School Year {year}", className="text-muted small mb-2"),
                            html.P(
                                f"{count} active class{'es' if count != 1 else ''}",
                                className="text-muted mb-3"
                            ),
                            dbc.Button(
                                "View Active Classes",
                                href=f"{PROFILE_PATH}/{cycle_id}",
                                color="primary",
                                outline=True,
                                className="w-100"
                            )
                        ]),
                        className="h-100 shadow-sm"
                    ),
                    xs=12, sm=6, lg=3, className="mb-3"
                )
            )

        return (
            options, year, dbc.Row(cards),
            f"School Year: {year}", "", "success", False
        )
    except Exception as exc:
        return (
            get_school_year_options(), selected_year, dbc.Alert(
                f"Unable to load quarters: {exc}", color="danger"
            ), "", f"Unable to load school-year quarters: {exc}", "danger", True
        )
