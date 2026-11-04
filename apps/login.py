import hashlib


import dash_bootstrap_components as dbc
from dash import dcc, html, callback_context
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate


from app import app
from apps import dbconnect as db


layout = html.Div(
    dbc.Card(
        dbc.CardBody([
            html.H2('Welcome back!', className='login-title'),
            html.P('Log in to your account', className='login-subtitle'),

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
    ],
    [
        Input('login_loginbtn', 'n_clicks'), # begin login query via button click
        Input('sessionlogout', 'modified_timestamp'), # reset session userid to -1 if logged out
    ],
    [
        State('login_username', 'value'),
        State('login_password', 'value'),  
        State('sessionlogout', 'data'),
        State('currentuserid', 'data'),
        State('url', 'pathname'),
    ]
)
def loginprocess(loginbtn, sessionlogout_time,
                 
                 username, password,
                 sessionlogout, currentuserid,
                 pathname):
   
    ctx = callback_context
   
    if ctx.triggered:
        openalert = False
        eventid = ctx.triggered[0]['prop_id'].split('.')[0]
    else:
        raise PreventUpdate
   
   
    if eventid == 'login_loginbtn': # trigger for login process
   
        if loginbtn and username and password:
            sql = """SELECT user_id
            FROM users
            WHERE
                user_name = %s AND
                user_password = %s AND
                NOT user_delete_ind"""
           
            # we match the encrypted input to the encrypted password in the db
            encrypt_string = lambda string: hashlib.sha256(string.encode('utf-8')).hexdigest()
           
            values = [username, encrypt_string(password)]
            cols = ['userid']
            df = db.getDataFromDB(sql, values, cols)
           
            if df.shape[0]: # if query returns rows
                currentuserid = df['userid'][0]
            else:
                currentuserid = -1
                openalert = True
               
    elif eventid == 'sessionlogout' and pathname == '/logout': # reset the userid if logged out
        currentuserid = -1
       
    else:
        raise PreventUpdate
   
    return [openalert, currentuserid]




@app.callback(
    [
        Output('url', 'pathname'),
    ],
    [
        Input('currentuserid', 'modified_timestamp'),
    ],
    [
        State('currentuserid', 'data'),
    ]
)
def routelogin(logintime, userid):
    ctx = callback_context
    if ctx.triggered:
        if userid > 0:
            url = '/home'
        else:
            url = '/'
    else:
        raise PreventUpdate
    return [url]

