import hashlib


import dash_bootstrap_components as dbc
# >>> CHANGED: added no_update
from dash import dcc, html, callback_context, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate


from app import app
from apps import dbconnect as db


layout = html.Div(
    dbc.Card(
        dbc.CardBody([
            html.H2('Welcome back!', className='login-title'),
            html.P('Log in to your account', className='login-subtitle'),

            # Login error message: hidden by default, shown by the login_user callback below
            dbc.Alert(
                'Incorrect username or password. Please check and try again.',
                color='danger',
                id='login_alert',
                is_open=False,
                className='login-alert',
            ),

            dbc.Label('Username', html_for='login_username', className='login-label'),
            dbc.Input(
                type='text',
                id='login_username',
                placeholder='Enter username',
                className='mb-3',
            ),

            dbc.Label('Password', html_for='login_password', className='login-label'),
            dbc.InputGroup(
                [
                    dbc.Input(
                        type='password',
                        id='login_password',
                        placeholder='Enter password',
                    ),
                    dbc.Button(
                        html.I(id='login_toggle_icon', className='bi bi-eye'),
                        id='login_toggle_pw',
                        color='light',
                        n_clicks=0,
                        className='login-eye',
                    ),
                ],
                className='mb-4',
            ),

            dbc.Button('Log in', id='login_loginbtn', color='primary', className='w-100 mb-3'),

            html.Div(
                [
                    html.Hr(className='login-rule'),
                    html.Span('New user?', className='login-divider-text'),
                    html.Hr(className='login-rule'),
                ],
                className='login-divider',
            ),

            dbc.Button('Sign up', href='/signup', className='btn-outline-custom w-100'),
        ]),
        className='login-card',
    ),
    className='login-wrap',
)


@app.callback(
    Output('login_password', 'type'),
    Output('login_toggle_icon', 'className'),
    Input('login_toggle_pw', 'n_clicks'),
    prevent_initial_call=True,
)
def login_toggle_password(n_clicks):
    if n_clicks and n_clicks % 2:
        return 'text', 'bi bi-eye-slash'
    return 'password', 'bi bi-eye'


@app.callback(
    [
        Output('login_alert', 'is_open'),
        Output('currentuserid', 'data'),
        # >>> ADDED: lets this callback send the user to the home page after login
        Output('url', 'pathname', allow_duplicate=True),
    ],
    [
        Input('login_loginbtn', 'n_clicks'),
    ],
    [
        State('login_username', 'value'),
        State('login_password', 'value'),
        # >>> CHANGED: State('currentuserid') removed, it isn't needed anymore
    ],
    prevent_initial_call=True,
)
# >>> CHANGED: removed the currentuserid parameter to match the removed State
def login_user(loginbtn, username, password):
    ctx = callback_context
    if not ctx.triggered or ctx.triggered[0]['prop_id'].split('.')[0] != 'login_loginbtn':
        raise PreventUpdate

    # >>> CHANGED: no_update for the user id and url, so index.py doesn't
    # re-render the login page and wipe the error message
    if not username or not password:
        return True, no_update, no_update

    encrypted_password = hashlib.sha256(password.encode('utf-8')).hexdigest()

    sql = """
        SELECT user_id
        FROM users
        WHERE user_name = %s
          AND user_password = %s
          AND NOT user_delete_ind
    """
    values = [username, encrypted_password]
    cols = ['userid']
    df = db.getDataFromDB(sql, values, cols)

    if df.shape[0]:
        # >>> CHANGED: success hides the error, stores the user id (as a plain int),
        # and redirects to the home page
        return False, int(df['userid'][0]), '/home'

    # >>> CHANGED: wrong username or password, so show the error and leave everything else alone
    return True, no_update, no_update


# Optional: hides the error again once the user starts typing.
# Needs Dash 2.9 or newer for allow_duplicate. Delete this block if you don't want it.
@app.callback(
    Output('login_alert', 'is_open', allow_duplicate=True),
    Input('login_username', 'value'),
    Input('login_password', 'value'),
    prevent_initial_call=True,
)
def login_hide_alert(_u, _p):
    return False