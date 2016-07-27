import os
import logging
# import datetime

import pandas as pd

import bokeh
import bokeh.embed
import bokeh.plotting

import psycopg2


def get_credentials(credentialfile, logger, dbase=None):
    """Gets the credentials for a database from a file stored in local system
    """
    with open(credentialfile, 'r') as f:
        lines = f.readlines()
    credentials = {}
    if dbase is not None:
        credentials['dbname'] = dbase
    for i in lines:
        item = i.split('=')
        if str.strip(item[0]) == 'dbname':
            if dbase is None:
                credentials['dbname'] = str.strip(item[1])
        if str.strip(item[0]) == 'uname':
            credentials['user'] = str.strip(item[1])
        if str.strip(item[0]) == 'pwd':
            credentials['password'] = str.strip(item[1])
        if str.strip(item[0]) == 'host':
            credentials['host'] = str.strip(item[1])
    logger.info('credentials set for database %s on host %s' %
                (credentials['dbname'], credentials['host']))
    logger.info('for user %s' % credentials['user'])
    return credentials


def gap_filling(df, fill_value=None, method=None):
    if method is not None:
        df = df.fillna(method=method)
    elif fill_value is not None:
        df = df.fillna(fill_value)
    else:
        df = df.dropna(how='any')
    return df


def averaging(df, locations_x, locations_y):
    """Averages over rows for selection of locations, merges the two
    locationssets"""
    import pandas
    df_x = df.filter(locations_x).mean(axis=1)
    df_y = df.filter(locations_y).mean(axis=1)
    df_merged = pandas.concat([df_x, df_y], axis=1)
    df_merged.columns = ['x_locations', 'y_locations']
    return df_merged


def check_doubles(locations_x, locations_y, logger):
    locations_short = min(locations_x, locations_y, key=len)
    locations_long = max(locations_y, locations_x, key=len)
    # Important that the names are switched around here. in case of equal
    # length the first is picked as max/min, therefore the total location_set
    # is still correct when the lengths are equal.
    if any(location in locations_long for location in locations_short):
        logger.info("Same location in x and y locations")

        double_list = [location for location in locations_short
                       if location in locations_long]
        locations_stripped = [location for location in locations_short
                              if location not in double_list]
        locations_stripped = locations_stripped + locations_long
        return locations_stripped
    else:
        return locations_short + locations_long


def executesqlfetch(strSql, data, cur, logger):
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


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

fpath_root = os.path.join(os.path.dirname(os.path.abspath(__file__)))
fname_credentials = 'credentials.txt'
fpana_credentials = os.path.join(fpath_root, fname_credentials)
credentials = get_credentials(fpana_credentials, logger)

locations_x = ['M_AZ_001']
locations_y = ['M_AZ_002']
locations = check_doubles(locations_x, locations_y, logger)
parameter = 'P.obs'
startdate = '2009-01-01'
enddate = '2010-01-01'
interp_method = None


logger.debug("reading data")
conn = psycopg2.connect(**credentials)
cur = conn.cursor()

query = """
        select l.id, t.scalarvalue, t.datetime, p.name
        from fews.locations l
        join fews.timeserieskeys tk on tk.locationkey = l.locationkey
        join fews.parameterstable p on p.parameterkey = tk.parameterkey
        join fews.timeseriesvaluesandflags t on t.serieskey = tk.serieskey
        where l.id in %s
        and t.scalarvalue is not null
        and p.id = %s
        and to_char(datetime,'YYYY-MM-DD') BETWEEN %s and %s
        """
data = (tuple(locations), parameter, startdate, enddate)

ts = pd.DataFrame(executesqlfetch(query, data, cur, logger),
                  columns=['location_id', parameter,
                           'timestamp', 'parametername'])
logger.info("Selected %s rows for %s locations" % (len(ts),
                                                   len(locations)))
ts = ts.set_index('timestamp')
timeseries = {}
for ind, location in enumerate(locations):
    timeseries[location] = ts[ts.location_id == location]
    new_column = timeseries[location][parameter].cumsum()
    timeseries[location]['_cumsum'] = new_column
    if ind == 0:
        df = pd.DataFrame(timeseries[location]['_cumsum'])
    else:
        df = pd.concat([df, timeseries[location]['_cumsum']],
                       axis=1)
df.columns = locations
df = gap_filling(df, method=interp_method)
# Splitting series into x and y locations this is done after
# interpolation to make sure the same amount of timesteps is available
# for each station.
# This might go wrong in case there is a station that has no data for
# that period. In that case the script will return no data at all.
df_merged = averaging(df, locations_x, locations_y)

cur.close()
conn.close()

logger.debug("generating sources")
source = bokeh.models.ColumnDataSource(data=df_merged)

# plot
logger.debug("generating plots")
p = bokeh.plotting.Figure(title="Title")
p.line("x_locations", "y_locations", source=source)
p.xaxis.axis_label = 'locations_x'
p.yaxis.axis_label = 'locations_y'

# static
# bokeh.plotting.output_file("delfzijl_line.html", title="delfzijl example")
# df.to_json("delfzijl.json", orient="records")

# dynamic
#p.x_range.on_change("end", change)

#script, div = bokeh.embed.components(p)
#print(script)
#print(div)

curdoc = bokeh.plotting.curdoc()
curdoc.add_root(p)
curdoc.add_periodic_callback(periodic, 10000)
