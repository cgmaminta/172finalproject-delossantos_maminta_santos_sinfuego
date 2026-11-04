import json

import dash_bootstrap_components as dbc
from dash import ALL, dcc, html, callback_context
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import app
from apps import dbconnect as db


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
                    width=8,
                ),
                dbc.Col(
                    dbc.Button(
                        "Add a Class",
                        id="add_class_btn",
                        color="success",
                        n_clicks=0,
                        disabled=False,
                    ),
                    width=4,
                    className="text-end align-self-center",
                ),
            ],
            className="mb-3",
        ),

        dbc.Row(
            [
                dbc.Col(
                    dbc.Label("Show classes"),
                    width="auto",
                    className="align-self-center",
                ),
                dbc.Col(
                    dcc.Dropdown(
                        id="class_view_filter",
                        options=[
                            {"label": "Active Classes", "value": "active"},
                            {"label": "Archived Classes", "value": "archived"},
                        ],
                        value="active",
                        clearable=False,
                        searchable=False,
                    ),
                    md=4,
                    xs=8,
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

        # Create class modal
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Create a Class", id="class_modal_title")),
                dbc.ModalBody(
                    [
                        # Duplicate-section and validation alerts appear inside
                        # the modal so they remain visible above the form.
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
                                        dbc.Label("School Year", className="fw-bold"),
                                        dbc.Input(
                                            id="class_school_year",
                                            type="text",
                                            placeholder="e.g. 2026-2027",
                                        ),
                                    ],
                                    md=6,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Quarter", className="fw-bold"),
                                        dbc.Select(
                                            id="class_quarter",
                                            options=[
                                                {"label": "1st Quarter", "value": "1st Quarter"},
                                                {"label": "2nd Quarter", "value": "2nd Quarter"},
                                                {"label": "3rd Quarter", "value": "3rd Quarter"},
                                                {"label": "4th Quarter", "value": "4th Quarter"},
                                            ],
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

        # Native browser confirmation before soft-deleting a class
        dcc.ConfirmDialog(
            id="confirm_delete_class",
            message=(
                "Delete this class? It will be removed from the active and "
                "archived lists, but its database record and enrolment history "
                "will be retained."
            ),
        ),
    ]
)


# =============================================================================
# CALLBACK: CREATE CLASSES AND DISPLAY ACTIVE / ARCHIVED CLASSES
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
        Input("class_view_filter", "value"),
        Input("class_profile_refresh_store", "data"),
        Input({"type": "edit_class", "index": ALL}, "n_clicks"),
    ],
    [
        State("class_modal", "is_open"),
        State("class_grade_level", "value"),
        State("class_section", "value"),
        State("class_school_year", "value"),
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
    view_filter,
    refresh_value,
    edit_clicks,
    is_open,
    grade,
    section,
    school_year,
    quarter,
    teacher_id,
    editing_class_id,
):
    
    if not pathname or pathname.rstrip("/") != PAGE_PATH.rstrip("/"):
        raise PreventUpdate

    trigger_id = get_triggered_component()

    modal_open = bool(is_open)
    teacher_options = []
    alert_text = ""
    alert_color = "success"
    alert_open = False
    grade_output = grade
    section_output = section
    school_year_output = school_year
    quarter_output = quarter
    teacher_output = teacher_id
    modal_title = "Create a Class"
    editing_id_output = editing_class_id

    if trigger_id == "add_class_btn":
        modal_open = True
        teacher_options = get_teacher_options()
        grade_output = None
        section_output = None
        school_year_output = None
        quarter_output = None
        teacher_output = None
        modal_title = "Create a Class"
        editing_id_output = None

    elif isinstance(trigger_id, dict) and trigger_id.get("type") == "edit_class":
        class_id_to_edit = int(trigger_id["index"])
        sql_edit = """
            SELECT
                sc.grade_level,
                sc.student_section,
                pc.semester,
                sc.employee_id
            FROM student_class sc
            LEFT JOIN program_cycle pc ON sc.cycle_id = pc.cycle_id
            WHERE sc.class_id = %s
              AND COALESCE(sc.class_delete_ind, FALSE) = FALSE
        """
        df_edit = db.getDataFromDB(
            sql_edit,
            [class_id_to_edit],
            ["grade_level", "student_section", "semester", "employee_id"],
        )

        if df_edit is None or df_edit.empty:
            alert_text = "This class could not be found."
            alert_color = "warning"
            alert_open = True
            modal_open = False
            editing_id_output = None
        else:
            edit_row = df_edit.iloc[0]
            semester = str(edit_row["semester"] or "")
            if " - " in semester:
                school_year_output, quarter_output = semester.rsplit(" - ", 1)
            else:
                school_year_output, quarter_output = "", None

            grade_output = int(edit_row["grade_level"])
            section_output = edit_row["student_section"]
            teacher_output = (
                int(edit_row["employee_id"])
                if edit_row["employee_id"] is not None
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
        required_values = [grade, section, school_year, quarter]

        if not all(value is not None and str(value).strip() for value in required_values):
            alert_text = "Please complete Grade Level, Section, School Year, and Quarter."
            alert_color = "warning"
            alert_open = True
            modal_open = True
        else:
            try:
                grade_value = int(grade)
                if grade_value < 1 or grade_value > 6:
                    raise ValueError("Grade Level must be between 1 and 6.")

                section_value = section.strip()
                cycle_id = get_or_create_cycle(school_year, quarter)

                if cycle_id is None:
                    raise ValueError("Could not find or create the selected academic period.")

                # Section names must be unique across grade levels in the
                # same academic period. When editing, exclude this class itself.
                sql_check = """
                    SELECT class_id
                    FROM student_class
                    WHERE LOWER(BTRIM(student_section)) = LOWER(BTRIM(%s))
                      AND cycle_id = %s
                      AND COALESCE(class_delete_ind, FALSE) = FALSE
                      AND (%s IS NULL OR class_id <> %s)
                    LIMIT 1
                """
                df_existing = db.getDataFromDB(
                    sql_check,
                    [section_value, cycle_id, editing_class_id, editing_class_id],
                    ["class_id"],
                )

                if df_existing is not None and not df_existing.empty:
                    alert_text = (
                        "This section name is already used in the selected "
                        "school year and quarter, regardless of grade level."
                    )
                    alert_color = "warning"
                    alert_open = True
                    modal_open = True
                elif editing_class_id is not None:
                    sql_update = """
                        UPDATE student_class
                        SET grade_level = %s,
                            student_section = %s,
                            cycle_id = %s,
                            employee_id = %s
                        WHERE class_id = %s
                          AND COALESCE(class_delete_ind, FALSE) = FALSE
                    """
                    db.modifyDB(
                        sql_update,
                        [grade_value, section_value, cycle_id, teacher_id, editing_class_id],
                    )
                    alert_text = "Class updated successfully."
                    alert_open = True
                    modal_open = False
                    editing_id_output = None
                else:
                    sql_insert = """
                        INSERT INTO student_class
                            (grade_level, student_section, cycle_id, employee_id)
                        VALUES (%s, %s, %s, %s)
                    """
                    db.modifyDB(
                        sql_insert,
                        [grade_value, section_value, cycle_id, teacher_id],
                    )
                    alert_text = "Class created successfully."
                    alert_open = True
                    modal_open = False

            except Exception as exc:
                alert_text = f"Unable to create class: {exc}"
                alert_color = "danger"
                alert_open = True
                modal_open = True

    # Load only non-deleted classes, then select active or archived records.
    if view_filter == "archived":
        archive_condition = "COALESCE(sc.class_archive_ind, FALSE) = TRUE"
        empty_message = "There are no archived classes."
    else:
        archive_condition = "COALESCE(sc.class_archive_ind, FALSE) = FALSE"
        empty_message = "No active classes yet. Click 'Add a Class' to get started."

    sql_classes = f"""
        SELECT
            sc.class_id,
            sc.grade_level,
            sc.student_section,
            pc.semester,
            t.teacher_name,
            COUNT(pe.enrolment_id) AS student_count
        FROM student_class sc
        LEFT JOIN program_cycle pc
            ON sc.cycle_id = pc.cycle_id
        LEFT JOIN teacher t
            ON sc.employee_id = t.employee_id
        LEFT JOIN program_enrolment pe
            ON sc.class_id = pe.class_id
           AND COALESCE(pe.enrolment_status, TRUE) = TRUE
        WHERE COALESCE(sc.class_delete_ind, FALSE) = FALSE
          AND {archive_condition}
        GROUP BY
            sc.class_id,
            sc.grade_level,
            sc.student_section,
            pc.semester,
            t.teacher_name
        ORDER BY sc.grade_level, sc.student_section
    """

    df_classes = db.getDataFromDB(
        sql_classes,
        [],
        [
            "class_id",
            "grade_level",
            "student_section",
            "semester",
            "teacher_name",
            "student_count",
        ],
    )

    if df_classes is None or df_classes.empty:
        class_content = dbc.Alert(empty_message, color="info", className="m-0")
    else:
        class_cards = []

        for _, row in df_classes.iterrows():
            class_id = int(row["class_id"])
            class_title = f"Grade {row['grade_level']} - {row['student_section']}"
            academic_period = row["semester"] or "Academic period not specified"
            teacher_name = row["teacher_name"] or "No teacher assigned"
            student_count = int(row["student_count"] or 0)

            card_actions = [
                dbc.Button(
                    "View Enrolled Students",
                    href=f"/student-details/{class_id}",
                    color="primary",
                    outline=True,
                    className="w-100 mb-2",
                )
            ]

            card_actions.append(
                dbc.Button(
                    "Edit Class Details",
                    id={"type": "edit_class", "index": class_id},
                    color="info",
                    outline=True,
                    className="w-100 mb-2",
                    n_clicks=0,
                )
            )

            if view_filter == "archived":
                card_actions.append(
                    dbc.Button(
                        "Restore",
                        id={"type": "restore_class", "index": class_id},
                        color="success",
                        outline=True,
                        className="w-100 mb-2",
                        n_clicks=0,
                    )
                )
            else:
                card_actions.append(
                    dbc.Button(
                        "Archive",
                        id={"type": "archive_class", "index": class_id},
                        color="warning",
                        outline=True,
                        className="w-100 mb-2",
                        n_clicks=0,
                    )
                )

            card_actions.append(
                dbc.Button(
                    "Delete",
                    id={"type": "delete_class", "index": class_id},
                    color="danger",
                    outline=True,
                    className="w-100",
                    n_clicks=0,
                )
            )

            class_cards.append(
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H5(class_title, className="fw-bold mb-2"),
                                html.P(academic_period, className="text-muted mb-1"),
                                html.P(f"Teacher: {teacher_name}", className="mb-1"),
                                html.P(
                                    f"Enrolled students: {student_count}",
                                    className="mb-3",
                                ),
                                html.Div(card_actions),
                            ]
                        ),
                        className="h-100 shadow-sm",
                    ),
                    xs=12,
                    md=6,
                    lg=4,
                    className="mb-3",
                )
            )

        class_content = dbc.Row(class_cards)

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
# CALLBACK: ARCHIVE, RESTORE, AND SOFT-DELETE CLASSES
# =============================================================================

