from datetime import date

import dash_bootstrap_components as dbc
import pandas as pd
from dash import ALL, dcc, html, callback_context, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import app
from apps import dbconnect as db
from apps.academic_year import get_current_school_year
from apps.class_profiles.class_profiles_management import get_triggered_component


PAGE_PATH = "/student_details/student_details_management"


# =============================================================================
# HELPERS
# =============================================================================

def clean(value):
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
        dcc.Store(id="sdm_refresh_save", data=0),
        dcc.Store(id="sdm_refresh_delete", data=0),
        dcc.Store(id="sdm_editing_lrn", data=None),   # the student's ORIGINAL LRN
        dcc.Store(id="sdm_pending_delete_lrn", data=None),

        html.H2("Student Directory", className="fw-bold text-primary"),
        html.P(
            "All students across classes. To enrol a new student, open a class "
            "from Class Profiles and use 'Add a Student'.",
            className="text-muted",
        ),

        dbc.Alert(id="sdm_alert", is_open=False, dismissable=True, duration=5000),

        dbc.Row(
            [
                dbc.Col(
                    dbc.Input(
                        id="sdm_search",
                        type="text",
                        placeholder="Search by student name or LRN...",
                    ),
                    md=4,
                    xs=12,
                    className="mb-2",
                ),
                dbc.Col(
                    dbc.Select(
                        id="sdm_sex_filter",
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
                dbc.CardHeader(html.H5("Students", className="m-0 fw-bold")),
                dbc.CardBody(html.Div(id="sdm_student_list")),
            ],
            className="shadow-sm",
        ),

        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Edit Student")),
                dbc.ModalBody(
                    [
                        dbc.Alert(
                            id="sdm_modal_alert",
                            is_open=False,
                            dismissable=True,
                            className="mb-3",
                        ),
                        dbc.Label("LRN (12 digits)", className="fw-bold"),
                        dbc.Input(
                            id="sdm_lrn",
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
                                        dbc.Input(id="sdm_last_name", type="text", maxLength=70),
                                    ],
                                    md=4,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("First Name", className="fw-bold"),
                                        dbc.Input(id="sdm_first_name", type="text", maxLength=70),
                                    ],
                                    md=4,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Middle Name (optional)", className="fw-bold"),
                                        dbc.Input(id="sdm_middle_name", type="text", maxLength=70),
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
                                            id="sdm_birthdate",
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
                                            id="sdm_sex",
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
                        dbc.Input(id="sdm_address", type="text", maxLength=90),
                    ]
                ),
                dbc.ModalFooter(
                    [
                        dbc.Button("Cancel", id="sdm_cancel_btn", color="secondary", outline=True),
                        dbc.Button("Save Changes", id="sdm_save_btn", color="success"),
                    ]
                ),
            ],
            id="sdm_modal",
            is_open=False,
            centered=True,
            size="lg",
        ),

        dcc.ConfirmDialog(
            id="sdm_confirm_delete",
            message=(
                "Delete this student? They will be removed from all classes and "
                "from this directory, but the database record will be retained."
            ),
        ),
    ]
)


# =============================================================================
# STUDENT LIST
# =============================================================================

