import json

import dash_bootstrap_components as dbc
import pandas as pd
from dash import ALL, dcc, html, callback_context, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import app
from apps import dbconnect as db
from apps.academic_year import (
    QUARTERS,
    end_current_school_year,
    ensure_quarter_cycles,
    get_current_school_year,
    get_school_year_options,
    is_year_ended,
    next_school_year,
    quarter_from_semester,
    school_year_from_semester,
)


PAGE_PATH = "/class_profiles/class_profiles_management"


# =============================================================================
# DATABASE HELPERS
# =============================================================================

def get_teacher_options():
    sql = """
        SELECT employee_id, teacher_name
        FROM teacher
        WHERE COALESCE(teacher_delete_ind, FALSE) = FALSE
        ORDER BY teacher_name
    """
    df = db.getDataFromDB(sql, [], ["employee_id", "teacher_name"])

    if df is None or df.empty:
        return []

    return [
        {"label": row["teacher_name"], "value": int(row["employee_id"])}
        for _, row in df.iterrows()
    ]


def get_or_create_cycle(school_year, quarter):
    semester_label = f"{school_year.strip()} - {quarter}"

    sql_find = """
        SELECT cycle_id
        FROM program_cycle
        WHERE semester = %s
        ORDER BY cycle_id
        LIMIT 1
    """
    df = db.getDataFromDB(sql_find, [semester_label], ["cycle_id"])

    if df is not None and not df.empty:
        return int(df.iloc[0]["cycle_id"])

    db.modifyDB(
        "INSERT INTO program_cycle (semester) VALUES (%s)",
        [semester_label],
    )

    df = db.getDataFromDB(sql_find, [semester_label], ["cycle_id"])
    if df is None or df.empty:
        return None

    return int(df.iloc[0]["cycle_id"])


def get_triggered_component():
    """Return the ID of the component that triggered the current callback."""
    triggered = callback_context.triggered
    if not triggered:
        return None

    component_id = triggered[0]["prop_id"].rsplit(".", 1)[0]

    # Pattern-matching IDs are serialized as JSON strings.
    if component_id.startswith("{"):
        try:
            return json.loads(component_id)
        except json.JSONDecodeError:
            return component_id

    return component_id


# =============================================================================
# PAGE LAYOUT
# =============================================================================

