import dash_bootstrap_components as dbc
from dash import Input, Output, State, html
from dash.exceptions import PreventUpdate

from app import app
from apps.dbconnect import getDataFromDB

layout = html.Div(
    [
        html.Div(
            "Feeding Program Database Management System",
            className="page-header",
        ),

        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1(
                            'Welcome!',
                            id='home_title',
                            className='hero-title',
                        ),
                        html.P(
                            'Track attendance, plan meals, and keep every student fed. '
                            'This app brings daily logs, enrolments, class profiles, '
                            'and meal plans into one place.',
                            className='hero-intro',
                        ),
                        html.Div(
                            [
                                dbc.Button('Open Daily Log', color='primary',
                                           href='/daily_log/daily_log_management',
                                           className='me-3 mb-2'),
                                dbc.Button('View Reports', className='btn-outline-custom mb-2',
                                           href='/reports/report'),
                            ],
                            className='mt-4',
                        ),
                    ],
                    xs=12, lg=6, className='mb-4 d-flex flex-column justify-content-center',
                ),
                dbc.Col(
                    html.Img(
                        src='/assets/Feeding.webp',
                        className='hero-image',
                        alt='Students eating a meal together',
                    ),
                    xs=12, lg=6, className='mb-4',
                ),
            ],
            className='align-items-center mb-5',
        ),

        html.Hr(),
        html.P('Need help? Contact the app owner.', className='fst-italic',
               style={'opacity': 0.7}),
    ],
    className='px-4 pb-4',
)


@app.callback(
    Output('home_title', 'children'),
    Input('url', 'pathname'),
    State('currentuserid', 'data'),
)
def home_greeting(pathname, userid):
    if pathname not in ('/', '/home'):
        raise PreventUpdate

    name = None
    if userid and userid > 0:
        df = getDataFromDB(
            "SELECT user_name FROM users WHERE user_id = %s AND user_delete_ind = false",
            [userid], ['user_name'])
        if not df.empty:
            name = df['user_name'][0]

    if name:
        return ['Welcome, ', html.Span(name, className='hero-accent'), ' !']
    return 'Welcome!'