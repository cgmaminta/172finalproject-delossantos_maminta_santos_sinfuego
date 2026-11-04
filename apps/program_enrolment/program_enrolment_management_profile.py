from datetime import date
import math
import pandas as pd
import dash_bootstrap_components as dbc
from dash import ALL, dcc, html, callback_context, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import app
from apps import dbconnect as db
from apps.class_profiles.class_profiles_management import get_triggered_component

PATH_PREFIX = "/program_enrolment/program_enrolment_management_profile/"
BACK_PATH = "/program_enrolment/program_enrolment_management"


def parse_cycle_id(pathname):
    if not pathname or not pathname.startswith(PATH_PREFIX):
        return None
    tail = pathname.rstrip("/").rsplit("/", 1)[-1]
    return int(tail) if tail.isdigit() else None


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


def full_name(last, first, middle=None):
    name = f"{clean_text(last) or ''}, {clean_text(first) or ''}".strip(", ")
    middle = clean_text(middle)
    return f"{name} {middle}" if middle else name


def numeric(value):
    try:
        if value is None or str(value).strip() == "":
            return None
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def bmi_classification(bmi):
    """Asia-Pacific adult cutoffs shown in the user's reference image."""
    if bmi is None:
        return None, None
    if bmi < 18.5:
        return "Underweight", "Medium"
    if bmi <= 22.9:
        return "Normal", "Low"
    if bmi <= 24.9:
        return "Overweight", "Medium"
    return "Obese", "High"

# App Layout
layout = html.Div(
    [
        dcc.Store(id="pemp_refresh", data=0),
        dcc.Store(id="pemp_cycle_id", data=None),
        dcc.Store(id="pemp_health_lrn", data=None),
        dcc.Store(id="pemp_selected_class", data=None),

        dbc.Button("← Back to Program Cycles", 
                   href=BACK_PATH,
                    color="secondary", 
                    outline=True, 
                    size="sm", 
                    className="mb-3"),

        html.H2("Program Cycle Profile", 
                id="pemp_cycle_title",
            className="fw-bold text-primary"),

        html.P("Active classes and their enrolled students.", 
               className="text-muted"),

        dbc.Alert(id="pemp_page_alert", 
                  is_open=False, 
                  dismissable=True, 
                  duration=5000),   

        dbc.Card(
            [
            dbc.CardHeader(
                html.H5("List of Classes", className="m-0 fw-bold")
                ),
            dbc.CardBody(html.Div(id="pemp_class_list")),
        ], 
        className="shadow-sm mb-3"),

    html.Div(id="pemp_student_panel"),

    dbc.Modal(
        [
        dbc.ModalHeader(
            dbc.ModalTitle("Student Health Assessment", 
                           id="pemp_health_title")
                           ),
        dbc.ModalBody(
            [
            dbc.Alert(id="pemp_health_alert", 
                      is_open=False, 
                      dismissable=True),
            dbc.Row(
                [
                dbc.Col(
                    [dbc.Label("Assessment Date", 
                               className="fw-bold"),

                         dcc.DatePickerSingle(id="pemp_record_date", 
                                              date=date.today(),
                                              display_format="YYYY-MM-DD")
                                              ], 
                                              md=6),

                dbc.Col(
                    [
                        dbc.Label("BMI (kg/m²)", 
                                  className="fw-bold"),
                         dbc.Input(id="pemp_bmi", 
                                   type="number", 
                                   disabled=True,
                                   placeholder="Calculated from height and weight")
                                   ], 
                                   md=6),
            ], 
            className="mb-3"),

            dbc.Row(
                [
                dbc.Col(
                    [dbc.Label("Height (cm)", 
                               className="fw-bold"),

                         dbc.Input(id="pemp_height", 
                                   type="number", 
                                   min=1, 
                                   step="any",
                                   placeholder="Enter height in centimeters")
                                   ], 
                                   md=6),

                dbc.Col(
                    [
                        dbc.Label("Weight (kg)", className="fw-bold"),
                         dbc.Input(id="pemp_weight", 
                                   type="number", 
                                   min=0.1, 
                                   step="any",
                                   placeholder="Enter weight in kilograms")
                                   ], 
                                   md=6),
            ], 
            className="mb-2"),

            dbc.Alert(id="pemp_bmi_explanation", color="info", className="py-2"),
            
            dbc.Row(
                [
                dbc.Col(
                    [
                        dbc.Label("Nutritional Status (calculated)", 
                                  className="fw-bold"),

                         dbc.Input(id="pemp_nutritional_status", 
                                   disabled=True)
                                   ], 
                                   md=6),

                dbc.Col(
                    [
                        dbc.Label("Risk Status (calculated)", 
                                  className="fw-bold"),
                         dbc.Input(id="pemp_risk_status", 
                                   disabled=True)
                                   ], 
                                   md=6),

            ], 
            className="mb-3"),

            dbc.Label("Priority Level", className="fw-bold"),

            dbc.Select(id="pemp_priority",
                       options=[{"label": x, "value": x} for x in ["Low", "Medium", "High"]],
                       className="mb-3"),

            dbc.Row(
                [
                dbc.Col(
                    [
                        dbc.Label("Dietary Restrictions"),
                         dbc.Input(id="pemp_dietary", maxLength=70)
                         ], 
                         md=6),

                dbc.Col(
                    [dbc.Label("Allergy"),
                         dbc.Input(id="pemp_allergy", maxLength=70)
                         ], 
                         md=6),

            ], 
            className="mb-3"),

            dbc.Label("Z-Score", className="fw-bold"),

            dbc.Input(id="pemp_z_score", disabled=True,
                      placeholder="Requires pediatric age/sex reference standards"),

            dbc.FormText("A valid BMI-for-age Z-score cannot be calculated from the adult BMI chart. WHO child growth reference data must be configured first."),
            
            html.Hr(),
            
            html.H6("Previous Assessments", className="fw-bold"),
            
            html.Div(id="pemp_health_history"),
        ]
        ),
        
        dbc.ModalFooter(
            [
            dbc.Button("Cancel", id="pemp_health_cancel",
                       color="secondary", outline=True),
            dbc.Button("Save Health Record", id="pemp_health_save",
                       color="success", outline=True),
        ]
        ),
    ], 
    id="pemp_health_modal", 
    is_open=False, 
    size="lg", 
    centered=True),
]
)


