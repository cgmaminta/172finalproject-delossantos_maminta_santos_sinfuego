import logging

import dash
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, suppress_callback_exceptions=True)

app.title = 'Feeding Program Information Management System'

# Reduce terminal logs so you can see errors more clearly
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)