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

            # >>> CHANGED: the message is no longer hard-coded in the layout.
            # The saveuser callback now sets the text (children), so this alert
            # can show either "supply a username and password" or "username taken".
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
                # >>> ADDED: users.user_name is VARCHAR(32), so longer names would fail the insert
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
                className='mb-4',
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

# disable the signup button if passwords do not match
@app.callback(
    [
        Output('singup_signupbtn', 'disabled'),
    ],
    [
        Input('signup_password', 'value'),
        Input('signup_passwordconf', 'value'),
    ]
)
def deactivatesignup(password, passwordconf):

    # enable button if password exists and passwordconf exists
    #  and password = passwordconf
    enablebtn = password and passwordconf and password == passwordconf

    return [not enablebtn]


# To save the user
@app.callback(
    [
        Output('signup_alert', 'is_open'),
        # >>> ADDED: lets the callback change the alert text depending on the error
        Output('signup_alert', 'children'),
        Output('signup_modal', 'is_open')
    ],
    [
        Input('singup_signupbtn', 'n_clicks')
    ],
    [
        State('signup_username', 'value'),
        State('signup_password', 'value')
    ]
)
def saveuser(loginbtn, username, password):
    # >>> CHANGED: now returns 3 values (alert open, alert text, modal open)
    if not loginbtn:
        raise PreventUpdate

    # Missing username or password
    if not (username and password):
        # >>> CHANGED: the original message is now returned here instead of being fixed in the layout
        return True, 'Please supply a username and password.', False

    # >>> ADDED: check if the username already exists.
    # No "NOT user_delete_ind" filter on purpose: the UNIQUE constraint on
    # user_name also applies to soft-deleted users, so their names are still taken.
    check_sql = """
        SELECT user_id
        FROM users
        WHERE user_name = %s
    """
    existing = db.getDataFromDB(check_sql, [username], ['userid'])

    if existing.shape[0]:
        # >>> ADDED: username already taken, so show the error and do NOT insert
        return True, 'That username is already taken. Please choose a different one.', False

    sql = """INSERT INTO users (user_name, user_password)
    VALUES (%s, %s)"""

    # This lambda fcn encrypts the password before saving it
    # for security purposes, not even database admins should see
    # user passwords
    encrypt_string = lambda string: hashlib.sha256(string.encode('utf-8')).hexdigest()

    values = [username, encrypt_string(password)]

    # >>> ADDED: safety net. If two people sign up with the same name at nearly
    # the same time, the database's UNIQUE constraint rejects the second insert.
    # This catches that instead of crashing the callback.
    try:
        db.modifyDB(sql, values)
    except Exception:
        return True, 'That username is already taken. Please choose a different one.', False

    return False, '', True