@app.callback(
    [
        Output("pemp_cycle_title", "children"),
        Output("pemp_cycle_id", "data"),
        Output("pemp_class_list", "children")
        ],

    [
        Input("url", "pathname"), 
        Input("pemp_refresh", "data")
        ],
)

def render_cycle_profile(pathname, _refresh):

    cycle_id = parse_cycle_id(pathname)

    if cycle_id is None:
        raise PreventUpdate
    
    cycle = db.getDataFromDB(
        "SELECT semester FROM program_cycle WHERE cycle_id = %s",
        [cycle_id], ["semester"])
    
    if cycle is None or cycle.empty:
        return "Program Cycle Not Found", cycle_id, dbc.Alert("This program cycle does not exist.", color="warning")
    
    label = clean_text(cycle.iloc[0]["semester"]) or f"Cycle {cycle_id}"

    classes = db.getDataFromDB(
        """SELECT 
                sc.class_id, 
                sc.grade_level, 
                sc.student_section, 
                t.teacher_name,
                  COUNT(pe.enrolment_id) FILTER (
                      WHERE pe.enrolment_id IS NOT NULL
                  ) AS student_count,
                  COUNT(pe.enrolment_id) FILTER (
                      WHERE UPPER(BTRIM(COALESCE(pe.priority_level, ''))) = 'HIGH'
                  ) AS high_count,
                  COUNT(pe.enrolment_id) FILTER (
                      WHERE UPPER(BTRIM(COALESCE(pe.priority_level, ''))) = 'MEDIUM'
                  ) AS medium_count,
                  COUNT(pe.enrolment_id) FILTER (
                      WHERE UPPER(BTRIM(COALESCE(pe.priority_level, ''))) = 'LOW'
                  ) AS low_count
           FROM student_class sc
           LEFT JOIN teacher t ON t.employee_id = sc.employee_id
           LEFT JOIN program_enrolment pe ON pe.class_id = sc.class_id
                AND COALESCE(pe.enrolment_status, TRUE) = TRUE
           WHERE sc.cycle_id = %s
             AND COALESCE(sc.class_delete_ind, FALSE) = FALSE
             AND COALESCE(sc.class_archive_ind, FALSE) = FALSE
           GROUP BY 
                    sc.class_id, 
                    sc.grade_level, 
                    sc.student_section, 
                    t.teacher_name
           ORDER BY sc.grade_level, sc.student_section""",
        [cycle_id], ["class_id", "grade_level", "student_section", "teacher_name",
                     "student_count", "high_count", "medium_count", "low_count"])
    
    if classes is None or classes.empty:
        return label, cycle_id, dbc.Alert("No active classes are assigned to this program cycle. Assign classes through Class Profiles.", color="info")
    class_cards = []
    for _, row in classes.iterrows():
        class_id = int(row["class_id"])
        class_title = f"Grade {int(row['grade_level'])} - {row['student_section']}"
        teacher_name = clean_text(row["teacher_name"]) or "No teacher assigned"
        student_count = int(row["student_count"] or 0)

        priority_summary = dbc.Row([
            dbc.Col(dbc.Badge(f"High: {int(row['high_count'] or 0)}", color="danger",
                              className="w-100 py-2"), width=4),
            dbc.Col(dbc.Badge(f"Medium: {int(row['medium_count'] or 0)}", color="warning",
                              text_color="dark", className="w-100 py-2"), width=4),
            dbc.Col(dbc.Badge(f"Low: {int(row['low_count'] or 0)}", color="success",
                              className="w-100 py-2"), width=4),
        ], className="g-2 mb-3 text-center")

        class_cards.append(dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H5(class_title, className="fw-bold mb-2"),
                html.P(f"Program Cycle: {label}", className="text-muted mb-1"),
                html.P(f"Teacher: {teacher_name}", className="mb-1"),
                html.P(f"Enrolled students: {student_count}", className="mb-3"),
                priority_summary,
                dbc.Button("View Class", id={"type": "pemp_view_class", "index": class_id},
                           color="primary", outline=True, className="w-100", n_clicks=0),
            ]), className="h-100 shadow-sm"),
            xs=12, md=6, lg=4, className="mb-3"
        ))

    return label, cycle_id, dbc.Row(class_cards)


