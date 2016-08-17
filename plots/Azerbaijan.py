import os
import logging
import datetime

import pandas as pd
import numpy as np

import bokeh
import bokeh.embed
import bokeh.plotting

import psycopg2


def get_credentials(credentialfile, dbase=None):
    """Gets the credentials for a database from a file stored in local system
    """
    with open(credentialfile, "r") as f:
        lines = f.readlines()
    credentials = {}
    if dbase is not None:
        credentials["dbname"] = dbase
    for i in lines:
        item = i.split("=")
        if str.strip(item[0]) == "dbname":
            if dbase is None:
                credentials["dbname"] = str.strip(item[1])
        if str.strip(item[0]) == "uname":
            credentials["user"] = str.strip(item[1])
        if str.strip(item[0]) == "pwd":
            credentials["password"] = str.strip(item[1])
        if str.strip(item[0]) == "host":
            credentials["host"] = str.strip(item[1])
    logger.info("credentials set for database %s on host %s" %
                (credentials["dbname"], credentials["host"]))
    logger.info("for user %s" % credentials["user"])
    return credentials


def make_tuple(variable):
    """checks whether input is a tuple, and if not it makes it a tuple.
    Works for list, string"""
    if isinstance(variable, tuple):
        return variable
    elif isinstance(variable, str):
        return tuple([variable])
    elif isinstance(variable, list):
        return tuple(variable)


def gap_filling(df, fill_value=None, method=None, dropna=None):
    if method is not None:
        df = df.fillna(method=method)
    elif fill_value is not None:
        df = df.fillna(fill_value)
    elif dropna is not None:
        df = df.dropna(how="any")
    return df


def averaging(df, locations_x, locations_y):
    """Averages over rows for selection of locations, merges the two
    locationssets"""
    import pandas
    df_x = df.filter(locations_x).mean(axis=1)
    df_y = df.filter(locations_y).mean(axis=1)
    df_merged = pandas.concat([df_x, df_y], axis=1)
    df_merged.columns = ["x_locations", "y_locations"]
    return df_merged


def executesqlfetch(strSql, data, cur):
    """Executes a fetch sql that is given into the function, returns data"""
    try:
        cur.execute(strSql, data)
        p = cur.fetchall()
        logger.info(cur.statusmessage)
        logger.debug(cur.query)
        return p
    except Exception as e:
        logger.info(e)


def periodic():
    # for live data
    logger.warn("periodic updating data")


def get_timeseries(locations, parameters, startdate, enddate):
    """SQL query to get timeseries from database, with credential file.
    Based on sets of locations and parameters, and start and end date."""

    fpath_root = os.path.join(os.path.dirname(os.path.abspath(__file__)))

    fname_credentials = "credentials.txt"
    fpana_credentials = os.path.join(fpath_root, fname_credentials)
    credentials = get_credentials(fpana_credentials)

    conn = psycopg2.connect(**credentials)
    cur = conn.cursor()

    query = """
            select t.datetime, t.scalarvalue, l.id, p.id
            from fews.locations l
            join fews.timeserieskeys tk on tk.locationkey = l.locationkey
            join fews.parameterstable p on p.parameterkey = tk.parameterkey
            join fews.timeseriesvaluesandflags t on t.serieskey = tk.serieskey
            where l.id in %s
            and t.scalarvalue is not null
            and p.id in %s
            and to_char(datetime,'YYYY-MM-DD') BETWEEN %s and %s
            """
    data = (make_tuple(locations), make_tuple(parameters), startdate, enddate)
    product = False
    try:
        df = pd.DataFrame(executesqlfetch(query, data, cur),
                          columns=["timestamp", "data_values",
                                   "location_id", "parameter_id"])
        logging.info("Selected %s rows for %s locations" % (len(df),
                                                            len(locations)))
        product = df.set_index("timestamp")
    except Exception as e:
        logging.info(e.message)

    finally:
        cur.close()
        conn.close()
        return product


def create_df(df, locations, column):
    """Creates a dataframe with locations as columns and values are as
    specified in the column"""
    import pandas as pd
    ts = {}
    for ind, location in enumerate(locations):
        ts[location] = df[df.location_id == location]
        if ind == 0:
            df_out = pd.DataFrame(ts[location][column])
        else:
            df_out = pd.concat([df_out, ts[location][column]],
                               axis=1)
    df_out.columns = locations
    return df_out


def change(attr, old, new):
    ref_date = datetime.datetime(1970, 1, 1)
    t_end = ref_date + datetime.timedelta(seconds=p_tx.x_range.end / 1000)
    t_start = ref_date + datetime.timedelta(seconds=p_tx.x_range.start / 1000)
    x_start = df_merged[t_start: t_end]["x_locations"][0]
    x_end = df_merged[t_start: t_end]["x_locations"][-1]
    y_start = df_merged[t_start: t_end]["y_locations"][0]
    y_end = df_merged[t_start: t_end]["y_locations"][-1]
    quad.data_source.data["top"] = np.array([y_end])
    quad.data_source.data["bottom"] = np.array([y_start])
    quad.data_source.data["right"] = np.array([x_end])
    quad.data_source.data["left"] = np.array([x_start])


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

