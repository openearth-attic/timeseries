# timeseries
Time series demo.

# Prepare your computer
- install anaconda
- install bokeh
- download data (go to data directory and in a bash shell execute `get.sh`)

# Static example
- go to the plot directory
- call `bokeh html delfzijl.py`


# Supported setups


- static plot with dynamic data
website -> wps request -> prepare data -> wps server calls `bokeh static` -> return div + script -> embed in html

`loadPlot({
    // get the div and script from the wps server
    div: '<h2>plot for ijmuiden</h2>',
    script: '<script>console.log("wps script loaded");</script>',
    plotDiv: '#plot-wps-div',
    plotScript: '#plot-wps-script'
});
`

- static plot with static data
prepare data -> generate `bokeh html` per site -> upload to webserver


`loadPlot({
    // create plots for each station
    url: '/static/ijmuiden.html',
    plotDiv: '#plot-static-div',
    plotScript: '#plot-static-script'
});
`

- dynamic plot with dynamic data
website -> bokeh serve (with arguments for data connection) -> interactive plot (bound to live data, with possible LOD's)

`loadPlot({
    // plot for station is created on request
    url: 'http://localhost:5007/plot?station=ijmuiden',
    plotDiv: '#plot-div',
    plotScript: '#plot-script'
});
`

# Supported formats

Input
- NetCDF [station](http://cfconventions.org/cf-conventions/cf-conventions.html#_single_time_series_including_deviations_from_a_nominal_fixed_spatial_location)
- [FEWS PI](https://publicwiki.deltares.nl/display/FEWSDOC/Delft-Fews+Published+Interface+timeseries+Format+(PI)+Import) format
- [Sensor Observation Services](http://www.opengeospatial.org/standards/sos)
