
from datetime import date
import pandas as pd
import dash_bootstrap_components as dbc
from dash import dcc, html, callback_context, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import app
from apps import dbconnect as db
from apps.class_profiles.class_profiles_management import get_triggered_component

PAGE_PATH = "/program_enrolment/program_enrolment_management"
PROFILE_PATH = "/program_enrolment/program_enrolment_management_profile"
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


def cycle_label(school_year, quarter):
    return f"{school_year.strip()} - {quarter}"


layout = html.Div([
    dcc.Store(id="pem_refresh", data=0),

    html.H2("Program Enrolment Management", 
            className="fw-bold text-primary"),

    html.P("Create and manage quarterly School Feeding Program cycles.",
           className="text-muted"),

    dbc.Alert(id="pem_page_alert", is_open=False, dismissable=True, duration=5000),

    dbc.Row(
        [
        dbc.Col(
            dbc.Button("+ Create Program Cycle", id="pem_add_cycle_btn",
                           color="success",
                           n_clicks=0), 
                           width="auto")
    ], 
    className="mb-3"),

    
    dbc.Alert([
        html.Strong("Select a program cycle"),
        html.Div("Choose a cycle below to view its active classes and enrolled students.")
    ], 
    color="light", 
    className="mb-3"),

    html.Div(id="pem_cycle_list"),

    dbc.Modal(
        [
        dbc.ModalHeader(
            dbc.ModalTitle("Create Program Cycle")
            ),
        dbc.ModalBody(
            [
            dbc.Alert(id="pem_cycle_modal_alert", 
                      is_open=False, 
                      color="warning"),

            dbc.Label("School Year", 
                      className="fw-bold"),

            dbc.Input(id="pem_school_year", 
                      placeholder="e.g. 2026-2027",
                      maxLength=30, 
                      className="mb-3"),

            dbc.Label("Quarter", 
                      className="fw-bold"),

            dbc.Select(id="pem_quarter",
                       options=[{"label": q, "value": q} for q in QUARTERS],
                       placeholder="Select quarter"),
        ]
        ),
        dbc.ModalFooter(
            [
            dbc.Button("Cancel", id="pem_cycle_cancel", color="secondary", outline=True),
            dbc.Button("Create Cycle", 
                       id="pem_cycle_save", 
                       color="success"),
        ]
        ),
    ], id="pem_cycle_modal", is_open=False, centered=True),
])


@app.callback(
    [
        Output("pem_cycle_modal", "is_open"),
        Output("pem_cycle_modal_alert", "children"),
        Output("pem_cycle_modal_alert", "is_open"),
        Output("pem_school_year", "value"),
        Output("pem_quarter", "value"),
        Output("pem_refresh", "data"),
        Output("pem_page_alert", "children"),
        Output("pem_page_alert", "color"),
        Output("pem_page_alert", "is_open")
        ],

    [
        Input("pem_add_cycle_btn", "n_clicks"),
        Input("pem_cycle_cancel", "n_clicks"),
        Input("pem_cycle_save", "n_clicks")
        ],

    [
        State("pem_school_year", "value"), 
        State("pem_quarter", "value"),
        State("pem_refresh", "data")
        ],

    prevent_initial_call=True,
)

def manage_cycle_modal(_add, _cancel, _save, school_year, quarter, refresh):
    trigger = get_triggered_component()

    if trigger == "pem_add_cycle_btn":
        return True, "", False, None, None, no_update, no_update, no_update, no_update
    
    if trigger == "pem_cycle_cancel":
        return False, "", False, no_update, no_update, no_update, no_update, no_update, no_update
    
    if trigger != "pem_cycle_save":
        raise PreventUpdate
    if not school_year or not school_year.strip() or not quarter:
        return True, "Enter a school year and select a quarter.", True, no_update, no_update, no_update, no_update, no_update, no_update

    label = cycle_label(school_year, quarter)

    try:
        existing = db.getDataFromDB(
            "SELECT cycle_id FROM program_cycle WHERE LOWER(BTRIM(semester)) = LOWER(BTRIM(%s)) LIMIT 1",
            [label], ["cycle_id"])
        
        if existing is not None and not existing.empty:
            return True, "That program cycle already exists.", True, no_update, no_update, no_update, no_update, no_update, no_update
        db.modifyDB("INSERT INTO program_cycle (semester) VALUES (%s)", [label])
        return False, "", False, None, None, (refresh or 0) + 1, f"{label} created successfully.", "success", True
    
    except Exception as exc:
        return True, f"Unable to create program cycle: {exc}", True, no_update, no_update, no_update, no_update, no_update, no_update


@app.callback(
        
    Output("pem_cycle_list", "children"),

    [
        Input("url", "pathname"), 
        Input("pem_refresh", "data")
        ],
)
def render_cycles(pathname, _refresh):
    if not pathname or pathname.rstrip("/") != PAGE_PATH.rstrip("/"):
        raise PreventUpdate
    df = db.getDataFromDB(
        "SELECT cycle_id, semester FROM program_cycle ORDER BY cycle_id DESC",
        [], ["cycle_id", "semester"])
    if df is None or df.empty:
        return dbc.Alert("No program cycles yet. Create a cycle to get started.", color="info")

    cards = []
    for _, row in df.iterrows():
        cid = int(row["cycle_id"])

        label = clean_text(row["semester"]) or f"Program Cycle {cid}"

        count_df = db.getDataFromDB(
            """SELECT COUNT(*) AS class_count FROM student_class
               WHERE cycle_id = %s
                 AND COALESCE(class_delete_ind, FALSE) = FALSE
                 AND COALESCE(class_archive_ind, FALSE) = FALSE""",
            [cid], ["class_count"])
        
        count = int(count_df.iloc[0]["class_count"]) if count_df is not None and not count_df.empty else 0

        cards.append(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H5(label, className="fw-bold"),
                            html.P(f"{count} active class{'es' if count != 1 else ''}",
                                   className="text-muted mb-3"),
                                   
                                   dbc.Button("View Active Classes", href=f"{PROFILE_PATH}/{cid}",
                                                color="primary", 
                                                outline=True, 
                                                className="w-100"),

        ]
        ), 
        className="h-100 shadow-sm"), 
        md=4, 
        className="mb-3")
        )

    return dbc.Row(cards)
