from datetime import date
import pandas as pd
import dash_bootstrap_components as dbc
from dash import dcc, html, callback_context, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import app
from apps import dbconnect as db
from apps.class_profiles.class_profiles_management import get_triggered_component

PAGE_PATH = "/meal_plans/meal_plans_management"
PROFILE_PATH = "/meal_plans/meal_plans_management_profile"
# QUARTERS = ["1st Quarter", "2nd Quarter", "3rd Quarter", "4th Quarter"]

layout = html.Div([
    dcc.Store(id="pem_refresh", data=0),

    html.H2("Meal Plans (WIP!!)", 
            className="fw-bold text-primary"),

    html.P("Add or edit a meal plan.",
           className="text-muted"),
])