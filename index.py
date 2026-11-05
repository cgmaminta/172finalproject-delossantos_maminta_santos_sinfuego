import webbrowser

import dash
import dash_bootstrap_components as dbc
# >>> CHANGED: added no_update
from dash import dcc, html, Input, Output, State, no_update
from dash.exceptions import PreventUpdate

from app import app
from apps import commonmodules as cm
from apps import home, signup, login

from apps.class_profiles import class_profiles_management, class_profiles_management_profile
from apps.student_details import student_details_management, student_details_management_profile
from apps.daily_log import daily_log_management, daily_log_management_profile
from apps.meal_plans import meal_plans_management, meal_plans_management_profile
from apps.school_health_records import health_records_management, health_records_management_profile, student_health_records
from apps.reports import report


CONTENT_STYLE = {
    "margin-top": "1em",
    "margin-left": "1em",
    "margin-right": "1em",
    "padding": "1em 1em",
}


app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=True),

        # Login/session data
        dcc.Store(id="sessionlogout", data=True, storage_type="session"),
        dcc.Store(id="currentuserid", data=-1, storage_type="session"),
        dcc.Store(id="currentrole", data=-1, storage_type="session"),

        # Navigation bar
        html.Div(cm.navbar, id="navbar_div"),

        # Selected page is rendered here
        html.Div(id="page_content", className="m-2 p-2"),
    ]
)


@app.callback(
    [
        Output("page_content", "children"),
        Output("sessionlogout", "data"),
        Output("navbar_div", "className"),
        # >>> ADDED: displaypage now also resets the user id on /logout
        Output("currentuserid", "data", allow_duplicate=True),
    ],
    [
        Input("url", "pathname"),
        # Re-render the page whenever the logged-in user changes (login/logout)
        Input("currentuserid", "data"),
    ],
    [
        State("sessionlogout", "data"),
    ],
    # >>> ADDED: required because currentuserid is also written by login.py
    prevent_initial_call="initial_duplicate",
)
def displaypage(pathname, userid, sessionlogout):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    eventid = ctx.triggered[0]["prop_id"].split(".")[0]
    if eventid not in ("url", "currentuserid"):
        raise PreventUpdate

    if userid is None or userid < 0:  # User is logged out
        if pathname in ["/", "/logout"]:
            returnlayout = login.layout
        elif pathname == "/signup":
            returnlayout = signup.layout
        else:
            returnlayout = "404: request not found"

    else:
        if pathname == "/logout":
            returnlayout = login.layout
            sessionlogout = True

        elif pathname in ["/", "/home"]:
            returnlayout = home.layout

        # Logged-in users who open /signup go to home instead of a 404
        elif pathname == "/signup":
            returnlayout = home.layout

        elif pathname == "/reports/report":
            returnlayout = report.layout

        # Program Enrolment Management main page
        elif pathname == "/school_health_records/health_records_management":
            returnlayout = health_records_management.layout

        # Example: /program_enrolment/program_enrolment_management_profile/1
        elif pathname and pathname.startswith(
            "/school_health_records/health_records_management_profile/"
        ):
            returnlayout = health_records_management_profile.layout

        elif pathname and pathname.startswith(
            "/school_health_records/student_health_records/"
        ):
            returnlayout = student_health_records.layout

        # Class Profiles main page
        elif pathname == "/class_profiles/class_profiles_management":
            returnlayout = class_profiles_management.layout

        elif pathname == "/class_profiles/class_profiles_management_profile":
            returnlayout = class_profiles_management_profile.layout

        # Individual class page. The class ID is included at the end of the URL.
        # Example: /student-details/12
        elif pathname and pathname.startswith("/student-details/"):
            returnlayout = student_details_management_profile.layout

        elif pathname == "/daily_log/daily_log_management":
            returnlayout = daily_log_management.layout

        elif pathname == "/daily_log/daily_log_management_profile":
            returnlayout = daily_log_management_profile.layout

        elif pathname == "/meal_plans/meal_plans_management":
            returnlayout = meal_plans_management.layout

        elif pathname == "/meal_plans/meal_plans_management_profile":
            returnlayout = meal_plans_management_profile.layout

        else:
            returnlayout = "404: request not found"

    # Determine whether the session should be treated as logged out.
    logout_conditions = [
        pathname == "/logout",
        userid is None,
        userid == -1,
        not userid,
    ]
    sessionlogout = any(logout_conditions)

    # Hide the navbar when logged out.
    navbar_classname = "d-none" if sessionlogout else ""

    # >>> ADDED: on /logout, clear the stored user id; otherwise leave it alone
    new_userid = -1 if pathname == "/logout" else no_update

    # >>> CHANGED: returns 4 values now (added new_userid)
    return [returnlayout, sessionlogout, navbar_classname, new_userid]


# >>> REMOVED: the old reset_user_on_logout callback is gone,
# since displaypage now does the reset itself.


if __name__ == "__main__":
    webbrowser.open("http://127.0.0.1:8050/", new=0, autoraise=True)
    app.run(debug=False)