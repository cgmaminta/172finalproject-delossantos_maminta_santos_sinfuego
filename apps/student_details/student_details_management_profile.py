from datetime import date

import dash_bootstrap_components as dbc
import pandas as pd
from dash import ALL, dcc, html, callback_context, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import app
from apps import dbconnect as db
from apps.class_profiles.class_profiles_management import get_triggered_component
from apps.academic_year import is_year_ended, school_year_from_semester


PATH_PREFIX = "/student-details/"
BACK_PATH = "/class_profiles/class_profiles_management"


# =============================================================================
# HELPERS
# =============================================================================

def parse_class_id(pathname):
    """Extract the class ID from /student-details/<class_id>."""
    if not pathname or not pathname.startswith(PATH_PREFIX):
        return None
    tail = pathname.rstrip("/").rsplit("/", 1)[-1]
    return int(tail) if tail.isdigit() else None


def clean(value):
    """Turn NaN/NaT/None into None; otherwise return the value."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def clean_text(value):
    value = clean(value)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def format_age(value):
    """Age is derived in SQL from the birthdate; it is never stored."""
    value = clean(value)
    return str(int(value)) if value is not None else "—"


def format_birthdate(value):
    value = clean(value)
    if value is None:
        return "—"
    return value.strftime("%b %d, %Y") if hasattr(value, "strftime") else str(value)[:10]


def birthdate_to_input(value):
    """Value for a dbc.Input(type='date') (YYYY-MM-DD) or None."""
    value = clean(value)
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)[:10]


def parse_birthdate(value):
    """Return (date, error). The birthdate is optional (None when blank)."""
    if value is None or str(value).strip() == "":
        return None, None
    try:
        born = date.fromisoformat(str(value)[:10])
    except ValueError:
        return None, "Birthdate must be a valid date."
    today = date.today()
    if born > today:
        return None, "Birthdate cannot be in the future."
    if today.year - born.year > 99:
        return None, "Please check the birthdate; it makes the student over 99."
    return born, None


def full_name(last, first, middle):
    """Format as 'Last, First Middle'."""
    name = f"{clean_text(last) or ''}, {clean_text(first) or ''}".strip(", ")
    middle = clean_text(middle)
    return f"{name} {middle}" if middle else name


def is_valid_lrn(text):
    return bool(text) and text.isdigit() and len(text) == 12


# =============================================================================
# PAGE LAYOUT
# =============================================================================

layout = html.Div(
    [
        dcc.Store(id="sd_refresh_save", data=0),
        dcc.Store(id="sd_refresh_remove", data=0),
        dcc.Store(id="sd_editing_lrn", data=None),   # the student's ORIGINAL LRN
        dcc.Store(id="sd_pending_remove_enrolment_id", data=None),

        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Button(
                            "← Back to Class Profiles",
                            href=BACK_PATH,
                            color="secondary",
                            outline=True,
                            size="sm",
                            className="mb-3",
                        ),
                        html.H2(
                            "Class Students",
                            id="sd_class_title",
                            className="fw-bold text-primary",
                        ),
                        html.P("", id="sd_class_meta", className="text-muted"),
                    ],
                    width=8,
                ),
                dbc.Col(
                    dbc.Button(
                        "Add a Student",
                        id="sd_add_btn",
                        color="success",
                        n_clicks=0,
                    ),
                    width=4,
                    className="text-end align-self-center",
                ),
            ],
            className="mb-3",
        ),

        dbc.Alert(
            id="sd_page_alert",
            is_open=False,
            dismissable=True,
            duration=5000,
        ),

        dbc.Row(
            [
                dbc.Col(
                    dbc.Input(
                        id="sd_search",
                        type="text",
                        placeholder="Search by student name...",
                    ),
                    md=4,
                    xs=12,
                    className="mb-2",
                ),
                dbc.Col(
                    dbc.Select(
                        id="sd_sex_filter",
                        options=[
                            {"label": "All sexes", "value": "all"},
                            {"label": "Male", "value": "Male"},
                            {"label": "Female", "value": "Female"},
                        ],
                        value="all",
                    ),
                    md=3,
                    xs=12,
                    className="mb-2",
                ),
            ],
            className="mb-2",
        ),

        dbc.Card(
            [
                dbc.CardHeader(html.H5("Enrolled Students", className="m-0 fw-bold")),
                dbc.CardBody(html.Div(id="sd_student_list")),
            ],
            className="shadow-sm",
        ),

        # Add / edit student modal
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Add a Student", id="sd_modal_title")),
                dbc.ModalBody(
                    [
                        dbc.Alert(
                            id="sd_modal_alert",
                            is_open=False,
                            dismissable=True,
                            className="mb-3",
                        ),
                        dbc.Label("LRN (12 digits)", className="fw-bold"),
                        dbc.Input(
                            id="sd_lrn",
                            type="text",
                            inputMode="numeric",
                            maxLength=12,
                            placeholder="e.g. 123456789012",
                            className="mb-3",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label("Last Name", className="fw-bold"),
                                        dbc.Input(id="sd_last_name", type="text", maxLength=70),
                                    ],
                                    md=4,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("First Name", className="fw-bold"),
                                        dbc.Input(id="sd_first_name", type="text", maxLength=70),
                                    ],
                                    md=4,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Middle Name (optional)", className="fw-bold"),
                                        dbc.Input(id="sd_middle_name", type="text", maxLength=70),
                                    ],
                                    md=4,
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label("Birthdate", className="fw-bold"),
                                        dbc.Input(
                                            id="sd_birthdate",
                                            type="date",
                                            max=date.today().isoformat(),
                                        ),
                                        dbc.FormText("Age is calculated automatically from the birthdate."),
                                    ],
                                    md=6,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Sex", className="fw-bold"),
                                        dbc.Select(
                                            id="sd_sex",
                                            options=[
                                                {"label": "Male", "value": "Male"},
                                                {"label": "Female", "value": "Female"},
                                            ],
                                            placeholder="Select",
                                        ),
                                    ],
                                    md=6,
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.Label("Address", className="fw-bold"),
                        dbc.Input(
                            id="sd_address",
                            type="text",
                            maxLength=90,
                            placeholder="Home address",
                        ),
                    ]
                ),
                dbc.ModalFooter(
                    [
                        dbc.Button(
                            "Cancel",
                            id="sd_cancel_btn",
                            color="secondary",
                            outline=True,
                        ),
                        dbc.Button("Save Student", id="sd_save_btn", color="success"),
                    ]
                ),
            ],
            id="sd_modal",
            is_open=False,
            centered=True,
            size="lg",
        ),

        dcc.ConfirmDialog(
            id="sd_confirm_remove",
            message=(
                "Remove this student from the class? Their student record and "
                "enrolment history will be retained."
            ),
        ),
    ]
)


# =============================================================================
# CALLBACK: CLASS HEADER
# =============================================================================

@app.callback(
    [
        Output("sd_class_title", "children"),
        Output("sd_class_meta", "children"),
        Output("sd_add_btn", "disabled"),
    ],
    [Input("url", "pathname")],
)
def load_class_header(pathname):
    class_id = parse_class_id(pathname)
    if class_id is None:
        raise PreventUpdate

    sql = """
        SELECT sc.grade_level, sc.student_section, pc.semester, t.teacher_name
        FROM student_class sc
        LEFT JOIN program_cycle pc ON sc.cycle_id = pc.cycle_id
        LEFT JOIN teacher t ON sc.employee_id = t.employee_id
        WHERE sc.class_id = %s
          AND COALESCE(sc.class_delete_ind, FALSE) = FALSE
    """
    df = db.getDataFromDB(
        sql,
        [class_id],
        ["grade_level", "student_section", "semester", "teacher_name"],
    )

    if df is None or df.empty:
        return "Class not found", "This class does not exist or was deleted.", True

    row = df.iloc[0]
    title = f"Grade {row['grade_level']} - {row['student_section']}"
    meta = f"Teacher: {clean_text(row['teacher_name']) or 'No teacher assigned'}"

    # The page shows no academic year or quarter. The class's year is only used
    # to stop new enrolments once that academic year has been ended.
    year_ended = is_year_ended(school_year_from_semester(row["semester"]))
    if year_ended:
        meta += " | Academic year ended (students can no longer be added)"

    return title, meta, year_ended


# =============================================================================
# CALLBACK: STUDENT LIST
# =============================================================================

@app.callback(
    Output("sd_student_list", "children"),
    [
        Input("url", "pathname"),
        Input("sd_search", "value"),
        Input("sd_sex_filter", "value"),
        Input("sd_refresh_save", "data"),
        Input("sd_refresh_remove", "data"),
    ],
)
def load_student_list(pathname, search, sex_filter, _refresh_save, _refresh_remove):
    class_id = parse_class_id(pathname)
    if class_id is None:
        raise PreventUpdate

    search_text = (search or "").strip().lower()
    like_value = f"%{search_text}%"
    sex_value = "" if sex_filter in (None, "all") else sex_filter

    # Search matches "First Middle Last" and "Last First Middle" orderings.
    sql = """
        SELECT s.student_lrn, s.student_last_name, s.student_first_name,
               s.student_middle_name, s.student_birthdate,
               EXTRACT(YEAR FROM AGE(CURRENT_DATE, s.student_birthdate))::int AS student_age,
               s.student_sex::text, s.student_address, pe.enrolment_id
        FROM program_enrolment pe
        JOIN student s ON pe.student_lrn = s.student_lrn
        WHERE pe.class_id = %s
          AND COALESCE(pe.enrolment_status, TRUE) = TRUE
          AND COALESCE(s.student_delete_ind, FALSE) = FALSE
          AND (
                %s = ''
                OR LOWER(CONCAT_WS(' ', s.student_first_name,
                                        s.student_middle_name,
                                        s.student_last_name)) LIKE %s
                OR LOWER(CONCAT_WS(' ', s.student_last_name,
                                        s.student_first_name,
                                        s.student_middle_name)) LIKE %s
          )
          AND (%s = '' OR s.student_sex::text = %s)
        ORDER BY LOWER(BTRIM(s.student_last_name)),
                 LOWER(BTRIM(s.student_first_name)),
                 LOWER(BTRIM(COALESCE(s.student_middle_name, ''))),
                 s.student_lrn
    """
    df = db.getDataFromDB(
        sql,
        [class_id, search_text, like_value, like_value, sex_value, sex_value],
        [
            "student_lrn", "last_name", "first_name", "middle_name",
            "birthdate", "age", "sex", "address", "enrolment_id",
        ],
    )

    if df is None or df.empty:
        message = (
            "No students match your search or filter."
            if (search_text or sex_value)
            else "No students enrolled yet. Click 'Add a Student' to get started."
        )
        return dbc.Alert(message, color="info", className="m-0")

    header = html.Thead(
        html.Tr(
            [
                html.Th("#"),
                html.Th("LRN"),
                html.Th("Name"),
                html.Th("Birthdate"),
                html.Th("Age"),
                html.Th("Sex"),
                html.Th("Address"),
                html.Th("Actions", className="text-end"),
            ]
        )
    )

    body_rows = []
    for number, (_, row) in enumerate(df.iterrows(), start=1):
        lrn = int(row["student_lrn"])
        enrolment_id = int(row["enrolment_id"])

        body_rows.append(
            html.Tr(
                [
                    html.Td(number),
                    html.Td(lrn),
                    html.Td(
                        full_name(row["last_name"], row["first_name"], row["middle_name"]),
                        className="fw-semibold",
                    ),
                    html.Td(format_birthdate(row["birthdate"])),
                    html.Td(format_age(row["age"])),
                    html.Td(clean_text(row["sex"]) or "—"),
                    html.Td(clean_text(row["address"]) or "—"),
                    html.Td(
                        [
                            dbc.Button(
                                "Edit",
                                id={"type": "sd_edit", "index": lrn},
                                color="info",
                                outline=True,
                                size="sm",
                                className="me-2",
                                n_clicks=0,
                            ),
                            dbc.Button(
                                "Remove",
                                id={"type": "sd_remove", "index": enrolment_id},
                                color="danger",
                                outline=True,
                                size="sm",
                                n_clicks=0,
                            ),
                        ],
                        className="text-end",
                    ),
                ]
            )
        )

    return dbc.Table(
        [header, html.Tbody(body_rows)],
        hover=True,
        responsive=True,
        className="align-middle mb-0",
    )


# =============================================================================
# CALLBACK: ADD / EDIT STUDENT (MODAL + SAVE)
# =============================================================================

@app.callback(
    [
        Output("sd_modal", "is_open"),
        Output("sd_modal_title", "children"),
        Output("sd_modal_alert", "children"),
        Output("sd_modal_alert", "color"),
        Output("sd_modal_alert", "is_open"),
        Output("sd_page_alert", "children"),
        Output("sd_page_alert", "color"),
        Output("sd_page_alert", "is_open"),
        Output("sd_lrn", "value"),
        Output("sd_last_name", "value"),
        Output("sd_first_name", "value"),
        Output("sd_middle_name", "value"),
        Output("sd_birthdate", "value"),
        Output("sd_sex", "value"),
        Output("sd_address", "value"),
        Output("sd_editing_lrn", "data"),
        Output("sd_refresh_save", "data"),
    ],
    [
        Input("sd_add_btn", "n_clicks"),
        Input("sd_cancel_btn", "n_clicks"),
        Input("sd_save_btn", "n_clicks"),
        Input({"type": "sd_edit", "index": ALL}, "n_clicks"),
    ],
    [
        State("url", "pathname"),
        State("sd_lrn", "value"),
        State("sd_last_name", "value"),
        State("sd_first_name", "value"),
        State("sd_middle_name", "value"),
        State("sd_birthdate", "value"),
        State("sd_sex", "value"),
        State("sd_address", "value"),
        State("sd_editing_lrn", "data"),
        State("sd_refresh_save", "data"),
    ],
    prevent_initial_call=True,
)
def manage_student_modal(
    add_clicks, cancel_clicks, save_clicks, edit_clicks,
    pathname, lrn_input, last_name, first_name, middle_name,
    birthdate, sex, address, editing_lrn, refresh_value,
):
    class_id = parse_class_id(pathname)
    if class_id is None:
        raise PreventUpdate

    trigger_id = get_triggered_component()
    if trigger_id is None:
        raise PreventUpdate

    # Ignore buttons that were just (re)rendered with n_clicks = 0.
    triggered = callback_context.triggered
    if not triggered or not triggered[0].get("value"):
        raise PreventUpdate

    # Defaults: change nothing.
    modal_open = no_update
    modal_title = no_update
    modal_alert = ("", "warning", False)
    page_alert = (no_update, no_update, no_update)
    fields = [no_update] * 7   # lrn, last, first, middle, birthdate, sex, address
    editing_output = no_update
    refresh_output = no_update

    # ---------- Add ----------
    if trigger_id == "sd_add_btn":
        modal_open = True
        modal_title = "Add a Student"
        fields = [None] * 7
        editing_output = None

    # ---------- Edit (open) ----------
    elif isinstance(trigger_id, dict) and trigger_id.get("type") == "sd_edit":
        lrn = int(trigger_id["index"])
        df = db.getDataFromDB(
            """
            SELECT student_last_name, student_first_name, student_middle_name,
                   student_birthdate, student_sex::text, student_address
            FROM student
            WHERE student_lrn = %s
              AND COALESCE(student_delete_ind, FALSE) = FALSE
            """,
            [lrn],
            ["last_name", "first_name", "middle_name", "birthdate", "sex", "address"],
        )
        if df is None or df.empty:
            page_alert = ("This student could not be found.", "warning", True)
        else:
            row = df.iloc[0]
            fields = [
                str(lrn),
                clean_text(row["last_name"]),
                clean_text(row["first_name"]),
                clean_text(row["middle_name"]),
                birthdate_to_input(row["birthdate"]),
                clean_text(row["sex"]),
                clean_text(row["address"]),
            ]
            modal_open = True
            modal_title = "Edit Student"
            editing_output = lrn          # remember the original LRN

    # ---------- Cancel ----------
    elif trigger_id == "sd_cancel_btn":
        modal_open = False
        editing_output = None

    # ---------- Save ----------
    elif trigger_id == "sd_save_btn":
        lrn_text = clean_text(lrn_input)
        last_value = clean_text(last_name)
        first_value = clean_text(first_name)
        middle_value = clean_text(middle_name)
        sex_value = clean_text(sex)
        address_value = clean_text(address)
        birth_value, birth_error = parse_birthdate(birthdate)

        is_new = editing_lrn is None

        if not is_valid_lrn(lrn_text):
            modal_alert = ("LRN must be exactly 12 digits.", "warning", True)
            modal_open = True
        elif not last_value or not first_value:
            modal_alert = ("Please enter the student's last name and first name.", "warning", True)
            modal_open = True
        elif birth_error:
            modal_alert = (birth_error, "warning", True)
            modal_open = True
        else:
            try:
                new_lrn = int(lrn_text)

                if not is_new:
                    old_lrn = int(editing_lrn)

                    # If the LRN was corrected, make sure the new one is free.
                    if new_lrn != old_lrn:
                        df_dup = db.getDataFromDB(
                            "SELECT student_lrn FROM student WHERE student_lrn = %s",
                            [new_lrn],
                            ["student_lrn"],
                        )
                        if df_dup is not None and not df_dup.empty:
                            raise ValueError(
                                "Another student record already uses this LRN."
                            )

                    # ON UPDATE CASCADE on the foreign keys carries the new
                    # LRN through to the enrolment records.
                    db.modifyDB(
                        """
                        UPDATE student
                        SET student_lrn = %s,
                            student_last_name = %s,
                            student_first_name = %s,
                            student_middle_name = %s,
                            student_birthdate = %s,
                            student_sex = %s,
                            student_address = %s
                        WHERE student_lrn = %s
                          AND COALESCE(student_delete_ind, FALSE) = FALSE
                        """,
                        [
                            new_lrn, last_value, first_value, middle_value,
                            birth_value, sex_value, address_value, old_lrn,
                        ],
                    )
                    page_alert = ("Student updated successfully.", "success", True)
                else:
                    lrn = new_lrn

                    # Does a student with this LRN already exist?
                    df_match = db.getDataFromDB(
                        """
                        SELECT student_lrn, COALESCE(student_delete_ind, FALSE)
                        FROM student
                        WHERE student_lrn = %s
                        """,
                        [lrn],
                        ["student_lrn", "deleted"],
                    )

                    if df_match is not None and not df_match.empty:
                        if bool(df_match.iloc[0]["deleted"]):
                            raise ValueError(
                                "This LRN belongs to a deleted student record. "
                                "Please contact an administrator to restore it."
                            )
                        # Existing student: reuse the record and just enrol them.
                    else:
                        db.modifyDB(
                            """
                            INSERT INTO student
                                (student_lrn, student_last_name, student_first_name,
                                 student_middle_name, student_birthdate, student_sex,
                                 student_address)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            [
                                lrn, last_value, first_value, middle_value,
                                birth_value, sex_value, address_value,
                            ],
                        )

                    # Is the student already in this class?
                    df_enrol = db.getDataFromDB(
                        """
                        SELECT enrolment_id, COALESCE(enrolment_status, TRUE)
                        FROM program_enrolment
                        WHERE student_lrn = %s AND class_id = %s
                        ORDER BY enrolment_id
                        LIMIT 1
                        """,
                        [lrn, class_id],
                        ["enrolment_id", "status"],
                    )

                    if df_enrol is not None and not df_enrol.empty:
                        if bool(df_enrol.iloc[0]["status"]):
                            raise ValueError("This student is already enrolled in this class.")
                        db.modifyDB(
                            "UPDATE program_enrolment SET enrolment_status = TRUE WHERE enrolment_id = %s",
                            [int(df_enrol.iloc[0]["enrolment_id"])],
                        )
                    else:
                        db.modifyDB(
                            """
                            INSERT INTO program_enrolment (student_lrn, class_id, enrolment_status)
                            VALUES (%s, %s, TRUE)
                            """,
                            [lrn, class_id],
                        )
                    page_alert = ("Student added to the class.", "success", True)

                modal_open = False
                editing_output = None
                refresh_output = (refresh_value or 0) + 1

            except ValueError as exc:
                modal_alert = (str(exc), "warning", True)
                modal_open = True
            except Exception as exc:
                modal_alert = (f"Unable to save student: {exc}", "danger", True)
                modal_open = True

    return (
        modal_open, modal_title,
        modal_alert[0], modal_alert[1], modal_alert[2],
        page_alert[0], page_alert[1], page_alert[2],
        *fields,
        editing_output, refresh_output,
    )


