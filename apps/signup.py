import hashlib

import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import app
from apps import dbconnect as db

layout = html.Div(
    dbc.Card(
        dbc.CardBody([
            html.H2('Create your account', className='login-title'),
            html.P('Set up your account', className='login-subtitle'),

            dbc.Alert(
                'Please supply a username and password.',
                color='danger',
                id='signup_alert',
                is_open=False,
                className='login-alert',
            ),

            dbc.Label('Username', html_for='signup_username', className='login-label'),
            dbc.Input(
                type='text',
                id='signup_username',
                placeholder='Enter a username',
                maxLength=32,
                className='mb-3',
            ),

            dbc.Label('Password', html_for='signup_password', className='login-label'),
            dbc.InputGroup(
                [
                    dbc.Input(
                        type='password',
                        id='signup_password',
                        placeholder='Enter a password',
                    ),
                    dbc.Button(
                        html.I(id='signup_toggle_icon', className='bi bi-eye'),
                        id='signup_toggle_pw',
                        color='light',
                        n_clicks=0,
                        className='login-eye',
                    ),
                ],
                className='mb-3',
            ),

            dbc.Label('Confirm password', html_for='signup_passwordconf', className='login-label'),
            dbc.InputGroup(
                [
                    dbc.Input(
                        type='password',
                        id='signup_passwordconf',
                        placeholder='Re-type the password',
                    ),
                    dbc.Button(
                        html.I(id='signup_toggle_icon2', className='bi bi-eye'),
                        id='signup_toggle_pw2',
                        color='light',
                        n_clicks=0,
                        className='login-eye',
                    ),
                ],
                className='mb-2',
            ),

            html.Div(
                id='signup_match_msg',
                style={'color': '#9a4f44', 'fontSize': '0.9rem',
                       'marginBottom': '1rem'},
            ),

            dbc.Button('Sign up', id='singup_signupbtn', color='primary', className='w-100 mb-3'),

            html.Div(
                [
                    html.Hr(className='login-rule'),
                    html.Span('Already have an account?', className='login-divider-text'),
                    html.Hr(className='login-rule'),
                ],
                className='login-divider',
            ),

            dbc.Button('Back to log in', href='/', className='btn-outline-custom w-100'),

            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle('User Saved')),
                    dbc.ModalBody('User has been saved', id='signup_confirmation'),
                    dbc.ModalFooter(
                        dbc.Button('Okay', href='/')
                    ),
                ],
                id='signup_modal',
                is_open=False,
            ),
        ]),
        className='login-card',
    ),
    className='login-wrap',
)


@app.callback(
    Output('signup_password', 'type'),
    Output('signup_toggle_icon', 'className'),
    Input('signup_toggle_pw', 'n_clicks'),
    prevent_initial_call=True,
)
def signup_toggle_password(n_clicks):
    if n_clicks and n_clicks % 2:
        return 'text', 'bi bi-eye-slash'
    return 'password', 'bi bi-eye'


@app.callback(
    Output('signup_passwordconf', 'type'),
    Output('signup_toggle_icon2', 'className'),
    Input('signup_toggle_pw2', 'n_clicks'),
    prevent_initial_call=True,
)
def signup_toggle_confirm(n_clicks):
    if n_clicks and n_clicks % 2:
        return 'text', 'bi bi-eye-slash'
    return 'password', 'bi bi-eye'


# Disable the Sign up button and show a message while the passwords differ
@app.callback(
    Output('singup_signupbtn', 'disabled'),
    Output('signup_match_msg', 'children'),
    Input('signup_password', 'value'),
    Input('signup_passwordconf', 'value'),
)
def deactivatesignup(password, passwordconf):
    # Don't show anything until the user has started typing the confirmation
    if not passwordconf:
        return True, ''
    if password != passwordconf:
        return True, 'Passwords do not match.'
    return not password, ''


# To save the user
@app.callback(
    [
        Output('signup_alert', 'is_open'),
        Output('signup_alert', 'children'),
        Output('signup_modal', 'is_open'),
    ],
    [
        Input('singup_signupbtn', 'n_clicks')
    ],
    [
        State('signup_username', 'value'),
        State('signup_password', 'value'),
        State('signup_passwordconf', 'value'),
    ]
)
def saveuser(loginbtn, username, password, passwordconf):
    if not loginbtn:
        raise PreventUpdate

    # Missing username or password
    if not (username and password):
        return True, 'Please supply a username and password.', False

    # Passwords must match (the button should already prevent this)
    if password != passwordconf:
        return True, 'Passwords do not match.', False

    # Check if the username already exists.
    # No "NOT user_delete_ind" filter on purpose: the UNIQUE constraint on
    # user_name also applies to soft-deleted users, so their names are still taken.
    check_sql = """
        SELECT user_id
        FROM users
        WHERE user_name = %s
    """
    existing = db.getDataFromDB(check_sql, [username], ['userid'])

    if existing.shape[0]:
        return True, 'That username is already taken. Please choose a different one.', False

    sql = """INSERT INTO users (user_name, user_password)
    VALUES (%s, %s)"""

    # Encrypt the password before saving it, so the plain text is never stored
    encrypt_string = lambda string: hashlib.sha256(string.encode('utf-8')).hexdigest()

    values = [username, encrypt_string(password)]

    # If two people register the same name at nearly the same time, the
    # UNIQUE constraint rejects the second insert. Show the same message.
    try:
        db.modifyDB(sql, values)
    except Exception:
        return True, 'That username is already taken. Please choose a different one.', False

    return False, '', True