layout = html.Div(
    [
        dcc.Store(id="class_profile_refresh_store", data=0),
        dcc.Store(id="class_year_refresh", data=0),
        dcc.Store(id="pending_delete_class_id", data=None),
        dcc.Store(id="editing_class_id", data=None),

        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H2("Class Profiles", className="fw-bold text-primary"),
                        html.P(
                            "Create and manage classes. Select a class to view its students.",
                            className="text-muted",
                        ),
                    ],
                    md=6,
                ),
                dbc.Col(
                    [
                        dbc.Button(
                            "End Academic Year",
                            id="end_year_btn",
                            color="warning",
                            outline=True,
                            n_clicks=0,
                            className="me-2",
                        ),
                        dbc.Button(
                            "Add a Class",
                            id="add_class_btn",
                            color="success",
                            n_clicks=0,
                            disabled=False,
                        ),
                    ],
                    md=6,
                    className="text-md-end align-self-center",
                ),
            ],
            className="mb-3",
        ),

        # Page-level alert (End Academic Year result, etc.)
        dbc.Alert(id="class_page_alert", is_open=False, dismissable=True, duration=6000),

        # Filters: academic year, then quarter
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Academic Year", className="fw-bold"),
                        dcc.Dropdown(
                            id="class_year_filter",
                            options=[],
                            value=None,
                            clearable=False,
                            searchable=False,
                        ),
                    ],
                    md=3,
                    xs=6,
                ),
                dbc.Col(
                    [
                        dbc.Label("Quarter", className="fw-bold"),
                        dcc.Dropdown(
                            id="class_quarter_filter",
                            options=[{"label": "All Quarters", "value": "all"}]
                            + [{"label": q, "value": q} for q in QUARTERS],
                            value="all",
                            clearable=False,
                            searchable=False,
                        ),
                    ],
                    md=3,
                    xs=6,
                ),
                dbc.Col(
                    html.Div(id="class_year_status", className="text-muted small"),
                    md=6,
                    className="align-self-end pb-2",
                ),
            ],
            className="mb-3",
        ),

        dbc.Card(
            [
                dbc.CardHeader(
                    html.H5("List of Classes", className="m-0 fw-bold")
                ),
                dbc.CardBody(html.Div(id="class_list_container")),
            ],
            className="shadow-sm",
        ),

        # Create / edit class modal
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Create a Class", id="class_modal_title")),
                dbc.ModalBody(
                    [
                        dbc.Alert(
                            id="class_alert",
                            is_open=False,
                            dismissable=True,
                            className="mb-3",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label("Grade Level", className="fw-bold"),
                                        dbc.Input(
                                            id="class_grade_level",
                                            type="number",
                                            min=1,
                                            max=6,
                                            step=1,
                                            placeholder="e.g. 1",
                                        ),
                                    ],
                                    md=4,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Section", className="fw-bold"),
                                        dbc.Input(
                                            id="class_section",
                                            type="text",
                                            maxLength=70,
                                            placeholder="e.g. Sampaguita",
                                        ),
                                    ],
                                    md=8,
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label("Academic Year", className="fw-bold"),
                                        # Read-only: classes are always created in
                                        # the current academic year.
                                        dbc.Input(
                                            id="class_school_year",
                                            type="text",
                                            disabled=True,
                                        ),
                                    ],
                                    md=6,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Quarter", className="fw-bold"),
                                        dbc.Select(
                                            id="class_quarter",
                                            options=[{"label": q, "value": q} for q in QUARTERS],
                                            placeholder="Select Quarter",
                                        ),
                                    ],
                                    md=6,
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.Label("Assigned Teacher", className="fw-bold"),
                        dcc.Dropdown(
                            id="class_teacher_dropdown",
                            options=[],
                            placeholder="Select Teacher (optional)",
                            clearable=True,
                        ),
                    ]
                ),
                dbc.ModalFooter(
                    [
                        dbc.Button(
                            "Cancel",
                            id="class_modal_cancel_btn",
                            color="secondary",
                            outline=True,
                        ),
                        dbc.Button(
                            "Save Class",
                            id="class_modal_save_btn",
                            color="success",
                        ),
                    ]
                ),
            ],
            id="class_modal",
            is_open=False,
            centered=True,
        ),

        dcc.ConfirmDialog(
            id="confirm_delete_class",
            message=(
                "Delete this class? It will be removed from the class list, "
                "but its database record and enrolment history will be retained."
            ),
        ),

        dcc.ConfirmDialog(id="confirm_end_year", message=""),
    ]
)


# =============================================================================
# CALLBACK: ACADEMIC-YEAR DROPDOWN
# =============================================================================

@app.callback(
    [
        Output("class_year_filter", "options"),
        Output("class_year_filter", "value"),
    ],
    [
        Input("url", "pathname"),
        Input("class_year_refresh", "data"),
    ],
    [State("class_year_filter", "value")],
)
def populate_year_filter(pathname, _year_refresh, current_value):
    if not pathname or pathname.rstrip("/") != PAGE_PATH.rstrip("/"):
        raise PreventUpdate

    options = get_school_year_options()
    valid = {item["value"] for item in options}
    trigger = get_triggered_component()

    # Keep the user's selection, except right after ending a year (or on first
    # load), when the dropdown jumps to the current academic year.
    if trigger == "class_year_refresh" or current_value not in valid:
        value = get_current_school_year()
    else:
        value = current_value

    return options, value


# =============================================================================
# CALLBACK: YEAR STATUS, ADD BUTTON, END-YEAR CONFIRMATION TEXT
# =============================================================================

@app.callback(
    [
        Output("class_year_status", "children"),
        Output("add_class_btn", "disabled"),
        Output("confirm_end_year", "message"),
    ],
    [
        Input("class_year_filter", "value"),
        Input("class_year_refresh", "data"),
    ],
)
def update_year_controls(selected_year, _year_refresh):
    current = get_current_school_year()
    selected = selected_year or current
    ended = is_year_ended(selected)

    # Nothing is shown for the current year; ended years get a small note.
    status = (
        f"Academic year {selected} has ended. Its classes are view-only."
        if ended else ""
    )

    message = (
        f"End academic year {current}?\n\n"
        f"{next_school_year(current)} will become the current academic year. "
        f"Classes and student records from {current} stay viewable but can no "
        f"longer be changed. This cannot be undone."
    )
    return status, ended, message


# =============================================================================
# CALLBACK: END ACADEMIC YEAR
# =============================================================================

