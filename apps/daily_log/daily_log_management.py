from datetime import date
import pandas as pd
import dash_bootstrap_components as dbc
from dash import dcc, html, callback_context, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import app
from apps import dbconnect as db
from apps.class_profiles.class_profiles_management import get_triggered_component

PAGE_PATH = "/daily_log/daily_log_management"
PROFILE_PATH = "/daily_log/daily_log_management_profile"
# QUARTERS = ["1st Quarter", "2nd Quarter", "3rd Quarter", "4th Quarter"]

layout = html.Div([
    dcc.Store(id="pem_refresh", data=0),

    html.H2("Daily Log (WIP!!)", 
            className="fw-bold text-primary"),

    html.P("Log a student's attendance for the day.",
           className="text-muted"),
])