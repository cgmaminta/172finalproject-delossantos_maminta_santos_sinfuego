''' import dash_bootstrap_components as dbc
from dash import dcc, html, callback_context
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import app
from apps import dbconnect as db

# =============================================================================
# LAYOUT STRUCTURE
# =============================================================================

layout = html.Div(
    [
        # Header Section
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H2("Program Enrolment Management", className="fw-bold text-primary"),
                        html.P("Enroll students into program cycles and manage class sections.", className="text-muted"),
                    ],
                    width=8
                ),
                dbc.Col(
                    [
                        dbc.Button(
                            "+ Enroll Student", 
                            id="enroll_open_student_modal_btn", 
                            color="success"
                        ),
                    ],
                    width=4,
                    className="text-end align-self-center"
                )
            ],
            className="mb-4"
        ),

        # Alert banner for messages
        dbc.Alert(id="enroll_alert", is_open=False, dismissable=True, className="mb-3"),

        # Enrolled Students Table Card
        dbc.Card(
            [
                dbc.CardHeader(html.H5("Enrolled Students Roster", className="m-0 fw-bold")),
                dbc.CardBody(
                    html.Div(id="enroll_students_table_container")
                )
            ],
            className="shadow-sm"
        ),

        # ---------------------------------------------------------------------
        # MODAL: ENROLL NEW STUDENT
        # ---------------------------------------------------------------------
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Enroll Student to Program")),
                dbc.ModalBody(
                    [
                        dbc.Form(
                            [
                                html.H6("Class & Academic Period Details", className="fw-bold text-secondary mb-2"),
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                dbc.Label("Grade Level", className="fw-bold"),
                                                dbc.Input(id="enroll_grade_level", type="number", min=1, max=6, placeholder="e.g. 1"),
                                            ],
                                            md=4
                                        ),
                                        dbc.Col(
                                            [
                                                dbc.Label("Student Section", className="fw-bold"),
                                                dbc.Input(id="enroll_student_section", type="text", placeholder="e.g. Sampaguita"),
                                            ],
                                            md=8
                                        ),
                                    ],
                                    className="mb-3"
                                ),
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                # School Year with label example note
                                                dbc.Label("School Year", className="fw-bold"),
                                                dbc.Input(id="enroll_school_year", type="text", placeholder="e.g. 2026-2027"),
                                            ],
                                            md=4
                                        ),
                                        dbc.Col(
                                            [
                                                # Quarter Dropdown
                                                dbc.Label("Quarter", className="fw-bold"),
                                                dbc.Select(
                                                    id="enroll_quarter",
                                                    options=[
                                                        {"label": "1st Quarter", "value": "1st Quarter"},
                                                        {"label": "2nd Quarter", "value": "2nd Quarter"},
                                                        {"label": "3rd Quarter", "value": "3rd Quarter"},
                                                        {"label": "4th Quarter", "value": "4th Quarter"},
                                                    ],
                                                    placeholder="Select Quarter"
                                                ),
                                            ],
                                            md=4
                                        ),
                                        dbc.Col(
                                            [
                                                dbc.Label("Assigned Teacher", className="fw-bold"),
                                                dcc.Dropdown(id="enroll_teacher_dropdown", placeholder="Select Teacher"),
                                            ],
                                            md=4
                                        ),
                                    ],
                                    className="mb-3"
                                ),
                                html.Hr(),
                                html.H6("Student Information", className="fw-bold text-secondary mb-2"),
                                html.Div(
                                    [
                                        dbc.Label("Learner Reference Number (LRN)", className="fw-bold"),
                                        dbc.Input(id="student_lrn", type="number", placeholder="Enter Student LRN"),
                                    ],
                                    className="mb-3"
                                ),
                                html.Div(
                                    [
                                        # Full Name with example in label
                                        dbc.Label("Full Name", className="fw-bold"),
                                        dbc.Input(id="student_name", type="text", placeholder="e.g., Juan B. Dela Cruz"),
                                    ],
                                    className="mb-3"
                                ),
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                dbc.Label("Age", className="fw-bold"),
                                                dbc.Input(id="student_age", type="number", step="0.01", min=4, max=18, placeholder="Age"),
                                            ],
                                            md=6
                                        ),
                                        dbc.Col(
                                            [
                                                dbc.Label("Sex", className="fw-bold"),
                                                dbc.Select(
                                                    id="student_sex",
                                                    options=[
                                                        {"label": "Female", "value": "Female"},
                                                        {"label": "Male", "value": "Male"}
                                                    ],
                                                    placeholder="Select Sex"
                                                ),
                                            ],
                                            md=6
                                        ),
                                    ],
                                    className="mb-3"
                                ),
                                html.Div(
                                    [
                                        dbc.Label("Address", className="fw-bold"),
                                        dbc.Textarea(id="student_address", placeholder="Enter complete address"),
                                    ],
                                    className="mb-3"
                                ),
                            ]
                        )
                    ]
                ),
                dbc.ModalFooter(
                    [
                        dbc.Button("Cancel", id="student_modal_cancel_btn", color="secondary", outline=True),
                        dbc.Button("Enroll Student", id="student_modal_save_btn", color="success"),
                    ]
                ),
            ],
            id="student_modal",
            is_open=False,
            size="lg"
        ),
    ]
)

# =============================================================================
# CALLBACK 1: TOGGLE MODAL & LOAD TEACHERS
# =============================================================================

@app.callback(
    [
        Output("student_modal", "is_open"),
        Output("enroll_teacher_dropdown", "options")
    ],
    [
        Input("enroll_open_student_modal_btn", "n_clicks"),
        Input("student_modal_cancel_btn", "n_clicks")
    ],
    [State("student_modal", "is_open")]
)
def toggle_modal_and_load_teachers(n_open, n_close, is_open):
    ctx = callback_context
    teacher_options = []

    if ctx.triggered:
        # Load Teachers
        sql_teachers = "SELECT employee_id, teacher_name FROM teacher WHERE NOT teacher_delete_ind ORDER BY teacher_name"
        df_teachers = db.getDataFromDB(sql_teachers, [], ['employee_id', 'teacher_name'])
        if df_teachers.shape[0] > 0:
            teacher_options = [{"label": row['teacher_name'], "value": row['employee_id']} for _, row in df_teachers.iterrows()]

        return [not is_open, teacher_options]

    return [is_open, teacher_options]


# =============================================================================
# CALLBACK 2: SAVE ENROLMENT RECORD
# =============================================================================

@app.callback(
    [
        Output("enroll_alert", "children"),
        Output("enroll_alert", "color"),
        Output("enroll_alert", "is_open"),
        Output("enroll_students_table_container", "children")
    ],
    [
        Input("url", "pathname"),
        Input("student_modal_save_btn", "n_clicks")
    ],
    [
        State("student_lrn", "value"),
        State("student_name", "value"),
        State("student_age", "value"),
        State("student_sex", "value"),
        State("student_address", "value"),
        State("enroll_grade_level", "value"),
        State("enroll_student_section", "value"),
        State("enroll_school_year", "value"),
        State("enroll_quarter", "value"),
        State("enroll_teacher_dropdown", "value"),
    ]
)
def manage_enrolment(pathname, save_clicks, lrn, name, age, sex, address,
                     grade_level, section, school_year, quarter, teacher_id):
    
    ctx = callback_context
    alert_text = ""
    alert_color = "success"
    open_alert = False

    if ctx.triggered:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if trigger_id == "student_modal_save_btn" and save_clicks:
            if lrn and name and grade_level and section:
                # 1. Check or insert program cycle based on SY and Quarter
                semester_label = f"{school_year} - {quarter}" if school_year and quarter else (school_year or quarter or "N/A")
                
                sql_check_cycle = "SELECT cycle_id FROM program_cycle WHERE semester = %s"
                df_cycle = db.getDataFromDB(sql_check_cycle, [semester_label], ['cycle_id'])

                if df_cycle.shape[0] > 0:
                    cycle_id = df_cycle['cycle_id'][0]
                else:
                    sql_insert_cycle = "INSERT INTO program_cycle (semester) VALUES (%s) RETURNING cycle_id"
                    # If dbconnect supports returning or standard modifyDB execution:
                    db.modifyDB(sql_insert_cycle, [semester_label])
                    df_new_cycle = db.getDataFromDB(sql_check_cycle, [semester_label], ['cycle_id'])
                    cycle_id = df_new_cycle['cycle_id'][0] if df_new_cycle.shape[0] > 0 else None

                # 2. Insert or check existing student
                sql_check_student = "SELECT student_LRN FROM student WHERE student_LRN = %s"
                df_student_check = db.getDataFromDB(sql_check_student, [lrn], ['student_LRN'])

                if df_student_check.shape[0] == 0:
                    sql_insert_student = """
                        INSERT INTO student (student_LRN, student_name, student_age, student_sex, student_address)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    db.modifyDB(sql_insert_student, [lrn, name, age, sex, address])

                # 3. Insert into program_enrolment (without priority_level)
                sql_insert_enrolment = """
                    INSERT INTO program_enrolment 
                    (grade_level, student_section, employee_id, cycle_id, student_LRN)
                    VALUES (%s, %s, %s, %s, %s)
                """
                db.modifyDB(sql_insert_enrolment, [grade_level, section, teacher_id, cycle_id, lrn])

                alert_text = f"Student {name} (LRN: {lrn}) enrolled successfully!"
                open_alert = True
            else:
                alert_text = "Please complete the required fields: LRN, Full Name, Grade Level, and Section."
                alert_color = "warning"
                open_alert = True

    # Render Table of Enrolled Students
    sql_get_enrolled = """
        SELECT 
            pe.enrolment_id,
            s.student_LRN,
            s.student_name,
            s.student_age,
            s.student_sex,
            pe.grade_level,
            pe.student_section,
            pc.semester AS academic_period,
            t.teacher_name
        FROM program_enrolment pe
        JOIN student s ON pe.student_LRN = s.student_LRN
        LEFT JOIN program_cycle pc ON pe.cycle_id = pc.cycle_id
        LEFT JOIN teacher t ON pe.employee_id = t.employee_id
        WHERE pe.enrolment_status = true AND NOT s.student_delete_ind
        ORDER BY pe.grade_level, pe.student_section, s.student_name
    """
    cols = ['enrolment_id', 'lrn', 'name', 'age', 'sex', 'grade', 'section', 'period', 'teacher']
    df_enrolled = db.getDataFromDB(sql_get_enrolled, [], cols)

    if df_enrolled.shape[0] == 0:
        table_content = dbc.Alert("No students currently enrolled.", color="info", className="m-0")
    else:
        table_header = [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Enrolment ID"),
                        html.Th("LRN"),
                        html.Th("Student Name"),
                        html.Th("Age"),
                        html.Th("Sex"),
                        html.Th("Grade & Section"),
                        html.Th("School Year & Quarter"),
                        html.Th("Teacher"),
                    ]
                )
            )
        ]

        table_rows = [
            html.Tr(
                [
                    html.Td(row['enrolment_id']),
                    html.Td(row['lrn'], className="fw-bold"),
                    html.Td(row['name']),
                    html.Td(row['age']),
                    html.Td(row['sex']),
                    html.Td(f"Grade {row['grade']} - {row['section']}"),
                    html.Td(row['period'] if row['period'] else "N/A"),
                    html.Td(row['teacher'] if row['teacher'] else "N/A"),
                ]
            )
            for _, row in df_enrolled.iterrows()
        ]

        table_content = dbc.Table(
            table_header + [html.Tbody(table_rows)], 
            striped=True, 
            bordered=True, 
            hover=True, 
            responsive=True
        )

    return [alert_text, alert_color, open_alert, table_content]
    '''