@app.callback(
    [
        Output("confirm_end_year", "displayed"),
        Output("class_year_refresh", "data"),
        Output("class_page_alert", "children"),
        Output("class_page_alert", "color"),
        Output("class_page_alert", "is_open"),
    ],
    [
        Input("end_year_btn", "n_clicks"),
        Input("confirm_end_year", "submit_n_clicks"),
    ],
    [State("class_year_refresh", "data")],
    prevent_initial_call=True,
)
def end_academic_year(end_clicks, confirm_clicks, refresh_value):
    trigger_id = get_triggered_component()
    triggered = callback_context.triggered
    if trigger_id is None or not triggered or not triggered[0].get("value"):
        raise PreventUpdate

    if trigger_id == "end_year_btn":
        return True, no_update, no_update, no_update, no_update

    if trigger_id == "confirm_end_year":
        try:
            ended, new_year = end_current_school_year()
        except Exception as exc:
            return False, no_update, f"Unable to end the academic year: {exc}", "danger", True
        return (
            False,
            (refresh_value or 0) + 1,
            f"Academic year {ended} has ended. {new_year} is now the current academic year.",
            "success",
            True,
        )

    raise PreventUpdate


# =============================================================================
# CALLBACK: CREATE / EDIT CLASSES AND DISPLAY THE CLASS LIST
# =============================================================================