locations_x = ["M_AZ_001"]
locations_y = ["M_AZ_002", "M_AZ_063"]
locations = tuple(np.unique(np.array(locations_x + locations_y)))
parameter = "P.obs"
startdate = "2009-01-01"
enddate = "2010-01-01"
interp_method = "ffill"

logging.info(locations)

df = get_timeseries(locations, parameter, startdate, enddate)

df["_cumsum"] = df.groupby(df.location_id).cumsum()

# creates a new dataframe with n_loc columns, where n_loc is the number of
# locations and the values in hte columns are the values for each location.
df_cumsum = create_df(df, locations, "_cumsum")

df_filled = gap_filling(df_cumsum, method=interp_method)

# Splitting series into x and y locations is done after interpolation to
# make sure the same amount of timesteps is available for each station.
# This might go wrong in case there is a station that has no data for
# that period. In that case the script will return no data at all.
df_merged = averaging(df_filled, locations_x, locations_y)

df_ts = create_df(df, locations, "data_values")
df_ts_filled = gap_filling(df_ts, method=None)

df_merged = pd.concat([df_merged, df_ts_filled], axis=1)
df_merged.reset_index()

logger.debug("generating sources")
source = bokeh.models.ColumnDataSource(data=df_merged)

x_start = df_merged["x_locations"][0]
x_end = df_merged["x_locations"][-1]
y_start = df_merged["y_locations"][0]
y_end = df_merged["y_locations"][-1]

# plot
logger.debug("generating plots")
Tools = "box_zoom, wheel_zoom, pan, reset"
p = bokeh.plotting.Figure(title="Title", tools=Tools,
                          active_scroll=bokeh.models.tools.WheelZoomTool())
p.line("x_locations", "y_locations", source=source, color="firebrick")
p.xaxis.axis_label = ("Cumulative precipitation\nlocations_x: "
                      + ", ".join(locations_x))
p.yaxis.axis_label = ("Cumulative precipitation\nlocations_y: "
                      + ", ".join(locations_y))
cr = p.circle("x_locations", "y_locations", size=20,
              fill_color=None, hover_fill_color="firebrick",
              hover_alpha=0.3, line_color=None, hover_line_color="white",
              source=source)
quad = p.quad(top=np.array([y_end]), bottom=np.array([y_start]),
              left=np.array([x_start]), right=np.array([x_end]),
              color="navy", alpha=0.1)

p.add_tools(bokeh.models.tools.HoverTool(tooltips=None, renderers=[cr],
                                         mode="hline"))

Tools_x = "box_zoom, wheel_zoom, xpan, reset"
# timeseries plotting x_locations
p_tx = bokeh.plotting.Figure(title="Timeseries x", x_axis_type="datetime",
                             tools=Tools_x,
                             active_scroll=bokeh.models.tools.WheelZoomTool())
p_tx.yaxis.axis_label = "Precipitation mm/d"
crx = []
for location in locations_x:
    p_tx.line("timestamp", location, source=source, legend=location)
    crx.append(p_tx.circle("timestamp", location, size=20,
                           fill_color=None, hover_fill_color="#1f77b4",
                           hover_alpha=0.3, line_color=None,
                           hover_line_color="white", source=source))
p_tx.add_tools(bokeh.models.tools.HoverTool(tooltips=None, renderers=crx,
                                            mode="vline"))

# timeseries plotting x_locations
p_ty = bokeh.plotting.Figure(title="Timeseries y", x_axis_type="datetime",
                             x_range=p_tx.x_range, y_range=p_tx.y_range,
                             tools=Tools_x,
                             active_scroll=bokeh.models.tools.WheelZoomTool())
p_ty.yaxis.axis_label = "Precipitation mm/d"
cry = []
colors = ["#1f77b4", "firebrick"]
for ind, location in enumerate(locations_y):
    p_ty.line("timestamp", location, source=source, color=colors[ind],
              legend=location)
    cry.append(p_ty.circle("timestamp", location, size=20,
                           fill_color=None, hover_fill_color=colors[ind],
                           hover_alpha=0.3, line_color=None,
                           hover_line_color="white", source=source))
p_ty.add_tools(bokeh.models.tools.HoverTool(tooltips=None, renderers=cry,
                                            mode="vline"))

# Grouping plots
grd = bokeh.plotting.gridplot([[p, p_ty, p_tx]])
# static
#bokeh.plotting.output_file("Azerbaijan.html", title="Azerbaijan example")
#bokeh.plotting.show(grd)
#df.to_json("Azerbaijan.json", orient="records")

# dynamic
p_tx.x_range.on_change("end", change)
p_ty.x_range.on_change("end", change)

#script, div = bokeh.embed.components(p)
#print(script)
#print(div)

curdoc = bokeh.plotting.curdoc()
curdoc.add_root(grd)
curdoc.add_periodic_callback(periodic, 10000)