@app.callback(
    
    Output("pemp_student_panel", "children"),

    [
        Input({"type": "pemp_view_class", "index": ALL}, "n_clicks"),
        Input({"type": "pemp_back_to_classes", "index": ALL}, "n_clicks")
        ],

    [
        State("url", "pathname")
        ],
)

def show_selected_class(view_clicks, back_clicks, pathname):

    trigger = get_triggered_component()

    if isinstance(trigger, dict) and trigger.get("type") == "pemp_back_to_classes":
        return None
    
    if not isinstance(trigger, dict) or trigger.get("type") != "pemp_view_class":
        raise PreventUpdate
    
    triggered_value = callback_context.triggered[0].get("value") if callback_context.triggered else None

    if not triggered_value:
        raise PreventUpdate
    
    class_id = int(trigger["index"])

    cycle_id = parse_cycle_id(pathname)

    if cycle_id is None:
        raise PreventUpdate
    
    class_info = db.getDataFromDB(
        """SELECT 
                sc.grade_level, 
                sc.student_section, 
                t.teacher_name
           FROM student_class sc LEFT JOIN teacher t ON t.employee_id = sc.employee_id
           WHERE sc.class_id = %s AND sc.cycle_id = %s
             AND COALESCE(sc.class_delete_ind, FALSE) = FALSE
             AND COALESCE(sc.class_archive_ind, FALSE) = FALSE""",
        [class_id, cycle_id], ["grade_level", "student_section", "teacher_name"])
    
    if class_info is None or class_info.empty:
        return dbc.Alert("This class is no longer available in this program cycle.", color="warning")
    
    row = class_info.iloc[0]
    
    title = f"Grade {int(row['grade_level'])} - {row['student_section']}"
    teacher = clean_text(row["teacher_name"]) or "No teacher assigned"
    
    return dbc.Card(
        [
        dbc.CardHeader(
            dbc.Row(
                [
            dbc.Col(
                [
                    html.H5(title, className="fw-bold mb-1"),
                     html.Small(f"Teacher: {teacher}", className="text-muted")
                     ]
                     ),
            dbc.Col(dbc.Button("← Back to Classes", id={"type": "pemp_back_to_classes", "index": class_id},
                               color="secondary", outline=True, size="sm"), width="auto",
                     className="text-end align-self-center"),
        ], 
        justify="between", 
        align="center")
        ),
        dbc.CardBody(load_students(class_id)),
    ], 
    className="shadow-sm")