@app.callback(
    [
        Output("class_modal", "is_open"),
        Output("class_teacher_dropdown", "options"),
        Output("class_alert", "children"),
        Output("class_alert", "color"),
        Output("class_alert", "is_open"),
        Output("class_list_container", "children"),
        Output("class_grade_level", "value"),
        Output("class_section", "value"),
        Output("class_school_year", "value"),
        Output("class_quarter", "value"),
        Output("class_teacher_dropdown", "value"),
        Output("class_modal_title", "children"),
        Output("editing_class_id", "data"),
    ],
    [
        Input("url", "pathname"),
        Input("add_class_btn", "n_clicks"),
        Input("class_modal_cancel_btn", "n_clicks"),
        Input("class_modal_save_btn", "n_clicks"),
        Input("class_year_filter", "value"),
        Input("class_quarter_filter", "value"),
        Input("class_profile_refresh_store", "data"),
        Input({"type": "edit_class", "index": ALL}, "n_clicks"),
    ],
    [
        State("class_modal", "is_open"),
        State("class_grade_level", "value"),
        State("class_section", "value"),
        State("class_quarter", "value"),
        State("class_teacher_dropdown", "value"),
        State("editing_class_id", "data"),
    ],
)
def manage_class_profiles(
    pathname,
    add_clicks,
    cancel_clicks,
    save_clicks,
    year_filter,
    quarter_filter,
    refresh_value,
    edit_clicks,
    is_open,
    grade,
    section,
    quarter,
    teacher_id,
    editing_class_id,
):
    if not pathname or pathname.rstrip("/") != PAGE_PATH.rstrip("/"):
        raise PreventUpdate

    trigger_id = get_triggered_component()
    triggered = callback_context.triggered
    triggered_value = triggered[0].get("value") if triggered else None

    current_year = get_current_school_year()
    selected_year = year_filter or current_year
    year_is_open = not is_year_ended(selected_year)

    modal_open = bool(is_open)
    teacher_options = no_update
    alert_text = ""
    alert_color = "success"
    alert_open = False
    grade_output = grade
    section_output = section
    school_year_output = current_year
    quarter_output = quarter
    teacher_output = teacher_id
    modal_title = "Create a Class"
    editing_id_output = editing_class_id

    if trigger_id == "add_class_btn":
        modal_open = True
        teacher_options = get_teacher_options()
        grade_output = None
        section_output = None
        school_year_output = current_year
        quarter_output = None
        teacher_output = None
        modal_title = "Create a Class"
        editing_id_output = None

    elif (
        isinstance(trigger_id, dict)
        and trigger_id.get("type") == "edit_class"
        and triggered_value
    ):
        class_id_to_edit = int(trigger_id["index"])
        df_edit = db.getDataFromDB(
            """
            SELECT sc.grade_level, sc.student_section, pc.semester, sc.employee_id
            FROM student_class sc
            LEFT JOIN program_cycle pc ON sc.cycle_id = pc.cycle_id
            WHERE sc.class_id = %s
              AND COALESCE(sc.class_delete_ind, FALSE) = FALSE
            """,
            [class_id_to_edit],
            ["grade_level", "student_section", "semester", "employee_id"],
        )

        if df_edit is None or df_edit.empty:
            alert_text = "This class could not be found."
            alert_color = "warning"
            alert_open = True
            modal_open = False
            editing_id_output = None
        elif is_year_ended(school_year_from_semester(df_edit.iloc[0]["semester"])):
            alert_text = "This class belongs to an ended academic year and can no longer be edited."
            alert_color = "warning"
            alert_open = True
            modal_open = False
            editing_id_output = None
        else:
            edit_row = df_edit.iloc[0]
            semester = str(edit_row["semester"] or "")
            school_year_output = school_year_from_semester(semester) or current_year
            quarter_output = quarter_from_semester(semester)
            grade_output = int(edit_row["grade_level"])
            section_output = edit_row["student_section"]
            teacher_output = (
                int(edit_row["employee_id"])
                if pd.notna(edit_row["employee_id"])
                else None
            )
            editing_id_output = class_id_to_edit
            modal_title = "Edit Class"
            modal_open = True
            teacher_options = get_teacher_options()

    elif trigger_id == "class_modal_cancel_btn":
        modal_open = False
        editing_id_output = None

    elif trigger_id == "class_modal_save_btn":
        if not all(value is not None and str(value).strip() for value in [grade, section, quarter]):
            alert_text = "Please complete Grade Level, Section, and Quarter."
            alert_color = "warning"
            alert_open = True
            modal_open = True
        else:
            try:
                grade_value = int(grade)
                if grade_value < 1 or grade_value > 6:
                    raise ValueError("Grade Level must be between 1 and 6.")

                section_value = section.strip()

                # Classes are always saved into the CURRENT academic year.
                ensure_quarter_cycles(current_year)
                cycle_id = get_or_create_cycle(current_year, quarter)
                if cycle_id is None:
                    raise ValueError("Could not find or create the selected academic period.")

                # Section names must be unique across ALL grade levels, academic
                # years and quarters. When editing, exclude the class itself.
                df_existing = db.getDataFromDB(
                    """
                    SELECT class_id
                    FROM student_class
                    WHERE LOWER(BTRIM(student_section)) = LOWER(BTRIM(%s))
                      AND COALESCE(class_delete_ind, FALSE) = FALSE
                      AND (%s IS NULL OR class_id <> %s)
                    LIMIT 1
                    """,
                    [section_value, editing_class_id, editing_class_id],
                    ["class_id"],
                )

                if df_existing is not None and not df_existing.empty:
                    alert_text = (
                        "This section name is already in use. Section names "
                        "must be unique across all grade levels, academic "
                        "years and quarters."
                    )
                    alert_color = "warning"
                    alert_open = True
                    modal_open = True
                elif editing_class_id is not None:
                    db.modifyDB(
                        """
                        UPDATE student_class
                        SET grade_level = %s,
                            student_section = %s,
                            cycle_id = %s,
                            employee_id = %s
                        WHERE class_id = %s
                          AND COALESCE(class_delete_ind, FALSE) = FALSE
                        """,
                        [grade_value, section_value, cycle_id, teacher_id, editing_class_id],
                    )
                    alert_text = "Class updated successfully."
                    alert_open = True
                    modal_open = False
                    editing_id_output = None
                else:
                    db.modifyDB(
                        """
                        INSERT INTO student_class
                            (grade_level, student_section, cycle_id, employee_id)
                        VALUES (%s, %s, %s, %s)
                        """,
                        [grade_value, section_value, cycle_id, teacher_id],
                    )
                    alert_text = "Class created successfully."
                    alert_open = True
                    modal_open = False

            except Exception as exc:
                alert_text = f"Unable to save class: {exc}"
                alert_color = "danger"
                alert_open = True
                modal_open = True

    # -------------------------------------------------------------------------
    # Class list for the selected academic year (+ optional quarter)
    # -------------------------------------------------------------------------
    sql_classes = """
        SELECT
            sc.class_id,
            sc.grade_level,
            sc.student_section,
            pc.semester,
            t.teacher_name,
            COUNT(pe.enrolment_id) AS student_count
        FROM student_class sc
        JOIN program_cycle pc
            ON sc.cycle_id = pc.cycle_id
        LEFT JOIN teacher t
            ON sc.employee_id = t.employee_id
        LEFT JOIN program_enrolment pe
            ON sc.class_id = pe.class_id
           AND COALESCE(pe.enrolment_status, TRUE) = TRUE
        WHERE COALESCE(sc.class_delete_ind, FALSE) = FALSE
          AND pc.semester LIKE %s
          {quarter_clause}
        GROUP BY
            sc.class_id, sc.grade_level, sc.student_section,
            pc.semester, t.teacher_name
    """
    params = [f"{selected_year} - %"]
    if quarter_filter and quarter_filter != "all":
        quarter_clause = "AND pc.semester = %s"
        params.append(f"{selected_year} - {quarter_filter}")
    else:
        quarter_clause = ""

    df_classes = db.getDataFromDB(
        sql_classes.format(quarter_clause=quarter_clause),
        params,
        ["class_id", "grade_level", "student_section", "semester",
         "teacher_name", "student_count"],
    )

    if df_classes is None or df_classes.empty:
        empty_message = (
            "No classes match the selected academic year and quarter."
            if not year_is_open
            else "No classes yet for this selection. Click 'Add a Class' to get started."
        )
        class_content = dbc.Alert(empty_message, color="info", className="m-0")
    else:
        # Sort by quarter, then grade level, then section.
        df_classes["quarter_name"] = df_classes["semester"].map(quarter_from_semester)
        df_classes["quarter_order"] = df_classes["quarter_name"].map(
            lambda q: QUARTERS.index(q) if q in QUARTERS else len(QUARTERS)
        )
        df_classes = df_classes.sort_values(
            ["quarter_order", "grade_level", "student_section"]
        )

        header = html.Thead(
            html.Tr(
                [
                    html.Th("Grade"),
                    html.Th("Section"),
                    html.Th("Quarter"),
                    html.Th("Teacher"),
                    html.Th("Enrolled", className="text-center"),
                    html.Th("Actions", className="text-end"),
                ]
            )
        )

        body_rows = []
        for _, row in df_classes.iterrows():
            class_id = int(row["class_id"])

            actions = [
                dbc.Button(
                    "View Students",
                    href=f"/student-details/{class_id}",
                    color="primary",
                    outline=True,
                    size="sm",
                    className="me-2",
                )
            ]
            if year_is_open:
                actions.extend(
                    [
                        dbc.Button(
                            "Edit",
                            id={"type": "edit_class", "index": class_id},
                            color="info",
                            outline=True,
                            size="sm",
                            className="me-2",
                            n_clicks=0,
                        ),
                        dbc.Button(
                            "Delete",
                            id={"type": "delete_class", "index": class_id},
                            color="danger",
                            outline=True,
                            size="sm",
                            n_clicks=0,
                        ),
                    ]
                )

            body_rows.append(
                html.Tr(
                    [
                        html.Td(f"Grade {int(row['grade_level'])}"),
                        html.Td(row["student_section"], className="fw-semibold"),
                        html.Td(row["quarter_name"] or "—"),
                        html.Td(row["teacher_name"] or "No teacher assigned"),
                        html.Td(int(row["student_count"] or 0), className="text-center"),
                        html.Td(actions, className="text-end text-nowrap"),
                    ]
                )
            )

        class_content = dbc.Table(
            [header, html.Tbody(body_rows)],
            hover=True,
            striped=True,
            responsive=True,
            className="align-middle mb-0",
        )

    return (
        modal_open,
        teacher_options,
        alert_text,
        alert_color,
        alert_open,
        class_content,
        grade_output,
        section_output,
        school_year_output,
        quarter_output,
        teacher_output,
        modal_title,
        editing_id_output,
    )


