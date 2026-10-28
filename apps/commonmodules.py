# Usual Dash dependencies
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.exceptions import PreventUpdate

# Let us import the app object in case we need to define
# callbacks here
from app import app

navlink_style = {'color': '#fff', 'margin-right': '1.5em'}

navbar = dbc.Navbar(
    dbc.Container(
        [
            html.A(
                dbc.Row(
                    [
                        dbc.Col(dbc.NavbarBrand("IE 172 Project", className="ms-2")),
                    ],
                    align="center",
                    className='g-0 me-4'
                ),
                href="/home",
                style={'textDecoration': 'none'}
            ),
            dbc.NavLink("Home", href="/home", style=navlink_style),
            dbc.NavLink("Program Enrolment", href="/program_enrolment/program_enrolment_management", style=navlink_style),
            dbc.NavLink("Daily Log", href="/daily_log/daily_log_management", style=navlink_style),
            dbc.NavLink("Class Profiles", href="/class_profiles/class_profiles_management", style = navlink_style),
            dbc.NavLink("Meal Plans", href="/meal_plans/meal_plans_management", style=navlink_style),
            dbc.NavLink("Reports", href="/reports/report", style=navlink_style),
            dbc.NavLink("Logout", href="/logout", style=navlink_style),
        ], className='m-0 justify-content-start'
        
    ),
    dark=True,
    color='dark'
)