def load_students(class_id):
    df = db.getDataFromDB(
        """SELECT s.student_lrn, s.student_last_name, s.student_first_name,
                  s.student_middle_name, s.student_sex::text, pe.enrolment_id,
                  pe.priority_level,
                  (SELECT COUNT(*) FROM health_record hr
                    WHERE hr.student_lrn = s.student_lrn) AS health_count,
                  (SELECT hr.nutritional_status FROM health_record hr
                    WHERE hr.student_lrn = s.student_lrn
                    ORDER BY hr.record_date DESC NULLS LAST, hr.record_id DESC LIMIT 1) AS latest_status
           
           FROM program_enrolment pe
           JOIN student s ON s.student_lrn = pe.student_lrn
           WHERE pe.class_id = %s
             AND COALESCE(pe.enrolment_status, TRUE) = TRUE
             AND COALESCE(s.student_delete_ind, FALSE) = FALSE
           
           ORDER BY LOWER(BTRIM(s.student_last_name)), LOWER(BTRIM(s.student_first_name))""",
        [class_id], ["student_lrn", "last_name", "first_name", "middle_name",
                     "sex", "enrolment_id", "priority", "health_count", "latest_status"])
    
    if df is None or df.empty:
        return dbc.Alert("No active students are enrolled in this class yet.", color="light")
    
    rows = []
    
    for _, student in df.iterrows():
        lrn = int(student["student_lrn"])
        has_record = int(student["health_count"] or 0) > 0
        priority = clean_text(student["priority"]) or "Not set"
        
        rows.append(html.Tr([
            html.Td(lrn),
            html.Td(full_name(student["last_name"], student["first_name"], student["middle_name"]),
                    className="fw-semibold"),
            html.Td(clean_text(student["sex"]) or "â€”"),
            html.Td(clean_text(student["latest_status"]) or ("Assessment available" if has_record else "No record")),
            html.Td(priority),
            html.Td(dbc.Button("View / Add Health Record" if has_record else "Create Health Record",
                               id={"type": "pemp_health_open", "index": lrn}, # open -> btn
                               color="info" if has_record else "success",
                               outline=True, size="sm", n_clicks=0)),
        ]))
    return dbc.Table([
        html.Thead(html.Tr([html.Th("LRN"), html.Th("Student"), html.Th("Sex"),
                            html.Th("Latest Nutritional Status"), html.Th("Priority"),
                            html.Th("Health Profile")])),
        html.Tbody(rows),
    ], hover=True, responsive=True, size="sm", className="mb-0 align-middle")


@app.callback(
    [
        Output("pemp_health_modal", "is_open"),
        Output("pemp_health_lrn", "data"),
        Output("pemp_health_title", "children"),
        Output("pemp_health_alert", "children"),
        Output("pemp_health_alert", "color"),
        Output("pemp_health_alert", "is_open"),
        Output("pemp_record_date", "date"),
        Output("pemp_height", "value"),
        Output("pemp_weight", "value"),
        Output("pemp_bmi", "value"),
        Output("pemp_nutritional_status", "value"),
        Output("pemp_risk_status", "value"),
        Output("pemp_priority", "value"),
        Output("pemp_dietary", "value"),
        Output("pemp_allergy", "value"),
        Output("pemp_z_score", "value"),
        Output("pemp_bmi_explanation", "children"),
        Output("pemp_health_history", "children")
        ],

    [
        Input({"type": "pemp_health_open", "index": ALL}, "n_clicks"),
        Input("pemp_health_cancel", "n_clicks"),
        Input("pemp_health_save", "n_clicks")
        ],

    
    [
        State("url", "pathname"),
        State("pemp_health_lrn", "data"),
        State("pemp_record_date", "date"),
        State("pemp_height", "value"),
        State("pemp_weight", "value"),
        State("pemp_bmi", "value"),
        State("pemp_nutritional_status", "value"),
        State("pemp_risk_status", "value"),
        State("pemp_priority", "value"),
        State("pemp_dietary", "value"),
        State("pemp_allergy", "value")
        ],
    prevent_initial_call=True,
)