# =============================================================================
# CALLBACK: REMOVE STUDENT FROM CLASS (SOFT)
# =============================================================================

@app.callback(
    [
        Output("sd_confirm_remove", "displayed"),
        Output("sd_pending_remove_enrolment_id", "data"),
        Output("sd_refresh_remove", "data"),
    ],
    [
        Input({"type": "sd_remove", "index": ALL}, "n_clicks"),
        Input("sd_confirm_remove", "submit_n_clicks"),
    ],
    [
        State("sd_pending_remove_enrolment_id", "data"),
        State("sd_refresh_remove", "data"),
    ],
    prevent_initial_call=True,
)
def remove_student(remove_clicks, confirm_clicks, pending_id, refresh_value):
    trigger_id = get_triggered_component()
    triggered = callback_context.triggered
    if trigger_id is None or not triggered or not triggered[0].get("value"):
        raise PreventUpdate

    if trigger_id == "sd_confirm_remove":
        if pending_id is None:
            raise PreventUpdate
        db.modifyDB(
            "UPDATE program_enrolment SET enrolment_status = FALSE WHERE enrolment_id = %s",
            [int(pending_id)],
        )
        return False, None, (refresh_value or 0) + 1

    if isinstance(trigger_id, dict) and trigger_id.get("type") == "sd_remove":
        return True, int(trigger_id["index"]), no_update

    raise PreventUpdate