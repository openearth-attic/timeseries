loadPlot({
    url: 'http://localhost:5007/plot?station=ijmuiden',
    plotDiv: '#plot-div',
    plotScript: '#plot-script'
});
loadPlot({
    url: '/static/ijmuiden.html',
    plotDiv: '#plot-static-div',
    plotScript: '#plot-static-script'
});
loadPlot({
    // get the div and script from the wps server
    div: '<h2>plot for ijmuiden</h2>',
    script: '<script>console.log("wps script loaded");</script>',
    plotDiv: '#plot-wps-div',
    plotScript: '#plot-wps-script'
});