def health_modal(_open, _cancel, _save, pathname, current_lrn, record_date,
                 height, weight, bmi, nutritional, risk, priority, dietary, allergy):
    

    trigger = get_triggered_component()

    if trigger == "pemp_health_cancel":
        return (False, None, no_update, "", "warning", False,
                no_update, no_update, no_update, no_update, no_update, no_update,
                no_update, no_update, no_update, no_update, no_update, no_update)

    if isinstance(trigger, dict) and trigger.get("type") == "pemp_health_open":

        triggered_value = (
            callback_context.triggered[0].get("value")
            if callback_context.triggered
            else None
        )

        # Prevent the modal from opening when Dash
        # merely detects newly generated health buttons.
        if not triggered_value or triggered_value <= 0:
            raise PreventUpdate      
          
        lrn = int(trigger["index"])
        
        student = db.getDataFromDB(
            """SELECT student_last_name, student_first_name, student_middle_name
               FROM student WHERE student_lrn = %s""",
            [lrn], ["last_name", "first_name", "middle_name"])
        
        name = full_name(student.iloc[0]["last_name"], student.iloc[0]["first_name"],
                         student.iloc[0]["middle_name"]) if student is not None and not student.empty else str(lrn)
        
        hist = db.getDataFromDB(
            """SELECT record_date, nutritional_status, risk_status, height, weight, bmi, z_score
               FROM health_record WHERE student_lrn = %s
               ORDER BY record_date DESC NULLS LAST, record_id DESC""",
            [lrn], ["record_date", "nutritional", "risk", "height", "weight", "bmi", "z_score"])
        
        if hist is None or hist.empty:
            history = dbc.Alert("No previous assessments for this student.", color="light")
        else:
            history_rows = [html.Tr([
                html.Td(str(clean(h["record_date"]) or "-”")),
                html.Td(clean_text(h["nutritional"]) or "-"),
                html.Td(clean_text(h["risk"]) or "-"),
                html.Td(clean(h["height"]) if clean(h["height"]) is not None else "-"),
                html.Td(clean(h["weight"]) if clean(h["weight"]) is not None else "-"),
                html.Td(clean(h["bmi"]) if clean(h["bmi"]) is not None else "-"),
                html.Td(clean(h["z_score"]) if clean(h["z_score"]) is not None else "-"),
            ]) for _, h in hist.iterrows()]

            history = dbc.Table([
                html.Thead(html.Tr([html.Th(x) for x in
                                    ["Date", "Nutritional", "Risk", "Height", "Weight", "BMI", "Z-Score"]])),
                html.Tbody(history_rows)], responsive=True, size="sm", bordered=True)
            
        return (True, lrn, f"Health Assessment - {name}", "", "warning", False,
                date.today().isoformat(), None, None, None, None, None, None,
                None, None, None,
                "Enter height and weight to calculate BMI. Classification uses the Asia-Pacific adult cutoffs in your reference image; these are not pediatric standards.",
                history)

    if trigger == "pemp_health_save":

        cycle_id = parse_cycle_id(pathname)

        if current_lrn is None or cycle_id is None:
            raise PreventUpdate
        # Recalculate server-side; never trust a client-supplied BMI/category.
        h_cm, w_kg = numeric(height), numeric(weight)
        if h_cm is None or h_cm <= 0 or w_kg is None or w_kg <= 0:
            return (True, current_lrn, no_update, "Enter a valid height and weight.", "warning", True,
                    no_update, no_update, no_update, no_update, no_update, no_update,
                    no_update, no_update, no_update, no_update, no_update, no_update)
        
        calculated_bmi = round(w_kg / ((h_cm / 100) ** 2), 2)
        
        category, calculated_priority = bmi_classification(calculated_bmi)
        
        if not record_date:
            return (True, current_lrn, no_update, "Select an assessment date.", "warning", True,
                    no_update, no_update, no_update, no_update, no_update, no_update,
                    no_update, no_update, no_update, no_update, no_update, no_update)
        
        if priority not in ("Low", "Medium", "High"):
            priority = calculated_priority
        try:
            # Confirm the student is actively enrolled in a class in this cycle.
            enrol = db.getDataFromDB(
                """SELECT pe.enrolment_id FROM program_enrolment pe
                   JOIN student_class sc ON sc.class_id = pe.class_id
                   WHERE pe.student_lrn = %s AND sc.cycle_id = %s
                     AND COALESCE(pe.enrolment_status, TRUE) = TRUE
                     AND COALESCE(sc.class_delete_ind, FALSE) = FALSE
                     AND COALESCE(sc.class_archive_ind, FALSE) = FALSE
                   ORDER BY pe.enrolment_id DESC LIMIT 1""",
                [int(current_lrn), cycle_id], ["enrolment_id"])
            
            if enrol is None or enrol.empty:
                raise ValueError("This student is no longer actively enrolled in this program cycle.")
            
            enrolment_id = int(enrol.iloc[0]["enrolment_id"])
            
            db.modifyDB(
                """INSERT INTO health_record
                   (student_lrn, record_date, nutritional_status, risk_status,
                    dietary_restrictions, allergy, height, weight, bmi, z_score)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)""",
                [int(current_lrn), record_date, category, category,
                 clean_text(dietary), clean_text(allergy), h_cm, w_kg, calculated_bmi])
            
            db.modifyDB(
                "UPDATE program_enrolment SET priority_level = %s WHERE enrolment_id = %s",
                [priority, enrolment_id])
            return (False, None, no_update, "", "success", False,
                    no_update, no_update, no_update, no_update, no_update, no_update,
                    no_update, no_update, no_update, no_update, no_update, no_update)
        except ValueError as exc:
            return (True, current_lrn, no_update, str(exc), "warning", True,
                    no_update, no_update, no_update, no_update, no_update, no_update,
                    no_update, no_update, no_update, no_update, no_update, no_update)
        except Exception as exc:
            return (True, current_lrn, no_update, f"Unable to save health record: {exc}", "danger", True,
                    no_update, no_update, no_update, no_update, no_update, no_update,
                    no_update, no_update, no_update, no_update, no_update, no_update)
    raise PreventUpdate


