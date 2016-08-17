import os
import logging

import pandas as pd

import bokeh
import bokeh.embed
import bokeh.plotting

import psycopg2

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# plot
logger.debug("generating plots")
p = bokeh.plotting.Figure(title="Title")

curdoc = bokeh.plotting.curdoc()
logger.info('curdoc %s', curdoc)
try:
    logger.info('session_context %s', curdoc.session_context)
    logger.info('request %s', curdoc.session_context.request)
    logger.info('arguments %s', curdoc.session_context.request.arguments)
except:
    logger.exception('no session')
curdoc.add_root(p)
