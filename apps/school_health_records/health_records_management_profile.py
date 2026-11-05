
import pandas as pd
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

from app import app
from apps import dbconnect as db

PATH_PREFIX = "/school_health_records/health_records_management_profile"
BACK_PATH = "/school_health_records/health_records_management"
HEALTH_RECORDS_PATH = "/school_health_records/student_health_records"


def parse_cycle_id(pathname):
    if not pathname or not pathname.startswith(PATH_PREFIX):
        return None
    tail = pathname.rstrip("/").rsplit("/", 1)[-1]
    return int(tail) if tail.isdigit() else None


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


layout = html.Div([
    dbc.Button("← Back to School Years", href=BACK_PATH,
               color="secondary", outline=True, size="sm", className="mb-3"),
    html.H2("Quarter Classes", id="pemp_cycle_title", className="fw-bold text-primary"),
    html.P("All active classes assigned to this quarter.", className="text-muted"),
    dbc.Alert(id="pemp_page_alert", is_open=False, dismissable=True),
    
    # Add grade filters
    dbc.Card(
        [
        dbc.CardHeader(
            html.H5("Active Classes", className="m-0 fw-bold")
            ),
            dbc.CardBody([
        dbc.Row([
            dbc.Col([
                dbc.Label("Filter Classes by Grade Level",
                          className="fw-bold"),

                dcc.Dropdown(
                    id="pemp_grade_filter",
                    options=[],
                    value=None,
                    placeholder="All Grade Levels",
                    clearable=True,
                    searchable=True
                )
            ], md=4)
        ], className="mb-4"),

        html.Div(id="pemp_class_list")
    ])
], className="shadow-sm"),
])

@app.callback(
    [
        Output("pemp_grade_filter", "options"),
        Output("pemp_grade_filter", "value")
    ],
    Input("url", "pathname")
)

def populate_grade_filter(pathname):

    cycle_id = parse_cycle_id(pathname)

    if cycle_id is None:
        raise PreventUpdate

    grades = db.getDataFromDB(
        """
        SELECT DISTINCT grade_level
        FROM student_class
        WHERE cycle_id = %s
          AND COALESCE(class_delete_ind, FALSE) = FALSE
          AND COALESCE(class_archive_ind, FALSE) = FALSE
        ORDER BY grade_level
        """,
        [cycle_id],
        ["grade_level"]
    )

    options = []

    if grades is not None and not grades.empty:
        options = [
            {
                "label": f"Grade {int(row['grade_level'])}",
                "value": int(row["grade_level"])
            }
            for _, row in grades.iterrows()
        ]

    # Reset the filter whenever a different quarter is opened.
    return options, None


@app.callback(
    [
        Output("pemp_cycle_title", "children"),
        Output("pemp_class_list", "children")
        ],

    [
        Input("url", "pathname"),
        Input("pemp_grade_filter", "value")
        ]
)

def render_quarter_classes(pathname, selected_grade):

    # DEBUGGING
    #print("CALLBACK RUNNING") 
    #print("PATHNAME:", pathname)
    #print("SELECTED grade:", selected_grade)

    cycle_id = parse_cycle_id(pathname)

    if cycle_id is None:
        raise PreventUpdate

    cycle = db.getDataFromDB(
        "SELECT semester FROM program_cycle WHERE cycle_id = %s",
        [cycle_id], ["semester"])
    if cycle is None or cycle.empty:
        return "Quarter Not Found", dbc.Alert("This quarter does not exist.", color="warning")

    label = clean_text(cycle.iloc[0]["semester"]) or f"Quarter {cycle_id}"
    classes = db.getDataFromDB(
        """SELECT sc.class_id, sc.grade_level, sc.student_section, t.teacher_name,
                  COUNT(pe.enrolment_id) FILTER (WHERE pe.enrolment_id IS NOT NULL) AS student_count,
                  COUNT(pe.enrolment_id) FILTER (WHERE UPPER(BTRIM(COALESCE(pe.priority_level, ''))) = 'HIGH') AS high_count,
                  COUNT(pe.enrolment_id) FILTER (WHERE UPPER(BTRIM(COALESCE(pe.priority_level, ''))) = 'MEDIUM') AS medium_count,
                  COUNT(pe.enrolment_id) FILTER (WHERE UPPER(BTRIM(COALESCE(pe.priority_level, ''))) = 'LOW') AS low_count
           FROM student_class sc
           LEFT JOIN teacher t ON t.employee_id = sc.employee_id
           LEFT JOIN program_enrolment pe ON pe.class_id = sc.class_id
                AND COALESCE(pe.enrolment_status, TRUE) = TRUE
           WHERE sc.cycle_id = %s
             AND COALESCE(sc.class_delete_ind, FALSE) = FALSE
             AND COALESCE(sc.class_archive_ind, FALSE) = FALSE
           GROUP BY sc.class_id, sc.grade_level, sc.student_section, t.teacher_name
           ORDER BY sc.grade_level, sc.student_section""",
        [cycle_id], ["class_id", "grade_level", "student_section", "teacher_name",
                     "student_count", "high_count", "medium_count", "low_count"])

    if classes is None or classes.empty:
        return label, dbc.Alert(
            "No active classes are assigned to this quarter yet. Assign classes through Class Profiles.",
            color="info")
     
        # Filter classes according to the selected grade level.
    if selected_grade is not None:
        classes = classes[
            pd.to_numeric(
                classes["grade_level"],
                errors="coerce"
            ) == int(selected_grade)
        ]

        if classes.empty:
            message=(
                f"No active classes found for Grade {selected_grade} in this quarter."
                if selected_grade is not None
                else "No active classes are assigned to this quarter yet.")
            
            return label, dbc.Alert(
                message,
                color="info",
                className="mt-3"
            )
        
    cards = []
    for _, row in classes.iterrows():
        class_id = int(row["class_id"])
        class_title = f"Grade {int(row['grade_level'])} - {clean_text(row['student_section']) or ''}"
        teacher = clean_text(row["teacher_name"]) or "No teacher assigned"
        student_count = int(row["student_count"] or 0)
        priorities = dbc.Row([
            dbc.Col(dbc.Badge(f"High: {int(row['high_count'] or 0)}", color="danger", className="w-100 py-2"), width=4),
            dbc.Col(dbc.Badge(f"Medium: {int(row['medium_count'] or 0)}", color="warning", text_color="dark", className="w-100 py-2"), width=4),
            dbc.Col(dbc.Badge(f"Low: {int(row['low_count'] or 0)}", color="success", className="w-100 py-2"), width=4),
        ], className="g-2 mb-3 text-center")
        cards.append(dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H5(class_title, className="fw-bold mb-2"),
                html.P(f"Quarter: {label}", className="text-muted mb-1"),
                html.P(f"Teacher: {teacher}", className="mb-1"),
                html.P(f"Enrolled students: {student_count}", className="mb-3"),
                priorities,
                dbc.Button("View Enrolled Students", href=f"{HEALTH_RECORDS_PATH}/{cycle_id}/{class_id}",
                           color="primary", outline=True, className="w-100"),
            ]), className="h-100 shadow-sm"), xs=12, md=6, lg=4, className="mb-3"))

    return label, dbc.Row(cards)
