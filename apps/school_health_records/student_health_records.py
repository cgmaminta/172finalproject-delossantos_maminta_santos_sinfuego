
from datetime import date
from functools import lru_cache

from pathlib import Path
from statistics import NormalDist
import math
import pandas as pd

import dash_bootstrap_components as dbc
from dash import ALL, dcc, html, callback_context, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate


from app import app
from apps import dbconnect as db
from apps.class_profiles.class_profiles_management import get_triggered_component

# Get the directory where this Python file is located
BASE_DIR = Path(__file__).resolve().parent

# WHO BMI-for-age reference files
BOYS_REFERENCE = pd.read_excel(
    BASE_DIR / "bmi-boys-z-who-2007-exp.xlsx"
)

GIRLS_REFERENCE = pd.read_excel(
    BASE_DIR / "bmi-girls-z-who-2007-exp.xlsx"
)
print("Boys reference:")
print(BOYS_REFERENCE.head())

print("Girls reference:")
print(GIRLS_REFERENCE.head())

PATH_PREFIX = "/school_health_records/student_health_records/"
BACK_PATH = "/school_health_records/health_records_management_profile"


def parse_route(pathname):
    """Route format: /school_health_records/student_health_records/<cycle_id>/<class_id>."""
    if not pathname or not pathname.startswith(PATH_PREFIX):
        return None, None
    parts = pathname.rstrip("/").split("/")
    if len(parts) < 2 or not parts[-1].isdigit() or not parts[-2].isdigit():
        return None, None
    return int(parts[-2]), int(parts[-1])


def parse_cycle_id(pathname):
    return parse_route(pathname)[0]



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


# Place the two WHO Excel reference files in this same folder:
#   bmi-boys-z-who-2007-exp.xlsx
#   bmi-girls-z-who-2007-exp.xlsx
WHO_REFERENCE_DIR = Path(__file__).resolve().parent
WHO_FILES = {
    "Male": WHO_REFERENCE_DIR / "bmi-boys-z-who-2007-exp.xlsx",
    "Female": WHO_REFERENCE_DIR / "bmi-girls-z-who-2007-exp.xlsx",
}


@lru_cache(maxsize=2)
def load_who_reference(sex):
    """Load and cache the WHO 2007 monthly BMI-for-age LMS reference."""
    file_path = WHO_FILES.get(sex)
    if file_path is None or not file_path.exists():
        raise FileNotFoundError(
            f"WHO reference file not found: {file_path}. "
            "Place both WHO Excel files beside student_health_records.py."
        )

    reference = pd.read_excel(file_path)
    # Normalize column names to tolerate minor differences in capitalization.
    reference.columns = [str(column).strip().lower() for column in reference.columns]

    required = {"month", "l", "m", "s"}
    if not required.issubset(reference.columns):
        raise ValueError(
            f"{file_path.name} must contain Month, L, M, and S columns. "
            f"Found: {list(reference.columns)}"
        )

    reference["month"] = pd.to_numeric(reference["month"], errors="coerce")
    return reference.dropna(subset=["month"]).set_index("month")


def approximate_age_months(age):
    """
    Approximate age in months from the existing age-in-years field.

    Because the database currently stores whole years only, use the
    midpoint of that year. This is provisional until date of birth or
    age in months is stored.
    """
    age_years = numeric(age)
    if age_years is None or age_years < 5 or age_years > 19:
        return None

    # WHO 2007 BMI-for-age reference spans 61 through 228 months.
    return min(228, round(age_years * 12 + 6))


def calculate_bmi_z_score(bmi, age, sex):
    """Calculate BMI-for-age Z-score using the WHO LMS method."""
    if bmi is None or bmi <= 0:
        return None

    age_months = approximate_age_months(age)
    if age_months is None or sex not in WHO_FILES:
        return None

    reference = load_who_reference(sex)
    if age_months not in reference.index:
        return None

    row = reference.loc[age_months]
    L, M, S = float(row["l"]), float(row["m"]), float(row["s"])
    if M <= 0 or S <= 0:
        return None

    try:
        if L == 0:
            z_score = math.log(bmi / M) / S
        else:
            z_score = (((bmi / M) ** L) - 1) / (L * S)
        return round(z_score, 2) if math.isfinite(z_score) else None
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