# =============================================================================
# CALLBACK: SOFT-DELETE CLASSES
# (Per-class archive/restore was removed; ending the academic year replaces it.)
# =============================================================================

@app.callback(
    [
        Output("confirm_delete_class", "displayed"),
        Output("pending_delete_class_id", "data"),
        Output("class_profile_refresh_store", "data"),
    ],
    [
        Input({"type": "delete_class", "index": ALL}, "n_clicks"),
        Input("confirm_delete_class", "submit_n_clicks"),
    ],
    [
        State("pending_delete_class_id", "data"),
        State("class_profile_refresh_store", "data"),
    ],
    prevent_initial_call=True,
)
def manage_class_status(delete_clicks, confirm_clicks, pending_delete_id, refresh_value):
    trigger_id = get_triggered_component()
    if trigger_id is None:
        raise PreventUpdate

    # Ignore buttons that were just rendered with n_clicks = 0.
    triggered = callback_context.triggered
    if not triggered or not triggered[0].get("value"):
        raise PreventUpdate

    refresh_value = (refresh_value or 0) + 1

    if trigger_id == "confirm_delete_class":
        if pending_delete_id is None:
            raise PreventUpdate

        db.modifyDB(
            """
            UPDATE student_class
            SET class_delete_ind = TRUE
            WHERE class_id = %s
            """,
            [int(pending_delete_id)],
        )
        return False, None, refresh_value

    if isinstance(trigger_id, dict) and trigger_id.get("type") == "delete_class":
        return True, int(trigger_id["index"]), refresh_value - 1

    raise PreventUpdate