@app.callback(
    [
        Output("confirm_delete_class", "displayed"),
        Output("pending_delete_class_id", "data"),
        Output("class_profile_refresh_store", "data"),
    ],
    [
        Input({"type": "archive_class", "index": ALL}, "n_clicks"),
        Input({"type": "restore_class", "index": ALL}, "n_clicks"),
        Input({"type": "delete_class", "index": ALL}, "n_clicks"),
        Input("confirm_delete_class", "submit_n_clicks"),
    ],
    [
        State("pending_delete_class_id", "data"),
        State("class_profile_refresh_store", "data"),
    ],
    prevent_initial_call=True,
)
def manage_class_status(
    archive_clicks,
    restore_clicks,
    delete_clicks,
    confirm_clicks,
    pending_delete_id,
    refresh_value,
):
    trigger_id = get_triggered_component()
    if trigger_id is None:
        raise PreventUpdate

    # Ignore pattern-matching button insertions where n_clicks is still 0.
    # Only process an actual click or confirmation.
    triggered = callback_context.triggered
    if not triggered or not triggered[0].get("value"):
        raise PreventUpdate

    refresh_value = (refresh_value or 0) + 1

    # User confirmed the delete dialog. Soft-delete the class so enrolment
    # history remains in the database.
    if trigger_id == "confirm_delete_class":
        if pending_delete_id is None:
            raise PreventUpdate

        db.modifyDB(
            """
            UPDATE student_class
            SET class_delete_ind = TRUE,
                class_archive_ind = FALSE
            WHERE class_id = %s
            """,
            [int(pending_delete_id)],
        )
        return False, None, refresh_value

    # Pattern-matching button IDs contain the class ID in their "index".
    if not isinstance(trigger_id, dict):
        raise PreventUpdate

    class_id = int(trigger_id["index"])
    action_type = trigger_id["type"]

    if action_type == "archive_class":
        db.modifyDB(
            """
            UPDATE student_class
            SET class_archive_ind = TRUE
            WHERE class_id = %s
              AND COALESCE(class_delete_ind, FALSE) = FALSE
            """,
            [class_id],
        )
        return False, None, refresh_value

    if action_type == "restore_class":
        # Do not restore if another non-deleted class already uses this
        # section name in the same academic period.
        sql_conflict = """
            SELECT other.class_id
            FROM student_class current_class
            JOIN student_class other
              ON other.cycle_id = current_class.cycle_id
             AND LOWER(BTRIM(other.student_section)) =
                 LOWER(BTRIM(current_class.student_section))
             AND other.class_id <> current_class.class_id
            WHERE current_class.class_id = %s
              AND COALESCE(other.class_delete_ind, FALSE) = FALSE
            LIMIT 1
        """
        df_conflict = db.getDataFromDB(sql_conflict, [class_id], ["class_id"])

        if df_conflict is not None and not df_conflict.empty:
            # Leave it archived; the user can resolve the duplicate first.
            return False, None, refresh_value

        db.modifyDB(
            """
            UPDATE student_class
            SET class_archive_ind = FALSE
            WHERE class_id = %s
              AND COALESCE(class_delete_ind, FALSE) = FALSE
            """,
            [class_id],
        )
        return False, None, refresh_value

    if action_type == "delete_class":
        return True, class_id, refresh_value - 1

    raise PreventUpdate
