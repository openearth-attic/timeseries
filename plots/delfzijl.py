import os
import logging
import datetime

import numpy as np
import pandas as pd
import netCDF4

import bokeh
import bokeh.embed
import bokeh.plotting

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

DATA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "data"
)


logger.debug("reading data")
# [-100000:] subset for performance
s = slice(-200000, None)
ds = netCDF4.Dataset(os.path.join(DATA_DIR, "id1-DELFZL.nc"))
sea_surface_height = ds.variables["sea_surface_height"][0][s]
t_num = ds.variables["time"][s]
logger.debug("converting times to objects ")
t = netCDF4.num2date(t_num, ds.variables["time"].units)
logger.debug("closing dataset")
ds.close()

logger.debug("converting objects")
# convert to pandas
df = pd.DataFrame(
    data={
        "sea_surface_height": sea_surface_height,
        "time": t
    }
)
df = df.set_index("time")

logger.debug("computing means")
df_days = df.resample("1D").agg([np.mean, np.amin, np.amax])
df_months = df.resample("1M").agg([np.mean, np.amin, np.amax])
df_years = df.resample("12M").agg([np.mean, np.amin, np.amax])

for df_i in [df_days, df_months, df_years]:
    df_i.columns = df_i.columns.droplevel(0)
    df_i["sea_surface_height"] = df_i["mean"]

for df_i in [df_days, df_months, df_years, df]:
    df_i["left"] = df_i.index
    df_i["right"] = df_i.index
    df_i.loc[0:-1, "right"] = df_i.index[1:]

df['mean'] = df['sea_surface_height']
df['amin'] = df['sea_surface_height']
df['amax'] = df['sea_surface_height']

# import ipdb
# ipdb.set_trace()

# plot
logger.debug("generating sources")
source = bokeh.models.ColumnDataSource(data=df_years)
source_raw = bokeh.models.ColumnDataSource(data=df)
source_days = bokeh.models.ColumnDataSource(data=df_days)
source_months = bokeh.models.ColumnDataSource(data=df_months)
source_years = bokeh.models.ColumnDataSource(data=df_years)

logger.debug("generating plots")
p = bokeh.plotting.Figure(x_axis_type="datetime", title="Title")
for key in ["sea_surface_height", "mean"]:
    p.line("time", key, source=source)
p.quad(left="left", right="right", bottom="amin", top="amax", source=source, alpha=0.2)
p.xaxis.axis_label = 'time'
p.yaxis.axis_label = 'sea_surface_height'
p.x_range.name = 'time'
p.y_range.name = 'sea_surface_height'

# static
# bokeh.plotting.output_file("delfzijl_line.html", title="delfzijl example")
# df.to_json("delfzijl.json", orient="records")


def change(attr, old, new):
    date_range = (
        datetime.datetime.fromtimestamp(p.x_range.end / 1000)
        -
        datetime.datetime.fromtimestamp(p.x_range.start / 1000)
    )

    months = date_range.total_seconds() / (3600 * 24 * 30)
    if months < 1:
        logger.debug("switching to < 0.1 months ")
        source.data.update(source_raw.data)
    elif months < 10:
        logger.debug("switching to < 1 months ")
        source.data.update(source_days.data)
    elif months < 100:
        logger.debug("switching to < 11 months ")
        source.data.update(source_months.data)
    elif months < 1000:
        logger.debug("switching to < 110 months ")
        source.data.update(source_years.data)
    else:
        logger.debug("switching to geological scale ")
        source.data.update(source_years.data)


def periodic():
    # for live data
    logger.warn("periodic updating data")

# dynamic
p.x_range.on_change("end", change)

script, div = bokeh.embed.components(p)
print(script)
print(div)

curdoc = bokeh.plotting.curdoc()
curdoc.add_root(p)
curdoc.add_periodic_callback(periodic, 10000)