@app.callback(
    [
        Output("pemp_bmi", "value"),
        Output("pemp_nutritional_status", "value"),
        Output("pemp_risk_status", "value"),
        Output("pemp_priority", "value"),
        Output("pemp_bmi_explanation", "children")
        ],

    [
        Input("pemp_height", "value"), 
        Input("pemp_weight", "value")
        ],
)

def calculate_bmi(height, weight):
    h_cm, w_kg = numeric(height), numeric(weight)

    if h_cm is None or h_cm <= 0 or w_kg is None or w_kg <= 0:
        return None, None, None, None, "Enter valid height and weight to calculate BMI."
    
    bmi = round(w_kg / ((h_cm / 100) ** 2), 2)

    category, priority = bmi_classification(bmi)
    
    return (bmi, category, category, priority,
            f"BMI: {bmi} kg/mÂ². Asia-Pacific adult classification: {category}. "
            f"Suggested priority: {priority}. Pediatric interpretation requires age/sex-specific standards.")


@app.callback(
    Output("pemp_refresh", "data"),
    Input("pemp_health_save", "n_clicks"),
    State("pemp_refresh", "data"),
    prevent_initial_call=True,
)
def refresh_after_health_save(_clicks, refresh):
    # The save callback closes the modal only after a successful insert. This
    # refresh is triggered by the save click; harmlessly refreshes after validation too.
    return (refresh or 0) + 1