def classify_percentile(z_score):
    """
    Apply the percentile boundaries from the user's supplied table:
    below P5, P5–<P15, P15–P85, and above P85.
    """
    if z_score is None:
        return None, None, None

    percentile = NormalDist().cdf(z_score) * 100

    if percentile < 5:
        category, priority = "Underweight / CED", "High"
    elif percentile < 15:
        category, priority = "Mildly Underweight", "Medium"
    elif percentile <= 85:
        category, priority = "Normal Weight", "Low"
    else:
        category, priority = "Overweight", "Medium"

    return category, priority, round(percentile, 2)

# App Layout
layout = html.Div(
    [
        dcc.Store(id="pemp_refresh", data=0),
        dcc.Store(id="pemp_cycle_id", data=None),
        dcc.Store(id="pemp_health_lrn", data=None),

        dbc.Button("← Back to Classes", 
                   id="pemp_back_to_classes", href=BACK_PATH,
                    color="secondary", 
                    outline=True, 
                    size="sm", 
                    className="mb-3"),

        html.H2("Student Health Records", 
                id="pemp_cycle_title",
            className="fw-bold text-primary"),

        html.P("View enrolled students and manage their health assessments.", 
               className="text-muted"),

        dbc.Alert(id="pemp_page_alert", 
                  is_open=False, 
                  dismissable=True, 
                  duration=5000),   

        dbc.Card([
            dbc.CardHeader(html.Div(id="pemp_class_heading", className="fw-bold")),
            dbc.CardBody(html.Div(id="pemp_student_list")),
        ], className="shadow-sm mb-3"),

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

            dbc.Row([
                dbc.Col([
                    dbc.Label("BMI-for-age Z-score (WHO)", className="fw-bold"),
                    dbc.Input(id="pemp_z_score", type="number", disabled=True,
                              placeholder="Calculated from BMI, age, and sex")
                ], md=6),
                dbc.Col([
                    dbc.Label("Percentile", className="fw-bold"),
                    dbc.Input(id="pemp_percentile", type="number", disabled=True,
                              placeholder="Calculated percentile")
                ], md=6),
            ], className="mb-3"),

            dbc.Label("Priority Level (calculated)", className="fw-bold"),
            dbc.Input(id="pemp_priority", disabled=True, className="mb-3"),

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

# To fix percentile calculation
            #dbc.Label("Percentile", className="fw-bold"),

            #dbc.Input(id="pemp_z_score", disabled=True,
                      #placeholder="Requires pediatric age/sex reference standards"),

            #dbc.FormText("A valid BMI-for-age Z-score cannot be calculated from the adult BMI chart. WHO child growth reference data must be configured first."),
            
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
    [Output("pemp_cycle_title", "children"),
     Output("pemp_class_heading", "children"),
     Output("pemp_student_list", "children"),
     Output("pemp_back_to_classes", "href")],
    [Input("url", "pathname"), Input("pemp_refresh", "data")],
)
def render_selected_class(pathname, _refresh):
    cycle_id, class_id = parse_route(pathname)
    if cycle_id is None or class_id is None:
        raise PreventUpdate

    class_info = db.getDataFromDB(
        """SELECT sc.grade_level, sc.student_section, t.teacher_name, pc.semester
           FROM student_class sc
           LEFT JOIN teacher t ON t.employee_id = sc.employee_id
           LEFT JOIN program_cycle pc ON pc.cycle_id = sc.cycle_id
           WHERE sc.class_id = %s AND sc.cycle_id = %s
             AND COALESCE(sc.class_delete_ind, FALSE) = FALSE
             AND COALESCE(sc.class_archive_ind, FALSE) = FALSE""",
        [class_id, cycle_id], ["grade_level", "student_section", "teacher_name", "semester"])

    if class_info is None or class_info.empty:
        return "Class Not Found", "", dbc.Alert("This class is not active in the selected quarter.", color="warning"), BACK_PATH

    row = class_info.iloc[0]
    class_title = f"Grade {int(row['grade_level'])} - {clean_text(row['student_section']) or ''}"
    teacher = clean_text(row["teacher_name"]) or "No teacher assigned"
    quarter = clean_text(row["semester"]) or f"Quarter {cycle_id}"
    heading = html.Div([
        html.H5(class_title, className="fw-bold mb-1"),
        html.Small(f"{quarter} · Teacher: {teacher}", className="text-muted"),
    ])
    return "Student Health Records", heading, load_students(class_id), f"/school_health_records/health_records_management_profile/{cycle_id}"


def load_students(class_id):
    df = db.getDataFromDB(
        """SELECT s.student_lrn, s.student_last_name, s.student_first_name,
                  s.student_middle_name, s.student_sex::text, s.student_age, pe.enrolment_id,
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
                     "sex", "age", "enrolment_id", "priority", "health_count", "latest_status"])
    
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
        Output("pemp_percentile", "value"),
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
    
    #print("========== SAVE DEBUG ==========")
    #print("TRIGGER:", get_triggered_component())
    #print("SAVE CLICKS:", _save)
    #print("STUDENT LRN:", current_lrn)
    #print("HEIGHT:", height)
    #print("WEIGHT:", weight)
    #print("RECORD DATE:", record_date)
    #print("================================")

    trigger = get_triggered_component()

    if trigger == "pemp_health_cancel":
        return (False, None, no_update, "", "warning", False,
                *([no_update] * 13))

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
            """SELECT student_last_name, student_first_name, student_middle_name,
                      student_age, student_sex::text
               FROM student WHERE student_lrn = %s""",
            [lrn], ["last_name", "first_name", "middle_name", "age", "sex"])
        
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
                html.Td(str(clean(h["record_date"]) or "-")),
                html.Td(clean_text(h["nutritional"]) or "-"),
                html.Td(clean_text(h["risk"]) or "-"),
                html.Td(clean(h["height"]) if clean(h["height"]) is not None else "-"),
                html.Td(clean(h["weight"]) if clean(h["weight"]) is not None else "-"),
                html.Td(clean(h["bmi"]) if clean(h["bmi"]) is not None else "-"),
                html.Td(clean(h["z_score"]) if clean(h["z_score"]) is not None else "-"),
            ]) for _, h in hist.iterrows()]

            history = dbc.Table([
                html.Thead(html.Tr([html.Th(x) for x in
                                    ["Date", "Nutritional", "Risk", "Height", "Weight", "BMI", "Z-score"]])),
                html.Tbody(history_rows)], responsive=True, size="sm", bordered=True)
            
        return (True, lrn, f"Health Assessment - {name}", "", "warning", False,
                date.today().isoformat(), None, None, None, None, None, None,
                None, None, None, None,
                "Enter height and weight. BMI-for-age Z-score uses the WHO reference and the percentile boundaries supplied for this project. Age is currently approximated from whole years.",
                history)

    if trigger == "pemp_health_save":

        cycle_id, class_id = parse_route(pathname)

        if current_lrn is None or cycle_id is None or class_id is None:
            raise PreventUpdate
        # Recalculate server-side; never trust a client-supplied BMI/category.
        h_cm, w_kg = numeric(height), numeric(weight)
        if h_cm is None or h_cm <= 0 or w_kg is None or w_kg <= 0:
            return (True, current_lrn, no_update, "Enter a valid height and weight.", "warning", True,
                    *([no_update] * 13))
        
        calculated_bmi = round(w_kg / ((h_cm / 100) ** 2), 2)

        student_info = db.getDataFromDB(
            """SELECT student_age, student_sex::text FROM student WHERE student_lrn = %s""",
            [int(current_lrn)], ["age", "sex"]
        )
        if student_info is None or student_info.empty:
            return (True, current_lrn, no_update, "Student age and sex could not be retrieved.", "warning", True,
                    *([no_update] * 13))

        student_age = numeric(student_info.iloc[0]["age"])
        student_sex = clean_text(student_info.iloc[0]["sex"])
        try:
            calculated_z_score = calculate_bmi_z_score(
                calculated_bmi, student_age, student_sex
            )
        except (FileNotFoundError, ValueError, OSError) as exc:
            return (True, current_lrn, no_update, str(exc), "danger", True,
                    *([no_update] * 13))

        category, calculated_priority, calculated_percentile = classify_percentile(
            calculated_z_score
        )
        if category is None:
            return (True, current_lrn, no_update,
                    "A WHO BMI-for-age Z-score could not be calculated. Check the student's age (5–19), sex, and WHO reference files.",
                    "warning", True, *([no_update] * 13))

        # Priority is calculated from the percentile, not manually selected.
        priority = calculated_priority

        if not record_date:
            return (True, current_lrn, no_update, "Select an assessment date.", "warning", True,
                    *([no_update] * 13))

        try:
            # Confirm the student is actively enrolled in a class in this cycle.
            enrol = db.getDataFromDB(
                """SELECT pe.enrolment_id FROM program_enrolment pe
                   JOIN student_class sc ON sc.class_id = pe.class_id
                   WHERE pe.student_lrn = %s AND sc.cycle_id = %s AND sc.class_id = %s
                     AND COALESCE(pe.enrolment_status, TRUE) = TRUE
                     AND COALESCE(sc.class_delete_ind, FALSE) = FALSE
                     AND COALESCE(sc.class_archive_ind, FALSE) = FALSE
                   ORDER BY pe.enrolment_id DESC LIMIT 1""",
                [int(current_lrn), cycle_id, class_id], ["enrolment_id"])
            
            if enrol is None or enrol.empty:
                raise ValueError("This student is no longer actively enrolled in this program cycle.")
            
            enrolment_id = int(enrol.iloc[0]["enrolment_id"])
            
            db.modifyDB(
                """INSERT INTO health_record
                (student_lrn, record_date, nutritional_status, risk_status,
                 dietary_restrictions, allergy, height, weight, bmi, z_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                [int(current_lrn), record_date, category, category,
                 clean_text(dietary), clean_text(allergy), h_cm, w_kg,
                 calculated_bmi, calculated_z_score])
            
            db.modifyDB(
                "UPDATE program_enrolment SET priority_level = %s WHERE enrolment_id = %s",
                [priority, enrolment_id])
            return (False, None, no_update, "", "success", False,
                    *([no_update] * 13))
        except ValueError as exc:
            return (True, current_lrn, no_update, str(exc), "warning", True,
                    *([no_update] * 13))
        except Exception as exc:
            return (True, current_lrn, no_update, f"Unable to save health record: {exc}", "danger", True,
                    *([no_update] * 13))
    raise PreventUpdate


@app.callback(
    [
        Output("pemp_bmi", "value"),
        Output("pemp_nutritional_status", "value"),
        Output("pemp_risk_status", "value"),
        Output("pemp_priority", "value"),
        Output("pemp_bmi_explanation", "children"),
        Output("pemp_z_score", "value"),
        Output("pemp_percentile", "value"),
    ],
    [
        Input("pemp_height", "value"),
        Input("pemp_weight", "value"),
        Input("pemp_health_lrn", "data"),
    ],
)
def calculate_bmi(height, weight, current_lrn):
    h_cm, w_kg = numeric(height), numeric(weight)

    if h_cm is None or h_cm <= 0 or w_kg is None or w_kg <= 0:
        return None, None, None, None, "Enter valid height and weight.", None, None

    if current_lrn is None:
        return None, None, None, None, "Open a student's health record first.", None, None

    student_info = db.getDataFromDB(
        """SELECT student_age, student_sex::text FROM student WHERE student_lrn = %s""",
        [int(current_lrn)], ["age", "sex"]
    )
    if student_info is None or student_info.empty:
        return None, None, None, None, "Student age and sex could not be retrieved.", None, None

    bmi = round(w_kg / ((h_cm / 100) ** 2), 2)
    age = numeric(student_info.iloc[0]["age"])
    sex = clean_text(student_info.iloc[0]["sex"])

    try:
        z_score = calculate_bmi_z_score(bmi, age, sex)
    except (FileNotFoundError, ValueError, OSError) as exc:
        return bmi, None, None, None, str(exc), None, None

    category, priority, percentile = classify_percentile(z_score)
    if category is None:
        return (bmi, None, None, None,
                "A BMI-for-age Z-score could not be calculated. Check age, sex, and WHO reference files.",
                None, None)

    explanation = (
        f"BMI: {bmi} kg/m². BMI-for-age Z-score: {z_score}. "
        f"Estimated percentile: P{percentile}. Nutritional status: {category}. "
        f"Calculated priority: {priority}. Age is approximated from whole years."
    )
    return bmi, category, category, priority, explanation, z_score, percentile



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