@app.callback(
    Output("sdm_student_list", "children"),
    [
        Input("url", "pathname"),
        Input("sdm_search", "value"),
        Input("sdm_sex_filter", "value"),
        Input("sdm_refresh_save", "data"),
        Input("sdm_refresh_delete", "data"),
    ],
)
def load_students(pathname, search, sex_filter, _r1, _r2):
    if pathname != PAGE_PATH:
        raise PreventUpdate

    search_text = (search or "").strip().lower()
    like_value = f"%{search_text}%"
    sex_value = "" if sex_filter in (None, "all") else sex_filter

    # Search matches name (either ordering) or the LRN.
    sql = """
        SELECT s.student_lrn, s.student_last_name, s.student_first_name,
               s.student_middle_name, s.student_birthdate,
               EXTRACT(YEAR FROM AGE(CURRENT_DATE, s.student_birthdate))::int AS student_age,
               s.student_sex::text, s.student_address,
               STRING_AGG(
                   DISTINCT 'Grade ' || sc.grade_level || ' - ' || sc.student_section,
                   ', ' ORDER BY 'Grade ' || sc.grade_level || ' - ' || sc.student_section
               ) AS classes
        FROM student s
        LEFT JOIN program_enrolment pe
               ON pe.student_lrn = s.student_lrn
              AND COALESCE(pe.enrolment_status, TRUE) = TRUE
        LEFT JOIN student_class sc
               ON sc.class_id = pe.class_id
              AND COALESCE(sc.class_delete_ind, FALSE) = FALSE
              AND sc.cycle_id IN (SELECT cycle_id FROM program_cycle
                                  WHERE semester LIKE %s)
        WHERE COALESCE(s.student_delete_ind, FALSE) = FALSE
          AND (
                %s = ''
                OR LOWER(CONCAT_WS(' ', s.student_first_name,
                                        s.student_middle_name,
                                        s.student_last_name)) LIKE %s
                OR LOWER(CONCAT_WS(' ', s.student_last_name,
                                        s.student_first_name,
                                        s.student_middle_name)) LIKE %s
                OR s.student_lrn::text LIKE %s
          )
          AND (%s = '' OR s.student_sex::text = %s)
        GROUP BY s.student_lrn, s.student_last_name, s.student_first_name,
                 s.student_middle_name, s.student_birthdate, s.student_sex,
                 s.student_address
        ORDER BY LOWER(BTRIM(s.student_last_name)),
                 LOWER(BTRIM(s.student_first_name)),
                 LOWER(BTRIM(COALESCE(s.student_middle_name, ''))),
                 s.student_lrn
    """
    df = db.getDataFromDB(
        sql,
        [f"{get_current_school_year()} - %",
         search_text, like_value, like_value, like_value, sex_value, sex_value],
        [
            "student_lrn", "last_name", "first_name", "middle_name",
            "birthdate", "age", "sex", "address", "classes",
        ],
    )

    if df is None or df.empty:
        return dbc.Alert("No students found.", color="info", className="m-0")

    header = html.Thead(
        html.Tr(
            [
                html.Th("LRN"),
                html.Th("Name"),
                html.Th("Birthdate"),
                html.Th("Age"),
                html.Th("Sex"),
                html.Th("Address"),
                html.Th("Current Class"),
                html.Th("Actions", className="text-end"),
            ]
        )
    )

    rows = []
    for _, row in df.iterrows():
        lrn = int(row["student_lrn"])
        rows.append(
            html.Tr(
                [
                    html.Td(lrn),
                    html.Td(
                        full_name(row["last_name"], row["first_name"], row["middle_name"]),
                        className="fw-semibold",
                    ),
                    html.Td(format_birthdate(row["birthdate"])),
                    html.Td(format_age(row["age"])),
                    html.Td(clean_text(row["sex"]) or "—"),
                    html.Td(clean_text(row["address"]) or "—"),
                    html.Td(clean_text(row["classes"]) or "Not enrolled"),
                    html.Td(
                        [
                            dbc.Button(
                                "Edit",
                                id={"type": "sdm_edit", "index": lrn},
                                color="info",
                                outline=True,
                                size="sm",
                                className="me-2",
                                n_clicks=0,
                            ),
                            dbc.Button(
                                "Delete",
                                id={"type": "sdm_delete", "index": lrn},
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
        [header, html.Tbody(rows)],
        hover=True,
        responsive=True,
        className="align-middle mb-0",
    )


# =============================================================================
# EDIT MODAL + SAVE
# =============================================================================

@app.callback(
    [
        Output("sdm_modal", "is_open"),
        Output("sdm_modal_alert", "children"),
        Output("sdm_modal_alert", "color"),
        Output("sdm_modal_alert", "is_open"),
        Output("sdm_alert", "children"),
        Output("sdm_alert", "color"),
        Output("sdm_alert", "is_open"),
        Output("sdm_lrn", "value"),
        Output("sdm_last_name", "value"),
        Output("sdm_first_name", "value"),
        Output("sdm_middle_name", "value"),
        Output("sdm_birthdate", "value"),
        Output("sdm_sex", "value"),
        Output("sdm_address", "value"),
        Output("sdm_editing_lrn", "data"),
        Output("sdm_refresh_save", "data"),
    ],
    [
        Input({"type": "sdm_edit", "index": ALL}, "n_clicks"),
        Input("sdm_cancel_btn", "n_clicks"),
        Input("sdm_save_btn", "n_clicks"),
    ],
    [
        State("sdm_lrn", "value"),
        State("sdm_last_name", "value"),
        State("sdm_first_name", "value"),
        State("sdm_middle_name", "value"),
        State("sdm_birthdate", "value"),
        State("sdm_sex", "value"),
        State("sdm_address", "value"),
        State("sdm_editing_lrn", "data"),
        State("sdm_refresh_save", "data"),
    ],
    prevent_initial_call=True,
)
def manage_edit_modal(
    edit_clicks, cancel_clicks, save_clicks,
    lrn_input, last_name, first_name, middle_name, birthdate, sex, address,
    editing_lrn, refresh_value,
):
    trigger_id = get_triggered_component()
    triggered = callback_context.triggered
    if trigger_id is None or not triggered or not triggered[0].get("value"):
        raise PreventUpdate

    modal_open = no_update
    modal_alert = ("", "warning", False)
    page_alert = (no_update, no_update, no_update)
    fields = [no_update] * 7   # lrn, last, first, middle, birthdate, sex, address
    editing_output = no_update
    refresh_output = no_update

    # ---------- Edit (open) ----------
    if isinstance(trigger_id, dict) and trigger_id.get("type") == "sdm_edit":
        lrn = int(trigger_id["index"])
        df = db.getDataFromDB(
            """
            SELECT student_last_name, student_first_name, student_middle_name,
                   student_birthdate, student_sex::text, student_address
            FROM student
            WHERE student_lrn = %s AND COALESCE(student_delete_ind, FALSE) = FALSE
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
            editing_output = lrn          # remember the original LRN

    # ---------- Cancel ----------
    elif trigger_id == "sdm_cancel_btn":
        modal_open = False
        editing_output = None

    # ---------- Save ----------
    elif trigger_id == "sdm_save_btn":
        if editing_lrn is None:
            raise PreventUpdate

        lrn_text = clean_text(lrn_input)
        last_value = clean_text(last_name)
        first_value = clean_text(first_name)
        middle_value = clean_text(middle_name)
        birth_value, birth_error = parse_birthdate(birthdate)

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
                old_lrn = int(editing_lrn)

                # If the LRN was corrected, make sure the new one is free.
                if new_lrn != old_lrn:
                    df_dup = db.getDataFromDB(
                        "SELECT student_lrn FROM student WHERE student_lrn = %s",
                        [new_lrn],
                        ["student_lrn"],
                    )
                    if df_dup is not None and not df_dup.empty:
                        raise ValueError("Another student record already uses this LRN.")

                # ON UPDATE CASCADE on the foreign keys carries the new LRN
                # through to the enrolment records.
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
                        new_lrn, last_value, first_value, middle_value, birth_value,
                        clean_text(sex), clean_text(address), old_lrn,
                    ],
                )
                page_alert = ("Student updated successfully.", "success", True)
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
        modal_open, modal_alert[0], modal_alert[1], modal_alert[2],
        page_alert[0], page_alert[1], page_alert[2],
        *fields, editing_output, refresh_output,
    )


# =============================================================================
# SOFT DELETE
# =============================================================================

@app.callback(
    [
        Output("sdm_confirm_delete", "displayed"),
        Output("sdm_pending_delete_lrn", "data"),
        Output("sdm_refresh_delete", "data"),
    ],
    [
        Input({"type": "sdm_delete", "index": ALL}, "n_clicks"),
        Input("sdm_confirm_delete", "submit_n_clicks"),
    ],
    [
        State("sdm_pending_delete_lrn", "data"),
        State("sdm_refresh_delete", "data"),
    ],
    prevent_initial_call=True,
)
def delete_student(delete_clicks, confirm_clicks, pending_lrn, refresh_value):
    trigger_id = get_triggered_component()
    triggered = callback_context.triggered
    if trigger_id is None or not triggered or not triggered[0].get("value"):
        raise PreventUpdate

    if trigger_id == "sdm_confirm_delete":
        if pending_lrn is None:
            raise PreventUpdate
        lrn = int(pending_lrn)
        db.modifyDB(
            "UPDATE student SET student_delete_ind = TRUE WHERE student_lrn = %s",
            [lrn],
        )
        db.modifyDB(
            "UPDATE program_enrolment SET enrolment_status = FALSE WHERE student_lrn = %s",
            [lrn],
        )
        return False, None, (refresh_value or 0) + 1

    if isinstance(trigger_id, dict) and trigger_id.get("type") == "sdm_delete":
        return True, int(trigger_id["index"]), no_update

    raise PreventUpdate